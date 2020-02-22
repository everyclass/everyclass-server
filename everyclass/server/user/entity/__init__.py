from typing import NamedTuple

from everyclass.server.user.entity.identity_verify_request import IdentityVerifyRequest


class Visitor(NamedTuple):
    name: str
    user_type: str
    identifier_encoded: str
    last_semester: str
    visit_time: int  # not sure


__all__ = (IdentityVerifyRequest, Visitor)
