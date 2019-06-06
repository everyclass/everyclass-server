import json
import os

import git


class LazyRefType:
    """
    The great lazy reference type.

    Sometimes you want a field to reference another field (i.e., `FIELD1 = FIELD2`). However, if you do this in
    base class and the referenced field is overwritten in subclass, the FIELD1 will still be associated with the
    base class. This is not what we want.

    For example, you have a field called `MONGODB_DB` which defines the database name you use in your business
    logic. However, the Flask-session extension requires a field called `SESSION_MONGODB_DB` which defines the
    database name that stores the session. Both of them need to be defined in base `Config` class. So you
    define:

    MONGODB_DB = "everyclass-db"
    SESSION_MONGODB_DB = MONGODB_DB

    Things go pretty well until you change `MONGODB_DB` in ProductionConfig. The `SESSION_MONGODB_DB` will still
    be "everyclass-db". So the "reference" is not really a reference now.

    If you do `SESSION_MONGODB_DB = LazyRefType("MONGODB_DB")` and call `LazyRefType.link(MixedConfig)` at last,
    the reference will be correctly linked.
    """

    def __init__(self, var_name):
        self.var_name = var_name

    @classmethod
    def link(cls, final_config):
        for key in dir(final_config):
            value = getattr(final_config, key)
            if isinstance(value, cls):
                setattr(final_config, key, getattr(final_config, value.var_name))


