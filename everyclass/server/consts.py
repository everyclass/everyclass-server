"""
This file defines consts, such as session keys and return messages.
"""

"""
Session keys

All session keys should be defined here
"""
SESSION_LAST_VIEWED_STUDENT = "last_viewed_student"  # a everyclass.server.db.model.Student type
SESSION_CURRENT_USER = "current_logged_in_user"  # a everyclass.server.db.model.Student type marking the logged in user
SESSION_VER_REQ_ID = "verification_req_id"  # current verification req id, a uuid.UUID type

"""
Return messages
"""
MSG_INTERNAL_ERROR = "抱歉。遇到了一个内部错误，请稍后重试或明天再来"
MSG_NOT_LOGGED_IN = "您还没有登录，请先登录"
MSG_TIMEOUT = "请求超时，请稍后重试"
MSG_404 = "资源不存在"
MSG_400 = "你发起了一个异常的请求，请回到首页"
MSG_TOKEN_INVALID = "令牌无效或已过期，请重新注册"

"""
提示信息
"""
MSG_WEAK_PASSWORD = "密码过于简单，请使用复杂一些的密码。"
MSG_INVALID_CAPTCHA = "人类验证未通过，请重试。"
MSG_WRONG_PASSWORD = "密码错误，请重试。"
MSG_REGISTER_SUCCESS = "注册成功，请牢记你的密码。"
