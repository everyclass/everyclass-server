import gc
import logging
import os

from datadog import DogStatsd
from ddtrace import tracer
from flask import Flask, g, render_template, request, session
from flask_cdn import CDN
from flask_moment import Moment
from htmlmin import minify
from raven.contrib.flask import Sentry
from raven.handlers.logging import SentryHandler

from everyclass.server.utils import web_consts
from everyclass.server.utils.common_helpers import plugin_available
from everyclass.server.utils.session import EncryptedSessionInterface

logger = logging.getLogger(__name__)
sentry = Sentry()
statsd = None
__app = None

try:
    import uwsgidecorators

    """
    使用 `uwsgidecorators.postfork` 装饰的函数会在 fork() 后的**每一个**子进程内被执行，执行顺序与这里的定义顺序一致
    """

    @uwsgidecorators.postfork
    def enable_gc():
        """重新启用垃圾回收"""
        gc.set_threshold(700)

    @uwsgidecorators.postfork
    def init_plugins():
        """初始化日志、错误追踪、打点插件"""
        from everyclass.rpc import init as init_rpc
        from everyclass.common.flask import print_config

        # Sentry
        if plugin_available("sentry"):
            sentry.init_app(app=__app)
            sentry_handler = SentryHandler(sentry.client)
            sentry_handler.setLevel(logging.WARNING)
            logging.getLogger().addHandler(sentry_handler)

            init_rpc(sentry=sentry)
            logger.info('Sentry is inited because you are in {} mode.'.format(__app.config['CONFIG_NAME']))

        # metrics
        global statsd
        statsd = DogStatsd(namespace=f"{__app.config['SERVICE_NAME']}.{os.environ.get('MODE').lower()}",
                           use_default_route=True)

        init_rpc(logger=logger)

        print_config(__app, logger)

    @uwsgidecorators.postfork
    def init_db():
        """初始化数据库连接"""
        from everyclass.server.utils.db.postgres import init_pool as init_pg

        # init_mongo(__app)
        init_pg()


    @uwsgidecorators.postfork
    def fetch_remote_manifests():
        """
        在 gevent 模式下，创建 Flask 对象时无法进行 HTTP 请求。因为此时 urllib2 是 gevent 补丁后的版本，而 gevent 引擎还没启动。
        因此我们只能在 fork 后的每个进程中进行请求。
        """
        cron_update_remote_manifest()

    @uwsgidecorators.cron(0, -1, -1, -1, -1)
    def daily_update_data_time(signum):
        """每天凌晨更新数据最后更新时间"""
        cron_update_remote_manifest()

except ModuleNotFoundError:
    pass


def cron_update_remote_manifest():
    """更新数据最后更新时间"""
    from everyclass.rpc.http import HttpRpc

    # 获取安卓客户端下载链接
    android_manifest = HttpRpc.call(method="GET",
                                    url="https://everyclass.cdn.admirable.pro/android/manifest.json",
                                    retry=True)
    android_ver = android_manifest['latestVersions']['mainstream']['versionCode']
    __app.config['ANDROID_CLIENT_URL'] = android_manifest['releases'][android_ver]['url']

    # 更新数据最后更新时间
    _api_server_status = HttpRpc.call(method="GET",
                                      url=__app.config['ENTITY_BASE_URL'] + '/info/service',
                                      retry=True,
                                      headers={'X-Auth-Token': __app.config['ENTITY_TOKEN']})
    __app.config['DATA_LAST_UPDATE_TIME'] = _api_server_status["data_time"]


