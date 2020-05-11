from sqlalchemy import Column, String, Integer, Float

from everyclass.server.utils.db.postgres import Base


class KlassReview(Base):
    __tablename__ = 'klass_review'

    klass_id = Column(String(30))  # 教学班ID
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
