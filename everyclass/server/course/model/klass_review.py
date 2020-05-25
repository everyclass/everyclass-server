import os
import random
import re

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from everyclass.server.utils.db.postgres import Base, db_session


class KlassReview(Base):
    __tablename__ = 'klass_review'

    review_id = Column(Integer, primary_key=True)  # 评价自增ID
    klass_id = Column(Integer, ForeignKey("klass_meta.klass_id"))  # 教学班ID
    klass = relationship("KlassMeta", back_populates="reviews", lazy=True)
    user_identifier = Column(String(15), nullable=False)  # 评价人学号
    user_nickname = Column(String, nullable=False)  # 昵称，用来在前台展示的描述性标识符，如"计算机学院16级学生"

    rating_knowledge = Column(Integer)
    # 是否学到了新的知识
    # 5：非常有收获，学习到了相当多的知识
    # 4：比较有收获，对我有一定启发
    # 3：收获一般，有的知识还挺有用的
    # 2：没什么收获，大部分都废话或听不懂
    # 1：完全没用，听了也白听

    rating_attendance = Column(Integer)
    # 出勤严格程度（是否点名）
    # 5：非常严，如果点名没到后果很严重
    # 4：比较严，不太好请假
    # 3：一般严，跟老师请假一般都能通过
    # 2：比较松，偶尔不来被发现问题不大
    # 1：很松，反正我没上过几节

    final_score = Column(Float)  # 期末得分，百分制的得分

    gender_rate = Column(Integer)
    # 男女比
    # 5：几乎全是女生
    # 4：女生占大多数
    # 3：男女比例一半一半吧
    # 2：男生占大多数
    # 1：几乎全是男生

    comments = Column(String)  # 文字评价内容

    create_time = Column(DateTime(timezone=True), server_default=func.now())

    @classmethod
    def new(cls, klass_id: int, user_id: str, rk: int, ra: int, fs: float, gr: int, comment: str):
        from everyclass.server.entity import service as entity_service
        student = entity_service.get_student(user_id)

        grade_str = ""
        groups = re.findall(r'\d+', student.klass)
        if len(groups) > 0:
            grade_str = f"{groups[0][:2]}级"

        db_session.add(KlassReview(klass_id=klass_id, user_identifier=user_id, user_nickname=f"{student.deputy}{grade_str}学生",
                                   rating_knowledge=rk, rating_attendance=ra, final_score=fs, gender_rate=gr, comments=comment))
        db_session.commit()

    @classmethod
    def import_demo_content(cls):
        """给每一门class导入若干随机生成的评价"""
        from everyclass.server.course.model import KlassMeta

        comments_content = [
            "这个课挺好的",
            "不知道老师在讲啥",
            "老师讲的非常好",
            "英语学渣表示听不懂"
        ]
        comments_score = [
            "分给的有点低",
            "分数还可以",
            "分数巨高",
            "分数很满意",
            "分太低了"
        ]

        student_ids = []
        with open(os.path.join(os.path.dirname(__file__), "student_ids.csv")) as f:
            for line in f.readlines():
                student_ids.append(line[:len(line) - 1])

        classes = db_session.query(KlassMeta).all()
        for klass in classes:
            for _ in range(random.randint(0, 3)):
                student_id = random.choice(student_ids)
                print("student_id: %s" % student_id)
                cls.new(klass.klass_id, student_id, random.randint(2, 5), random.randint(2, 5), random.randint(60, 100),
                        random.randint(0, 5), f"{random.choice(comments_content)}，{random.choice(comments_score)}")
