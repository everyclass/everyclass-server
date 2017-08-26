"""
日历相关函数
"""
from flask import Blueprint
from flask import request, session, redirect, url_for, render_template
from flask import current_app as app
from everyclass.commons import semester_to_string, semester_to_tuple
from everyclass.mysql_operations import get_classes_for_student, semester

cal_blueprint = Blueprint('cal', __name__)


# 导出日历交换格式文件
@cal_blueprint.route('/calendar')
def generate_ics():
    if request.values.get('id'):
        session['stu_id'] = request.values.get('id')
    if request.values.get('semester'):
        if semester_to_tuple(request.values.get('semester')) in app.config['AVAILABLE_SEMESTERS']:
            session['semester'] = semester_to_tuple(request.values.get('semester'))
    if session.get('stu_id', None):
        from generate_ics import generate_ics
        student_name, student_classes = get_classes_for_student(session['stu_id'])
        generate_ics(session['stu_id'], student_name, student_classes, semester_to_string(semester(), simplify=True),
                     semester())
        return render_template('ics.html', student_id=session['stu_id'],
                               semester=semester_to_string(semester(), simplify=True))
    else:
        return redirect(url_for('main'))
