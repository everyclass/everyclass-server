import re

from flask import Flask, g, render_template, send_from_directory, redirect, url_for, flash, request, jsonify
from flask_cdn import CDN
from htmlmin import minify
from termcolor import cprint
from markupsafe import escape
from raven.contrib.flask import Sentry

from .exceptions import NoClassException, NoStudentException
from .cal import cal_blueprint
from .query import query_blueprint
from .api import api_v1 as api_blueprint
from .config import load_config

config = load_config()


def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='')
    app.config.from_object(load_config())
    cprint('App created. Running under [{}] config'.format(app.config['CONFIG_NAME']), color='blue')

    # CDN
    CDN(app)

    # Sentry
    sentry = Sentry(app)

    # register blueprints
    app.register_blueprint(cal_blueprint)
    app.register_blueprint(query_blueprint)
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    # 结束时关闭数据库连接
    @app.teardown_appcontext
    def close_db(error):
        if hasattr(g, 'mysql_db'):
            g.mysql_db.close()

    # 首页
    @app.route('/')
    def main():
        return render_template('index.html')

    # 帮助
    @app.route('/faq')
    def faq():
        return render_template('faq.html')

    # 关于
    @app.route('/about')
    def about():
        return render_template('about.html')

    # 帮助
    @app.route('/guide')
    def guide():
        return render_template('guide.html')

    # 测试
    @app.route('/testing')
    def testing():
        return render_template('testing.html')

    @app.route('/<student_id>-<semester>.ics')
    def get_ics(student_id, semester):
        return send_from_directory("ics", student_id + "-" + semester + ".ics",
                                   as_attachment=True,
                                   mimetype='text/calendar')

    # Minify html response to decrease site traffic using htmlmin
    @app.after_request
    def response_minify(response):
        if app.config['HTML_MINIFY'] and response.content_type == u'text/html; charset=utf-8':
            response.set_data(
                minify(response.get_data(as_text=True))
            )
            return response
        return response

    # If STATIC_VERSIONED, use versioned file like 'style-v1-c012dr.css' instead of 'style-v1.css'
    @app.template_filter('versioned')
    def version_filter(filename):
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

    # 404跳转回首页
    @app.errorhandler(404)
    def page_not_found(error):
        # 404 errors are never handled on the blueprint level
        # unless raised from a view func so actual 404 errors,
        # i.e. "no route for it" defined, need to be handled
        # here on the application level
        if request.path.startswith('/api/'):
            response = jsonify({'error': 'not found'})
            response.status_code = 404
            return response
        return redirect(url_for('main'))

    # 405跳转回首页
    @app.errorhandler(405)
    def method_not_allowed(error):
        return redirect(url_for('main'))

    @app.errorhandler(NoStudentException)
    def invalid_usage(error):
        flash('没有在数据库中找到你哦。是不是输错了？你刚刚输入的是%s' % escape(error))
        return redirect(url_for('main'))

    @app.errorhandler(NoClassException)
    def invalid_usage(error):
        flash('没有这门课程哦')
        return redirect(url_for('main'))

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


def semester_code(xq):
    """
    获取用于数据表命名的学期，输入(2016,2017,2)，输出16_17_2

    :param xq: tuple (2016,2017,2)
    :return: str 16_17_2
    """
    if xq == '':
        return semester_code(config.DEFAULT_SEMESTER)
    else:
        if xq in config.AVAILABLE_SEMESTERS:
            return str(xq[0])[2:4] + "_" + str(xq[1])[2:4] + "_" + str(xq[2])


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


def tuple_semester(xq):
    """
    Convert a string like "2016-2017-2" to a tuple like [2016,2017,2].
    `xq` may come from a form posted by user, so we NEED to check if is valid.

    :param xq: str"2016-2017-2"
    :return: [2016,2017,2]
    """

    if re.match(r'\d{4}-\d{4}-\d', xq):
        splitted = re.split(r'-', xq)
        return int(splitted[0]), int(splitted[1]), int(splitted[2])
    else:
        return config.DEFAULT_SEMESTER


def string_semester(xq, simplify=False):
    """
    因为to_string的参数一定来自程序内部，所以不检查有效性

    :param xq: tuple or list, like [2016,2017,2]
    :param simplify: True if you want short str
    :return: str like '16-17-2' if simplify==True, '2016-2017-2' is simplify==False
    """
    if not simplify:
        return str(xq[0]) + '-' + str(xq[1]) + '-' + str(xq[2])
    else:
        return str(xq[0])[2:4] + '-' + str(xq[1])[2:4] + '-' + str(xq[2])
