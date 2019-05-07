from flask import Blueprint

cr_blueprint = Blueprint('course_review', __name__)


@cr_blueprint.route("/<course_id>/<hb_id>")
def show_review(course_id: str, hb_id: str):
    """查看某门课程的评价"""
    pass
