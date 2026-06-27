from abc import ABC, abstractmethod
from collections.abc import Iterable

from lab1.models import Book, Request, User


class UserStore(ABC):
    @abstractmethod
    def add(self, user: User) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, name: str) -> User:
        raise NotImplementedError

    @abstractmethod
    def save(self, user: User) -> None:
        raise NotImplementedError


class BookStore(ABC):
    @abstractmethod
    def get(self, title: str) -> Book:
        raise NotImplementedError

    @abstractmethod
    def save(self, book: Book) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, title: str) -> bool:
        raise NotImplementedError


class RequestStore(ABC):
    @abstractmethod
    def add(self, request: Request) -> Request:
        raise NotImplementedError

    @abstractmethod
    def get(self, request_id: int) -> Request:
        raise NotImplementedError

    @abstractmethod
    def save(self, request: Request) -> None:
        raise NotImplementedError

    @abstractmethod
    def all(self) -> Iterable[Request]:
        raise NotImplementedError
