from ddtrace import tracer
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from everyclass.rpc.tencent_captcha import TencentCaptcha
from everyclass.server import logger
from everyclass.server.calendar import service as calendar_service
from everyclass.server.consts import MSG_400, MSG_ALREADY_REGISTERED, MSG_EMPTY_PASSWORD, MSG_EMPTY_USERNAME, \
    MSG_INVALID_CAPTCHA, MSG_NOT_REGISTERED, MSG_PWD_DIFFERENT, MSG_REGISTER_SUCCESS, \
    MSG_TOKEN_INVALID, MSG_USERNAME_NOT_EXIST, MSG_VIEW_SCHEDULE_FIRST, MSG_WEAK_PASSWORD, MSG_WRONG_PASSWORD, \
    SESSION_CURRENT_USER, SESSION_EMAIL_VER_REQ_ID, SESSION_LAST_VIEWED_STUDENT, SESSION_PWD_VER_REQ_ID, \
    SESSION_USER_REGISTERING
from everyclass.server.entity import service as entity_service
from everyclass.server.user import service as user_service
from everyclass.server.utils.decorators import login_required
from everyclass.server.utils.err_handle import handle_exception_with_error_page
from everyclass.server.utils.session import USER_TYPE_TEACHER, USER_TYPE_STUDENT, UserSession

user_bp = Blueprint('user', __name__)


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
        if not TencentCaptcha.verify_old():
            flash(MSG_INVALID_CAPTCHA)
            return redirect(url_for("user.login"))

        if request.form.get("xh", None):  # 已手动填写用户名
            identifier = request.form["xh"]

            # 检查学号/教工号是否存在
            try:
                entity_service.get_people_info(identifier)
            except entity_service.PeopleNotFoundError:
                flash(MSG_USERNAME_NOT_EXIST)
                return redirect(url_for("user.login"))
            except Exception as e:
                return handle_exception_with_error_page(e)

        else:
            if session.get(SESSION_LAST_VIEWED_STUDENT, None):
                identifier = session[SESSION_LAST_VIEWED_STUDENT].sid_orig  # 没有手动填写，使用获取最后浏览的学生
            else:
                flash(MSG_EMPTY_USERNAME)  # 没有最后浏览的学生，必须填写用户名
                return redirect(url_for("user.login"))

        try:
            success = user_service.check_password(identifier, request.form["password"])
        except user_service.UserNotExists:
            # 未注册
            flash(MSG_NOT_REGISTERED)
            return redirect(url_for("user.register"))

        if success:
            try:
                _set_current_user(identifier)
            except Exception as e:
                return handle_exception_with_error_page(e)

            return redirect(url_for("user.main"))
        else:
            flash(MSG_WRONG_PASSWORD)
            return redirect(url_for("user.login"))


@user_bp.route('/register', methods=["GET", "POST"])
def register():
    """注册：第一步：输入学号或教工号"""
    if request.method == 'GET':
        return render_template('user/register.html')
    else:
        if not request.form.get("xh", None):  # 表单为空
            flash(MSG_EMPTY_USERNAME)
            return redirect(url_for("user.register"))
        # todo: change frontend to tell users that teachers can register now
        # 检查学号/教工号是否存在
        try:
            entity_service.get_people_info(request.form.get("xh", None))
        except entity_service.PeopleNotFoundError:
            flash(MSG_USERNAME_NOT_EXIST)
            return redirect(url_for("user.register"))
        except Exception as e:
            return handle_exception_with_error_page(e)

        r = _set_current_registering(request.form.get("xh", None))
        if r:
            return r

        # 如果输入的学号或教工号已经注册，跳转到登录页面
        if user_service.user_exist(session[SESSION_USER_REGISTERING].identifier):
            flash(MSG_ALREADY_REGISTERED)
            return redirect(url_for('user.login'))

        return redirect(url_for('user.register_choice'))


@user_bp.route('/register/choice')
def register_choice():
    """注册：第二步：选择注册方式"""
    if not session.get(SESSION_USER_REGISTERING, None):  # 步骤异常，跳回第一步
        return redirect(url_for('user.register'))
    return render_template('user/registerChoice.html')


