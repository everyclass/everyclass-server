import elasticapm
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from zxcvbn import zxcvbn

from everyclass.server import logger
from everyclass.server.consts import MSG_400, MSG_ALREADY_REGISTERED, MSG_EMPTY_PASSWORD, MSG_EMPTY_USERNAME, \
    MSG_INTERNAL_ERROR, MSG_INVALID_CAPTCHA, MSG_NOT_REGISTERED, MSG_PWD_DIFFERENT, MSG_REGISTER_SUCCESS, \
    MSG_TOKEN_INVALID, MSG_USERNAME_NOT_EXIST, MSG_VIEW_SCHEDULE_FIRST, MSG_WEAK_PASSWORD, MSG_WRONG_PASSWORD, \
    SESSION_CURRENT_USER, SESSION_LAST_VIEWED_STUDENT, SESSION_STUDENT_TO_REGISTER, SESSION_VER_REQ_ID
from everyclass.server.db.dao import CalendarTokenDAO, ID_STATUS_PASSWORD_SET, ID_STATUS_PWD_SUCCESS, ID_STATUS_SENT, \
    ID_STATUS_TKN_PASSED, ID_STATUS_WAIT_VERIFY, IdentityVerificationDAO, PrivacySettingsDAO, RedisDAO, \
    SimplePasswordDAO, UserDAO, VisitorDAO
from everyclass.server.models import StudentSession
from everyclass.server.rpc import RpcResourceNotFound, handle_exception_with_error_page
from everyclass.server.rpc.api_server import APIServer
from everyclass.server.rpc.auth import Auth
from everyclass.server.rpc.tencent_captcha import TencentCaptcha
from everyclass.server.utils.decorators import login_required

user_bp = Blueprint('user', __name__)


def _session_save_student_to_register_(student_id: str):
    # 将需要注册的用户并保存到 SESSION_STUDENT_TO_REGISTER
    with elasticapm.capture_span('rpc_get_student'):
        try:
            student = APIServer.get_student(student_id)
        except Exception as e:
            return handle_exception_with_error_page(e)

    session[SESSION_STUDENT_TO_REGISTER] = StudentSession(sid_orig=student.student_id,
                                                          sid=student.student_id_encoded,
                                                          name=student.name)


@user_bp.route('/login', methods=["GET", "POST"])
def login():
    """
    登录页

    判断学生是否未注册，若已经注册，渲染登录页。否则跳转到注册页面。
    """
    if request.method == 'GET':
        if session.get(SESSION_LAST_VIEWED_STUDENT, None):
            user_name = session[SESSION_LAST_VIEWED_STUDENT].name
        else:
            user_name = None

        return render_template('user/login.html', name=user_name)
    else:  # 表单提交
        if not request.form.get("password", None):
            flash(MSG_EMPTY_PASSWORD)
            return redirect(url_for("user.login"))

        # captcha
        if not TencentCaptcha.verify():
            flash(MSG_INVALID_CAPTCHA)
            return redirect(url_for("user.login"))

        if request.form.get("xh", None):  # 已手动填写用户名
            student_id = request.form["xh"]

            # 检查学号是否存在
            try:
                _ = APIServer.get_student(student_id)
            except RpcResourceNotFound:
                flash(MSG_USERNAME_NOT_EXIST)
                return redirect(url_for("user.login"))
            except Exception as e:
                return handle_exception_with_error_page(e)

        else:
            if session.get(SESSION_LAST_VIEWED_STUDENT, None):
                student_id = session[SESSION_LAST_VIEWED_STUDENT].sid_orig  # 没有手动填写，使用获取最后浏览的学生
            else:
                flash(MSG_EMPTY_USERNAME)  # 没有最后浏览的学生，必须填写用户名
                return redirect(url_for("user.login"))

        try:
            success = UserDAO.check_password(student_id, request.form["password"])
        except ValueError:
            # 未注册
            flash(MSG_NOT_REGISTERED)
            _session_save_student_to_register_(student_id)
            return redirect(url_for("user.register"))

        if success:
            try:
                student = APIServer.get_student(student_id)
            except Exception as e:
                return handle_exception_with_error_page(e)

            # 登录态写入 session
            session[SESSION_CURRENT_USER] = StudentSession(sid_orig=student_id,
                                                           sid=student.student_id_encoded,
                                                           name=student.name)
            return redirect(url_for("user.main"))
        else:
            flash(MSG_WRONG_PASSWORD)
            return redirect(url_for("user.login"))


