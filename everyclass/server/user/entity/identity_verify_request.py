import uuid
from dataclasses import dataclass


@dataclass
class IdentityVerifyRequest:
    request_id: uuid.UUID
    identifier: str
    method: str
    status: str
    extra: dict
