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
from .models import (
    HexClaim,
    LoginToken,
    Upload,
    UploadStatus,
    UploadStatusValue,
    User,
    UserGroup,
    UserGroupMembership,
    UserSession,
)
from .predicates import (
    Equals,
    Filter,
    GreaterThan,
    GreaterThanOrEqual,
    Guard,
    In,
    IsNull,
    LessThan,
    LessThanOrEqual,
    Like,
    NotEquals,
    NotIn,
    Or,
    Predicate,
    Range,
    Related,
)
from .repository import NotAuthorisedError, Repository
from .resources import ResourceType
from .views import HexClaimByCell, View

__all__ = [
    "BaseModel",
    "Equals",
    "Filter",
    "GreaterThan",
    "GreaterThanOrEqual",
    "Guard",
    "HexClaim",
    "HexClaimByCell",
    "In",
    "IsNull",
    "LessThan",
    "LessThanOrEqual",
    "Like",
    "LoginToken",
    "NotAuthorisedError",
    "NotEquals",
    "NotIn",
    "Or",
    "Predicate",
    "Range",
    "Related",
    "Repository",
    "ResourceType",
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
