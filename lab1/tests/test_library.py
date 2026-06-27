import pytest

from lab1 import Library, MemoryBookStore, MemoryRequestStore, MemoryUserStore
from lab1.errors import AccessError, DuplicateUserError, RuleError
from lab1.models import RequestStatus, Role


def lib() -> Library:
    return Library(MemoryUserStore(), MemoryBookStore(), MemoryRequestStore())


def test_user_name_is_unique() -> None:
    app = lib()
    app.register_user("ann", {Role.READER})

    with pytest.raises(DuplicateUserError):
        app.register_user("ann", {Role.WRITER})


def test_librarian_approves_borrow_request() -> None:
    app = lib()
    app.register_user("bob", {Role.READER})
    app.register_user("lib", {Role.LIBRARIAN})
    app.seed_book("Clean Code", "Martin", circulation=2, stored=1)

    request = app.borrow("bob", "Clean Code")
    assert request.status == RequestStatus.CREATED

    approved = app.approve("lib", request.id)

    assert approved.status == RequestStatus.APPROVED
    assert app.users.get("bob").books == {"Clean Code"}
    assert app.users.get("bob").history == {"Clean Code"}
    assert app.books.get("Clean Code").available == 0


def test_reject_keeps_book_out_of_reader_hands() -> None:
    app = lib()
    app.register_user("bob", {Role.READER})
    app.register_user("lib", {Role.LIBRARIAN})
    app.seed_book("Patterns", "Gamma", circulation=1, stored=1)

    request = app.borrow("bob", "Patterns")
    rejected = app.reject("lib", request.id, "busy")

    assert rejected.status == RequestStatus.REJECTED
    assert rejected.reason == "busy"
    assert app.users.get("bob").books == set()
    assert app.books.get("Patterns").available == 1


def test_writer_adds_own_book_after_approval() -> None:
    app = lib()
    app.register_user("kate", {Role.WRITER})
    app.register_user("lib", {Role.LIBRARIAN})

    request = app.offer("kate", "Python", circulation=3, amount=2)
    assert request.status == RequestStatus.CREATED

    app.approve("lib", request.id)
    book = app.books.get("Python")

    assert book.author == "kate"
    assert book.stored == 2
    assert book.available == 2


def test_writer_cannot_exceed_circulation_with_pending_requests() -> None:
    app = lib()
    app.register_user("kate", {Role.WRITER})
    app.offer("kate", "Python", circulation=3, amount=2)

    with pytest.raises(RuleError):
        app.offer("kate", "Python", circulation=3, amount=2)


def test_writer_cannot_offer_another_author_book() -> None:
    app = lib()
    app.register_user("kate", {Role.WRITER})
    app.seed_book("Rust", "graydon", circulation=5, stored=1)

    with pytest.raises(RuleError):
        app.offer("kate", "Rust", circulation=5, amount=1)


def test_reader_cannot_take_same_book_twice() -> None:
    app = lib()
    app.register_user("bob", {Role.READER})
    app.register_user("lib", {Role.LIBRARIAN})
    app.seed_book("Algorithms", "Sedgewick", circulation=2, stored=2)
    app.approve("lib", app.borrow("bob", "Algorithms").id)

    with pytest.raises(RuleError):
        app.borrow("bob", "Algorithms")


def test_reader_cannot_borrow_when_no_copies() -> None:
    app = lib()
    app.register_user("bob", {Role.READER})
    app.seed_book("Algorithms", "Sedgewick", circulation=1, stored=0)

    with pytest.raises(RuleError):
        app.borrow("bob", "Algorithms")


def test_librarian_reader_gets_book_without_manual_approval() -> None:
    app = lib()
    app.register_user("root", {Role.READER, Role.LIBRARIAN})
    app.seed_book("SQL", "Date", circulation=1, stored=1)

    request = app.borrow("root", "SQL")

    assert request.status == RequestStatus.APPROVED
    assert app.users.get("root").books == {"SQL"}


def test_librarian_writer_adds_book_without_manual_approval() -> None:
    app = lib()
    app.register_user("root", {Role.WRITER, Role.LIBRARIAN})

    request = app.offer("root", "Own", circulation=2, amount=2)

    assert request.status == RequestStatus.APPROVED
    assert app.books.get("Own").stored == 2


def test_return_book_goes_through_request() -> None:
    app = lib()
    app.register_user("bob", {Role.READER})
    app.register_user("lib", {Role.LIBRARIAN})
    app.seed_book("Compilers", "Aho", circulation=1, stored=1)
    app.approve("lib", app.borrow("bob", "Compilers").id)

    request = app.give_back("bob", "Compilers")
    assert request.status == RequestStatus.CREATED

    app.approve("lib", request.id)

    assert app.users.get("bob").books == set()
    assert app.users.get("bob").history == {"Compilers"}
    assert app.books.get("Compilers").available == 1


def test_return_without_book_is_forbidden() -> None:
    app = lib()
    app.register_user("bob", {Role.READER})

    with pytest.raises(RuleError):
        app.give_back("bob", "Compilers")


def test_only_librarian_can_close_requests() -> None:
    app = lib()
    app.register_user("bob", {Role.READER})
    app.register_user("kate", {Role.WRITER})
    app.seed_book("Math", "Knuth", circulation=1, stored=1)
    request = app.borrow("bob", "Math")

    with pytest.raises(AccessError):
        app.approve("kate", request.id)


def test_closed_request_cannot_be_closed_again() -> None:
    app = lib()
    app.register_user("bob", {Role.READER})
    app.register_user("lib", {Role.LIBRARIAN})
    app.seed_book("Math", "Knuth", circulation=1, stored=1)
    request = app.borrow("bob", "Math")

    app.reject("lib", request.id)

    with pytest.raises(RuleError):
        app.approve("lib", request.id)


def test_role_is_checked_for_reader_and_writer_actions() -> None:
    app = lib()
    app.register_user("max", {Role.READER})
    app.seed_book("Math", "Knuth", circulation=1, stored=1)

    with pytest.raises(AccessError):
        app.offer("max", "Math 2", circulation=1, amount=1)
