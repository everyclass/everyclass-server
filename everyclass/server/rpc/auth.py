from flask import current_app as app

from everyclass.server.rpc.http import HttpRpc


class Auth:
    @classmethod
    def register_by_email(cls, request_id: str, student_id: str):
        return HttpRpc.call(method='POST',
                            url='{}/register_by_email'.format(app.config['AUTH_BASE_URL']),
                            data={'request_id': request_id,
                                  'student_id': student_id},
                            retry=True)

    @classmethod
    def verify_email_token(cls, token: str):
        return HttpRpc.call(method='POST',
                            url='{}/verify_email_token'.format(app.config['AUTH_BASE_URL']),
                            data={"email_token": token},
                            retry=True)

    @classmethod
    def register_by_password(cls, request_id: str, student_id: str, password: str):
        return HttpRpc.call(method='POST',
                            url='{}/register_by_password'.format(app.config['AUTH_BASE_URL']),
                            data={'request_id': request_id,
                                  'student_id': student_id,
                                  'password'  : password})

    @classmethod
    def get_result(cls, request_id: str):
        return HttpRpc.call(method='GET',
                            url='{}/get_result'.format(app.config['AUTH_BASE_URL']),
                            data={'request_id': request_id},
                            retry=True)
