import os


def load_config():
    mode = os.environ.get('MODE')
    try:
        if mode == 'PRODUCTION':
            from .production import ProductionConfig
            return ProductionConfig
        elif mode == 'DEVELOPMENT':
            from .development import DevelopmentConfig
            return DevelopmentConfig
        elif mode == 'STAGING':
            from .staging import StagingConfig
            return StagingConfig
    except ImportError:
        from .default import Config
        return Config