class Config(object):
    """
    the base class for configuration. all keys must define here.
    """
    DEBUG = True
    SECRET_KEY = 'development_key'

    """
    Git Hash
    """
    _git_repo = git.Repo(search_parent_directories=True)
    GIT_HASH = _git_repo.head.object.hexsha
    try:
        GIT_BRANCH_NAME = _git_repo.active_branch.name
    except TypeError:
        GIT_BRANCH_NAME = 'detached'
    _describe_raw = _git_repo.git.describe(tags=True).split("-")  # like `v0.8.0-1-g000000`
    GIT_DESCRIBE = _describe_raw[0]  # actual tag name like `v0.8.0`
    if len(_describe_raw) > 1:
        GIT_DESCRIBE += "." + _describe_raw[1]  # tag 之后的 commit 计数，代表小版本
        # 最终结果类似于：v0.8.0.1

    """
    Connection settings
    """
    # database
    MONGODB = {
        'host'              : 'mongodb',
        'port'              : 12306,
        'uuidRepresentation': 'standard'
    }
    MONGODB_DB = 'everyclass_server'
    REDIS = {
        'host': '127.0.0.1',
        'port': 6379,
        'db'  : 1
    }

    # server side session
    SESSION_TYPE = 'mongodb'
    SESSION_MONGODB = None  # lazy init after fork
    SESSION_MONGODB_DB = LazyRefType("MONGODB_DB")
    SESSION_MONGODB_COLLECT = 'session'

    # Sentry, APM and logstash
    SENTRY_CONFIG = {
        'dsn'    : '',
        'release': '',
        'tags'   : {'environment': 'default'}
    }
    ELASTIC_APM = {
        'SERVICE_NAME'                : 'everyclass-server',
        'SECRET_TOKEN'                : 'token',
        'SERVER_URL'                  : 'http://127.0.0.1:8200',
        # https://www.elastic.co/guide/en/apm/agent/python/2.x/configuration.html#config-auto-log-stacks
        'AUTO_LOG_STACKS'             : False,
        'SERVICE_VERSION'             : GIT_DESCRIBE,
        'TRANSACTIONS_IGNORE_PATTERNS': ['GET /_healthCheck']
    }
    LOGSTASH = {
        'HOST': '127.0.0.1',
        'PORT': 8888
    }

    # other micro-services
    API_SERVER_BASE_URL = 'http://everyclass-api-server'
    API_SERVER_TOKEN = ''
    AUTH_BASE_URL = 'http://everyclass-auth'

    """
    维护模式
    """
    MAINTENANCE_CREDENTIALS = {
    }
    MAINTENANCE_FILE = os.path.join(os.getcwd(), 'maintenance')
    if os.path.exists(MAINTENANCE_FILE):
        MAINTENANCE = True
    else:
        MAINTENANCE = False

    """
    静态文件、CDN 及网络优化
    """
    CDN_DOMAIN = 'cdn.domain.com'
    CDN_ENDPOINTS = ['images', 'static']
    CDN_TIMESTAMP = False
    HTML_MINIFY = True
    STATIC_VERSIONED = True
    with open(os.path.join(os.path.dirname(__file__), '../../../frontend/rev-manifest.json'), 'r') as static_manifest:
        STATIC_MANIFEST = json.load(static_manifest)

    """
    业务设置
    """
    DATA_LAST_UPDATE_TIME = '2018 年 9 月 7 日'  # 数据最后更新日期，在页面下方展示
    DEFAULT_SEMESTER = (2018, 2019, 1)
    AVAILABLE_SEMESTERS = {
        (2016, 2017, 1): {
            'start': (2016, 9, 5),
        },
        (2016, 2017, 2): {
            'start': (2017, 2, 20),
        },
        (2017, 2018, 1): {
            'start': (2017, 9, 4),
        },
        (2017, 2018, 2): {
            'start': (2018, 2, 26),
        },
        (2018, 2019, 1): {
            'start'      : (2018, 9, 3),
            'adjustments': {
                (2018, 12, 31): {
                    'to': (2018, 12, 29)
                }
            }
        },
        (2018, 2019, 2): {
            'start'      : (2019, 2, 25),  # 学期开始日
            'adjustments': {
                (2019, 4, 5): {
                    'to': None  # 调整到 None 表示这天直接放掉，而非调休
                },
                (2019, 5, 1): {
                    'to': None
                },
                (2019, 5, 2): {
                    "to": (2019, 4, 28)
                },
                (2019, 5, 3): {
                    "to": (2019, 5, 5)
                },
                (2019, 5, 4): {
                    'to': None
                },
                (2019, 6, 7): {
                    "to": None
                }
            }
        }
    }

    ANDROID_CLIENT_URL = ''  # apk file for android client, dynamically fetched when starting

    FEATURE_GATING = {
        'course_review': False,
        'user'         : True
    }
    DEFAULT_PRIVACY_LEVEL = 0

    RESOURCE_IDENTIFIER_ENCRYPTION_KEY = 'z094gikTit;5gt5h'

    TENCENT_CAPTCHA_AID = ''
    TENCENT_CAPTCHA_SECRET = ''

    # define available environments for logs, APM and error tracking
    SENTRY_AVAILABLE_IN = ('production', 'staging', 'testing', 'development')
    APM_AVAILABLE_IN = ('production', 'staging', 'testing',)
    LOGSTASH_AVAILABLE_IN = ('production', 'staging', 'testing',)
    DEBUG_LOG_AVAILABLE_IN = ('development', 'testing', 'staging')

    # fields that should be overwritten in production environment
    PRODUCTION_OVERWRITE_FIELDS = ('SECRET_KEY',
                                   'TENCENT_CAPTCHA_AID',
                                   'TENCENT_CAPTCHA_SECRET',
                                   'RESOURCE_IDENTIFIER_ENCRYPTION_KEY'
                                   )

    # fields that should not be in log
    PRODUCTION_SECURE_FIELDS = ("SENTRY_CONFIG.dsn",
                                "MYSQL_CONFIG.password",
                                "MYSQL_CONFIG.passwd",
                                "REDIS.password",
                                "MONGODB.password",
                                "ELASTIC_APM.SECRET_TOKEN",
                                "MAINTENANCE_CREDENTIALS",
                                "SECRET_KEY",
                                "TENCENT_CAPTCHA_SECRET",
                                "RESOURCE_IDENTIFIER_ENCRYPTION_KEY"
                                )
