from dataclasses import dataclass, field
from enum import StrEnum


class Role(StrEnum):
    READER = "reader"
    WRITER = "writer"
    LIBRARIAN = "librarian"


class RequestType(StrEnum):
    BORROW = "borrow"
    ADD = "add"
    RETURN = "return"


class RequestStatus(StrEnum):
    CREATED = "created"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(slots=True)
class User:
    name: str
    roles: set[Role]
    books: set[str] = field(default_factory=set)
    history: set[str] = field(default_factory=set)

    def has(self, role: Role) -> bool:
        return role in self.roles


@dataclass(slots=True)
class Book:
    title: str
    author: str
    circulation: int
    stored: int = 0
    holders: set[str] = field(default_factory=set)

    @property
    def available(self) -> int:
        return self.stored - len(self.holders)


@dataclass(slots=True)
class Request:
    id: int
    type: RequestType
    user_name: str
    book_title: str
    amount: int = 1
    circulation: int | None = None
    status: RequestStatus = RequestStatus.CREATED
    reason: str = ""
