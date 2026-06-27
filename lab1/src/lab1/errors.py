class LibraryError(Exception):
    """Base class for library domain errors."""


class DuplicateUserError(LibraryError):
    """Raised when user name is already used."""


class NotFoundError(LibraryError):
    """Raised when requested entity does not exist."""


class AccessError(LibraryError):
    """Raised when user role is not enough for an action."""


class RuleError(LibraryError):
    """Raised when a business rule is broken."""
