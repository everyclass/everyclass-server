import uuid
from dataclasses import dataclass
from typing import NamedTuple


class Visitor(NamedTuple):
    name: str
    user_type: str
    identifier_encoded: str
    last_semester: str
    visit_time: int  # not sure


@dataclass
class IdentityVerifyRequest:
    request_id: uuid.UUID
    identifier: str
    method: str
    status: str
    extra: dict


__all__ = (IdentityVerifyRequest, Visitor)
