class Config(object):
    # App basic config
    CONFIG_NAME = 'default'
    DEBUG = True
    SECRET_KEY = 'development_key'
    # SERVER_NAME = 'localhost'
    CDN_DOMAIN = 'cdn.domain.com'
    CDN_ENDPOINTS = ['images', 'static']
    CDN_TIMESTAMP = False
    SENTRY_CONFIG = {
        'dsn': 'https://XXX@sentry.io/project',
    }
    HTML_MINIFY = True
    # Semester and database settings
    DATA_LAST_UPDATE_TIME = 'Apr. 29, 2017'  # 数据最后更新日期
    DEFAULT_SEMESTER = (2016, 2017, 2)
    AVAILABLE_SEMESTERS = {
        (2016, 2017, 2): {
            'start': (2017, 2, 20),
        },
    }

    # Database config
    MYSQL_CONFIG = {
        'user': 'database_user',
        'password': 'database_password',
        'host': '127.0.0.1',
        'port': '6666',
        'database': 'everyclass',
        'raise_on_warnings': True,
    }
