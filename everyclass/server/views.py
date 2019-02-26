import os
import time

from flask import Blueprint, Response, jsonify, redirect, render_template, request, url_for

from everyclass.server.config import get_config

main_blueprint = Blueprint('main', __name__)


@main_blueprint.route('/')
def main():
    """首页"""
    return render_template('common/index.html')


@main_blueprint.route('/sleep')
def sleep():
    """休眠测试"""
    time.sleep(50)
    return render_template('common/index.html')


@main_blueprint.route('/about')
def about():
    """关于页面"""
    return render_template('common/about.html')


@main_blueprint.route('/guide')
def guide():
    """帮助页面"""
    return render_template('common/guide.html')


@main_blueprint.route('/testing')
def testing():
    """测试页面"""
    return render_template('testing.html')


@main_blueprint.route('/donate')
def donate():
    """点击发送邮件后的捐助页面"""
    return render_template('common/donate.html')


@main_blueprint.route('/_healthCheck')
def health_check():
    """健康检查"""
    return jsonify({"status": "ok"})


@main_blueprint.route("/_maintenance")
def enter_maintenance():
    config = get_config()
    auth = request.authorization
    if auth \
            and auth.username in config.MAINTENANCE_CREDENTIALS \
            and config.MAINTENANCE_CREDENTIALS[auth.username] == auth.password:
        open(config.MAINTENANCE_FILE, "w+").close()  # maintenance file
        open(os.path.join(os.getcwd(), 'reload'), "w+").close()  # uwsgi reload
        return 'success'
    else:
        return Response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})


@main_blueprint.route("/_exitMaintenance")
def exit_maintenance():
    config = get_config()
    auth = request.authorization
    if auth \
            and auth.username in config.MAINTENANCE_CREDENTIALS \
            and config.MAINTENANCE_CREDENTIALS[auth.username] == auth.password:
        try:
            os.remove(config.MAINTENANCE_FILE)  # remove maintenance file
        except OSError:
            return 'Not in maintenance mode. Ignore command.'
        open(os.path.join(os.getcwd(), 'reload'), "w+").close()  # uwsgi reload
        return 'success'
    else:
        return Response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})


@main_blueprint.app_errorhandler(404)
def page_not_found(error):
    # 404跳转回首页
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
