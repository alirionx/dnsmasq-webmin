from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.models import ServiceStatus
from app.systemd import DnsmasqService


def get_dnsmasq_service(request: Request) -> DnsmasqService:
    return request.app.state.dnsmasq


Dnsmasq = Annotated[DnsmasqService, Depends(get_dnsmasq_service)]

router = APIRouter(prefix="/service", tags=["dnsmasq service"])


@router.get("", response_model=ServiceStatus, summary="dnsmasq systemd status")
def status(svc: Dnsmasq):
    return svc.status()


@router.post(
    "/restart",
    response_model=ServiceStatus,
    summary="Test config and restart dnsmasq",
    responses={
        422: {"description": "`dnsmasq --test` rejected the configuration, nothing was restarted."},
        502: {"description": "systemctl failed (e.g. missing permissions)."},
        503: {"description": "dnsmasq is not managed by systemd."},
    },
)
def restart(svc: Dnsmasq):
    """Runs `dnsmasq --test` first and only restarts if the configuration is valid."""
    return svc.restart()