@user_bp.route('/register/byEmail')
def register_by_email():
    """注册：第三步：使用邮箱验证注册"""
    if not session.get(SESSION_USER_REGISTERING, None):  # 步骤异常，跳回第一步
        return redirect(url_for('user.register'))

    identifier = session[SESSION_USER_REGISTERING].identifier

    try:
        request_id = user_service.register_by_email(identifier)
    except Exception as e:
        return handle_exception_with_error_page(e)
    else:
        return render_template('user/emailSent.html', request_id=request_id)


@user_bp.route('/emailVerification', methods=['GET', 'POST'])
def email_verification():
    """注册：邮箱验证"""
    if request.method == 'POST':
        # 设置密码表单提交
        if not session.get(SESSION_EMAIL_VER_REQ_ID, None):
            return render_template("common/error.html", message=MSG_400)
        if any(map(lambda x: not request.form.get(x, None), ("password", "password2"))):  # check if empty password
            flash(MSG_EMPTY_PASSWORD)
            return redirect(url_for("user.email_verification"))
        if request.form["password"] != request.form["password2"]:
            flash(MSG_PWD_DIFFERENT)
            return redirect(url_for("user.email_verification"))

        try:
            identifier = user_service.register_by_email_set_password(session[SESSION_EMAIL_VER_REQ_ID], request.form["password"])
        except user_service.IdentityVerifyRequestNotFoundError:
            return render_template("common/error.html", message=MSG_TOKEN_INVALID)
        except user_service.PasswordTooWeakError:
            flash(MSG_WEAK_PASSWORD)
            return redirect(url_for("user.email_verification"))
        except user_service.AlreadyRegisteredError:
            flash(MSG_ALREADY_REGISTERED)
            return redirect(url_for("user.email_verification"))

        del session[SESSION_EMAIL_VER_REQ_ID]
        flash(MSG_REGISTER_SUCCESS)

        # 查询 entity 获得基本信息
        try:
            _set_current_user(identifier)
        except Exception as e:
            return handle_exception_with_error_page(e)
        return redirect(url_for("user.main"))
    else:
        if not request.args.get("token", None) and session.get(SESSION_EMAIL_VER_REQ_ID, None):
            return render_template("common/error.html", message=MSG_400)
        if request.args.get("token", None):
            try:
                request_id = user_service.register_by_email_token_check(request.args.get("token"))
            except Exception as e:
                return handle_exception_with_error_page(e)

            session[SESSION_EMAIL_VER_REQ_ID] = request_id
        return render_template('user/emailVerificationProceed.html')


@user_bp.route('/register/byPassword', methods=['GET', 'POST'])
def register_by_password():
    """注册：第三步：使用密码验证注册"""
    if not session.get(SESSION_USER_REGISTERING, None):
        return render_template('common/error.html', message=MSG_VIEW_SCHEDULE_FIRST)

    if request.method == 'POST':
        if any(map(lambda x: not request.form.get(x, None), ("password", "password2", "jwPassword"))):
            flash(MSG_EMPTY_PASSWORD)
            return redirect(url_for("user.register_by_password"))
        if request.form["password"] != request.form["password2"]:
            flash(MSG_PWD_DIFFERENT)
            return redirect(url_for("user.register_by_password"))
        # captcha
        if not TencentCaptcha.verify_old():
            flash(MSG_INVALID_CAPTCHA)
            return redirect(url_for("user.register_by_password"))

        try:
            request_id = user_service.register_by_password(request.form["jwPassword"],
                                                           request.form["password"],
                                                           session.get(SESSION_USER_REGISTERING, None).identifier)
        except user_service.PasswordTooWeakError:
            flash(MSG_WEAK_PASSWORD)
            return redirect(url_for("user.register_by_password"))
        except Exception as e:
            return handle_exception_with_error_page(e)

        session[SESSION_PWD_VER_REQ_ID] = request_id
        return render_template('user/passwordRegistrationPending.html', request_id=request_id)
    else:
        # show password registration page
        return render_template("user/passwordRegistration.html", name=session[SESSION_USER_REGISTERING].name)


@user_bp.route('/register/passwordStrengthCheck', methods=["POST"])
def password_strength_check():
    """AJAX 密码强度检查"""
    if request.form.get("password", None):
        # 密码强度检查
        score = user_service.score_password_strength(request.form["password"])
        if score < 2:
            return jsonify({"strong": False,
                            "score": score})
        else:
            return jsonify({"strong": True,
                            "score": score})
    return jsonify({"invalid_request": True})


