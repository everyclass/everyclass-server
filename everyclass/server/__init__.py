import copy
import os

import logbook
import logbook.queues
from elasticapm.contrib.flask import ElasticAPM
from flask import Flask, g, render_template, session
from flask_cdn import CDN
from htmlmin import minify
from raven.contrib.flask import Sentry
from raven.handlers.logbook import SentryHandler

from everyclass.server.utils import monkey_patch

logger = logbook.Logger(__name__)

sentry = Sentry()

ElasticAPM.request_finished = monkey_patch.ElasticAPM.request_finished(ElasticAPM.request_finished)


def create_app(offline=False) -> Flask:
    """创建 flask app
    @param offline: 如果设置为 `True`，则为离线模式。此模式下不会连接到 Sentry 和 ElasticAPM
    """
    from everyclass.server.db.dao import new_user_id_sequence
    from everyclass.server.db.mysql import get_connection, init_pool
    from everyclass.server.utils.log import LogstashHandler, LogstashFormatter

    app = Flask(__name__,
                static_folder='../../frontend/dist',
                static_url_path='',
                template_folder="../../frontend/templates")

    # load app config
    from everyclass.server.config import get_config
    _config = get_config()
    app.config.from_object(_config)

    # logbook handlers
    # 规则如下：
    # - 全部输出到 stdout（本地开发调试、服务器端文件日志）
    # - 全部日志通过自定义的 handler 通过 TCP 输出到 LogStash，然后发送到日志中心
    # - WARNING 以上级别的输出到 Sentry
    #
    # 日志等级：
    # critical – for errors that lead to termination
    # error – for errors that occur, but are handled
    # warning – for exceptional circumstances that might not be errors
    # notice – for non-error messages you usually want to see
    # info – for messages you usually don’t want to see
    # debug – for debug messages
    #
    #
    # Sentry：
    # https://docs.sentry.io/clients/python/api/#raven.Client.captureMessage
    # - stack 默认是 False
    # - 默认事件类型是 `raven.events.Message`，设置 `exc_info` 为 `True` 将把事件类型升级为`raven.events.Exception`
    stderr_handler = logbook.StderrHandler(bubble=True)
    logger.handlers.append(stderr_handler)

    if not offline:
        # Sentry
        sentry.init_app(app=app)
        sentry_handler = SentryHandler(sentry.client, level='WARNING')  # Sentry 只处理 WARNING 以上的
        logger.handlers.append(sentry_handler)

        # Elastic APM
        ElasticAPM(app)

        # Log to Logstash
        logstash_handler = LogstashHandler(host=app.config['LOGSTASH']['HOST'],
                                           port=app.config['LOGSTASH']['PORT'],
                                           bubble=True)
        logger.handlers.append(logstash_handler)

    # CDN
    CDN(app)

    # 初始化数据库
    if os.getenv('MODE', None) != "CI":
        init_pool(app)

    # 导入并注册 blueprints
    from everyclass.server.calendar.views import cal_blueprint
    from everyclass.server.query import query_blueprint
    from everyclass.server.views import main_blueprint as main_blueprint
    from everyclass.server.api import api_v1 as api_blueprint
    app.register_blueprint(cal_blueprint)
    app.register_blueprint(query_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

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
        return render_template('500.html',
                               event_id=g.sentry_event_id,
                               public_dsn=sentry.client.get_public_dsn('https'))

    logger.info('App created with `{0}` config'.format(app.config['CONFIG_NAME']), stack=False)

    # 输出配置内容
    logger.info('Below are configurations:')
    logger.info('================================================================')
    for key, value in app.config.items():
        if key not in ('SECRET_KEY',):
            value = copy.copy(value)

            # 敏感内容抹去
            if key == 'SENTRY_CONFIG':
                value['dsn'] = '[secret]'
            if key == 'MYSQL_CONFIG':
                value['password'] = '[secret]'
            if key == 'ELASTIC_APM':
                value['SECRET_TOKEN'] = '[secret]'

            logger.info('{}: {}'.format(key, value))
    logger.info('================================================================')

    return app
