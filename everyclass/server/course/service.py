from everyclass.server.course.model import Question, Questionnaire, AnswerSheet


def get_classes():
    """从课程池中获得本学期所有课程列表"""

    #
    pass


def get_advice_questions():
    """获得选修课推荐问卷"""
    questionnaire = Questionnaire()

    q0 = Question("你选修课程的主要目的是什么？", ['学习专业外感兴趣的知识', '尽可能提升加权成绩', '结识具有相同兴趣的同学'])
    # KnowledgeProcessor: 使用课程评价中"是否学到了新的知识"进行打分
    # 如果选了'学习专业外感兴趣的知识'，加权为20；
    # 如果选了'结识具有相同兴趣的同学'，加权为10；
    # 如果选了'尽可能提升加权成绩'，加权为5；

    q1 = Question("你期望的成绩区间是？", ['>95', '>90', '>80', '成绩无所谓，学到东西就好'])
    # ScoreProcessor:
    # 如果q1选了'尽可能提升加权成绩'，作为过滤器使用，不符合要求直接过滤；
    # 否则：当满足成绩要求时，满足度=100，每低于要求一档，满足度-20

    q2 = Question("你感兴趣的课程主题是？", ['前沿科技', '社会心理', '户外实践', '文学'], multiple=True)
    # ThemeProcessor：
    # 如果q1选了'学习专业外感兴趣的知识'，表明有非常强的选题倾向性，满足所选分类的课程给100满足度，否则给20
    # 如果q1选择了'结识具有相同兴趣的同学'，满足所选分类给100满足度，否则给50
    # 如果q1选择了'尽可能提升加权成绩'，满足所选分类课程给100满足度，否则给80

    q3 = Question("你希望通过这门课认识更多朋友吗？", ['希望认识更多朋友，无论性别', '希望认识更多异性朋友', '随缘', '不用，我听课就好'])
    q4 = Question("你希望结交", ['男生', '女生'], condition="4:2")
    # FriendProcessor：如果q1选了3，且q4选了2，则严筛，否则粗筛

    q5 = Question("对课堂考勤有什么想法吗？", ['无所谓，反正我每节课都会来', '希望偶尔能请假', '希望老师要求松一点，偶尔不来也问题不大'])
    # AttendanceProcessor：
    # 如果选择了'无所谓，反正我每节课都会来'，加权为-10；
    # 如果选择了'希望偶尔能请假'，给4、5惩罚加权-20；
    # 如果选择了'希望老师要求松一点，偶尔不来也不会被发现'，4、5过滤，3惩罚加权-20

    questionnaire.add_questions([q0, q1, q2, q3, q4, q5])

    return questionnaire


def get_advice_result(answer_sheet: AnswerSheet):
    """根据选修课推荐问卷获得推荐结果"""
    # 从 entity 获得教学班列表

    # 使用过滤器过滤，如果最终结果太多，调用精排方法
    pass
