from flask import Blueprint, render_template, send_from_directory, request, jsonify, redirect, url_for, flash
from markupsafe import escape

from everyclass.exceptions import NoClassException, NoStudentException

main_blueprint = Blueprint('main', __name__)


@main_blueprint.route('/')
def main():
    """首页"""
    return render_template('index.html')


@main_blueprint.route('/faq')
def faq():
    """帮助页面"""
    return render_template('faq.html')


@main_blueprint.route('/about')
def about():
    """关于页面"""
    return render_template('about.html')


@main_blueprint.route('/guide')
def guide():
    """帮助页面"""
    return render_template('guide.html')


@main_blueprint.route('/testing')
def testing():
    """测试页面"""
    return render_template('testing.html')


@main_blueprint.route('/<student_id>-<semester>.ics')
def get_ics(student_id, semester):
    """serve ics file"""
    # TODO: if file not exist, try to generate one.(implement after ORM and database adjustment)
    return send_from_directory("ics", student_id + "-" + semester + ".ics",
                               as_attachment=True,
                               mimetype='text/calendar')


# 404跳转回首页
@main_blueprint.app_errorhandler(404)
def page_not_found(error):
    # 404 errors are never handled on the blueprint level
    # unless raised from a view func so actual 404 errors,
    # i.e. "no route for it" defined, need to be handled
    # here on the application level
    if request.path.startswith('/api/'):
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return redirect(url_for('main.main'))


# 405跳转回首页
@main_blueprint.app_errorhandler(405)
def method_not_allowed(error):
    return redirect(url_for('main.main'))


@main_blueprint.app_errorhandler(NoStudentException)
def invalid_usage(error):
    flash('没有在数据库中找到你哦。是不是输错了？你刚刚输入的是%s' % escape(error))
    return redirect(url_for('main.main'))


@main_blueprint.app_errorhandler(NoClassException)
def invalid_usage(error):
    flash('没有这门课程哦')
    return redirect(url_for('main.main'))
