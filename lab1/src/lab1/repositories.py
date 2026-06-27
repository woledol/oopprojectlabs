from lab1.errors import DuplicateUserError, NotFoundError
from lab1.interfaces import BookStore, RequestStore, UserStore
from lab1.models import Book, Request, User


class MemoryUserStore(UserStore):
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def add(self, user: User) -> None:
        if user.name in self._users:
            raise DuplicateUserError(user.name)
        self._users[user.name] = user

    def get(self, name: str) -> User:
        try:
            return self._users[name]
        except KeyError as err:
            raise NotFoundError(name) from err

    def save(self, user: User) -> None:
        if user.name not in self._users:
            raise NotFoundError(user.name)
        self._users[user.name] = user


class MemoryBookStore(BookStore):
    def __init__(self) -> None:
        self._books: dict[str, Book] = {}

    def get(self, title: str) -> Book:
        try:
            return self._books[title]
        except KeyError as err:
            raise NotFoundError(title) from err

    def save(self, book: Book) -> None:
        self._books[book.title] = book

    def exists(self, title: str) -> bool:
        return title in self._books


class MemoryRequestStore(RequestStore):
    def __init__(self) -> None:
        self._requests: dict[int, Request] = {}
        self._next_id = 1

    def add(self, request: Request) -> Request:
        request.id = self._next_id
        self._next_id += 1
        self._requests[request.id] = request
        return request

    def get(self, request_id: int) -> Request:
        try:
            return self._requests[request_id]
        except KeyError as err:
            raise NotFoundError(str(request_id)) from err

    def save(self, request: Request) -> None:
        if request.id not in self._requests:
            raise NotFoundError(str(request.id))
        self._requests[request.id] = request

    def all(self) -> list[Request]:
        return list(self._requests.values())
