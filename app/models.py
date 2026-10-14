"""Pydantic data models.

All string fields that end up in a dnsmasq config line are restricted by patterns,
so no user input can inject separators (``,`` ``/``) or additional lines.
"""

from enum import StrEnum
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, StringConstraints, model_validator

# --------------------------------------------------------------------------- #
# Reusable constrained types
# --------------------------------------------------------------------------- #

Hostname = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        max_length=253,
        pattern=r"^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.?$",
    ),
    Field(examples=["nas.home.lan"]),
]

ConfigName = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"),
    Field(description="Name of the config file (used in the file name).", examples=["home-lan"]),
]

_SingleLine = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200, pattern=r"^[^\r\n]*$")]

# Description/examples live on the optional type itself, so they end up on the
# property in the OpenAPI schema instead of inside the anyOf branch.
Comment = Annotated[
    _SingleLine | None,
    Field(description="Rendered as a '#' comment line above the entry.", examples=["NAS in the basement"]),
]

FileDescription = Annotated[
    _SingleLine | None,
    Field(description="Rendered as a '#' comment line in the file header.", examples=["Home LAN"]),
]

Tag = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$"), Field(examples=["lan"])]

LeaseTime = Annotated[
    Annotated[str, StringConstraints(pattern=r"^(infinite|\d+[smhdw]?)$")] | None,
    Field(description="Lease time, e.g. '12h', '30m', '3600' or 'infinite'.", examples=["12h"]),
]

Ttl = Annotated[
    Annotated[int, Field(ge=0, le=2_147_483_647)] | None,
    Field(description="TTL in seconds.", examples=[300]),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Config file kinds
# --------------------------------------------------------------------------- #


class ConfigKind(StrEnum):
    dns = "dns"
    dhcp = "dhcp"


# --------------------------------------------------------------------------- #
# DNS entries (discriminated by ``type``)
# --------------------------------------------------------------------------- #


class HostRecord(StrictModel):
    """``host-record=<name>[,<name>...],[<IPv4>],[<IPv6>][,<TTL>]`` – A/AAAA + PTR records."""

    type: Literal["host-record"] = "host-record"
    names: list[Hostname] = Field(min_length=1)
    ipv4: IPv4Address | None = None
    ipv6: IPv6Address | None = None
    ttl: Ttl = None
    comment: Comment = None

    @model_validator(mode="after")
    def _require_address(self) -> Self:
        if self.ipv4 is None and self.ipv6 is None:
            raise ValueError("at least one of 'ipv4' or 'ipv6' is required")
        return self


class AddressRecord(StrictModel):
    """``address=/<domain>[/<domain>...]/<ip>`` – answer the domain *and all subdomains* with ip."""

    type: Literal["address"] = "address"
    domains: list[Hostname] = Field(min_length=1)
    ip: IPvAnyAddress
    comment: Comment = None


class CnameRecord(StrictModel):
    """``cname=<alias>[,<alias>...],<target>[,<TTL>]`` – target must be known to dnsmasq."""

    type: Literal["cname"] = "cname"
    aliases: list[Hostname] = Field(min_length=1)
    target: Hostname
    ttl: Ttl = None
    comment: Comment = None


DnsEntryCreate = Annotated[HostRecord | AddressRecord | CnameRecord, Field(discriminator="type")]


class _HasId(BaseModel):
    id: UUID


class HostRecordOut(HostRecord, _HasId):
    pass


class AddressRecordOut(AddressRecord, _HasId):
    pass


class CnameRecordOut(CnameRecord, _HasId):
    pass


DnsEntry = Annotated[HostRecordOut | AddressRecordOut | CnameRecordOut, Field(discriminator="type")]


# --------------------------------------------------------------------------- #
# DHCP ranges
# --------------------------------------------------------------------------- #


class DhcpRangeCreate(StrictModel):
    """``dhcp-range=[tag:<tag>,...][set:<tag>,]<start>,<end>[,<netmask>|<prefix-len>][,<lease>]``"""

    start: IPvAnyAddress
    end: IPvAnyAddress
    netmask: IPv4Address | None = Field(default=None, description="IPv4 only.")
    prefix_length: int | None = Field(default=None, ge=64, le=128, description="IPv6 only.")
    lease_time: LeaseTime = None
    match_tags: list[Tag] = Field(default_factory=list, description="Rendered as 'tag:<tag>'.")
    set_tag: Tag | None = Field(default=None, description="Rendered as 'set:<tag>'.")
    comment: Comment = None

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.start.version != self.end.version:
            raise ValueError("'start' and 'end' must be of the same IP version")
        if int(self.start) > int(self.end):
            raise ValueError("'start' must not be greater than 'end'")
        if self.start.version == 4 and self.prefix_length is not None:
            raise ValueError("'prefix_length' is only valid for IPv6 ranges")
        if self.start.version == 6 and self.netmask is not None:
            raise ValueError("'netmask' is only valid for IPv4 ranges")
        return self


class DhcpRange(DhcpRangeCreate, _HasId):
    pass


# --------------------------------------------------------------------------- #
# Config files
# --------------------------------------------------------------------------- #


class ConfigFileCreate(StrictModel):
    name: ConfigName
    description: FileDescription = None


class ConfigFileUpdate(StrictModel):
    """Partial update; renaming also renames the file on disk."""

    name: ConfigName | None = Field(default=None, description="New name; renames the file on disk.", examples=["home-lan"])
    description: FileDescription = None


class ConfigFileBase(BaseModel):
    name: ConfigName
    kind: ConfigKind
    filename: str = Field(description="File name inside the dnsmasq conf dir.")
    description: str | None = None


class DnsConfigFile(ConfigFileBase):
    entries: list[DnsEntry]


class DhcpConfigFile(ConfigFileBase):
    entries: list[DhcpRange]


class RenderedFile(BaseModel):
    name: str
    kind: ConfigKind
    filename: str
    content: str


class SyncResult(BaseModel):
    written: list[str]
    removed: list[str]


class ServiceStatus(BaseModel):
    available: bool = Field(description="True if dnsmasq runs as systemd unit and can be restarted.")
    unit: str | None = None
    active_state: str | None = Field(default=None, examples=["active"])
    sub_state: str | None = Field(default=None, examples=["running"])
    since: str | None = Field(default=None, description="Timestamp the unit entered the active state.")
    reason: str | None = Field(default=None, description="Why restarting is not available.")
