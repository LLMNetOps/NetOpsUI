"""LLM provider support: connection test and targeted edits of a backend's
config.yaml `model:` block.

config.yaml files are hand-maintained (comments, ordering, unrelated settings),
so they are never re-serialized. Instead single lines inside the target block
are edited in place, and the result is re-parsed and compared with the original
so that *only* the intended keys differ. Any mismatch aborts before writing.
"""
from __future__ import annotations

import copy
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

DELETE = object()  # sentinel: remove the key


class ConfigEditError(Exception):
    pass


# ── connection test ──────────────────────────────────────────────────────────

def check_url(url: str) -> str:
    p = urllib.parse.urlparse(url.strip())
    if p.scheme not in ("http", "https") or not p.netloc:
        raise ValueError("Base URL harus diawali http:// atau https://")
    return url.strip().rstrip("/")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # never follow: a redirect could carry the key elsewhere
        return None


def list_models(base_url: str, api_key: str | None, timeout: float = 10.0) -> dict:
    """GET {base_url}/models (OpenAI-compatible; Ollama's /v1 too). Never raises:
    returns {ok, models, latency_ms} or {ok: False, error}. The key is never
    echoed back, including in error text."""
    url = check_url(base_url) + "/models"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    opener = urllib.request.build_opener(_NoRedirect)
    t0 = time.monotonic()
    try:
        with opener.open(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
            raw = r.read(2_000_000)
    except urllib.error.HTTPError as e:
        hint = {401: "API key ditolak (401)", 403: "Akses ditolak (403)", 404: "Endpoint /models tidak ditemukan (404): cek Base URL, biasanya berakhiran /v1"}
        return {"ok": False, "error": hint.get(e.code, f"HTTP {e.code}")}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"Tidak terjangkau: {e.reason}"}
    except Exception as e:  # timeouts, resets
        return {"ok": False, "error": f"Gagal: {type(e).__name__}"}
    try:
        data = json.loads(raw)
    except ValueError:
        return {"ok": False, "error": "Respons bukan JSON: bukan endpoint OpenAI-compatible?"}
    items = data.get("data") if isinstance(data, dict) else None
    if items is None and isinstance(data, dict):
        items = data.get("models")  # Ollama native shape
    ids = sorted({str(m.get("id") or m.get("name")) for m in (items or []) if isinstance(m, dict) and (m.get("id") or m.get("name"))})
    return {"ok": True, "models": ids, "latency_ms": round((time.monotonic() - t0) * 1000)}


# ── targeted config.yaml edits ───────────────────────────────────────────────

def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _content(line: str) -> bool:
    s = line.strip()
    return bool(s) and not s.startswith("#")


def _key_re(key: str) -> re.Pattern:
    return re.compile(rf"^{re.escape(key)}\s*:(\s|$)")


def _locate(lines: list[str], path: list[str]):
    """Block-style YAML only. Returns (lo, hi, child_indent) of the mapping under
    `path`: lines[lo:hi] are its lines."""
    lo, hi = 0, len(lines)
    child = 0
    for key in path:
        child = next((_indent(l) for l in lines[lo:hi] if _content(l)), None)
        if child is None:
            return None
        idx = next((i for i in range(lo, hi)
                    if _content(lines[i]) and _indent(lines[i]) == child and _key_re(key).match(lines[i].strip())), None)
        if idx is None:
            return None
        end = next((j for j in range(idx + 1, hi) if _content(lines[j]) and _indent(lines[j]) <= child), hi)
        lo, hi = idx + 1, end
    ci = next((_indent(l) for l in lines[lo:hi] if _content(l)), None)
    return None if ci is None else (lo, hi, ci)


def _scalar(v) -> str:
    out = yaml.safe_dump(v, width=10**6, allow_unicode=True).strip()
    return out[:-4].strip() if out.endswith("\n...") else out


