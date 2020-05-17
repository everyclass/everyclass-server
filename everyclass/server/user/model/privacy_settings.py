import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from everyclass.server.utils.db.postgres import Base


class PrivacySettings(Base):
    student_id = sa.Column('student_id', sa.VARCHAR(length=15), autoincrement=False, nullable=False, primary_key=True)
    level = sa.Column('level', sa.SMALLINT(), autoincrement=False, nullable=False)
    create_time = sa.Column('create_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False)
    sa.PrimaryKeyConstraint('student_id', name='privacy_settings_pkey')

    __tablename__ = 'privacy_settings'
