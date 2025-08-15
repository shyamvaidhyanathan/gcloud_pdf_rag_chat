# Get the env at the very top before any
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
APP_TZ = os.getenv("APP_TIMEZONE", "America/New_York")


#get the logger done also at the top.
from utils.logger import init_logger
logger = init_logger(__name__)

from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


def now_ts() -> str:
    """Return an ISO8601 timestamp in configured timezone (fallback: naive local)."""
    try:
        if ZoneInfo is not None:
            return datetime.now(ZoneInfo(APP_TZ)).isoformat()
    except Exception:
        pass
    return datetime.now().isoformat()

def format_ts(ts: str) -> str:
    """Pretty-print a timestamp that was saved via now_ts()."""
    if not ts:
        return ""
    dt = None
    try:
        dt = datetime.fromisoformat(ts)
    except Exception:
        try:
            dt = datetime.fromtimestamp(float(ts))
        except Exception:
            dt = None
    if dt is None:
        return ts
    try:
        if dt.tzinfo is None and ZoneInfo is not None:
            dt = dt.replace(tzinfo=ZoneInfo(APP_TZ))
    except Exception:
        pass
    try:
        return dt.strftime("%b %d, %Y %I:%M %p %Z")
    except Exception:
        return dt.isoformat()