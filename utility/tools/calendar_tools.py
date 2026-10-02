from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _parse_date(value: str) -> date:
    """Parse an ISO date (YYYY-MM-DD)."""
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Date must use YYYY-MM-DD format") from error


def get_current_datetime(timezone: str = "UTC") -> dict:
    """Return the current date and time for an IANA timezone."""
    try:
        now = datetime.now(ZoneInfo(timezone))
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Unknown timezone: {timezone}") from error

    return {
        "timezone": timezone,
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M:%S"),
        "datetime": now.isoformat(),
        "day_of_week": now.strftime("%A"),
    }


def get_day_of_week(date_value: str) -> str:
    """Return the weekday for an ISO date."""
    return _parse_date(date_value).strftime("%A")


def add_days(date_value: str, days: int) -> str:
    """Add or subtract a number of days from an ISO date."""
    return (_parse_date(date_value) + timedelta(days=days)).isoformat()


def days_between(start_date: str, end_date: str) -> int:
    """Return the number of calendar days between two ISO dates."""
    return (_parse_date(end_date) - _parse_date(start_date)).days


CALENDAR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Get the current date and time for an IANA timezone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone, such as UTC or America/New_York.",
                        "default": "UTC",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_day_of_week",
            "description": "Get the weekday for a date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_value": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format.",
                    }
                },
                "required": ["date_value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_days",
            "description": "Add or subtract days from a date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_value": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to add; negative values subtract.",
                    },
                },
                "required": ["date_value", "days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "days_between",
            "description": "Calculate calendar days from the start date to the end date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format.",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
]


CALENDAR_TOOLS_MAPPING = {
    "get_current_datetime": get_current_datetime,
    "get_day_of_week": get_day_of_week,
    "add_days": add_days,
    "days_between": days_between,
}