@user_bp.route('/register', methods=["GET", "POST"])
def register():
    """注册：第一步：输入学号"""
    if request.method == 'GET':
        return render_template('user/register.html')
    else:
        if not request.form.get("xh", None):  # 表单为空
            flash(MSG_EMPTY_USERNAME)
            return redirect(url_for("user.register"))

        _session_save_student_to_register_(request.form.get("xh", None))

        # 如果输入的学号已经注册，跳转到登录页面
        if UserDAO.exist(session[SESSION_STUDENT_TO_REGISTER].sid_orig):
            flash(MSG_ALREADY_REGISTERED)
            return redirect(url_for('user.login'))

        return redirect(url_for('user.register_choice'))


@user_bp.route('/register/choice')
def register_choice():
    """注册：第二步：选择注册方式"""
    if not session.get(SESSION_STUDENT_TO_REGISTER, None):  # 步骤异常，跳回第一步
        return redirect(url_for('user.register'))
    return render_template('user/registerChoice.html')


@user_bp.route('/register/byEmail')
def register_by_email():
    """注册：第三步：使用邮箱验证注册"""
    if not session.get(SESSION_STUDENT_TO_REGISTER, None):  # 步骤异常，跳回第一步
        return redirect(url_for('user.register'))

    sid_orig = session[SESSION_STUDENT_TO_REGISTER].sid_orig

    if UserDAO.exist(sid_orig):
        return render_template("common/error.html", message=MSG_ALREADY_REGISTERED)

    request_id = IdentityVerificationDAO.new_register_request(sid_orig, "email", ID_STATUS_SENT)

    with elasticapm.capture_span('send_email'):
        try:
            rpc_result = Auth.register_by_email(request_id, sid_orig)
        except Exception as e:
            return handle_exception_with_error_page(e)

    if rpc_result['acknowledged']:
        return render_template('user/emailSent.html', request_id=request_id)
    else:
        return render_template('common/error.html', message=MSG_INTERNAL_ERROR)


@user_bp.route('/emailVerification', methods=['GET', 'POST'])
def email_verification():
    """注册：邮箱验证"""
    if request.method == 'POST':
        # 设置密码表单提交
        if not session.get(SESSION_VER_REQ_ID, None):
            return render_template("common/error.html", message=MSG_400)

        req = IdentityVerificationDAO.get_request_by_id(session[SESSION_VER_REQ_ID])
        if not req:
            return render_template("common/error.html", message=MSG_TOKEN_INVALID)

        # 由于 SESSION_VER_REQ_ID 在密码验证和邮件验证两个验证方式中共享，当使用密码验证写入了 session 之后，如果马上在邮件验证页面
        # POST，并且此处不做请求状态的判断，将会绕过验证过程直接设置密码
        if req["status"] != ID_STATUS_TKN_PASSED:
            return render_template("common/error.html", message=MSG_TOKEN_INVALID)

        if any(map(lambda x: not request.form.get(x, None), ("password", "password2"))):  # check if empty password
            flash(MSG_EMPTY_PASSWORD)
            return redirect(url_for("user.email_verification"))

        if request.form["password"] != request.form["password2"]:
            flash(MSG_PWD_DIFFERENT)
            return redirect(url_for("user.email_verification"))

        sid_orig = req['sid_orig']

        # 密码强度检查
        pwd_strength_report = zxcvbn(password=request.form["password"])
        if pwd_strength_report['score'] < 2:
            SimplePasswordDAO.new(password=request.form["password"], sid_orig=sid_orig)
            flash(MSG_WEAK_PASSWORD)
            return redirect(url_for("user.email_verification"))

        UserDAO.add_user(sid_orig=sid_orig, password=request.form['password'])
        del session[SESSION_VER_REQ_ID]
        IdentityVerificationDAO.set_request_status(str(req["request_id"]), ID_STATUS_PASSWORD_SET)
        flash(MSG_REGISTER_SUCCESS)

        # 查询 api-server 获得学生基本信息
        try:
            student = APIServer.get_student(sid_orig)
        except Exception as e:
            return handle_exception_with_error_page(e)

        # 登录态写入 session
        session[SESSION_CURRENT_USER] = StudentSession(sid_orig=student.student_id,
                                                       sid=student.student_id_encoded,
                                                       name=student.name)
        return redirect(url_for("user.main"))
    else:
        # 设置密码页面
        if not session.get(SESSION_VER_REQ_ID, None):
            if not request.args.get("token", None):
                return render_template("common/error.html", message=MSG_400)

            with elasticapm.capture_span('verify_email_token'):
                try:
                    rpc_result = Auth.verify_email_token(token=request.args.get("token", None))
                except Exception as e:
                    return handle_exception_with_error_page(e)

            if rpc_result['success']:
                session[SESSION_VER_REQ_ID] = rpc_result['request_id']
                IdentityVerificationDAO.set_request_status(rpc_result['request_id'], ID_STATUS_TKN_PASSED)
                return render_template('user/emailVerificationProceed.html')
            else:
                return render_template("common/error.html", message=MSG_TOKEN_INVALID)
        else:
            # have session
            return render_template('user/emailVerificationProceed.html')