def create_app() -> Flask:
    """创建 flask app"""
    from everyclass.server.utils.web_consts import MSG_INTERNAL_ERROR
    from everyclass.server import plugin_available
    from everyclass.server.utils import generate_error_response, api_helpers
    from everyclass.common.env import is_production

    app = Flask(__name__,
                static_folder='../../frontend/dist',
                static_url_path='',
                template_folder="../../frontend/templates")

    # load app config
    from everyclass.server.utils.config import get_config
    _config = get_config()
    app.config.from_object(_config)  # noqa: T484

    """
    每课统一日志机制


    规则如下：
    - DEBUG 模式下会输出 DEBUG 等级的日志，否则输出 INFO 及以上等级的日志
    - 日志为 JSON 格式，会被节点上的 agent 采集并发送到 datadog，方便结合 metrics 和 APM 数据分析
    - WARNING 以上级别的输出到 Sentry 做错误聚合


    日志等级：
    critical – for errors that lead to termination
    error – for errors that occur, but are handled
    warning – for exceptional circumstances that might not be errors
    notice – for non-error messages you usually want to see
    info – for messages you usually don’t want to see
    debug – for debug messages


    Sentry：
    https://docs.sentry.io/clients/python/api/#raven.Client.captureMessage
    - stack 默认是 False
    """
    if app.config['DEBUG']:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    # CDN
    CDN(app)

    # moment
    Moment(app)

    # encrypted session
    app.session_interface = EncryptedSessionInterface()

    # 导入并注册 blueprints
    from everyclass.server.calendar.views import calendar_bp
    from everyclass.server.entity.views import entity_bp
    from everyclass.server.user.views import user_bp
    from everyclass.server.course.views import course_bp
    from everyclass.server.views_main import main_blueprint
    from everyclass.server.views_mobile_api import mobile_blueprint
    app.register_blueprint(calendar_bp)
    app.register_blueprint(entity_bp)
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(main_blueprint)
    app.register_blueprint(mobile_blueprint, url_prefix='/mobile')

    # 初始化 RPC 模块
    from everyclass.server.utils.encryption import encrypt
    from everyclass.rpc import init as init_rpc
    from everyclass.rpc.entity import Entity
    from everyclass.rpc.auth import Auth
    init_rpc(resource_id_encrypt_function=encrypt)  # 为 everyclass.rpc 模块注入 encrypt 函数
    if 'ENTITY_BASE_URL' in app.config:
        Entity.set_base_url(app.config['ENTITY_BASE_URL'])
    if 'ENTITY_TOKEN' in app.config:
        Entity.set_request_token(app.config['ENTITY_TOKEN'])
    if 'AUTH_BASE_URL' in app.config:
        Auth.set_base_url(app.config['AUTH_BASE_URL'])

    # course review feature gating
    if app.config['FEATURE_GATING']['course']:
        app.register_blueprint(course_bp, url_prefix='/course')

    @app.before_request
    def set_user_id():
        """在请求之前设置 session uid，方便 APM 标识用户"""
        from everyclass.server.utils.web_consts import SESSION_CURRENT_USER
        from everyclass.server.user import service as user_service

        if not session.get('user_id', None) and request.endpoint not in ("main.health_check", "static"):
            logger.info(f"Give a new user ID for new user. endpoint: {request.endpoint}")
            session['user_id'] = user_service.get_user_id()
        if session.get('user_id', None):
            tracer.current_root_span().set_tag("user_id", session['user_id'])  # 唯一用户 ID
        if session.get(SESSION_CURRENT_USER, None):
            tracer.current_root_span().set_tag("username", session[SESSION_CURRENT_USER].identifier)  # 学号或教工号

    @app.before_request
    def log_request():
        """日志中记录请求"""
        logger.info(f'Request received: {request.method} {request.path}')

    @app.after_request
    def response_minify(response):
        """用 htmlmin 压缩 HTML，减轻带宽压力"""
        if app.config['HTML_MINIFY'] and response.content_type == u'text/html; charset=utf-8':
            response.set_data(minify(response.get_data(as_text=True)))
        return response

    from everyclass.server.utils.db.postgres import db_session

    @app.teardown_appcontext
    def shutdown_db_session(exception=None):
        db_session.remove()

    @app.template_filter('versioned')
    def version_filter(filename):
        """
        模板过滤器。如果 STATIC_VERSIONED，返回类似 'style-v1-c012dr.css' 的文件，而不是 'style-v1.css'

        :param filename: 文件名
        :return: 新的文件名
        """
        if app.config['STATIC_VERSIONED']:
            if filename[:4] == 'css/':
                new_filename = app.config['STATIC_MANIFEST'][filename[4:]]
                return 'css/' + new_filename
            elif filename[:3] == 'js/':
                new_filename = app.config['STATIC_MANIFEST'][filename[3:]]
                return new_filename
            else:
                return app.config['STATIC_MANIFEST'][filename]
        return filename

    @app.context_processor
    def inject_consts():
        """允许在模板中使用常量模块，以便使用session key等常量而不用在模板中硬编码"""
        return dict(consts=web_consts)

    @app.errorhandler(500)
    def internal_server_error(error):
        # blueprint-level 500 handler is not possible at the moment, so internal error of mobile API must be handler here
        if request.path.startswith("/mobile"):
            # not show actual error in production
            actual_error = {'status_message_overwrite': f"server internal error: {repr(error)}"} if not is_production() else {}

            return generate_error_response(None, api_helpers.STATUS_CODE_INTERNAL_ERROR, **actual_error)
        if plugin_available("sentry"):
            return render_template('common/error.html',
                                   message=MSG_INTERNAL_ERROR,
                                   event_id=g.sentry_event_id,
                                   public_dsn=sentry.client.get_public_dsn('https'))
        return "<h4>500 Error: {}</h4><br>You are seeing this page because Sentry is not available.".format(repr(error))

    global __app
    __app = app

    return app
