from flask import Blueprint, render_template, send_from_directory, request, jsonify, redirect, url_for, flash
from markupsafe import escape

from everyclass.exceptions import NoClassException, NoStudentException

main_blueprint = Blueprint('main', __name__)


# 首页
@main_blueprint.route('/')
def main():
    return render_template('index.html')


# 帮助
@main_blueprint.route('/faq')
def faq():
    return render_template('faq.html')


# 关于
@main_blueprint.route('/about')
def about():
    return render_template('about.html')


# 帮助
@main_blueprint.route('/guide')
def guide():
    return render_template('guide.html')


# 测试
@main_blueprint.route('/testing')
def testing():
    return render_template('testing.html')


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
