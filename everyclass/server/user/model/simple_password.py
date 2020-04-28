from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func

from everyclass.server.utils.db.postgres import Base, db_session


class SimplePassword(Base):
    identifier = Column('student_id', String(15), nullable=False)
    time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    password = Column(Text, nullable=False)

    @classmethod
    def new(cls, password: str, identifier: str):
        sp = SimplePassword(identifier=identifier, password=password)
        db_session.add(sp)
        db_session.commit()
