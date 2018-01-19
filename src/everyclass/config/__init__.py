import os
from termcolor import cprint


def load_config():
    mode = os.environ.get('MODE')

    if mode == 'PRODUCTION':
        from .production import ProductionConfig
        return ProductionConfig
    elif mode == 'DEVELOPMENT':
        from .development import DevelopmentConfig
        return DevelopmentConfig
    elif mode == 'STAGING':
        from .staging import StagingConfig
        return StagingConfig
    else:
        from .default import Config
        cprint('No MODE environment variable specified. The program will use default config.', color='yellow')
        return Config
