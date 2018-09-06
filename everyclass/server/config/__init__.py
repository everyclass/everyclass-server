import os

from everyclass.server import logger

_config = None


def get_config():
    """
    单例配置加载
    :return: Config 类的实例
    """
    global _config

    if _config:
        return _config
    else:
        mode = os.environ.get('MODE')

        if mode == 'PRODUCTION':
            from everyclass.server.config.production import ProductionConfig
            _config = ProductionConfig
            _config.CONFIG_NAME = 'production'
        elif mode == 'DEVELOPMENT':
            from everyclass.server.config.development import DevelopmentConfig
            _config = DevelopmentConfig
            _config.CONFIG_NAME = 'development'
        elif mode == 'STAGING':
            from everyclass.server.config.staging import StagingConfig
            _config = StagingConfig
            _config.CONFIG_NAME = 'staging'
        else:
            from everyclass.server.config.default import Config
            _config = Config
            _config.CONFIG_NAME = 'default'
            logger.critical('No valid MODE environment variable specified. Default config will be used.')
        return _config
