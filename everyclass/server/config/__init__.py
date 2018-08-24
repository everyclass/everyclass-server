import os
from termcolor import cprint


def load_config():
    mode = os.environ.get('MODE')

    if mode == 'PRODUCTION':
        from everyclass.server.config.production import ProductionConfig
        return ProductionConfig
    elif mode == 'DEVELOPMENT':
        from everyclass.server.config.development import DevelopmentConfig
        return DevelopmentConfig
    elif mode == 'STAGING':
        from everyclass.server.config.staging import StagingConfig
        return StagingConfig
    else:
        from everyclass.server.config.default import Config
        cprint('No MODE environment variable specified. The program will use default config.', color='yellow')
        return Config
