from sqlalchemy import Column, String

from everyclass.server.utils.db.postgres import Base


class CourseAdditionalMeta(Base):
    __tablename__ = 'course_additional_meta'

    course_id = Column(String(30), primary_key=True)
    description = Column(String, nullable=False)
    course_type = Column(String, nullable=False)
