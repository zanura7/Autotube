from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.db.models import Project

router = APIRouter(prefix="/history", tags=["History"])

@router.get("/")
def get_projects(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
    return {"projects": projects}
