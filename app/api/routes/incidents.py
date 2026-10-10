from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import SessionLocal
from app.models.incident import Incident


router = APIRouter(
    prefix="/api/incidents",
    tags=["Incidents"],
    dependencies=[Depends(get_current_user)],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/")
def get_incidents(db: Session = Depends(get_db)):
    incidents = (
        db.query(Incident)
        .order_by(Incident.timestamp.desc())
        .all()
    )

    return incidents


@router.get("/page")
def get_incident_page(
    before_id: int | None = Query(None, ge=1),
    limit: int = Query(5, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Incident)

    if before_id is not None:
        query = query.filter(Incident.id < before_id)

    page = query.order_by(Incident.id.desc()).limit(limit + 1).all()
    has_more = len(page) > limit
    incidents = page[:limit]

    total = db.query(func.count(Incident.id)).scalar() or 0
    open_incidents = (
        db.query(func.count(Incident.id))
        .filter(Incident.status == "open")
        .scalar()
        or 0
    )

    return {
        "items": incidents,
        "total": total,
        "open": open_incidents,
        "has_more": has_more
    }


@router.get("/{incident_id}")
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db)
):
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    return incident


@router.delete("/")
def delete_all_incidents(db: Session = Depends(get_db)):
    deleted_count = db.query(Incident).delete(synchronize_session=False)
    db.commit()

    return {
        "message": "All incidents deleted successfully",
        "deleted_count": deleted_count
    }


@router.delete("/{incident_id}")
def delete_incident(
    incident_id: int,
    db: Session = Depends(get_db)
):
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    db.delete(incident)
    db.commit()

    return {
        "message": "Incident deleted successfully",
        "incident_id": incident_id
    }