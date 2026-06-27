from lab1.errors import AccessError, RuleError
from lab1.interfaces import BookStore, RequestStore, UserStore
from lab1.models import Book, Request, RequestStatus, RequestType, Role, User


class Library:
    def __init__(self, users: UserStore, books: BookStore, requests: RequestStore) -> None:
        self.users = users
        self.books = books
        self.requests = requests

    def register_user(self, name: str, roles: set[Role]) -> User:
        if not name:
            raise RuleError("empty name")
        if not roles:
            raise RuleError("empty roles")
        user = User(name=name, roles=set(roles))
        self.users.add(user)
        return user

    def seed_book(self, title: str, author: str, circulation: int, stored: int) -> Book:
        self._check_initial_book_numbers(circulation, stored)
        book = Book(title=title, author=author, circulation=circulation, stored=stored)
        self.books.save(book)
        return book

    def borrow(self, reader_name: str, title: str) -> Request:
        user = self._user_with_role(reader_name, Role.READER)
        book = self.books.get(title)
        if title in user.history:
            raise RuleError("book already taken")
        if book.available <= 0:
            raise RuleError("no copies")
        request = self._new_request(RequestType.BORROW, reader_name, title)
        return self._auto_approve(user, request)

    def offer(self, writer_name: str, title: str, circulation: int, amount: int = 1) -> Request:
        user = self._user_with_role(writer_name, Role.WRITER)
        self._check_book_numbers(circulation, amount)
        if self.books.exists(title):
            book = self.books.get(title)
            if book.author != writer_name:
                raise RuleError("not writer's book")
            if book.circulation != circulation:
                raise RuleError("wrong circulation")
            total = book.stored
        else:
            total = 0
        if total + self._pending_add(title) + amount > circulation:
            raise RuleError("circulation exceeded")
        request = self._new_request(
            RequestType.ADD,
            writer_name,
            title,
            amount=amount,
            circulation=circulation,
        )
        return self._auto_approve(user, request)

    def give_back(self, reader_name: str, title: str) -> Request:
        user = self._user_with_role(reader_name, Role.READER)
        if title not in user.books:
            raise RuleError("book is not held")
        request = self._new_request(RequestType.RETURN, reader_name, title)
        return self._auto_approve(user, request)

    def approve(self, librarian_name: str, request_id: int) -> Request:
        self._user_with_role(librarian_name, Role.LIBRARIAN)
        request = self.requests.get(request_id)
        if request.status != RequestStatus.CREATED:
            raise RuleError("request is closed")
        self._apply(request)
        request.status = RequestStatus.APPROVED
        self.requests.save(request)
        return request

    def reject(self, librarian_name: str, request_id: int, reason: str = "") -> Request:
        self._user_with_role(librarian_name, Role.LIBRARIAN)
        request = self.requests.get(request_id)
        if request.status != RequestStatus.CREATED:
            raise RuleError("request is closed")
        request.status = RequestStatus.REJECTED
        request.reason = reason
        self.requests.save(request)
        return request

    def _user_with_role(self, name: str, role: Role) -> User:
        user = self.users.get(name)
        if not user.has(role):
            raise AccessError(f"{name}: {role.value}")
        return user

    def _new_request(
        self,
        type_: RequestType,
        user_name: str,
        title: str,
        amount: int = 1,
        circulation: int | None = None,
    ) -> Request:
        return self.requests.add(
            Request(
                id=0,
                type=type_,
                user_name=user_name,
                book_title=title,
                amount=amount,
                circulation=circulation,
            )
        )

    def _auto_approve(self, user: User, request: Request) -> Request:
        if user.has(Role.LIBRARIAN):
            return self.approve(user.name, request.id)
        return request

    def _apply(self, request: Request) -> None:
        if request.type == RequestType.ADD:
            self._apply_add(request)
        elif request.type == RequestType.BORROW:
            self._apply_borrow(request)
        else:
            self._apply_return(request)

    def _apply_add(self, request: Request) -> None:
        circulation = request.circulation
        if circulation is None:
            raise RuleError("empty circulation")
        if self.books.exists(request.book_title):
            book = self.books.get(request.book_title)
        else:
            book = Book(
                title=request.book_title,
                author=request.user_name,
                circulation=circulation,
            )
        if book.stored + request.amount > book.circulation:
            raise RuleError("circulation exceeded")
        book.stored += request.amount
        self.books.save(book)

    def _apply_borrow(self, request: Request) -> None:
        user = self.users.get(request.user_name)
        book = self.books.get(request.book_title)
        if request.book_title in user.history:
            raise RuleError("book already taken")
        if book.available <= 0:
            raise RuleError("no copies")
        book.holders.add(user.name)
        user.books.add(book.title)
        user.history.add(book.title)
        self.books.save(book)
        self.users.save(user)

    def _apply_return(self, request: Request) -> None:
        user = self.users.get(request.user_name)
        book = self.books.get(request.book_title)
        if book.title not in user.books:
            raise RuleError("book is not held")
        book.holders.remove(user.name)
        user.books.remove(book.title)
        self.books.save(book)
        self.users.save(user)

    def _pending_add(self, title: str) -> int:
        return sum(
            request.amount
            for request in self.requests.all()
            if request.type == RequestType.ADD
            and request.book_title == title
            and request.status == RequestStatus.CREATED
        )

    @staticmethod
    def _check_book_numbers(circulation: int, amount: int) -> None:
        if circulation <= 0:
            raise RuleError("bad circulation")
        if amount <= 0:
            raise RuleError("bad amount")
        if amount > circulation:
            raise RuleError("circulation exceeded")

    @staticmethod
    def _check_initial_book_numbers(circulation: int, stored: int) -> None:
        if circulation <= 0:
            raise RuleError("bad circulation")
        if stored < 0:
            raise RuleError("bad amount")
        if stored > circulation:
            raise RuleError("circulation exceeded")
