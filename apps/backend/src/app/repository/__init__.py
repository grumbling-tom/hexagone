"""Repository package for database models, queries, and filtering.

This package consolidates all repository-related code including:
- Database connection and session management
- SQLAlchemy models
- Repository pattern implementation
- Query filters

Cross-layer utilities (cursor, pagination, logging, dependencies, base schemas)
are located in the utils/ package.
"""

from .database import (
    BaseModel,
    SessionLocal,
    check_database_health,
    engine,
    get_db,
)
from .filters import (
    EqualsFilter,
    Filter,
    GreaterThanFilter,
    GreaterThanOrEqualFilter,
    InFilter,
    IsNullFilter,
    LessThanFilter,
    LessThanOrEqualFilter,
    LikeFilter,
    NotEqualsFilter,
    NotInFilter,
    RangeFilter,
)
from .models import User, UserSession
from .repository import Repository

__all__ = [
    "BaseModel",
    "EqualsFilter",
    "Filter",
    "GreaterThanFilter",
    "GreaterThanOrEqualFilter",
    "InFilter",
    "IsNullFilter",
    "LessThanFilter",
    "LessThanOrEqualFilter",
    "LikeFilter",
    "NotEqualsFilter",
    "NotInFilter",
    "RangeFilter",
    "Repository",
    "SessionLocal",
    "User",
    "UserSession",
    "check_database_health",
    "engine",
    "get_db",
]
