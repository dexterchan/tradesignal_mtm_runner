from datetime import datetime

def convert_datetime_to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)

def convert_ms_to_datetime(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000)