"""All tools imported and indexed in TOOL_MAP. Per-agent lists are derived from AgentLoader."""

from __future__ import annotations

from tools.reachability import check_reachability, check_ssh_access
from tools.system import get_system_info
from tools.routing import get_routing_full, get_router_config, get_bgp_sessions, get_ospf_neighbors
from tools.interface import get_interface_stats
from tools.traffic import get_interface_traffic, get_traffic_summary, get_top_talkers, get_queue_stats, get_traffic_all, get_top_interfaces_all
from tools.dhcp import get_dhcp_leases, get_router_leases, search_device, audit_dhcp
from tools.log import get_router_log
from tools.config_read import run_command, run_command_all
from tools.config_write import run_command_write
from tools.config_backup import backup_router_config, list_backups, diff_config
from tools.security import audit_security
from tools.diagnostic import run_diagnostic
from tools.report import list_reports, get_report, get_report_section, get_report_toc
from tools.utility import list_routers, get_current_time
from tools.document import list_templates, read_template, write_document, create_template, write_skill
from tools.web import fetch_url
from tools.netbox import (
    get_netbox_devices, get_netbox_device_interfaces, get_netbox_device_ips,
    get_netbox_drift_report, add_netbox_ip_address, update_netbox_interface,
    populate_netbox_from_router,
    get_netbox_vlan_groups, get_next_available_vlan, create_netbox_vlan_interface,
    get_netbox_vlan_group_detail,
)

_ALL_TOOLS = [
    list_routers, get_current_time,
    check_reachability, check_ssh_access,
    get_system_info,
    get_routing_full, get_router_config, get_bgp_sessions, get_ospf_neighbors,
    get_interface_stats,
    get_interface_traffic, get_traffic_summary, get_top_talkers, get_queue_stats, get_traffic_all, get_top_interfaces_all,
    get_dhcp_leases, get_router_leases, search_device, audit_dhcp,
    get_router_log,
    run_command, run_command_all, run_command_write,
    backup_router_config, list_backups, diff_config,
    audit_security,
    run_diagnostic,
    list_reports, get_report, get_report_section, get_report_toc,
    list_templates, read_template, write_document, create_template, write_skill,
    fetch_url,
    get_netbox_devices, get_netbox_device_interfaces, get_netbox_device_ips,
    get_netbox_drift_report, add_netbox_ip_address, update_netbox_interface,
    populate_netbox_from_router,
    get_netbox_vlan_groups, get_next_available_vlan, create_netbox_vlan_interface,
    get_netbox_vlan_group_detail,
]

# Flat map: tool name → callable
TOOL_MAP: dict[str, object] = {t.name: t for t in _ALL_TOOLS}
