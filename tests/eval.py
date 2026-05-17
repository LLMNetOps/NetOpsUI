#!/usr/bin/env python3
"""
Evaluator script — jalankan scenario YAML dan verifikasi perilaku agent.

Usage:
    python tests/eval.py                        # semua scenarios, mock mode
    python tests/eval.py bgp-ospf-report        # satu scenario by ID
    python tests/eval.py --lab                  # pakai tool asli (butuh koneksi router)
    python tests/eval.py --list                 # list scenario tersedia
    python tests/eval.py -v                     # verbose (tampilkan semua events)
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

# ── Setup path ────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

SCENARIOS_DIR = Path(__file__).parent / "scenarios"

# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    description: str
    passed: bool
    reason: str = ""


@dataclass
class ScenarioResult:
    scenario_id: str
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)
    events: list[tuple[str, str]] = field(default_factory=list)
    called_agents: list[str] = field(default_factory=list)
    called_tools: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    error: str = ""

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)


# ── Mock patching ─────────────────────────────────────────────────────────────

def _make_invoke_mock(fn: object) -> object:
    """Buat objek dengan method .invoke() yang memanggil fn dengan args dict."""
    class MockTool:
        def invoke(self, input: Any, **kwargs: Any) -> str:
            if isinstance(input, dict):
                return fn(**input)  # type: ignore[operator]
            return fn(input)  # type: ignore[operator]
    return MockTool()


def _patch_tool_map(fixture_set: dict[str, object]) -> dict[str, object]:
    """Return patched TOOL_MAP menggunakan fixture functions."""
    from agents.tools import TOOL_MAP
    patched: dict[str, object] = {}
    for name, tool_obj in TOOL_MAP.items():
        if name in fixture_set:
            mock = _make_invoke_mock(fixture_set[name])
            # Preserve name dan description dari tool asli agar bind_tools tetap bekerja
            mock.name = getattr(tool_obj, "name", name)  # type: ignore[attr-defined]
            mock.description = getattr(tool_obj, "description", "")  # type: ignore[attr-defined]
            mock.args_schema = getattr(tool_obj, "args_schema", None)  # type: ignore[attr-defined]
            patched[name] = mock
        else:
            patched[name] = tool_obj
    return patched


# ── Scenario loading ──────────────────────────────────────────────────────────

def load_scenario(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_scenarios() -> list[Path]:
    return sorted(SCENARIOS_DIR.glob("*.yaml"))


# ── Acceptance criteria evaluation ───────────────────────────────────────────

def _eval_criteria(
    criteria: list[dict],
    result: ScenarioResult,
) -> list[CheckResult]:
    checks: list[CheckResult] = []

    for c in criteria:
        ctype = c["type"]
        desc = c.get("description", ctype)

        if ctype == "tool_called":
            tool = c["tool"]
            passed = tool in result.called_tools
            checks.append(CheckResult(
                description=desc,
                passed=passed,
                reason=f"tool '{tool}' {'dipanggil' if passed else 'TIDAK dipanggil'}",
            ))

        elif ctype == "agent_used":
            agent = c["agent"]
            passed = agent in result.called_agents
            checks.append(CheckResult(
                description=desc,
                passed=passed,
                reason=f"agent '{agent}' {'digunakan' if passed else 'TIDAK digunakan'}",
            ))

        elif ctype == "file_created":
            target_dir = ROOT / c["dir"]
            files = list(target_dir.glob("*")) if target_dir.exists() else []
            passed = len(files) > 0
            checks.append(CheckResult(
                description=desc,
                passed=passed,
                reason=f"{'ditemukan' if passed else 'TIDAK ada'} file di {c['dir']}",
            ))

        elif ctype == "output_contains":
            text = c["text"]
            full_output = " ".join(content for _, content in result.events if _ == "ai")
            passed = text.lower() in full_output.lower()
            checks.append(CheckResult(
                description=desc,
                passed=passed,
                reason=f"'{text}' {'ditemukan' if passed else 'TIDAK ditemukan'} di output",
            ))

        elif ctype == "output_not_contains":
            text = c["text"]
            full_output = " ".join(content for _, content in result.events if _ == "ai")
            passed = text.lower() not in full_output.lower()
            checks.append(CheckResult(
                description=desc,
                passed=passed,
                reason=f"'{text}' {'tidak ada (ok)' if passed else 'DITEMUKAN (tidak boleh)'} di output",
            ))

        elif ctype == "output_contains_any":
            texts = c["texts"]
            full_output = " ".join(content for _, content in result.events if _ == "ai")
            found = next((t for t in texts if t.lower() in full_output.lower()), None)
            passed = found is not None
            checks.append(CheckResult(
                description=desc,
                passed=passed,
                reason=(
                    f"'{found}' ditemukan di output" if passed
                    else f"tidak ada dari {texts} yang ditemukan di output"
                ),
            ))

        elif ctype == "trace_contains_any":
            # Cek seluruh event trace (termasuk tool_result), bukan hanya AI output
            texts = c["texts"]
            full_trace = " ".join(content for _, content in result.events)
            found = next((t for t in texts if t.lower() in full_trace.lower()), None)
            passed = found is not None
            checks.append(CheckResult(
                description=desc,
                passed=passed,
                reason=(
                    f"'{found}' ditemukan di trace" if passed
                    else f"tidak ada dari {texts} yang ditemukan di trace eksekusi"
                ),
            ))

        elif ctype == "no_error":
            errors = [content for etype, content in result.events if etype == "error"]
            passed = len(errors) == 0
            checks.append(CheckResult(
                description=desc,
                passed=passed,
                reason="tidak ada error" if passed else f"error: {errors[0][:100]}",
            ))

        else:
            checks.append(CheckResult(
                description=desc,
                passed=False,
                reason=f"tipe criteria tidak dikenal: '{ctype}'",
            ))

    return checks


# ── Scenario runner ───────────────────────────────────────────────────────────

def run_scenario(scenario: dict, mock_mode: bool = True, verbose: bool = False) -> ScenarioResult:
    from agent import create_agent, reset_agent, stream_agent_response

    scenario_id = scenario["id"]
    result = ScenarioResult(scenario_id=scenario_id, passed=False)

    # Fixture setup untuk mock mode
    patched_tool_map: dict | None = None
    if mock_mode:
        from tests.mocks.fixtures import get_fixture_set
        fixture_set_name = scenario.get("fixture_set", "default")
        fixtures = get_fixture_set(fixture_set_name)
        patched_tool_map = _patch_tool_map(fixtures)

    thread_id = f"eval-{scenario_id}-{uuid.uuid4().hex[:8]}"

    def _stream() -> None:
        graph, config = create_agent(thread_id)
        for event_type, content in stream_agent_response(graph, config, scenario["input"]):
            result.events.append((event_type, content))

            if event_type == "routing":
                # "[supervisor] → monitor_agent" atau "[supervisor] routing to config_agent"
                for agent_name in [
                    "monitor_agent", "diagnose_agent", "config_agent",
                    "security_agent", "document_agent", "validasi_agent",
                    "netbox_agent",
                ]:
                    if agent_name in content and agent_name not in result.called_agents:
                        result.called_agents.append(agent_name)

            elif event_type == "tool_call":
                # "[monitor_agent] check_reachability({...})"
                for tool_name in _extract_tool_names(content):
                    if tool_name not in result.called_tools:
                        result.called_tools.append(tool_name)

            if verbose:
                _print_event(event_type, content)

    t0 = time.monotonic()
    try:
        if mock_mode and patched_tool_map is not None:
            with patch("agents.nodes.TOOL_MAP", patched_tool_map):
                _stream()
        else:
            _stream()
    except Exception as exc:
        result.events.append(("error", str(exc)))
        result.error = str(exc)

    result.duration_s = time.monotonic() - t0
    result.checks = _eval_criteria(scenario.get("acceptance_criteria", []), result)
    result.passed = all(c.passed for c in result.checks)
    return result


def _extract_tool_names(content: str) -> list[str]:
    """Ekstrak nama tool dari event content seperti '[agent] tool_name({...})'."""
    known_tools = [
        "list_routers", "get_current_time", "check_reachability", "check_ssh_access",
        "get_system_info", "get_routing_full", "get_router_config", "get_bgp_sessions",
        "get_ospf_neighbors", "get_interface_stats", "get_interface_traffic",
        "get_traffic_summary", "get_top_talkers", "get_queue_stats", "get_traffic_all",
        "get_dhcp_leases", "get_router_leases", "search_device", "audit_dhcp",
        "get_router_log", "run_command", "run_command_all", "run_command_write",
        "backup_router_config", "list_backups", "diff_config", "audit_security",
        "run_diagnostic", "list_reports", "get_report", "get_report_section",
        "get_report_toc", "list_templates", "read_template", "write_document",
        "create_template", "write_skill", "fetch_url",
    ]
    return [t for t in known_tools if t in content]


# ── Output formatting ─────────────────────────────────────────────────────────

RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
DIM = "\033[2m"


def _print_event(event_type: str, content: str) -> None:
    color = {
        "routing": CYAN,
        "tool_call": YELLOW,
        "tool_result": DIM,
        "ai": GREEN,
        "error": RED,
        "approval_required": YELLOW,
    }.get(event_type, RESET)
    short = content[:120] + "…" if len(content) > 120 else content
    print(f"  {color}[{event_type}]{RESET} {short}")


def _print_result(result: ScenarioResult, verbose: bool = False) -> None:
    status = f"{GREEN}PASS{RESET}" if result.passed else f"{RED}FAIL{RESET}"
    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}{result.scenario_id}{RESET}  →  {status}  ({result.duration_s:.1f}s)")
    print(f"  Agents: {result.called_agents or ['—']}")
    print(f"  Tools:  {result.called_tools or ['—']}")
    print(f"  Checks: {result.pass_count} pass / {result.fail_count} fail")

    for check in result.checks:
        icon = f"{GREEN}✓{RESET}" if check.passed else f"{RED}✗{RESET}"
        print(f"    {icon} {check.description}")
        if not check.passed or verbose:
            print(f"       {DIM}{check.reason}{RESET}")

    if result.error:
        print(f"  {RED}Error: {result.error[:200]}{RESET}")


def _print_summary(results: list[ScenarioResult]) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    total_time = sum(r.duration_s for r in results)

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}SUMMARY{RESET}  {passed}/{total} passed  ({total_time:.1f}s total)")
    if failed:
        print(f"{RED}FAILED:{RESET}")
        for r in results:
            if not r.passed:
                fails = [c.description for c in r.checks if not c.passed]
                print(f"  ✗ {r.scenario_id}: {', '.join(fails)}")
    else:
        print(f"{GREEN}Semua scenario berhasil.{RESET}")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="NetOps agent evaluator")
    parser.add_argument("scenario_id", nargs="?", help="ID scenario (opsional, default: semua)")
    parser.add_argument("--lab", action="store_true", help="Pakai tool asli (butuh koneksi router)")
    parser.add_argument("--list", action="store_true", help="List scenario tersedia")
    parser.add_argument("-v", "--verbose", action="store_true", help="Tampilkan semua events")
    args = parser.parse_args()

    if args.list:
        print("Scenarios tersedia:")
        for path in list_scenarios():
            s = load_scenario(path)
            print(f"  {s['id']:30s}  {s.get('description', '')}")
        return

    mock_mode = not args.lab

    # Pilih scenario
    if args.scenario_id:
        candidates = [p for p in list_scenarios() if p.stem == args.scenario_id]
        if not candidates:
            print(f"Scenario '{args.scenario_id}' tidak ditemukan.", file=sys.stderr)
            sys.exit(1)
        paths = candidates
    else:
        paths = list_scenarios()

    if not paths:
        print("Tidak ada scenario ditemukan di tests/scenarios/", file=sys.stderr)
        sys.exit(1)

    mode_label = "MOCK" if mock_mode else "LAB"
    print(f"\n{BOLD}NetOps Evaluator — {mode_label} mode{RESET}")
    print(f"Scenario: {len(paths)}  |  Ollama: menghubungi model untuk routing & reasoning\n")

    results: list[ScenarioResult] = []
    for path in paths:
        scenario = load_scenario(path)
        print(f"▶ {scenario['id']} — {scenario.get('description', '')}")

        if args.verbose:
            print(f"  Input: \"{scenario['input']}\"")

        result = run_scenario(scenario, mock_mode=mock_mode, verbose=args.verbose)
        _print_result(result, verbose=args.verbose)
        results.append(result)

    _print_summary(results)

    # Exit code: 0 = semua pass, 1 = ada yang fail
    sys.exit(0 if all(r.passed for r in results) else 1)


if __name__ == "__main__":
    main()
