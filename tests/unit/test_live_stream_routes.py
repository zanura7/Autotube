from datetime import datetime, timezone

from fastapi import HTTPException
import pytest

from src.api.routes.livestream import (
    DailyScheduleRequest,
    LiveStreamRequest,
    _database_utc,
    schedule_daily,
)


def valid_stream_request():
    return LiveStreamRequest(
        stream_key="temporary-key",
        visual_paths=["C:/media/background.mp4"],
        audio_paths=["C:/media/music.mp3"],
    )


def test_daily_schedule_rejects_identical_start_and_stop_times():
    request = DailyScheduleRequest(
        stream_data=valid_stream_request(),
        start_time="08:00",
        stop_time="08:00",
        timezone="Asia/Jakarta",
    )

    with pytest.raises(HTTPException, match="must be different") as error:
        schedule_daily(request)

    assert error.value.status_code == 422


def test_image_background_rejects_original_audio_mode():
    request = valid_stream_request()
    request.background_type = "images"
    request.audio_mode = "keep"

    from src.api.routes.livestream import _normalized_paths

    with pytest.raises(HTTPException, match="replacement audio") as error:
        _normalized_paths(request)

    assert error.value.status_code == 422


def test_sqlite_datetime_without_offset_is_restored_as_utc():
    stored_value = datetime(2026, 9, 25, 12, 30)

    restored = _database_utc(stored_value)

    assert restored == datetime(2026, 9, 25, 12, 30, tzinfo=timezone.utc)
