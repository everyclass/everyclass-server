from typing import NamedTuple

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from everyclass.server.utils.db.postgres import Base


class Visitor(NamedTuple):
    name: str
    user_type: str
    identifier_encoded: str
    last_semester: str
    visit_time: int  # not sure


class VisitTrack(Base):
    host_id = sa.Column('host_id', sa.VARCHAR(length=15), autoincrement=False, nullable=False, primary_key=True)
    visitor_id = sa.Column('visitor_id', sa.VARCHAR(length=15), autoincrement=False, nullable=False, primary_key=True)
    last_visit_time = sa.Column('last_visit_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False)

    __tablename__ = 'visit_tracks'
    __table_args__ = (sa.Index('idx_host_time', 'host_id', 'last_visit_time', unique=False),
                      sa.UniqueConstraint('host_id', 'visitor_id', name='unq_host_visitor')
                      )
