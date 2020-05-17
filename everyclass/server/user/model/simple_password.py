from sqlalchemy import Column, String, DateTime, Text, Integer, Index
from sqlalchemy.sql import func

from everyclass.server.utils.db.postgres import Base, db_session


class SimplePassword(Base):
    __tablename__ = 'simple_passwords'

    record_id = Column(Integer, primary_key=True)
    identifier = Column('student_id', String(15), nullable=False)
    time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    password = Column(Text, nullable=False)

    __table_args__ = (Index('idx_time', 'time', unique=False),)

    @classmethod
    def new(cls, password: str, identifier: str):
        sp = SimplePassword(identifier=identifier, password=password)
        db_session.add(sp)
        db_session.commit()
