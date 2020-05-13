import datetime
from dataclasses import dataclass
from typing import List

from everyclass.rpc.entity import Entity
from everyclass.server.entity.domain import get_semester_date
from everyclass.server.utils import JSONSerializable
from everyclass.server.utils.encryption import encrypt, RTYPE_ROOM


@dataclass
class Room(JSONSerializable):
    name: str  # 教室名
    room_id: str  # 教室 ID
    room_id_encoded: str  # 编码后的教室 ID

    def __json_encode__(self):
        return {'name': self.name, 'room_id_encoded': self.room_id_encoded}


class AvailableRooms(JSONSerializable):
    rooms = List[Room]

    def __json_encode__(self):
        return {'rooms': self.rooms}

    def __init__(self, campus: str, building: str, date: datetime.date, time: str):
        _, week, day = get_semester_date(date)

        resp = Entity.get_available_rooms(week, f"{day}{time}", campus, building)
        for r in resp:
            Room(name=r['name'], room_id=r['code'], room_id_encoded=encrypt(RTYPE_ROOM, r['code']))
