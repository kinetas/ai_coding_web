from __future__ import annotations

from fastapi import APIRouter, Depends, Path

from backend.app.auth import get_current_user
from backend.app.models.alert import AlertCheckResponse, AlertListResponse, CreateAlertPayload
from backend.app.services.alert_service import AlertService


def build_router(service: AlertService) -> APIRouter:
    router = APIRouter()

    @router.get("/alerts", response_model=AlertListResponse)
    def list_alerts(current_user: dict = Depends(get_current_user)):
        return service.list_alerts(current_user)

    @router.post("/alerts", status_code=201)
    def create_alert(payload: CreateAlertPayload, current_user: dict = Depends(get_current_user)):
        return service.create_alert(
            user=current_user,
            name=payload.name,
            item_name=payload.item_name,
            condition=payload.condition,
            threshold=payload.threshold,
        )

    @router.delete("/alerts/{alert_id}")
    def delete_alert(
        alert_id: int = Path(..., gt=0),
        current_user: dict = Depends(get_current_user),
    ):
        return service.delete_alert(current_user, alert_id)

    @router.get("/alerts/check", response_model=AlertCheckResponse)
    def check_alerts(current_user: dict = Depends(get_current_user)):
        return service.check_alerts(current_user)

    return router
