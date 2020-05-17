import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from everyclass.server.utils.db.postgres import Base


class CalendarToken(Base):
    token = sa.Column('token', postgresql.UUID(), autoincrement=False, nullable=False, primary_key=True)
    type = sa.Column('type', postgresql.ENUM('student', 'teacher', name='people_type'), autoincrement=False, nullable=False)
    identifier = sa.Column('identifier', sa.VARCHAR(length=15), autoincrement=False, nullable=False)
    semester = sa.Column('semester', sa.VARCHAR(length=15), autoincrement=False, nullable=False)
    create_time = sa.Column('create_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False)
    last_used_time = sa.Column('last_used_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True)

    __tablename__ = 'calendar_tokens'
    __table_args__ = (sa.Index('idx_type_idt_sem', 'type', 'identifier', 'semester'),)
