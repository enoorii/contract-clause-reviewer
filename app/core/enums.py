from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    AVERAGE = "average"
    HIGH = "high"
    CRITICAL = "critical"


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
