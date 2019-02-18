import elasticapm
from flask import Blueprint, current_app as app, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from everyclass.server.db.dao import UserDAO
from everyclass.server.utils.rpc import HttpRpc

user_bp = Blueprint('user', __name__)


@user_bp.route('/login')
def login():
    """
    登录页

    判断学生是否未注册，若已经注册，渲染登陆页。否则跳转到注册页面。
    """
    if not request.args.get('sid'):
        flash('请求异常，请重新发起查询再登陆')
        return redirect('main.main')

    # contact api-server to get original sid
    with elasticapm.capture_span('rpc_query_student'):
        rpc_result = HttpRpc.call_with_handle_flash('{}/v1/student/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                              request.args.get('sid')))
        if isinstance(rpc_result, Response):
            return rpc_result
        api_response = rpc_result

    # if not registered, redirect to register page
    if not UserDAO.exist(api_response['sid']):
        return redirect(url_for('user.register', sid=request.args.get('sid')))

    return render_template('user/login.html',
                           name=api_response['name'])


@user_bp.route('/register')
def register():
    """学生注册"""
    from flask import flash

    if not request.args.get('sid'):
        flash('请求异常，请重新发起查询再登陆')
        return redirect('main.main')

    # if registered, redirect to login page
    if UserDAO.exist(request.args.get('sid')):
        flash('你已经注册了，请直接登录。')
        return redirect('user.login')

    return render_template('user/register.html',
                           viewing_sid=request.args.get('viewing_sid'))
