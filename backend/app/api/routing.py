from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import RequestLogOut, RequestLogSummary, RouteRequest
from app.db.session import get_db
from app.models.request_log import RequestLogORM
from app.routing.router import RoutingError
from app.routing.service import handle_routed_request

router = APIRouter(tags=["routing"])


@router.post("/route", response_model=RequestLogOut, status_code=201)
def route_request(payload: RouteRequest, db: Session = Depends(get_db)) -> RequestLogOut:
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt must not be empty")
    try:
        log = handle_routed_request(
            db,
            prompt=payload.prompt,
            category_hint=payload.category_hint,
            router_version=payload.router_version,
        )
    except RoutingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RequestLogOut.from_orm_log(log)


@router.get("/requests", response_model=list[RequestLogSummary])
def list_requests(db: Session = Depends(get_db)) -> list[RequestLogSummary]:
    logs = db.query(RequestLogORM).order_by(RequestLogORM.created_at.desc()).all()
    return [RequestLogSummary.from_orm_log(log) for log in logs]


@router.get("/requests/{request_id}", response_model=RequestLogOut)
def get_request(request_id: str, db: Session = Depends(get_db)) -> RequestLogOut:
    log = db.get(RequestLogORM, request_id)
    if log is None:
        raise HTTPException(status_code=404, detail=f"request {request_id!r} not found")
    return RequestLogOut.from_orm_log(log)
