import functools

import elasticapm
from flask import request, session


class ElasticAPM:
    @staticmethod
    def request_finished(original_func):
        @functools.wraps(original_func)
        def _patched(self, app, response):
            if not self.app.debug or self.client.config.debug:
                # add user_id in context
                elasticapm.set_user_context(user_id=request.cookies.get('UM_distinctid', None),
                                            username=session.get('stu_id', None))
                # 业务 context
                if hasattr(request, 'elastic_context'):
                    elasticapm.set_custom_context(request.elastic_context)

            # execute the original `request_finished` function
            original_func(self, app, response)

        return _patched
