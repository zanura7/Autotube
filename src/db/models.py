from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String)
    project_type = Column(String)  # "Download", "Generator", "Loop", "Mixer"
    status = Column(String)        # "Completed", "Failed"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Channel(Base):
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    youtube_id = Column(String, unique=True, index=True)
    access_token = Column(String)
    refresh_token = Column(String)
    token_uri = Column(String)
    client_id = Column(String)
    client_secret = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
