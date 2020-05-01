from typing import Dict

from flask import Blueprint, escape, flash, redirect, render_template, request, session, url_for

from everyclass.rpc.entity import teacher_list_to_tid_str
from everyclass.server.entity import service as entity_service
from everyclass.server.utils.db.dao import COTeachingClass, CourseReview
from everyclass.server.utils.web_consts import MSG_404, MSG_NOT_IN_COURSE, SESSION_CURRENT_USER
from everyclass.server.utils.web_helpers import login_required, handle_exception_with_error_page

course_bp = Blueprint('course', __name__)


def is_taking(cotc: Dict) -> bool:
    """检查当前用户是否选了这门课"""
    user_is_taking = False

    if session.get(SESSION_CURRENT_USER, None):
        # 检查当前用户是否选了这门课
        student = entity_service.get_student(session[SESSION_CURRENT_USER].identifier)
        for semester in sorted(student.semesters, reverse=True):  # 新学期可能性大，学期从新到旧查找
            timetable = entity_service.get_student_timetable(session[SESSION_CURRENT_USER].identifier, semester)
            for card in timetable.cards:
                if card.course_id == cotc["course_id"] and cotc["teacher_id_str"] == teacher_list_to_tid_str(
                        card.teachers):
                    user_is_taking = True
                    break
            if user_is_taking:
                break
    return user_is_taking


@course_bp.route("/<cotc_id>")
def show_review(cotc_id: int):
    """查看某个教学班的评价"""
    cotc_id = int(cotc_id)

    review_info = CourseReview.get_review(cotc_id)
    avg_rate = review_info['avg_rate']
    reviews = review_info['reviews']

    cotc = COTeachingClass.get_doc(cotc_id)
    if not cotc:
        return render_template('common/error.html', message=MSG_404)

    if session.get(SESSION_CURRENT_USER, None) \
            and CourseReview.get_my_review(cotc_id=cotc_id, student_id=session[SESSION_CURRENT_USER].identifier):
        reviewed_by_me = True
    else:
        reviewed_by_me = False
    return render_template('course_review/review.html',
                           cotc=cotc,
                           count=review_info['count'],
                           avg_rate=avg_rate,
                           reviews=reviews,
                           user_is_taking=is_taking(cotc),
                           reviewed_by_me=reviewed_by_me)


@course_bp.route("/<cotc_id>/_editMine", methods=["POST", "GET"])
@login_required
def edit_review(cotc_id: int):
    """进行评价"""
    cotc_id = int(cotc_id)
    cotc = COTeachingClass.get_doc(cotc_id)
    if not cotc:
        return render_template('common/error.html', message=MSG_404)

    if not is_taking(cotc):
        return render_template('common/error.html', message=MSG_NOT_IN_COURSE)

    if request.method == 'GET':  # 展示表单页面
        doc = CourseReview.get_my_review(cotc_id=cotc_id, student_id=session[SESSION_CURRENT_USER].identifier)  # 已经评分
        if doc:
            my_rating = doc["rate"]
            my_review = doc["review"]
        else:
            my_rating = 0
            my_review = ""
        return render_template("course_review/add_review.html",
                               cotc=cotc,
                               my_rating=my_rating,
                               my_review=my_review)
    else:  # 表单提交
        if not request.form.get("rate", None) or request.form["rate"] not in map(str, (1, 2, 3, 4, 5)):
            flash("请填写正确的评分")
            return redirect(url_for("course.edit_review", cotc_id=cotc_id))
        if not request.form.get("review", None):
            flash("请填写评价")
            return redirect(url_for("course.edit_review", cotc_id=cotc_id))
        if len(request.form["review"]) > 200:
            flash("评论不要超过200个字符")
            return redirect(url_for("course.edit_review", cotc_id=cotc_id))

        try:
            student = entity_service.get_student(session[SESSION_CURRENT_USER].identifier)
        except Exception as e:
            return handle_exception_with_error_page(e)

        fuzzy_name = student.klass + "学生"

        CourseReview.edit_my_review(cotc_id,
                                    session[SESSION_CURRENT_USER].identifier,
                                    int(request.form["rate"]),
                                    escape(request.form["review"]),
                                    fuzzy_name)
        flash("评分成功。")
        return redirect(url_for("course.show_review", cotc_id=cotc_id))
