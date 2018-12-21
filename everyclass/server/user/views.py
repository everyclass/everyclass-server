import elasticapm
from flask import current_app as app, flash, redirect, render_template, session, url_for
from werkzeug.wrappers import Response

from everyclass.server.db.dao import UserDAO
from everyclass.server.user import user_bp
from everyclass.server.utils.rpc import HttpRpc


@user_bp.route('/login')
def login():
    """
    登录页

    判断学生是否未注册，若已经注册，渲染登陆页。否则跳转到注册页面。
    """
    if not session.get('viewing_sid'):
        flash('请求异常，请重新发起查询再登陆')
        return redirect('main.main')

    # rpc to get real student id
    with elasticapm.capture_span('rpc_query_student'):
        rpc_result = HttpRpc.call_with_handle_flash('{}/v1/student/{}'.format(app.config['API_SERVER'],
                                                                              session['viewing_sid']))
        if isinstance(rpc_result, Response):
            return rpc_result
        api_response = rpc_result

    # if not registered, redirect to register page
    if not UserDAO.exist(api_response['sid']):
        return redirect(url_for('user.register'))

    return render_template('user/login.html',
                           viewing_sid=api_response['sid'])


@user_bp.route('/register')
def register():
    """学生注册"""
    from flask import session, flash

    if not session.get('viewing_sid'):
        flash('请求异常，请重新发起查询再登陆')
        return redirect('main.main')

    # if registered, redirect to login page
    if UserDAO.exist(session['viewing_sid']):
        flash('你已经注册了，请直接登录。')
        return redirect('user.login')

    return render_template('user/register.html',
                           viewing_sid=session['viewing_sid'])
