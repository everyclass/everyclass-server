import functools

import elasticapm
from flask import session

from everyclass.server.consts import SESSION_CURRENT_USER


class ElasticAPM:
    @staticmethod
    def request_finished(original_func):
        @functools.wraps(original_func)
        def _patched(self, app, response):
            if not self.app.debug or self.client.config.debug:
                # 在 context 的 user_id 中记录匿名 user id，在 username 中记录当前登录的用户学号
                if session.get('user_id', None):
                    user_id = session['user_id']
                    elasticapm.set_user_context(user_id=user_id)

                if session.get(SESSION_CURRENT_USER, None):
                    elasticapm.set_user_context(username=session[SESSION_CURRENT_USER])

            # execute the original `request_finished` function
            original_func(self, app, response)

        return _patched


class ReCaptcha(object):
    """replace the original google domain to domestic proxy site"""

    def get_code(self):
        """
        Returns the new ReCaptcha code
        :return:
        """
        return "" if not self.is_enabled else ("""
        <script src='//www.recaptcha.net/recaptcha/api.js'></script>
        <div class="g-recaptcha" data-sitekey="{SITE_KEY}" data-theme="{THEME}" data-type="{TYPE}" data-size="{SIZE}"\
         data-tabindex="{TABINDEX}"></div>
        """.format(SITE_KEY=self.site_key, THEME=self.theme, TYPE=self.type, SIZE=self.size, TABINDEX=self.tabindex))
