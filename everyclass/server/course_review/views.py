from flask import Blueprint, render_template

from everyclass.server.db.dao import COTeachingClass, CourseReview

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
        return 'invalid request'

    return render_template('course_review/review.html',
                           cotc=cotc,
                           count=review_info['count'],
                           avg_rate=avg_rate,
                           reviews=reviews)
