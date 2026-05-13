"""Web tools — fetch content from URLs for agent reference lookups."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urlparse

import requests
from langchain_core.tools import tool


class _TextExtractor(HTMLParser):
    """Minimal HTML-to-text extractor using stdlib only."""

    _SKIP_TAGS = {"script", "style", "head", "meta", "link", "noscript", "nav", "footer"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip: int = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip == 0:
            text = data.strip()
            if text:
                self._parts.append(text)

    def get_text(self) -> str:
        return "\n".join(self._parts)


def _strip_html(html: str) -> str:
    extractor = _TextExtractor()
    try:
        extractor.feed(html)
    except Exception:
        pass
    return extractor.get_text()


@tool
def fetch_url(url: str, max_chars: int = 6000) -> str:
    """
    Ambil konten teks dari URL — berguna untuk membaca file GitHub,
    dokumentasi vendor, atau halaman web sebagai referensi saat membuat skill.

    Untuk file di GitHub, gunakan URL raw agar langsung dapat plain text:
      https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}

    Args:
        url:       URL yang ingin diambil (hanya http/https).
        max_chars: Batas karakter konten yang dikembalikan (default 6000,
                   maksimum 20000). Naikkan jika referensi perlu dibaca lebih lengkap.

    Returns:
        Konten teks halaman. Jika HTML, tag otomatis dihapus.
        Jika gagal, kembalikan pesan error.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"Error: skema '{parsed.scheme}' tidak didukung. Gunakan http atau https."

    max_chars = min(max_chars, 20_000)

    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "NetOpsAI/1.0"},
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return f"Error: timeout saat mengambil {url} (> 15 detik)."
    except requests.exceptions.HTTPError as e:
        return f"Error HTTP {e.response.status_code}: {url}"
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

    content_type = resp.headers.get("content-type", "")
    text = resp.text

    if "text/html" in content_type:
        text = _strip_html(text)

    text = text.strip()
    if not text:
        return "(konten kosong)"

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[... terpotong — total {len(resp.text):,} karakter. Naikkan max_chars jika perlu.]"

    return text
