import os


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
