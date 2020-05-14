import datetime
from dataclasses import dataclass
from typing import List

from sqlalchemy import Column, String, Date, Integer, UniqueConstraint

from everyclass.rpc import ensure_slots
from everyclass.rpc.entity import Entity
from everyclass.server import logger
from everyclass.server.entity.domain import get_semester_date
from everyclass.server.utils import JSONSerializable
from everyclass.server.utils.db.postgres import Base, db_session
from everyclass.server.utils.db.redis import redis, redis_prefix
from everyclass.server.utils.encryption import encrypt, RTYPE_ROOM


@dataclass
class Room(JSONSerializable):
    name: str  # 教室名
    room_id: str  # 教室 ID
    room_id_encoded: str  # 编码后的教室 ID
    occupied_feedback_cnt: int  # 反馈已占用的人数

    def __json_encode__(self):
        return {'name': self.name, 'room_id_encoded': self.room_id_encoded, 'occupied_feedback_cnt': self.occupied_feedback_cnt}

    @classmethod
    def make(cls, name: str, room_id: str, feedback_cnt: int):
        dct = {'name': name,
               'room_id': room_id,
               'room_id_encoded': encrypt(RTYPE_ROOM, room_id),
               'occupied_feedback_cnt': feedback_cnt}
        return cls(**ensure_slots(cls, dct))


class AvailableRooms(JSONSerializable):

    def __json_encode__(self):
        return {'rooms': self.rooms, 'date': self.date}

    def __init__(self, campus: str, building: str, date: datetime.date, time: str):
        _, week, day = get_semester_date(date)

        self.date = f"{date.year}-{date.month}-{date.day}"

        resp = Entity.get_available_rooms(week, f"{day + 1}{time}", campus, building)
        logger.info(f"get available rooms for week={week}, session={day + 1}{time}, campus={campus}, building={building}")

        self.rooms: List[Room] = []
        for r in resp:
            # 反馈占用计数
            feedback_cnt = redis.get(f"{redis_prefix}:avail_room_occupy_fb:{week}:{day}:{time}:{r['code']}")

            self.rooms.append(Room.make(name=r['name'], room_id=r['code'], feedback_cnt=int(feedback_cnt.decode()) if feedback_cnt else 0))


class UnavailableRoomReport(Base):
    """空教室实际不可用的反馈"""

    __tablename__ = 'unavailable_room_report'

    record_id = Column(Integer, primary_key=True)
    room_id = Column(String)
    date = Column(Date)
    time = Column(String(4))
    reporter = Column(String(15))
    reporter_type = Column(String)

    __table_args__ = (UniqueConstraint('room_id', 'date', 'time', 'reporter', 'reporter_type', name='unavailable_room_report_uniq'),
                      )

    @classmethod
    def new(cls, room_id: str, date: datetime.date, time: str, user_type: str, user_id: str) -> "UnavailableRoomReport":
        report = UnavailableRoomReport(room_id=room_id, date=date, time=time, reporter=user_id, reporter_type=user_type)
        db_session.add(report)
        db_session.commit()

        _, week, day = get_semester_date(date)
        redis.incr(f"{redis_prefix}:avail_room_occupy_fb:{week}:{day}:{time}:{room_id}", 1)
        return report