@user_bp.route('/register/byPassword', methods=['GET', 'POST'])
def register_by_password():
    """注册：第三步：使用密码验证注册"""
    if request.method == 'POST':
        if any(map(lambda x: not request.form.get(x, None), ("password", "password2", "jwPassword"))):
            flash(MSG_EMPTY_PASSWORD)
            return redirect(url_for("user.register_by_password"))

        # 密码强度检查
        pwd_strength_report = zxcvbn(password=request.form["password"])
        if pwd_strength_report['score'] < 2:
            SimplePasswordDAO.new(password=request.form["password"],
                                  sid_orig=session[SESSION_STUDENT_TO_REGISTER].sid_orig)
            flash(MSG_WEAK_PASSWORD)
            return redirect(url_for("user.register_by_password"))

        if request.form["password"] != request.form["password2"]:
            flash(MSG_PWD_DIFFERENT)
            return redirect(url_for("user.register_by_password"))

        # captcha
        if not TencentCaptcha.verify():
            flash(MSG_INVALID_CAPTCHA)
            return redirect(url_for("user.register_by_password"))

        request_id = IdentityVerificationDAO.new_register_request(session[SESSION_STUDENT_TO_REGISTER].sid_orig,
                                                                  "password",
                                                                  ID_STATUS_WAIT_VERIFY,
                                                                  password=request.form["password"])

        # call everyclass-auth to verify password
        with elasticapm.capture_span('register_by_password'):
            try:
                rpc_result = Auth.register_by_password(request_id=str(request_id),
                                                       student_id=session[SESSION_STUDENT_TO_REGISTER].sid_orig,
                                                       password=request.form["jwPassword"])
            except Exception as e:
                return handle_exception_with_error_page(e)

        if rpc_result['acknowledged']:
            session[SESSION_VER_REQ_ID] = request_id
            return render_template('user/passwordRegistrationPending.html', request_id=request_id)
        else:
            return render_template('common/error.html', message=MSG_INTERNAL_ERROR)
    else:
        # show password registration page
        if not session.get(SESSION_STUDENT_TO_REGISTER, None):
            return render_template('common/error.html', message=MSG_VIEW_SCHEDULE_FIRST)

        return render_template("user/passwordRegistration.html", name=session[SESSION_STUDENT_TO_REGISTER].name)


@user_bp.route('/register/passwordStrengthCheck', methods=["POST"])
def password_strength_check():
    """AJAX 密码强度检查"""
    if request.form.get("password", None):
        # 密码强度检查
        pwd_strength_report = zxcvbn(password=request.form["password"])
        if pwd_strength_report['score'] < 2:
            return jsonify({"strong": False,
                            "score" : pwd_strength_report['score']})
        else:
            return jsonify({"strong": True,
                            "score" : pwd_strength_report['score']})
    return jsonify({"invalid_request": True})


