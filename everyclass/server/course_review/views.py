from flask import Blueprint, render_template, session

from everyclass.server.consts import MSG_404, SESSION_CURRENT_USER
from everyclass.server.db.dao import COTeachingClass, CourseReview
from everyclass.server.rpc.api_server import APIServer, teacher_list_to_tid_str

cr_blueprint = Blueprint('course_review', __name__)


@cr_blueprint.route("/<cotc_id>")
def show_review(cotc_id: int):
    """查看某个教学班的评价"""
    cotc_id = int(cotc_id)

    review_info = CourseReview.get_review(cotc_id)
    avg_rate = review_info['avg_rate']
    reviews = review_info['reviews']

    cotc = COTeachingClass.get_doc(cotc_id)
    if not cotc:
        return render_template('common/error.html', message=MSG_404)

    user_is_taking = False

    if session.get(SESSION_CURRENT_USER, None):
        # 检查当前用户是否选了这门课
        student = APIServer.get_student(session[SESSION_CURRENT_USER].sid_orig)
        for semester in student.semesters:
            timetable = APIServer.get_student_timetable(session[SESSION_CURRENT_USER].sid_orig, semester)
            for card in timetable.cards:
                if card.course_id == cotc["course_id"] and cotc["teacher_id_str"] == teacher_list_to_tid_str(
                        card.teachers):
                    user_is_taking = True

    return render_template('course_review/review.html',
                           cotc=cotc,
                           count=review_info['count'],
                           avg_rate=avg_rate,
                           reviews=reviews,
                           user_is_taking=user_is_taking)
