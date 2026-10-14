"""Render stored config documents into dnsmasq config file syntax."""

from collections.abc import Iterable

from app.models import (
    AddressRecord,
    CnameRecord,
    ConfigKind,
    DhcpRangeCreate,
    HostRecord,
)

MANAGED_MARKER = "# Managed by dnsmasq-webmin - manual changes will be overwritten."


def render_dns_entry(entry: HostRecord | AddressRecord | CnameRecord) -> str:
    match entry:
        case HostRecord():
            # dnsmasq detects the address family per field, so missing ones are simply omitted
            parts = [*entry.names, *(str(ip) for ip in (entry.ipv4, entry.ipv6) if ip is not None)]
            if entry.ttl is not None:
                parts.append(str(entry.ttl))
            return "host-record=" + ",".join(parts)
        case AddressRecord():
            return "address=/" + "/".join(entry.domains) + f"/{entry.ip}"
        case CnameRecord():
            parts = [*entry.aliases, entry.target]
            if entry.ttl is not None:
                parts.append(str(entry.ttl))
            return "cname=" + ",".join(parts)
    raise TypeError(f"unsupported DNS entry: {type(entry).__name__}")


def render_dhcp_range(entry: DhcpRangeCreate) -> str:
    parts = [f"tag:{t}" for t in entry.match_tags]
    if entry.set_tag:
        parts.append(f"set:{entry.set_tag}")
    parts += [str(entry.start), str(entry.end)]
    if entry.netmask is not None:
        parts.append(str(entry.netmask))
    if entry.prefix_length is not None:
        parts.append(str(entry.prefix_length))
    if entry.lease_time:
        parts.append(entry.lease_time)
    return "dhcp-range=" + ",".join(parts)


def render_file(
    name: str,
    kind: ConfigKind,
    description: str | None,
    entries: Iterable[HostRecord | AddressRecord | CnameRecord | DhcpRangeCreate],
) -> str:
    lines = [MANAGED_MARKER, f"# {kind.value} config: {name}"]
    if description:
        lines.append(f"# {description}")
    lines.append("")
    for entry in entries:
        if entry.comment:
            lines.append(f"# {entry.comment}")
        if kind is ConfigKind.dns:
            lines.append(render_dns_entry(entry))
        else:
            lines.append(render_dhcp_range(entry))
    return "\n".join(lines) + "\n"
