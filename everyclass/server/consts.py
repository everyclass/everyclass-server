"""
This file defines consts, such as session keys and return messages.
"""

"""
Session keys

All session keys should be defined here
"""
SESSION_LAST_VIEWED_STUDENT = "last_viewed_student"  # a everyclass.server.db.model.StudentSession type
SESSION_STUDENT_TO_REGISTER = "student_to_register"
SESSION_CURRENT_USER = "current_logged_in_user"  # a StudentSession type marking the logged in user
SESSION_PWD_VER_REQ_ID = "verification_req_id"  # current verification req id, a uuid.UUID type
SESSION_EMAIL_VER_REQ_ID = "email_verify_req_id"

"""
错误信息
"""
MSG_INTERNAL_ERROR = "抱歉。遇到了一个内部错误，请稍后重试。"
MSG_NOT_LOGGED_IN = "您还没有登录，请先登录。"
MSG_TIMEOUT = "请求超时，请稍后重试。"
MSG_404 = "没有找到你想要的页面哦。"
MSG_400 = "你发起了一个异常的请求，请回到首页。"
MSG_401 = "您没有权限查看本页面，请先登录。"
MSG_TOKEN_INVALID = "令牌无效或已过期，请重新注册。"
MSG_INVALID_IDENTIFIER = "无效的资源标识，请使用正常方法查询，不要拼接URL。"
MSG_NOT_IN_COURSE = "您不是该门课程的学生，无法评价该门课程。"
MSG_503 = "服务当前不可用，可能是程序员小哥哥正在更新数据哦，请稍后重试。"

"""
flash
"""
MSG_INVALID_CAPTCHA = "人机验证未通过，请先通过验证再提交。"
MSG_VIEW_SCHEDULE_FIRST = "请从个人课表页面进入本页面"

# 用户模块
MSG_WEAK_PASSWORD = "密码过于简单，为了保证账户安全，请使用复杂一些的密码。"
MSG_NOT_REGISTERED = "您尚未注册，请先注册。"
MSG_EMPTY_USERNAME = "请填写学号。"
MSG_WRONG_PASSWORD = "密码错误，请重试。"
MSG_EMPTY_PASSWORD = "密码不能为空。"
MSG_REGISTER_SUCCESS = "注册成功，请牢记你的密码。"
MSG_PWD_DIFFERENT = "两次密码不一致，请重新输入"
MSG_USERNAME_NOT_EXIST = "用户名错误，不存在此学号！"
MSG_ALREADY_REGISTERED = "您已经注册了，请直接登录。"
