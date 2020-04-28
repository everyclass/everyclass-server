from typing import NamedTuple


class Visitor(NamedTuple):
    name: str
    user_type: str
    identifier_encoded: str
    last_semester: str
    visit_time: int  # not sure
