"""
This file defines consts, such as session keys and return messages.
"""

"""
Session keys

All session keys should be defined here
"""
SESSION_LAST_VIEWED_STUDENT = "last_viewed_student"  # a everyclass.server.db.model.Student type
SESSION_CURRENT_USER = "current_logged_in_user"  # a everyclass.server.db.model.Student type marking the logged in user

"""
Return messages
"""
MSG_INTERNAL_ERROR = "抱歉。遇到了一个内部错误，请稍后重试或明天再来"
MSG_NOT_LOGGED_IN = "您还没有登录，请先登录。"
MSG_TIMEOUT = "请求超时，请稍后重试"
MSG_404 = "资源不存在"
MSG_400 = "你发起了一个异常的请求，请回到首页"
MSG_TOKEN_INVALID = "令牌无效或已过期，请重新开始注册流程"
