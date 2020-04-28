from sqlalchemy import Column, String, Integer

from everyclass.server.utils.db.postgres import Base


class KlassReview(Base):
    __tablename__ = 'klass_review'

    klass_id = Column(String(30))
    user_identifier = Column(String(15), nullable=False)
    user_nickname = Column(String, nullable=False)  # 昵称，用来在前台展示的描述性标识符，如"计算机学院16级学生"
    rating_interest = Column(Integer)  # 课堂有趣程度
    rating_knowledge = Column(Integer)  # 是否学到了新的知识
    rating_attendance = Column(Integer)  # 出勤严格程度（是否点名）
    comments = Column(String)  # 文字评价
