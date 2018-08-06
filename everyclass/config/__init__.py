import os
from termcolor import cprint


def load_config():
    mode = os.environ.get('MODE')

    if mode == 'PRODUCTION':
        from everyclass.config.production import ProductionConfig
        return ProductionConfig
    elif mode == 'DEVELOPMENT':
        from everyclass.config.development import DevelopmentConfig
        return DevelopmentConfig
    elif mode == 'STAGING':
        from everyclass.config.staging import StagingConfig
        return StagingConfig
    else:
        from everyclass.config.default import Config
        cprint('No MODE environment variable specified. The program will use default config.', color='yellow')
        return Config
