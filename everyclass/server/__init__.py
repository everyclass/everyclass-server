import copy
import gc
import json
import sys

import logbook
import requests
from flask import Flask, g, render_template, session
from flask_cdn import CDN
from htmlmin import minify
from raven.contrib.flask import Sentry
from raven.handlers.logbook import SentryHandler

logger = logbook.Logger(__name__)
sentry = Sentry()
__app = None
__first_spawn = True

try:
    import uwsgidecorators

    """
    below are functions that will be executed in **each** process after fork().
    these functions will be executed in the same order of definition here.
    """

    @uwsgidecorators.postfork
    def enable_gc():
        """enable garbage collection"""
        gc.set_threshold(700)

    @uwsgidecorators.postfork
    def init_db():
        """init database connection"""
        import everyclass.server.db.mysql
        import everyclass.server.db.mongodb

        global __app
        everyclass.server.db.mysql.init_pool(__app)
        everyclass.server.db.mongodb.init_pool(__app)

    @uwsgidecorators.postfork
    def init_log_handlers():
        """init log handlers"""
        from everyclass.server.utils.logbook_logstash.handler import LogstashHandler
        from elasticapm.contrib.flask import ElasticAPM
        from everyclass.server.utils import monkey_patch
        ElasticAPM.request_finished = monkey_patch.ElasticAPM.request_finished(ElasticAPM.request_finished)

        global __app, __first_spawn

        # Elastic APM
        if __app.config['CONFIG_NAME'] in __app.config['APM_AVAILABLE_IN']:
            ElasticAPM(__app)
            logger.info('You are in {} mode, so APM is inited.'.format(__app.config['CONFIG_NAME']))

        # Logstash centralized log
        if __app.config['CONFIG_NAME'] in __app.config['LOGSTASH_AVAILABLE_IN']:
            logstash_handler = LogstashHandler(host=__app.config['LOGSTASH']['HOST'],
                                               port=__app.config['LOGSTASH']['PORT'],
                                               release=__app.config['GIT_DESCRIBE'],
                                               bubble=True,
                                               logger=logger,
                                               filter=lambda r, h: r.level >= 11)  # do not send DEBUG
            logger.handlers.append(logstash_handler)
            logger.info('You are in {} mode, so LogstashHandler is inited.'.format(__app.config['CONFIG_NAME']))

        # Sentry
        if __app.config['CONFIG_NAME'] in __app.config['SENTRY_AVAILABLE_IN']:
            sentry.init_app(app=__app)
            sentry_handler = SentryHandler(sentry.client, level='WARNING')  # Sentry 只处理 WARNING 以上的
            logger.handlers.append(sentry_handler)
            logger.info('You are in {} mode, so Sentry is inited.'.format(__app.config['CONFIG_NAME']))

        # print current configuration
        import uwsgi
        if uwsgi.worker_id() == 1 and __first_spawn:
            # set to warning level because we want to monitor restarts
            logger.warning('App (re)started in `{0}` environment'
                           .format(__app.config['CONFIG_NAME']), stack=False)

            logger.info('Below are configurations we are using:')
            logger.info('================================================================')
            for key, value in __app.config.items():
                if key not in ('SECRET_KEY',):
                    value = copy.copy(value)

                    # 敏感内容抹去
                    if key == 'SENTRY_CONFIG':
                        value['dsn'] = '[secret]'
                    if key == 'MYSQL_CONFIG':
                        value['password'] = '[secret]'
                    if key == 'ELASTIC_APM':
                        value['SECRET_TOKEN'] = '[secret]'
                    if key == 'MAINTENANCE_CREDENTIALS':
                        value = '[secret]'

                    logger.info('{}: {}'.format(key, value))
            logger.info('================================================================')

            __first_spawn = False

    @uwsgidecorators.postfork
    def get_android_download_link():
        """
        It's not possible to make a HTTP request during `create_app` since the urllib2 is patched by gevent
        and the gevent engine is not started yet (controlled by uWSGI). So we can only do the initialization
        here.
        """
        android_manifest = requests.get("https://everyclass.cdn.admirable.pro/android/manifest.json").content
        android_manifest = json.loads(android_manifest)
        android_ver = android_manifest['latestVersions']['mainstream']['versionCode']
        __app.config['ANDROID_CLIENT_URL'] = android_manifest['releases'][android_ver]['url']
except ModuleNotFoundError:
    pass


def create_app(outside_container=False) -> Flask:
    """创建 flask app
    @param outside_container: 是否不在容器内运行
    """
    import everyclass.server.db.mysql
    import everyclass.server.db.mongodb
    from everyclass.server.db.dao import new_user_id_sequence
    from everyclass.server.utils.logbook_logstash.formatter import LOG_FORMAT_STRING
    from everyclass.server.exceptions import MSG_INTERNAL_ERROR
    from everyclass.server.utils import plugin_availability

    print("Creating app...")

    app = Flask(__name__,
                static_folder='../../frontend/dist',
                static_url_path='',
                template_folder="../../frontend/templates")

    # load app config
    from everyclass.server.config import get_config
    _config = get_config()
    app.config.from_object(_config)

    """
    每课统一日志机制


    规则如下：
    - WARNING 以下 log 输出到 stdout
    - WARNING 以上输出到 stderr
    - DEBUG 以上日志以 json 形式通过 TCP 输出到 Logstash，然后发送到日志中心
    - WARNING 以上级别的输出到 Sentry


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
    if app.config['CONFIG_NAME'] in app.config['DEBUG_LOG_AVAILABLE_IN']:
        stdout_handler = logbook.StreamHandler(stream=sys.stdout, bubble=True, filter=lambda r, h: r.level < 13)
    else:
        # ignore debug when not in debug
        stdout_handler = logbook.StreamHandler(stream=sys.stdout, bubble=True, filter=lambda r, h: 10 < r.level < 13)
    stdout_handler.format_string = LOG_FORMAT_STRING
    logger.handlers.append(stdout_handler)

    stderr_handler = logbook.StreamHandler(stream=sys.stderr, bubble=True, level='WARNING')
    stderr_handler.format_string = LOG_FORMAT_STRING
    logger.handlers.append(stderr_handler)

    # CDN
    CDN(app)

    # 容器外运行（无 uWSGI）时初始化数据库
    if outside_container and (app.config['CONFIG_NAME'] == "development"):
        everyclass.server.db.mysql.init_pool(app)
        everyclass.server.db.mongodb.init_pool(app)

    # 导入并注册 blueprints
    from everyclass.server.calendar.views import cal_blueprint
    from everyclass.server.query import query_blueprint
    from everyclass.server.views import main_blueprint as main_blueprint
    from everyclass.server.user.views import user_bp
    app.register_blueprint(cal_blueprint)
    app.register_blueprint(query_blueprint)
    app.register_blueprint(main_blueprint)

    if app.config['FEATURE_GATING']['user']:  # user feature gating
        app.register_blueprint(user_bp, url_prefix='/user')

    @app.before_request
    def set_user_id():
        """在请求之前设置 session uid，方便 Elastic APM 记录用户请求"""
        if not session.get('user_id', None):
            session['user_id'] = new_user_id_sequence()

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
        if plugin_availability("sentry"):
            return render_template('common/error.html',
                                   message=MSG_INTERNAL_ERROR,
                                   event_id=g.sentry_event_id,
                                   public_dsn=sentry.client.get_public_dsn('https'))
        return "<h4>500 Error: {}</h4><br>You are seeing this page because Sentry is not available.".format(repr(error))

    global __app
    __app = app

    return app
