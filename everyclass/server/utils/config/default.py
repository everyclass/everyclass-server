import json
import os

import git

from everyclass.common.env import is_production, is_staging


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
    SERVICE_NAME = "everyclass-server"
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
        'host': 'mongodb',
        'port': 12306,
        'uuidRepresentation': 'standard'
    }
    MONGODB_DB = 'everyclass_server'
    REDIS = {
        'host': '127.0.0.1',
        'port': 6379,
        'db': 1
    }
    POSTGRES_CONNECTION = {
        'dbname': 'everyclass',
        'user': 'everyclass_server',
        'password': '',
        'host': 'localhost',
        'port': 5432
    }
    POSTGRES_SCHEMA = 'everyclass_server'

    # Sentry, APM and logstash
    SENTRY_CONFIG = {
        'dsn': '',
        'release': '',
        'tags': {'environment': 'default'}
    }

    # other micro-services
    ENTITY_BASE_URL = 'http://everyclass-api-server'
    ENTITY_TOKEN = ''
    AUTH_BASE_URL = 'http://everyclass-auth'
    MOBILE_API_BASE_URL = 'https://api.everyclass.xyz'

    # API域名不同，此处强制指定cookie的domain
    if is_production():
        SESSION_COOKIE_DOMAIN = 'everyclass.xyz'
    elif is_staging():
        SESSION_COOKIE_DOMAIN = 'staging.everyclass.xyz'

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
    with open(os.path.join(os.path.dirname(__file__), '../../../../frontend/rev-manifest.json'), 'r') as static_manifest:
        STATIC_MANIFEST = json.load(static_manifest)

    """
    业务设置
    """
    DATA_LAST_UPDATE_TIME = '2018 年 9 月 7 日'  # 数据最后更新日期，在页面下方展示
    DEFAULT_SEMESTER = (2018, 2019, 1)
    AVAILABLE_SEMESTERS = {
        (2016, 2017, 1): {
            'start': (2016, 9, 4),
        },
        (2016, 2017, 2): {
            'start': (2017, 2, 19),
        },
        (2017, 2018, 1): {
            'start': (2017, 9, 3),
        },
        (2017, 2018, 2): {
            'start': (2018, 2, 25),
        },
        (2018, 2019, 1): {
            'start': (2018, 9, 2),
            'adjustments': {
                (2018, 12, 31): {
                    'to': (2018, 12, 29)
                }
            }
        },
        (2018, 2019, 2): {
            'start': (2019, 2, 24),  # 学期开始日
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
        },
        (2019, 2020, 1): {
            "start": (2019, 8, 25),
        },
        (2019, 2020, 2): {
            "start": (2020, 2, 23),
        }
    }

    ANDROID_CLIENT_URL = ''  # apk file for android client, dynamically fetched when starting

    FEATURE_GATING = {
        'course': False,
    }
    DEFAULT_PRIVACY_LEVEL = 0

    RESOURCE_IDENTIFIER_ENCRYPTION_KEY = 'z094gikTit;5gt5h'
    SESSION_CRYPTO_KEY = b'\xcb\xf2\x19H\xd9l\x05\xc7j\xb2\xd0^}B*\x8d\xb6\x8aPd\x1c%\x83\x1e_\xf0\xb9C\xa9XOC'

    JWT_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIICdQIBADANBgkqhkiG9w0BAQEFAASCAl8wggJbAgEAAoGBANQ7c5Om5Iqakcu7
PTwFC0JVtAU6MVYEbjVquJcxW2iICOMFgrcFrFv+8WLQvY6jATSK6URW2+vx0UNt
eWzWWXZ7Uqe4uztGv/DrUN8PSmkO/wJ0h1gpl3dse9YHV7U6VL50Oz5eTS/MwZ30
sC/nQFtwgECjR7JWAAgrTYE05Dy5AgMBAAECgYAQfV4JhtoS+teBINctJqctTENk
dJUIvediNxyIgsk7YfZuzSrO1Z4Ct9hBeT6BKqEZWAGv0Z/cwTklKAhbMHxa2BDv
Knb5AMyBefUHV9Wab7dEgIRNY8dqkvwnJ9o173j+Jt5JRTrQMxOOxFowWBob2LRS
s8ska/FgBNb+kmJwQQJBAPNPQpP5Fk6aeMUidrupQglhNYsvf53vaUoVDtD17dpl
3EDMBczzMYltVShxb7xLgTjmuXKOmJbO+oKpNaJDpSUCQQDfTTzAtEuXiukLG6PP
DqM8OtkwffV/88Bjny35YUlm0wzXTwm8YfchJ4wruC4N3/DMzqXz5e9cXH4pzCR9
dgcFAkBJ4TtaKzx2ybj6QyjCevauWnIjvVyG3HegIxzInqSGuH9UvZ7VSNM145kE
Gs3O4y5t1MFi46G5yUeP/Uln6BpxAkBFwAOFEgw2pt5KaPTO/XyBmMQ0wHOJ5yKm
O5eJuRjLdIsjSf35iQQ/p/HBykMgdF3sK3Rs7drJl96Uwb54LgDdAkBBGlNLnoIu
X7E63VLo3NnmiTH/sJBzMWPVClUoQBjy+mnfIuzf20QFc2g/3EahaBErU4U7zBkx
itvB71WSRfVV
-----END PRIVATE KEY-----

"""
    JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDUO3OTpuSKmpHLuz08BQtCVbQF
OjFWBG41ariXMVtoiAjjBYK3Baxb/vFi0L2OowE0iulEVtvr8dFDbXls1ll2e1Kn
uLs7Rr/w61DfD0ppDv8CdIdYKZd3bHvWB1e1OlS+dDs+Xk0vzMGd9LAv50BbcIBA
o0eyVgAIK02BNOQ8uQIDAQAB
-----END PUBLIC KEY-----
"""

    TENCENT_CAPTCHA_AID = ''
    TENCENT_CAPTCHA_SECRET = ''

    # define available environments for logs, APM and error tracking
    SENTRY_AVAILABLE_IN = ('production', 'staging', 'testing')

    # fields that should be overwritten in production environment
    PRODUCTION_OVERWRITE_FIELDS = ('SECRET_KEY',
                                   'TENCENT_CAPTCHA_AID',
                                   'TENCENT_CAPTCHA_SECRET',
                                   'RESOURCE_IDENTIFIER_ENCRYPTION_KEY',
                                   'SESSION_CRYPTO_KEY',
                                   'JWT_PRIVATE_KEY',
                                   'JWT_PUBLIC_KEY'
                                   )

    # fields that should not be in log
    PRODUCTION_SECURE_FIELDS = ("SENTRY_CONFIG.dsn",
                                "MYSQL_CONFIG.password",
                                "MYSQL_CONFIG.passwd",
                                "REDIS.password",
                                "MONGODB.password",
                                "MAINTENANCE_CREDENTIALS",
                                "SECRET_KEY",
                                "TENCENT_CAPTCHA_SECRET",
                                "RESOURCE_IDENTIFIER_ENCRYPTION_KEY",
                                "ENTITY_TOKEN",
                                "SESSION_CRYPTO_KEY",
                                "JWT_PRIVATE_KEY"
                                )
