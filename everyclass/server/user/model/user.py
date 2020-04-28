import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.security import check_password_hash, generate_password_hash

from everyclass.server.utils.db.postgres import Base, Session


class User(Base):
    __tablename__ = 'users'

    identifier = Column('student_id', String(15), primary_key=True)
    password = Column(String(120), nullable=False)
    create_time = Column(DateTime, nullable=False)

    def __repr__(self):
        return "<User(identifier='%s')>" % self.identifier

    def check_password(self, password: str) -> bool:
        """检查密码是否正确"""
        return check_password_hash(self.password, password)

    @classmethod
    def add_user(cls, identifier: str, password: str, password_encrypted: bool = False) -> None:
        """新增用户。当用户已存在时，抛出ValueError。

        :param identifier: 学号或教工号
        :param password: 密码
        :param password_encrypted: 密码是否已经被加密过了（否则会被二次加密）
        """
        if not password_encrypted:
            password_hash = generate_password_hash(password)
        else:
            password_hash = password

        user = User(identifier=identifier, password=password_hash, create_time=datetime.datetime.now())

        session = Session()
        session.add(user)
        try:
            session.commit()
        except IntegrityError as e:
            raise ValueError("User already exists") from e

    @classmethod
    def get_by_id(cls, identifier: str) -> Optional["User"]:
        """通过学号或教工号获取用户，如果获取不到返回none"""
        session = Session()
        try:
            return session.query(User).filter(User.identifier == identifier).one()
        except NoResultFound:
            return None

    @classmethod
    def exists(cls, identifier: str) -> bool:
        user = User.get_by_id(identifier)
        return user is not None
