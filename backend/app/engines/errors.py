"""Errores de los motores deterministas."""


class RuleViolation(ValueError):
    """La operación no está permitida por las reglas. El mensaje es legible para el usuario."""
