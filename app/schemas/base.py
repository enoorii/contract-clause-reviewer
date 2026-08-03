from pydantic import BaseModel


class PaginatedResponse[T](BaseModel):
    items: list[T]
    size: int
    total: int
    page: int
    pages: int
