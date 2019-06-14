from flask import current_app, request

from everyclass.rpc.http import HttpRpc


class TencentCaptcha:
    @classmethod
    def _verify(cls, ticket: str, rand_str: str, user_ip: str) -> bool:
        params = {
            "aid"         : current_app.config['TENCENT_CAPTCHA_AID'],
            "AppSecretKey": current_app.config['TENCENT_CAPTCHA_SECRET'],
            "Ticket"      : ticket,
            "Randstr"     : rand_str,
            "UserIP"      : user_ip
        }
        resp = HttpRpc.call(method="GET",
                            url='https://ssl.captcha.qq.com/ticket/verify',
                            params=params,
                            retry=True)
        return bool(resp["response"])

    @classmethod
    def verify(cls):
        if not all(map(request.form.get, ["captcha-ticket", "captcha-rand"])):
            return False
        else:
            return cls._verify(request.form["captcha-ticket"],
                               request.form["captcha-rand"],
                               request.remote_addr)
