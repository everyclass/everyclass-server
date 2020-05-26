import json
import os

import sqlalchemy as sa
from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import relationship

from everyclass.server.utils.db.postgres import Base, db_session
from everyclass.server.utils.jsonable import JSONSerializable


class KlassMeta(Base, JSONSerializable):
    __tablename__ = 'klass_meta'

    klass_id = Column(Integer, primary_key=True)  # 教学班ID
    course_id = Column(String(30), sa.ForeignKey("course_meta.course_id"))  # 课程 ID
    course = relationship("CourseMeta", back_populates="classes", lazy=False)
    semester = Column(String(15), nullable=False)  # 所在学期
    teachers = Column(pg.ARRAY(String))  # 任课教师名单

    # 评分的缓存，来源是klass_review，每日cron刷新
    score = Column("score", Float, nullable=False)
    rating_knowledge = Column(Float)
    rating_attendance = Column(Float)
    final_score = Column(Float)
    gender_rate = Column(Float)

    review_quote = Column(String, nullable=True)  # 示例评价内容
    reviews = relationship("KlassReview", back_populates="klass", lazy=True)

    def __json_encode__(self):
        from everyclass.server.entity.service import get_people_info

        return {'class_id': self.klass_id,
                'name': self.course.name,
                'teachers': [{'name': t.name, 'title': t.title} for t in [get_people_info(teacher_id)[1] for teacher_id in self.teachers]],
                # todo 速度太慢了，entity要出批量查询接口
                'score': round(self.score, 1),
                'review_quote': self.review_quote}

    @classmethod
    def get_all(cls):
        return db_session.query(cls).all()

    @classmethod
    def import_demo_content(cls):
        with open(os.path.join(os.path.dirname(__file__), "klass.json")) as f:
            data = json.loads(f.read())
            for line in data:
                course_id, teachers = line['course_code'], line['teacher_list']

                teachers = json.loads(teachers)
                teacher_list = [t['code'] for t in teachers]

                k = KlassMeta(course_id=course_id, semester='2019-2020-2', score=-1, teachers=teacher_list)
                db_session.add(k)
            db_session.commit()
