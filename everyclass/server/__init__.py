import os

import logbook
from elasticapm.contrib.flask import ElasticAPM
from elasticapm.handlers.logbook import LogbookHandler
from flask import Flask, g, render_template, session
from flask_cdn import CDN
from htmlmin import minify
from raven.contrib.flask import Sentry

from everyclass.server.config import load_config
from everyclass.server.db.mysql import get_conn, init_db
from everyclass.server.utils import monkey_patch

config = load_config()

# logbook logger
logger = logbook.Logger(__name__)

ElasticAPM.request_finished = monkey_patch.ElasticAPM.request_finished(ElasticAPM.request_finished)


def create_app() -> Flask:
    app = Flask(__name__,
                static_folder='../../frontend/dist',
                static_url_path='',
                template_folder="../../frontend/templates")

    # load config
    app.config.from_object(config)

    # CDN
    CDN(app)

    # Sentry
    sentry = Sentry(app)

    # 初始化数据库
    if os.getenv('MODE', None) != "CI":
        init_db(app)

    # Elastic APM
    apm = ElasticAPM(app)

    # log handlers
    elastic_handler = LogbookHandler(client=apm.client, bubble=True)
    logger.handlers.append(elastic_handler)
    # handler.push_application()
    stderr_handler = logbook.StderrHandler(bubble=True)
    logger.handlers.append(stderr_handler)

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
            # 数据库中生成唯一 ID，参考 https://blog.csdn.net/longjef/article/details/53117354
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute("REPLACE INTO user_id_sequence (stub) VALUES ('a');")
            session['user_id'] = cursor.lastrowid
            cursor.close()

    @app.teardown_request
    def close_db(error):
        """结束时关闭数据库连接"""
        if hasattr(g, 'mysql_db') and g.mysql_db:
            g.mysql_db.close()

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

    logger.info('App created with `{}` config'.format(app.config['CONFIG_NAME']), exc_info=False)
    return app
