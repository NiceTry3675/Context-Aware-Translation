from pydantic import BaseModel, field_serializer
import datetime
from typing import Optional

try:
    from zoneinfo import ZoneInfo
    # Windows 환경 호환을 위한 UTC 처리
    try:
        UTC_ZONE = ZoneInfo('UTC')
    except:
        UTC_ZONE = datetime.timezone.utc
    
    try:
        KST_ZONE = ZoneInfo('Asia/Seoul')
    except:
        # 백업: UTC+9 시간대 직접 생성
        KST_ZONE = datetime.timezone(datetime.timedelta(hours=9))
except ImportError:
    # Python < 3.9 또는 zoneinfo 없는 경우
    UTC_ZONE = datetime.timezone.utc
    KST_ZONE = datetime.timezone(datetime.timedelta(hours=9))

# --- Base Schemas for Reusability ---
class KSTTimezoneBase(BaseModel):
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(KST_ZONE)
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_ZONE)
        return dt.astimezone(KST_ZONE)

    class Config:
        from_attributes = True