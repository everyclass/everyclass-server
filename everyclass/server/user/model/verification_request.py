import uuid
from typing import Optional

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, ENUM, HSTORE
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash

from everyclass.server.utils.db.postgres import Base, session_maker


class VerificationRequest(Base):
    __tablename__ = 'identity_verify_requests'

    STATUS_SENT = "EMAIL_SENT"  # 邮件已发送（实际表示的是请求了auth服务，但不能确定邮件真的发出去了）
    STATUS_TKN_PASSED = "EMAIL_TOKEN_PASSED"  # 邮件验证通过，密码未设置
    STATUS_PASSWORD_SET = "PASSWORD_SET"

    STATUS_WAIT_VERIFY = "VERIFY_WAIT"  # 密码验证，等待 everyclass-auth 返回验证结果
    STATUS_PWD_SUCCESS = "PASSWORD_PASSED"  # 密码验证成功

    STATUSES = (STATUS_TKN_PASSED,
                STATUS_SENT,
                STATUS_PASSWORD_SET,
                STATUS_WAIT_VERIFY,
                STATUS_PWD_SUCCESS)

    METHOD_EMAIL = 'email'
    METHOD_PASSWORD = 'password'

    request_id = Column(UUID(as_uuid=True), primary_key=True)
    identifier = Column(String(15), nullable=False)
    method = Column(ENUM(METHOD_PASSWORD, METHOD_EMAIL, name='identity_verify_methods'), nullable=False)
    status = Column(ENUM(*STATUSES, name='identity_verify_statuses'), nullable=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    extra = Column(HSTORE)

    def _set_status(self, status: str):
        if status not in self.STATUSES:
            raise ValueError(f"invalid status {status}")

        self.status = status
        with session_maker() as session:
            session.add(self)
            session.commit()

    def set_status_token_passed(self):
        if self.status == self.STATUS_SENT:
            self._set_status(self.STATUS_TKN_PASSED)
        else:
            raise ValueError(f"state {self.status} cannot be transitioned to {self.STATUS_TKN_PASSED}")

    def set_status_password_set(self):
        if self.status == self.STATUS_TKN_PASSED:
            self._set_status(self.STATUS_PASSWORD_SET)
        else:
            raise ValueError(f"state {self.status} cannot be transitioned to {self.STATUS_PASSWORD_SET}")

    def set_status_success(self):
        if self.status == self.STATUS_WAIT_VERIFY:
            self._set_status(self.STATUS_PWD_SUCCESS)
        else:
            raise ValueError(f"state {self.status} cannot be transitioned to {self.STATUS_PWD_SUCCESS}")

    @classmethod
    def _new_request(cls, identifier: str, verification_method: str, status: str, password: str = None) -> str:
        """
        新增一条注册请求

        :param identifier: 学号/教工号
        :param verification_method: password or email
        :param status: status of the request
        :param password: if register by password, fill everyclass password here
        :return: the `request_id`
        """
        if verification_method not in (cls.METHOD_PASSWORD, cls.METHOD_EMAIL):
            raise ValueError("verification_method must be one of email and password")

        request_id = uuid.uuid4()

        extra_doc = {}
        if password:
            extra_doc.update({"password": generate_password_hash(password)})

        request = VerificationRequest(request_id=request_id, identifier=identifier, method=verification_method,
                                      status=status, extra=extra_doc)
        with session_maker() as session:
            session.add(request)
            session.commit()

        return str(request_id)

    @classmethod
    def new_email_request(cls, identifier: str):
        return cls._new_request(identifier, VerificationRequest.METHOD_EMAIL, VerificationRequest.STATUS_SENT)

    @classmethod
    def new_password_request(cls, identifier: str, password: str):
        return cls._new_request(identifier, cls.METHOD_PASSWORD, cls.STATUS_WAIT_VERIFY, password=password)

    @classmethod
    def find_by_id(cls, request_id: uuid.UUID) -> Optional["VerificationRequest"]:
        """通过ID查找注册请求，如果没找到返回None"""
        with session_maker() as session:
            try:
                return session.query(cls).filter(cls.request_id == request_id).one()
            except NoResultFound:
                return None
