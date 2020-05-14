from dataclasses import dataclass
from typing import List, Dict

from everyclass.rpc import ensure_slots
from everyclass.server.utils import JSONSerializable
from everyclass.server.utils.encryption import encrypt, RTYPE_ROOM


@dataclass
class Room(JSONSerializable):
    name: str
    room_id: str
    room_id_encoded: str

    def __json_encode__(self):
        return {'name': self.name, 'room_id_encoded': self.room_id_encoded}

    @classmethod
    def make(cls, room_id: str, name: str) -> "Room":
        return cls(**ensure_slots(cls, {"name": name, "room_id": room_id, "room_id_encoded": encrypt(RTYPE_ROOM, room_id)}))


@dataclass
class Building(JSONSerializable):
    name: str
    rooms: List[str]

    def __json_encode__(self):
        return {'name': self.name, 'rooms': self.rooms}

    @classmethod
    def make(cls, name: str, rooms: Dict[str, str]) -> "Building":
        dct_new = {"name": name, "rooms": [Room.make(room_id, name) for room_id, name in rooms.items()]}
        return cls(**ensure_slots(cls, dct_new))


@dataclass
class Campus(JSONSerializable):
    name: str
    buildings: List[Building]

    def __json_encode__(self):
        return {'name': self.name, 'buildings': self.buildings}

    @classmethod
    def make(cls, name: str, dct: Dict) -> "Campus":
        dct_new = {"name": name, "buildings": list()}
        for k, v in dct.items():
            dct_new["buildings"].append(Building.make(k, v))
        return cls(**ensure_slots(cls, dct_new))


@dataclass
class AllRooms(JSONSerializable):
    campuses: Dict[str, Campus]

    def __json_encode__(self):
        return {'campuses': self.campuses}

    @classmethod
    def make(cls, dct: Dict) -> "AllRooms":
        dct_new = {"campuses": {}}
        for k, v in dct.items():
            dct_new["campuses"][k] = Campus.make(k, v)
        return cls(**ensure_slots(cls, dct_new))
