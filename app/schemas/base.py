from typing import Annotated

from pydantic import AfterValidator, BaseModel


class PaginatedResponse[T](BaseModel):
    items: list[T]
    size: int
    total: int
    page: int
    pages: int


def validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one number")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/~`" for c in v):
        raise ValueError("Password must contain at least one special character")
    return v


StrongPassword = Annotated[str, AfterValidator(validate_password)]
