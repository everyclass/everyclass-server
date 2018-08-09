import functools

import elasticapm
from flask import request, session


class ElasticAPM:
    @staticmethod
    def request_finished(original_func):
        @functools.wraps(original_func)
        def _patched(self, app, response):
            if not self.app.debug or self.client.config.debug:
                # 在 context 中记录 cookie 中的 user id
                if session.get('user_id', None):
                    user_id = session['user_id']
                else:
                    user_id = request.cookies.get('UM_distinctid', None)
                elasticapm.set_user_context(user_id=user_id,
                                            username=session.get('stu_id', None))

            # execute the original `request_finished` function
            original_func(self, app, response)

        return _patched
