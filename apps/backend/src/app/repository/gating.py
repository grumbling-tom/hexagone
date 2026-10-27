"""Pin a caller's filter to what the viewer may see.

A filter on a field is a question about that field. If the viewer can't see
Carol's email, they mustn't be able to *ask* about it either:
``GET /users?email=carol@acme.com`` returning ``[carol]`` confirms the email
without ever showing it. ``gate`` rewrites every leaf of a caller's predicate
to ``leaf AND <that field's READ rule>``, so on a row where the field is
hidden the leaf is false whatever value was asked about.

Only the CALLER's filters are gated. The policy's own row rules are trusted:
they routinely test fields the viewer can't see (``is_me`` reads ``uid``,
``shares_group`` reads memberships), and gating them would make the rules
reject themselves.
"""

from typing import TYPE_CHECKING

from .policy import Operation, Policy
from .predicates import And, Anyone, FieldPredicate, Nobody, Or, Predicate, Related

if TYPE_CHECKING:
    from .database import BaseModel


class UnhandledPredicateError(TypeError):
    """``gate`` met a predicate kind it doesn't know how to gate.

    Raised rather than passing the predicate through: an ungated predicate is
    an oracle, so an unknown one fails closed.
    """


def relationship_target(entity: type[BaseModel], field: str) -> type[BaseModel]:
    """Return the class on the far side of ``entity.<field>``."""
    return getattr(entity, field).property.mapper.class_


def gate(pred: Predicate, entity: type[BaseModel], policy: Policy) -> Predicate:
    """Return ``pred`` with every field leaf ANDed with its READ visibility."""
    match pred:
        case And(predicates=ps):
            return And(predicates=[gate(p, entity, policy) for p in ps])
        case Or(predicates=ps):
            return Or(predicates=[gate(p, entity, policy) for p in ps])
        case Related(field=f, inner=p):
            # Crossing a relationship lands on rows of another entity. Those
            # rows must be ones the viewer could read (trusted row rules), and
            # the caller's inner predicate is gated against THAT entity's fields.
            target = relationship_target(entity, f)
            return Related(
                field=f,
                inner=And(
                    predicates=[
                        *policy.rows(target, Operation.READ),
                        gate(p, target, policy),
                    ]
                ),
            )
        case FieldPredicate(field=f):
            visible = policy.fields(entity, Operation.READ).get(f, Nobody())
            if isinstance(visible, Anyone):
                return pred  # nothing to pin; keep the SQL readable
            return And(predicates=[pred, visible])
        case Anyone() | Nobody():
            return pred
        case _:
            msg = f"Don't know how to gate {type(pred).__name__}"
            raise UnhandledPredicateError(msg)
