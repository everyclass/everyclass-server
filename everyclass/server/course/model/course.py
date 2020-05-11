from sqlalchemy import Column, String

from everyclass.server.utils.db.postgres import Base


class CourseAdditionalMeta(Base):
    __tablename__ = 'course_additional_meta'

    course_id = Column(String(30), primary_key=True)  # 课程ID
    description = Column(String, nullable=False)  # 课程简介
    course_type = Column(String, nullable=False)  # 课程类型
