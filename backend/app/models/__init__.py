"""Modelos de base de datos.

Importar aquí cada modelo para que Alembic los encuentre en ``Base.metadata``.
"""

from app.models.app_setting import AppSetting
from app.models.base import Base

__all__ = ["AppSetting", "Base"]
