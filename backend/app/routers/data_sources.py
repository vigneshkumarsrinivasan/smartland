from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DataSource

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


@router.get("")
def list_data_sources(db: Session = Depends(get_db)):
    sources = db.query(DataSource).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "category": s.category,
            "description": s.description,
            "status": s.status,
            "coverage": s.coverage,
            "last_updated": s.last_updated.isoformat() if s.last_updated else None,
        }
        for s in sources
    ]
