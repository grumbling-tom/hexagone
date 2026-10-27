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
from .gating import UnhandledPredicateError, gate
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
from .policy import FieldRules, Operation, Policy, SystemPolicy, queryable_fields
from .predicates import (
    And,
    Anyone,
    Equals,
    FieldPredicate,
    Filter,
    GreaterThan,
    GreaterThanOrEqual,
    Guard,
    In,
    IsNull,
    LessThan,
    LessThanOrEqual,
    Like,
    Nobody,
    NotEquals,
    NotIn,
    Or,
    Predicate,
    Range,
    Related,
)
from .repository import (
    NotAuthorisedError,
    PolicyConflictError,
    ScopedRepository,
    Transaction,
    UnscopedWriteError,
    UnsortableFieldError,
    forbid_unscoped_writes,
    hidden_fields,
    hide,
)
from .views import HexClaimByCell, View

__all__ = [
    "And",
    "Anyone",
    "BaseModel",
    "Equals",
    "FieldPredicate",
    "FieldRules",
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
    "Nobody",
    "NotAuthorisedError",
    "NotEquals",
    "NotIn",
    "Operation",
    "Or",
    "Policy",
    "PolicyConflictError",
    "Predicate",
    "Range",
    "Related",
    "ScopedRepository",
    "SessionLocal",
    "SystemPolicy",
    "Transaction",
    "UnhandledPredicateError",
    "UnscopedWriteError",
    "UnsortableFieldError",
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
    "forbid_unscoped_writes",
    "gate",
    "get_db",
    "hidden_fields",
    "hide",
    "queryable_fields",
]
