import os


def load_config():
    mode = os.environ.get('MODE')
    try:
        if mode == 'PRODUCTION':
            from everyclass.config.production import ProductionConfig
            return ProductionConfig
        else:
            from everyclass.config.development import DevelopmentConfig
            return DevelopmentConfig
    except ImportError:
        from everyclass.config.default import Config
        return Config
