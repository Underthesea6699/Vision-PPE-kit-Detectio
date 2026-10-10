from sqlalchemy.orm import Session
from app.models.incident import Incident


class IncidentService:

    @staticmethod
    def create_incident(
        db: Session,
        violation_type: str,
        person_track_id: int,
        confidence: float,
        snapshot_path: str,
        annotated_snapshot_path: str,
        message: str | None = None,
    ):
        incident = Incident(
            violation_type=violation_type,
            person_track_id=person_track_id,
            confidence=confidence,
            snapshot_path=snapshot_path,
            annotated_snapshot_path=annotated_snapshot_path,
            message=message,
            status="open",
        )

        db.add(incident)
        db.commit()
        db.refresh(incident)

        return incident