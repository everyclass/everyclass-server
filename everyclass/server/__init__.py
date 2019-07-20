import datetime
import logging
import os

import gc
from flask import Flask, g, redirect, render_template, request, session
from flask_cdn import CDN
from flask_moment import Moment
from flask_session import Session
from htmlmin import minify
from raven.contrib.flask import Sentry
from raven.handlers.logging import SentryHandler

logger = logging.getLogger(__name__)
sentry = Sentry()
__app = None
__load_time = datetime.datetime.now()


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
    def init_log_handlers():
        """初始化 log handlers 并将当前配置信息打 log"""
        from everyclass.server.config import print_config
        from everyclass.rpc import init as init_rpc

        # Sentry
        if __app.config['CONFIG_NAME'] in __app.config['SENTRY_AVAILABLE_IN']:
            sentry.init_app(app=__app)
            sentry_handler = SentryHandler(sentry.client)
            sentry_handler.setLevel(logging.WARNING)
            logger.addHandler(sentry_handler)

            init_rpc(sentry=sentry)
            logger.info('Sentry is inited because you are in {} mode.'.format(__app.config['CONFIG_NAME']))

        init_rpc(logger=logger)

        # 如果当前时间与模块加载时间相差一分钟之内，认为是第一次 spawn（进程随着时间的推移可能会被 uwsgi 回收），
        # 在 1 号 worker 里打印当前配置
        import uwsgi
        if uwsgi.worker_id() == 1 and (datetime.datetime.now() - __load_time) < datetime.timedelta(minutes=1):
            # 这里设置等级为 warning 因为我们希望在 sentry 里监控重启情况
            logger.warning('App (re)started in `{0}` environment'
                           .format(__app.config['CONFIG_NAME']))
            print_config(__app, logger)

    @uwsgidecorators.postfork
    def init_db():
        """初始化数据库连接"""
        from everyclass.server.db.mongodb import init_pool as init_mongo
        from everyclass.server.db.postgres import init_pool as init_pg

        init_mongo(__app)
        init_pg(__app)

    @uwsgidecorators.postfork
    def init_session():
        """初始化服务器端 session"""
        __app.config['SESSION_MONGODB'] = __app.mongo
        Session(__app)

    @uwsgidecorators.postfork
    def fetch_remote_manifests():
        """
        在 gevent 模式下，创建 Flask 对象时无法进行 HTTP 请求。因为此时 urllib2 是 gevent 补丁后的版本，而 gevent 引擎还没启动。
        因此我们只能在 fork 后的每个进程中进行请求。
        """
        cron_update_remote_manifest()

    @uwsgidecorators.cron(0, 0, -1, -1, -1)
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
                                      url=__app.config['API_SERVER_BASE_URL'] + '/info/service',
                                      retry=True,
                                      headers={'X-Auth-Token': __app.config['API_SERVER_TOKEN']})
    __app.config['DATA_LAST_UPDATE_TIME'] = _api_server_status["data_time"]


def create_app() -> Flask:
    """创建 flask app"""
    from everyclass.server.db.dao import new_user_id_sequence
    from everyclass.server.consts import MSG_INTERNAL_ERROR
    from everyclass.server.utils import plugin_available

    app = Flask(__name__,
                static_folder='../../frontend/dist',
                static_url_path='',
                template_folder="../../frontend/templates")

    # load app config
    from everyclass.server.config import get_config
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
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if _config.CONFIG_NAME != "development":  # 本地不用打文件日志
        from everyclass.server.utils.log import CustomisedJSONFormatter
        formatter = CustomisedJSONFormatter()

        log_path = "/var/log/app"
        log_filename = log_path + 'log.json'
        if not os.path.exists(log_path):
            os.makedirs(log_path)

        file_handler = logging.FileHandler(filename=log_filename)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    # CDN
    CDN(app)

    # moment
    Moment(app)

    # 导入并注册 blueprints
    from everyclass.server.calendar.views import cal_blueprint
    from everyclass.server.query import query_blueprint
    from everyclass.server.views import main_blueprint as main_blueprint
    from everyclass.server.user.views import user_bp
    from everyclass.server.course_review.views import cr_blueprint
    app.register_blueprint(cal_blueprint)
    app.register_blueprint(query_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(user_bp, url_prefix='/user')

    # 为 everyclass.rpc 模块注入 encrypt 函数
    from everyclass.server.utils.resource_identifier_encrypt import encrypt
    from everyclass.rpc import init as init_rpc
    init_rpc(resource_id_encrypt_function=encrypt)

    # course review feature gating
    if app.config['FEATURE_GATING']['course_review']:
        app.register_blueprint(cr_blueprint, url_prefix='/course_review')

    @app.before_request
    def set_user_id():
        """在请求之前设置 session uid，方便 Elastic APM 记录用户请求"""
        if not session.get('user_id', None) and request.endpoint != "main.health_check":
            session['user_id'] = new_user_id_sequence()

    @app.before_request
    def log_request():
        logger.info('{} {}'.format(request.method, request.path))

    @app.before_request
    def delete_old_session():
        """删除旧的客户端 session（长度过长导致无法在 mongodb 中建立索引）"""
        if request.cookies.get("session") and len(request.cookies.get("session")) > 50:
            session.clear()
            return redirect(request.url)

    @app.after_request
    def response_minify(response):
        """用 htmlmin 压缩 HTML，减轻带宽压力"""
        if app.config['HTML_MINIFY'] and response.content_type == u'text/html; charset=utf-8':
            response.set_data(minify(response.get_data(as_text=True)))
        return response

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

    @app.errorhandler(500)
    def internal_server_error(error):
        if plugin_available("sentry"):
            return render_template('common/error.html',
                                   message=MSG_INTERNAL_ERROR,
                                   event_id=g.sentry_event_id,
                                   public_dsn=sentry.client.get_public_dsn('https'))
        return "<h4>500 Error: {}</h4><br>You are seeing this page because Sentry is not available.".format(repr(error))

    global __app
    __app = app

    return app