@user_bp.route('/register/byPassword/statusRefresh')
def register_by_password_status():
    """AJAX 刷新教务验证状态"""
    if not request.args.get("request", None) or not isinstance(request.args["request"], str):
        return "Invalid request"
    req = IdentityVerificationDAO.get_request_by_id(request.args.get("request"))
    if not req:
        return "Invalid request"
    if req["verification_method"] != "password":
        logger.warn("Non-password verification request is trying get status from password interface")
        return "Invalid request"

    # fetch status from everyclass-auth
    with elasticapm.capture_span('get_result'):
        try:
            rpc_result = Auth.get_result(str(request.args.get("request")))
        except Exception as e:
            return handle_exception_with_error_page(e)

    if rpc_result['success']:  # 密码验证通过，设置请求状态并新增用户
        IdentityVerificationDAO.set_request_status(str(request.args.get("request")), ID_STATUS_PWD_SUCCESS)

        verification_req = IdentityVerificationDAO.get_request_by_id(str(request.args.get("request")))

        # 从 api-server 查询学生基本信息
        try:
            student = APIServer.get_student(verification_req["sid_orig"])
        except Exception as e:
            return handle_exception_with_error_page(e)

        # 添加用户
        try:
            UserDAO.add_user(sid_orig=verification_req["sid_orig"], password=verification_req["password"],
                             password_encrypted=True)
        except ValueError:
            pass  # 已经注册成功，但不知为何进入了中间状态，没有执行下面的删除 session 的代码，并且用户刷新页面

        # write login state to session
        flash(MSG_REGISTER_SUCCESS)
        if SESSION_VER_REQ_ID in session:
            del session[SESSION_VER_REQ_ID]
        session[SESSION_CURRENT_USER] = StudentSession(sid_orig=student.student_id,
                                                       sid=student.student_id_encoded,
                                                       name=student.name)

        return jsonify({"message": "SUCCESS"})
    elif rpc_result["message"] in ("PASSWORD_WRONG", "INTERNAL_ERROR"):
        return jsonify({"message": rpc_result["message"]})
    else:
        return jsonify({"message": "NEXT_TIME"})


@user_bp.route('/register/byPassword/success')
def register_by_password_success():
    """验证成功后跳转到用户首页"""
    return redirect(url_for("user.main"))


@user_bp.route('/main')
@login_required
def main():
    """用户主页"""
    try:
        student = APIServer.get_student(session[SESSION_CURRENT_USER].sid_orig)
    except Exception as e:
        return handle_exception_with_error_page(e)

    return render_template('user/main.html',
                           name=session[SESSION_CURRENT_USER].name,
                           student_id_encoded=session[SESSION_CURRENT_USER].sid,
                           last_semester=student.semesters[-1] if student.semesters else None,
                           privacy_level=PrivacySettingsDAO.get_level(session[SESSION_CURRENT_USER].sid_orig))


@user_bp.route('/logout')
@login_required
def logout():
    """用户退出登录"""
    del session[SESSION_CURRENT_USER]
    flash("退出登录成功。")
    return redirect(url_for('main.main'))


@user_bp.route('/setPreference', methods=["POST"])
@login_required
def js_set_preference():
    """AJAX更新偏好设置"""
    if request.form.get("privacyLevel", None):
        # update privacy level
        privacy_level = int(request.form["privacyLevel"])
        if privacy_level not in (0, 1, 2):
            logger.warn("Received malformed set preference request. privacyLevel value not valid.")
            return jsonify({"acknowledged": False,
                            "message"     : "Invalid value"})

        PrivacySettingsDAO.set_level(session[SESSION_CURRENT_USER].sid_orig, privacy_level)
    return jsonify({"acknowledged": True})


@user_bp.route('/resetCalendarToken')
@login_required
def reset_calendar_token():
    """重置日历订阅令牌"""
    CalendarTokenDAO.reset_tokens(session[SESSION_CURRENT_USER].sid_orig)
    flash("日历订阅令牌重置成功")
    return redirect(url_for("user.main"))


@user_bp.route('/visitors')
@login_required
def visitors():
    """我的访客页面"""
    visitor_list = VisitorDAO.get_visitors(session[SESSION_CURRENT_USER].sid_orig)
    visitor_count = RedisDAO.get_visitor_count(session[SESSION_CURRENT_USER].sid_orig)
    return render_template("user/visitors.html", visitor_list=visitor_list, visitor_count=visitor_count)
