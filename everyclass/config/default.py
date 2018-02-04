import os
import json
import git


class Config(object):
    # Basic config
    CONFIG_NAME = 'default'
    DEBUG = True
    SECRET_KEY = 'development_key'
    # SERVER_NAME = 'localhost'

    # CDN settings
    CDN_DOMAIN = 'cdn.domain.com'
    CDN_ENDPOINTS = ['images', 'static']
    CDN_TIMESTAMP = False

    # Git hash
    _repo = git.Repo(search_parent_directories=True)
    GIT_HASH = _repo.head.object.hexsha
    GIT_BRANCH_NAME = _repo.active_branch.name
    GIT_DESCRIBE = _repo.git.describe()

    # Sentry
    SENTRY_CONFIG = {
    }

    # Maintenance
    MAINTENANCE_FILE = os.path.join(os.getcwd(), 'maintenance')
    if os.path.exists(MAINTENANCE_FILE):
        MAINTENANCE = True
    else:
        MAINTENANCE = False

    # HTML minify
    HTML_MINIFY = True

    # Static file settings
    STATIC_VERSIONED = True
    with open(os.path.join(os.path.dirname(__file__), '../rev-manifest.json'), 'r') as static_manifest_file:
        STATIC_MANIFEST = json.load(static_manifest_file)

    # Semester settings
    DATA_LAST_UPDATE_TIME = 'Nov. 13, 2017'  # 数据最后更新日期，在页面下方展示
    DEFAULT_SEMESTER = (2017, 2018, 1)
    AVAILABLE_SEMESTERS = {
        (2016, 2017, 2): {
            'start': (2017, 2, 20),
        },
        (2017, 2018, 1): {
            'start': (2017, 9, 4),
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
