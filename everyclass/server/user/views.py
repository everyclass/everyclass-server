import elasticapm
from flask import Blueprint, current_app as app, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from everyclass.server.db.dao import ID_STATUS_NOT_SENT, IdentityVerificationDAO, UserDAO
from everyclass.server.exceptions import MSG_400, MSG_INTERNAL_ERROR, MSG_TOKEN_INVALID
from everyclass.server.utils.rpc import HttpRpc

user_bp = Blueprint('user', __name__)


@user_bp.route('/login')
def login():
    """
    登录页

    判断学生是否未注册，若已经注册，渲染登陆页。否则跳转到注册页面。
    """
    if not request.args.get('sid'):
        return render_template('common/badRequest.html')

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
    """学生注册页面"""
    from flask import flash

    if not request.args.get('sid'):
        return render_template('common/badRequest.html')

    # if registered, redirect to login page
    if UserDAO.exist(request.args.get('sid')):
        flash('你已经注册了，请直接登录。')
        return redirect('user.login?sid={sid}'.format(sid=request.args.get('sid')))

    return render_template('user/registerChoice.html', sid=request.args.get('sid'))


@user_bp.route('/register/byEmail')
def register_by_email():
    """学生注册-邮件"""
    if not request.args.get('sid'):
        return render_template('common/badRequest.html')

    # contact api-server to get original sid
    with elasticapm.capture_span('rpc_query_student'):
        rpc_result = HttpRpc.call_with_handle_flash('{}/v1/student/{}'.format(app.config['API_SERVER_BASE_URL'],
                                                                              request.args.get('sid')))
        if isinstance(rpc_result, Response):
            return rpc_result
        api_response = rpc_result

    sid_orig = api_response['sid']
    request_id = IdentityVerificationDAO.new_register_request(sid_orig, "email", ID_STATUS_NOT_SENT)

    # call everyclass-auth to send email
    with elasticapm.capture_span('rpc_query_student'):
        rpc_result = HttpRpc.call_with_handle_flash('{}/register_by_email'.format(app.config['AUTH_BASE_URL'],
                                                                                  request.args.get('sid')),
                                                    data={'request_id': request_id,
                                                          'student_id': sid_orig})
        if isinstance(rpc_result, Response):
            return rpc_result
        api_response = rpc_result

    # todo v2.1: 这里当前是骗用户发送成功了，其实有没有成功不知道。前端应该JS来刷新，从“正在发送”变成“已发送”

    if api_response['acknowledged']:
        return render_template('user/emailSent.html', request_id=request_id)
    else:
        return render_template('common/error.html', message=MSG_INTERNAL_ERROR)


@user_bp.route('/register/byPassword', methods=['GET'])
def register_by_password():
    """学生注册-密码"""
    pass
    # todo


@user_bp.route('/emailVerification')
def email_verification():
    """邮箱验证"""
    if not request.args.get("token"):
        return render_template("common/error.html", message=MSG_400)

    rpc_result = HttpRpc.call_with_handle_flash('{}/verify_email_token'.format(app.config['AUTH_BASE_URL'],
                                                                               request.args.get('token')),
                                                data={"email_token": request.args.get("token")})
    if isinstance(rpc_result, Response):
        return rpc_result
    api_response = rpc_result

    if api_response['success']:
        # email verification passed
        IdentityVerificationDAO.email_token_mark_passed(api_response['request_id'])
        return render_template('user/emailVerificationProceed.html', request_id=api_response['request_id'])
    else:
        return render_template("common/error.html", message=MSG_TOKEN_INVALID)
