import time

from flask import Flask, g, render_template, send_from_directory, current_app
from flask_cdn import CDN
from htmlmin import minify
from termcolor import cprint
from celery import Celery
from pymongo import MongoClient
from raven.contrib.flask import Sentry

from .config import load_config

config = load_config()

# Celery
# The fact that it provides the decorator means that it has to be created as a global variable, and
# that implies that the Flask application instance is not going to be around when it is created.
# It has to be treated carefully, in this way.
celery = Celery(__name__,
                broker=config.CELERY_BROKER_URL)


def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='')

    # load config
    app.config.from_object(config)
    cprint('App created. Running under `{}` config'.format(app.config['CONFIG_NAME']), color='blue')

    # CDN
    CDN(app)

    # Sentry
    sentry = Sentry(app)

    # celery
    celery.conf.update(app.config)

    # register blueprints
    from .cal import cal_blueprint
    from .query import query_blueprint
    from .views import main_blueprint as main_blueprint
    from .api import api_v1 as api_blueprint
    app.register_blueprint(cal_blueprint)
    app.register_blueprint(query_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    @app.teardown_appcontext
    def close_db(error):
        """结束时关闭数据库连接"""
        if hasattr(g, 'mysql_db'):
            g.mysql_db.close()

    @app.route('/<student_id>-<semester>.ics')
    def get_ics(student_id, semester):
        """serve ics file"""
        # TODO: if file not exist, try to generate one.
        return send_from_directory("ics", student_id + "-" + semester + ".ics",
                                   as_attachment=True,
                                   mimetype='text/calendar')

    @app.after_request
    def response_minify(response):
        """用 htmlmin 压缩 HTML，减轻带宽压力"""
        if app.config['HTML_MINIFY'] and response.content_type == u'text/html; charset=utf-8':
            response.set_data(
                minify(response.get_data(as_text=True))
            )
            return response
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

    return app


def get_day_chinese(digit):
    """
    get Chinese char of day of week
    """
    if digit == 1:
        return '周一'
    elif digit == 2:
        return '周二'
    elif digit == 3:
        return '周三'
    elif digit == 4:
        return '周四'
    elif digit == 5:
        return '周五'
    elif digit == 6:
        return '周六'
    else:
        return '周日'


def get_time_chinese(digit):
    """
    get Chinese time description for a single lesson time.
    """
    if digit == 1:
        return '第1-2节'
    elif digit == 2:
        return '第3-4节'
    elif digit == 3:
        return '第5-6节'
    elif digit == 4:
        return '第7-8节'
    elif digit == 5:
        return '第9-10节'
    else:
        return '第11-12节'


def get_time(digit):
    """
    get start and end time for a single lesson.
    """
    if digit == 1:
        return (8, 00), (9, 40)
    elif digit == 2:
        return (10, 00), (11, 40)
    elif digit == 3:
        return (14, 00), (15, 40)
    elif digit == 4:
        return (16, 00), (17, 40)
    elif digit == 5:
        return (19, 00), (20, 40)
    else:
        return (21, 00), (22, 40)


def is_chinese_char(uchar):
    """
    Check if a char is a Chinese character. It's used to check whether a string is a name.

    :param uchar: char
    :return: True or False
    """
    if u'\u4e00' <= uchar <= u'\u9fa5':
        return True
    else:
        return False


def print_formatted_info(info, show_debug_tip=False, info_about="DEBUG"):
    """
    调试输出函数

    :param info:
    :param show_debug_tip:
    :param info_about:
    :return:
    """
    from termcolor import cprint
    if show_debug_tip:
        cprint("-----" + info_about + "-----", "blue", attrs=['bold'])
    if isinstance(info, dict):
        for (k, v) in info.items():
            print("%s =" % k, v)
    elif isinstance(info, str):
        cprint(info, attrs=["bold"])
    else:
        for each_info in info:
            print(each_info)
    if show_debug_tip:
        cprint("----" + info_about + " ENDS----", "blue", attrs=['bold'])


@celery.task
def access_log(op_type, stu_id):
    """异步记录访问日志到 MongoDB 数据库，调用时使用 access_log.apply_async(args=[])

    :param op_type: 操作类型，for example:`q_stu`
    :param stu_id: 学号
    :return: None

    日志格式：
    type:
        prefix:
            `q_` means query traffics from front-end
            `a_` means query traffics from API
        suffix:
            `stu` means querying one's course schedule
            `export` means accessing the page of exporting
    ts: timestamp
    stu_id: student id
    """
    # todo
    mongo_client = MongoClient(current_app.config['MONGODB_HOST'], current_app.config['MONGODB_PORT'])
    log = mongo_client.everyclass_log.log
    log.insert({'type': op_type,
                'ts': int(time.time()),
                'stu_id': stu_id,
                })
