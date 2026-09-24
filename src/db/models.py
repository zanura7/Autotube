from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String)
    project_type = Column(String)
    status = Column(String)
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


class LiveStream(Base):
    __tablename__ = "live_streams"

    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False, default="Untitled stream")
    status = Column(String(32), nullable=False, default="draft", index=True)
    rtmp_url = Column(String(500), nullable=False)
    stream_key_encrypted = Column(Text, nullable=False)
    background_type = Column(String(16), nullable=False, default="videos")
    visual_paths_json = Column(Text, nullable=False, default="[]")
    audio_paths_json = Column(Text, nullable=False, default="[]")
    settings_json = Column(Text, nullable=False, default="{}")
    loop = Column(Boolean, nullable=False, default=True)
    shuffle = Column(Boolean, nullable=False, default=False)
    auto_restart = Column(Boolean, nullable=False, default=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=10)
    pid = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    scheduled_stop = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    logs = relationship(
        "LiveStreamLog", cascade="all, delete-orphan", back_populates="stream"
    )


class LiveStreamLog(Base):
    __tablename__ = "live_stream_logs"

    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(
        String(36),
        ForeignKey("live_streams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level = Column(String(16), nullable=False, default="INFO")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    stream = relationship("LiveStream", back_populates="logs")
