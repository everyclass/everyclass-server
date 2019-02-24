import elasticapm
from flask import Blueprint, current_app as app, flash, redirect, render_template, request, session, url_for
from zxcvbn import zxcvbn

from everyclass.server.consts import MSG_400, MSG_INTERNAL_ERROR, MSG_NOT_LOGGED_IN, MSG_TOKEN_INVALID, \
    SESSION_CURRENT_USER, SESSION_LAST_VIEWED_STUDENT, SESSION_VER_REQ_ID
from everyclass.server.db.dao import ID_STATUS_PASSWORD_SET, ID_STATUS_SENT, ID_STATUS_TKN_PASSED, \
    IdentityVerificationDAO, SimplePasswordDAO, UserDAO
from everyclass.server.utils.rpc import HttpRpc

user_bp = Blueprint('user', __name__)


@user_bp.route('/login', methods=["GET", "POST"])
def login():
    """
    登录页

    判断学生是否未注册，若已经注册，渲染登陆页。否则跳转到注册页面。
    """
    if not session.get(SESSION_LAST_VIEWED_STUDENT, None):
        return render_template('common/error.html', message=MSG_400)
    if request.method == 'GET':
        # if not registered, redirect to register page
        if not UserDAO.exist(session[SESSION_LAST_VIEWED_STUDENT].sid_orig):
            return redirect(url_for('user.register'))

        return render_template('user/login.html', name=session[SESSION_LAST_VIEWED_STUDENT].name)
    else:
        if request.form.get("password", None):
            success = UserDAO.check_password(session[SESSION_LAST_VIEWED_STUDENT].sid_orig, request.form["password"])
            if success:
                session[SESSION_CURRENT_USER] = session[SESSION_LAST_VIEWED_STUDENT]
                return redirect(url_for("user.main"))
            else:
                flash("密码错误，请重试。")
                return redirect(url_for("user.login"))
        return render_template('common/error.html', message=MSG_400)


@user_bp.route('/register')
def register():
    """学生注册页面"""
    from flask import flash

    if not session.get(SESSION_LAST_VIEWED_STUDENT, None):
        return render_template('common/error.html', message=MSG_400)

    # if registered, redirect to login page
    if UserDAO.exist(session[SESSION_LAST_VIEWED_STUDENT].sid_orig):
        flash('你已经注册了，请直接登录。')
        return redirect(url_for('user.login'))

    return render_template('user/registerChoice.html')


@user_bp.route('/register/byEmail')
def register_by_email():
    """学生注册-邮件"""
    if not session.get(SESSION_LAST_VIEWED_STUDENT, None):
        return render_template('common/error.html', message=MSG_400)

    sid_orig = session[SESSION_LAST_VIEWED_STUDENT].sid_orig

    if UserDAO.exist(sid_orig):
        return render_template("common/error.html", message="您已经注册过了，请勿重复注册。")

    request_id = IdentityVerificationDAO.new_register_request(sid_orig, "email", ID_STATUS_SENT)

    # call everyclass-auth to send email
    with elasticapm.capture_span('rpc_send_email'):
        rpc_result = HttpRpc.call_with_error_page('{}/register_by_email'.format(app.config['AUTH_BASE_URL']),
                                                  data={'request_id': str(request_id),
                                                        'student_id': sid_orig},
                                                  method='POST')
        if isinstance(rpc_result, str):
            return rpc_result
        api_response = rpc_result

    # todo v2.1: 这里当前是骗用户发送成功了，其实有没有成功不知道。前端应该JS来刷新，从“正在发送”变成“已发送”

    if api_response['acknowledged']:
        return render_template('user/emailSent.html', request_id=request_id)
    else:
        return render_template('common/error.html', message=MSG_INTERNAL_ERROR)


@user_bp.route('/emailVerification', methods=['GET', 'POST'])
def email_verification():
    """邮箱验证及注册"""
    if request.method == 'POST':
        # 设置密码表单提交
        if not session.get(SESSION_VER_REQ_ID, None):
            return render_template("common/error.html", message=MSG_400)

        req = IdentityVerificationDAO.get_request_by_id(session[SESSION_VER_REQ_ID])
        if not req:
            return render_template("common/error.html", message=MSG_TOKEN_INVALID)

        # password already set
        if req["status"] == ID_STATUS_PASSWORD_SET:
            return render_template("common/error.html", message=MSG_TOKEN_INVALID)

        if not request.form.get("password", None):  # check if empty password
            flash("请输入密码")
            return redirect(url_for("user.email_verification"))

        sid_orig = req['sid_orig']

        # password strength check
        pwd_strength_report = zxcvbn(password=request.form["password"])
        if pwd_strength_report['score'] < 3:
            SimplePasswordDAO.new(password=request.form["password"], sid_orig=sid_orig)
            flash("密码过于简单，请使用复杂一些的密码。")
            return redirect(url_for("user.email_verification"))

        UserDAO.add_user(sid_orig=sid_orig, password=request.form['password'])
        del session[SESSION_VER_REQ_ID]
        IdentityVerificationDAO.set_request_status(str(req["request_id"]), ID_STATUS_PASSWORD_SET)
        flash("注册成功，请牢记你的密码。")

        if session[SESSION_LAST_VIEWED_STUDENT].sid_orig == sid_orig:
            # it's difficult to get a student's basic information with api-server at the moment.
            # when api-server implemented GET /student/xxx, this redirect part could be improved.
            session[SESSION_CURRENT_USER] = session[SESSION_LAST_VIEWED_STUDENT]
            return redirect(url_for("user.main"))
        else:
            return redirect(url_for("main.main"))
    else:
        # 设置密码页面
        if not session.get(SESSION_VER_REQ_ID, None):
            if not request.args.get("token", None):
                return render_template("common/error.html", message=MSG_400)
            rpc_result = HttpRpc.call_with_error_page('{}/verify_email_token'.format(app.config['AUTH_BASE_URL']),
                                                      data={"email_token": request.args.get("token", None)},
                                                      method='POST')
            if isinstance(rpc_result, str):
                return rpc_result
            api_response = rpc_result

            if api_response['success']:
                session[SESSION_VER_REQ_ID] = api_response['request_id']
                IdentityVerificationDAO.set_request_status(api_response['request_id'], ID_STATUS_TKN_PASSED)
                return render_template('user/emailVerificationProceed.html')
            else:
                return render_template("common/error.html", message=MSG_TOKEN_INVALID)
        else:
            # have session
            return render_template('user/emailVerificationProceed.html')


@user_bp.route('/register/byPassword', methods=['GET'])
def register_by_password():
    """学生注册-密码"""
    pass
    # todo


@user_bp.route('/main')
def main():
    """用户主页"""
    if not session.get(SESSION_CURRENT_USER, None):
        return render_template('common/error.html', message=MSG_NOT_LOGGED_IN)

    return render_template('user/main.html', name=session[SESSION_CURRENT_USER].name)


@user_bp.route('/logout')
def logout():
    """用户退出登录"""
    if session.get(SESSION_CURRENT_USER, None):
        del session[SESSION_CURRENT_USER]
        flash("退出登录成功。")
    return redirect(url_for('main.main'))
