from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.services.zone_service import ZoneService


router = APIRouter(
    prefix="/api/zone",
    tags=["Restricted Zone"],
    dependencies=[Depends(get_current_user)],
)


zone_service = ZoneService()


class ZoneRequest(BaseModel):
    points: list[list[int]]


@router.get("/")
def get_zone():

    zone = zone_service.get_zone()

    return {
        "points": zone
    }


@router.post("/")
def save_zone(request: ZoneRequest):

    if len(request.points) < 3:
        raise HTTPException(
            status_code=400,
            detail="At least 3 points are required."
        )

    points = [
        (point[0], point[1])
        for point in request.points
    ]

    saved_zone = zone_service.save_zone(points)

    return {
        "message": "Restricted zone saved successfully",
        "points": saved_zone
    }


@router.delete("/")
def clear_zone():

    zone_service.clear_zone()

    return {
        "message": "Restricted zone cleared"
    }