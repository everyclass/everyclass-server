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
        elif mode == 'DEVELOPMENT':
            from everyclass.server.config.development import DevelopmentConfig
            _config = DevelopmentConfig
        elif mode == 'STAGING':
            from everyclass.server.config.staging import StagingConfig
            _config = StagingConfig
        else:
            from everyclass.server.config.default import Config
            _config = Config
            logger.critical('No MODE environment variable specified. The program will use default config.')
        return _config
