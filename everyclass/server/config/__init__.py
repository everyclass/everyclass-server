import os

from everyclass.server.config.default import Config as DefaultConfig

_config_inited = True


class MixedConfig(DefaultConfig):
    pass


def get_config():
    """
    单例配置加载
    :return: Config 类的实例
    """

    if _config_inited:
        return MixedConfig
    else:
        mode = os.environ.get('MODE')
        _override_config = {}

        if mode == 'PRODUCTION':
            from everyclass.server.config.production import ProductionConfig
            _override_config = ProductionConfig
            MixedConfig.CONFIG_NAME = 'production'
        elif mode == 'DEVELOPMENT':
            from everyclass.server.config.development import DevelopmentConfig
            _override_config = DevelopmentConfig
            MixedConfig.CONFIG_NAME = 'development'
        elif mode == 'STAGING':
            from everyclass.server.config.staging import StagingConfig
            _override_config = StagingConfig
            MixedConfig.CONFIG_NAME = 'staging'
        elif mode == 'TESTING':
            from everyclass.server.config.testing import TestingConfig
            _override_config = TestingConfig
            MixedConfig.CONFIG_NAME = 'testing'
        else:
            MixedConfig.CONFIG_NAME = 'default'
            print('No valid MODE environment variable specified. Default config will be used.')

        for key in dir(_override_config):
            if key.isupper():
                if isinstance(getattr(_override_config, key), dict) \
                        and key in dir(MixedConfig) \
                        and isinstance(getattr(MixedConfig, key), dict):
                    # 字典内容增量覆盖
                    dict_to_modify = getattr(MixedConfig, key)
                    for k, v in getattr(_override_config, key).items():
                        dict_to_modify[k] = v
                    setattr(MixedConfig, key, dict_to_modify)
                else:
                    # 其他类型的值直接覆盖
                    setattr(MixedConfig, key, getattr(_override_config, key))
        global _config_inited
        _config_inited = True
        return MixedConfig