def _edit_block(lines: list[str], path: list[str], updates: dict) -> None:
    loc = _locate(lines, path)
    if loc is None:
        raise ConfigEditError(f"Blok `{'.'.join(path)}` tidak ditemukan atau bukan format block-style YAML")
    lo, hi, ci = loc
    for key, val in updates.items():
        found = next((i for i in range(lo, hi)
                      if _content(lines[i]) and _indent(lines[i]) == ci and _key_re(key).match(lines[i].strip())), None)
        if val is DELETE:
            if found is not None:
                del lines[found]
                hi -= 1
            continue
        if found is not None:
            m = re.match(r"^(\s*" + re.escape(key) + r"\s*:)\s*(.*?)(\s+#.*)?$", lines[found])
            lines[found] = f"{m.group(1)} {_scalar(val)}{m.group(3) or ''}"
        else:
            last = max((i for i in range(lo, hi) if _content(lines[i])), default=lo - 1)
            lines.insert(last + 1, f"{' ' * ci}{key}: {_scalar(val)}")
            hi += 1


def _expected(data: dict, path: list[str], updates: dict) -> None:
    node = data
    for k in path:
        node = node[k]
    for key, val in updates.items():
        if val is DELETE:
            node.pop(key, None)
        else:
            node[key] = val


def edit_config(text: str, edits: list[tuple[list[str], dict]]) -> str:
    """Apply (path, updates) edits and prove that nothing else changed."""
    original = yaml.safe_load(text)
    lines = text.split("\n")
    expected = copy.deepcopy(original)
    for path, updates in edits:
        _edit_block(lines, path, updates)
        _expected(expected, path, updates)
    new_text = "\n".join(lines)
    if yaml.safe_load(new_text) != expected:
        raise ConfigEditError("Verifikasi gagal: hasil edit berbeda dari yang diharapkan. Config tidak ditulis.")
    return new_text


# ── reading the current LLM setup ────────────────────────────────────────────

def _key_info(v) -> dict:
    if not v:
        return {"key_source": "none", "key_ref": None}
    s = str(v)
    return {"key_source": "env", "key_ref": s} if re.fullmatch(r"\$\{[^}]+\}", s) else {"key_source": "literal", "key_ref": None}


def describe(backend: str, text: str | None) -> dict:
    if text is None:
        return {"exists": False}
    data = yaml.safe_load(text) or {}
    m = data.get("model") or {}
    if backend == "netops":
        out = {"exists": True, "model": m.get("name"), "base_url": m.get("base_url"), "provider": None, **_key_info(m.get("api_key"))}
        out["delegation"] = [
            {"agent": name, "model": (a.get("model") or {}).get("name"), "base_url": (a.get("model") or {}).get("base_url"),
             **_key_info((a.get("model") or {}).get("api_key"))}
            for name, a in ((data.get("delegation") or {}).get("agents") or {}).items() if isinstance(a, dict) and a.get("model")]
        return out
    return {"exists": True, "model": m.get("default"), "base_url": m.get("base_url"), "provider": m.get("provider"),
            **_key_info(m.get("api_key")), "delegation": []}


def plan_apply(backend: str, text: str, provider: dict, model: str, include_delegation: bool) -> str:
    """Config text with `provider` + `model` applied to the backend's model block(s).
    A provider without a key REMOVES any existing api_key, so the previous
    provider's key is never sent to the new provider's URL."""
    key = provider.get("api_key")
    key_edit = key if key else DELETE
    if backend == "netops":
        edits = [(["model"], {"name": model, "base_url": provider["base_url"], "api_key": key_edit})]
        if include_delegation:
            data = yaml.safe_load(text) or {}
            for name, a in ((data.get("delegation") or {}).get("agents") or {}).items():
                if isinstance(a, dict) and a.get("model"):
                    edits.append((["delegation", "agents", name, "model"],
                                  {"name": model, "base_url": provider["base_url"], "api_key": key_edit}))
    else:
        edits = [(["model"], {"default": model, "provider": "custom", "base_url": provider["base_url"], "api_key": key_edit})]
    return edit_config(text, edits)
