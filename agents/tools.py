"""Tool registries per specialist agent."""

from __future__ import annotations

from tools.reachability import check_reachability
from tools.system import get_system_info
from tools.routing import get_routing_full, get_router_config
from tools.interface import get_interface_stats
from tools.traffic import get_interface_traffic, get_traffic_summary, get_top_talkers, get_queue_stats, get_traffic_all
from tools.dhcp import get_dhcp_leases, get_router_leases, search_device, audit_dhcp
from tools.log import get_router_log
from tools.config_read import run_command, run_command_all
from tools.config_backup import backup_router_config, list_backups, diff_config
from tools.security import audit_security
from tools.diagnostic import run_diagnostic
from tools.report import list_reports, get_report, get_report_section, get_report_toc
from tools.utility import list_routers, get_current_time

MONITOR_TOOLS = [
    list_routers,
    check_reachability,
    get_system_info,
    get_routing_full,
    get_interface_stats,
    get_interface_traffic,
    get_traffic_summary,
    get_top_talkers,
    get_queue_stats,
    get_traffic_all,
    get_dhcp_leases,
    get_router_leases,
    audit_dhcp,
    get_router_log,
    run_command_all,
    list_reports,
    get_report,
    get_report_section,
    get_report_toc,
    get_current_time,
]

DIAGNOSE_TOOLS = [
    list_routers,
    check_reachability,
    run_diagnostic,
    get_router_log,
    search_device,
    get_dhcp_leases,
    get_router_leases,
    get_routing_full,
    run_command,
    get_system_info,
    get_current_time,
]

CONFIG_TOOLS = [
    list_routers,
    run_command,
    run_command_all,
    get_router_config,
    backup_router_config,
    list_backups,
    diff_config,
    list_reports,
    get_report,
    get_current_time,
]

SECURITY_TOOLS = [
    list_routers,
    audit_security,
    get_router_log,
    run_command,
    run_command_all,
    get_current_time,
]

# Flat map: tool name → callable (deduped by name)
TOOL_MAP: dict[str, object] = {}
for _t in MONITOR_TOOLS + DIAGNOSE_TOOLS + CONFIG_TOOLS + SECURITY_TOOLS:
    TOOL_MAP.setdefault(_t.name, _t)