@user_bp.route('/register/byPassword/statusRefresh')
def register_by_password_status():
    """AJAX 刷新教务验证状态"""
    if not request.args.get("request", None) or not isinstance(request.args["request"], str):
        return "Invalid request"

    try:
        success, message, identifier = user_service.register_by_password_status_refresh(request.args.get("request"))

        if success:
            # write login state to session
            flash(MSG_REGISTER_SUCCESS)
            if SESSION_PWD_VER_REQ_ID in session:
                del session[SESSION_PWD_VER_REQ_ID]

            _set_current_user(identifier)  # potential uncaught error
            return jsonify({"message": "SUCCESS"})
        elif message in ("PASSWORD_WRONG", "INTERNAL_ERROR", "INVALID_REQUEST_ID"):
            return jsonify({"message": message})
        else:
            return jsonify({"message": "NEXT_TIME"})

    except user_service.IdentityVerifyRequestNotFoundError:
        return "Invalid request"
    except user_service.IdentityVerifyMethodNotExpectedError:
        return "Invalid request"
    except user_service.AlreadyRegisteredError:
        # 已经注册成功，但不知为何（可能是网络原因）进入了中间状态，没有执行下面的删除 session 的代码，并且用户刷新页面
        if SESSION_PWD_VER_REQ_ID in session:
            del session[SESSION_PWD_VER_REQ_ID]
        flash(MSG_ALREADY_REGISTERED)
        return redirect(url_for('user.login'))


def _set_current_user(identifier: str):
    """
    设置session中当前登录用户为参数中的学号

    :param identifier: 学号或教工号
    """
    is_student, people = entity_service.get_people_info(identifier)
    session[SESSION_CURRENT_USER] = UserSession(user_type=USER_TYPE_STUDENT if is_student else USER_TYPE_TEACHER,
                                                identifier=people.student_id if is_student else people.teacher_id,
                                                identifier_encoded=people.student_id_encoded if is_student else people.teacher_id_encoded,
                                                name=people.name)


def _set_current_registering(identifier: str):
    """
    将正在注册的用户并保存到 SESSION_USER_REGISTERING

    :param identifier: 学号或教工号
    :return: None if there is no exception. Otherwise return an error page.
    """
    with tracer.trace('rpc_get_student'):
        try:
            is_student, people = entity_service.get_people_info(identifier)
            session[SESSION_USER_REGISTERING] = UserSession(user_type=USER_TYPE_STUDENT if is_student else USER_TYPE_TEACHER,
                                                            identifier=people.student_id if is_student else people.teacher_id,
                                                            identifier_encoded=people.student_id_encoded if is_student else people.teacher_id_encoded,
                                                            name=people.name)
        except Exception as e:
            return handle_exception_with_error_page(e)


@user_bp.route('/register/byPassword/success')
def register_by_password_success():
    """验证成功后跳转到用户首页"""
    return redirect(url_for("user.main"))


@user_bp.route('/main')
@login_required
def main():
    """用户主页"""
    try:
        is_student, student = entity_service.get_people_info(session[SESSION_CURRENT_USER].identifier)
        if not is_student:
            return "Teacher is not supported at the moment. Stay tuned!"
    except Exception as e:
        return handle_exception_with_error_page(e)

    return render_template('user/main.html',
                           name=session[SESSION_CURRENT_USER].name,
                           student_id_encoded=session[SESSION_CURRENT_USER].identifier_encoded,
                           last_semester=student.semesters[-1] if student.semesters else None,
                           privacy_level=user_service.get_privacy_level(session[SESSION_CURRENT_USER].identifier))


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
                            "message": "Invalid value"})

        user_service.set_privacy_level(session[SESSION_CURRENT_USER].identifier, privacy_level)
    return jsonify({"acknowledged": True})


@user_bp.route('/resetCalendarToken')
@login_required
def reset_calendar_token():
    """重置日历订阅令牌"""
    calendar_service.reset_calendar_tokens(session[SESSION_CURRENT_USER].identifier)
    flash("日历订阅令牌重置成功")
    return redirect(url_for("user.main"))


@user_bp.route('/visitors')
@login_required
def visitors():
    """我的访客页面"""
    visitor_list = user_service.get_visitors(session[SESSION_CURRENT_USER].identifier)
    visitor_count = user_service.get_visitor_count(session[SESSION_CURRENT_USER].identifier)
    return render_template("user/visitors.html", visitor_list=visitor_list, visitor_count=visitor_count)
