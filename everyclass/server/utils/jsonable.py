import abc
import json
from typing import Dict

from flask import Response

from everyclass.common.env import is_production


class JSONSerializable:
    """需要被序列化为JSON返回给上游的对象要继承这个类（实际上是接口）"""

    @abc.abstractmethod
    def __json_encode__(self) -> Dict:
        pass


class AdvancedJSONEncoder(json.JSONEncoder):
    """自定义的JSON Encoder，支持对JSONSerializable子类的处理

    >>> import json
    ...
    ... class Some(JSONSerializable):
    ...     def __json_encode__(self) -> Dict:
    ...        return {"key": "val"}
    ... json.dumps(Some(), cls=AdvancedJSONEncoder)
    """

    def default(self, obj):
        if isinstance(obj, JSONSerializable):
            return obj.__json_encode__()
        return json.JSONEncoder.default(self, obj)


def to_json(obj) -> str:
    return json.dumps(obj, cls=AdvancedJSONEncoder)


def to_json_response(obj) -> Response:
    resp = Response(to_json(obj), mimetype='application/json')
    resp.headers.add_header('Access-Control-Allow-Origin',
                            'https://everyclass.xyz' if is_production() else 'https://staging.everyclass.xyz')
    resp.headers.add_header('Access-Control-Allow-Credentials', 'true')
    # resp.headers.add_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    return resp
