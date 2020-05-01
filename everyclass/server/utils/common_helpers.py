import os


def plugin_available(plugin_name: str) -> bool:
    """
    check if a plugin (Sentry, apm, logstash) is available in the current environment.
    :return True if available else False
    """
    from everyclass.server.utils.config import get_config
    config = get_config()
    mode = os.environ.get("MODE", None)
    if mode:
        return mode.lower() in getattr(config, "{}_AVAILABLE_IN".format(plugin_name).upper())
    else:
        raise EnvironmentError("MODE not in environment variables")
