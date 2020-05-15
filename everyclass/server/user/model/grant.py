from typing import List, Optional

from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func

from everyclass.server.utils.db.postgres import Base, db_session

GRANT_TYPE_VIEWING = 'viewing'

GRANT_STATUS_PENDING = 'pending'
GRANT_STATUS_VALID = 'valid'
GRANT_STATUS_REVOKED = 'revoked'


class Grant(Base):
    """用户对用户的授权

    当前唯一的授权类型是查看课表，grant_type为1"""

    __tablename__ = 'grants'

    record_id = Column(Integer, primary_key=True)
    grant_type = Column(ENUM(GRANT_TYPE_VIEWING, name='grant_type'), nullable=False)  # 1 for viewing
    status = Column(ENUM(GRANT_STATUS_PENDING, GRANT_STATUS_VALID, GRANT_STATUS_REVOKED, name='grant_status'), nullable=False)
    grant_time = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(String(15), nullable=False)
    to_user_id = Column(String(15), nullable=False)

    @classmethod
    def new(cls, user_id: str, to_user_id: str) -> "Grant":
        grant = Grant(user_id=user_id, to_user_id=to_user_id, grant_type=GRANT_TYPE_VIEWING, status=GRANT_STATUS_PENDING)
        db_session.add(grant)
        db_session.commit()
        return grant

    def accept(self):
        if self.status == GRANT_STATUS_PENDING:
            self.status = GRANT_STATUS_VALID
        else:
            raise ValueError(f"status {self.status} cannot be transformed to valid")

    @classmethod
    def has_grant(cls, user_id: str, to_user_id: str) -> bool:
        """检查是否有访问授权，user_id为访问的人，to_user_id为被访问的人"""
        try:
            result = db_session.query(cls). \
                filter(cls.user_id == user_id). \
                filter(cls.to_user_id == to_user_id). \
                filter(cls.status == GRANT_STATUS_VALID).all()
            if len(result) > 0:
                return True
            else:
                return False
        except NoResultFound:
            return False

    @classmethod
    def request_for_grant(cls, user_id: str, to_user_id: str) -> "Grant":
        from everyclass.server.user.exceptions import AlreadyGranted
        from everyclass.server.user.exceptions import HasPendingRequest

        pending_grants = db_session.query(cls). \
            filter(cls.user_id == user_id). \
            filter(cls.to_user_id == to_user_id). \
            filter(cls.status == GRANT_STATUS_PENDING).all()

        if len(pending_grants) > 0:
            raise HasPendingRequest('当前已有等待通过的申请，请勿重复申请')

        if cls.has_grant(user_id, to_user_id):
            raise AlreadyGranted('权限已具备，请勿重复申请')
        return cls.new(user_id, to_user_id)

    @classmethod
    def get_requests(cls, user_id: str) -> List["Grant"]:
        pending_grants = db_session.query(cls). \
            filter(cls.to_user_id == user_id). \
            filter(cls.status == GRANT_STATUS_PENDING).all()
        return pending_grants

    @classmethod
    def get_by_id(cls, record_id: int) -> Optional["Grant"]:
        try:
            db_session.query(cls).filter(cls.record_id == record_id).one()
        except NoResultFound:
            return None
