from everyclass.server.course.model import Questionnaire, AnswerSheet, CourseMeta


def get_class_categories():
    """获得所有课程分类及课程"""
    return CourseMeta.get_categories()


def get_advice_questions():
    """获得选修课推荐问卷"""
    questionnaire = Questionnaire.get()
    return questionnaire


def get_advice_result(answer_sheet: AnswerSheet):
    return answer_sheet.get_advice()
