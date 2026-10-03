class AuthenticationError(Exception):
    pass


class PasswordChangeRequiredError(Exception):
    pass


class OutOfRange(Exception):
    pass


class WrongPasswordError(AuthenticationError):
    """
    Raised when a password-change request contains an incorrect old password.

    Why a dedicated type:
    - The request IS authenticated (the bearer token is valid).
    - The problem is with the request body, so the HTTP response should be
      400 (Bad Request), not 401 (Unauthorized).
    - Returning 401 causes well-behaved frontends to trigger token refresh
      and eventually force logout — wrong behavior for a form error.

    Subclasses AuthenticationError for backwards compatibility with callers
    that catch the broader category, but the HTTP layer catches it first
    and maps it to 400.
    """
