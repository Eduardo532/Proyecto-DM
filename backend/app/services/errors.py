class NotFound(LookupError):
    """El recurso no existe (se traduce a HTTP 404)."""


class Conflict(RuntimeError):
    """El estado actual no permite la operación (HTTP 409)."""


class Forbidden(PermissionError):
    """Hace falta el modo DM (HTTP 403)."""
