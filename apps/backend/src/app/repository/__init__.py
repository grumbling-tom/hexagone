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
    OrFilter,
    RangeFilter,
    RelationFilter,
)
from .models import (
    HexClaim,
    Upload,
    UploadStatus,
    UploadStatusValue,
    User,
    UserGroup,
    UserGroupMembership,
    UserSession,
)
from .repository import Repository
from .views import HexClaimByCell, View

__all__ = [
    "BaseModel",
    "EqualsFilter",
    "Filter",
    "GreaterThanFilter",
    "GreaterThanOrEqualFilter",
    "HexClaim",
    "HexClaimByCell",
    "InFilter",
    "IsNullFilter",
    "LessThanFilter",
    "LessThanOrEqualFilter",
    "LikeFilter",
    "NotEqualsFilter",
    "NotInFilter",
    "OrFilter",
    "RangeFilter",
    "RelationFilter",
    "Repository",
    "SessionLocal",
    "Upload",
    "UploadStatus",
    "UploadStatusValue",
    "User",
    "UserGroup",
    "UserGroupMembership",
    "UserSession",
    "View",
    "check_database_health",
    "engine",
    "get_db",
]
