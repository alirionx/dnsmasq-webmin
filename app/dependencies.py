from fastapi import Request

from app.service import ConfigService


def get_service(request: Request) -> ConfigService:
    return request.app.state.service
