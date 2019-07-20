from datetime import datetime

import json_log_formatter
import ujson


class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
    def __init__(self):
        super().__init__()
        self.json_lib = ujson

    def json_record(self, message, extra, record):
        extra['message'] = message
        extra['date'] = datetime.utcnow()
        if record.exc_info:
            extra['exc_info'] = self.formatException(record.exc_info)
        return extra


def log_request():
    from everyclass.server import logger
    from flask import request

    logger.info('{} {}'.format(request.method, request.path))
