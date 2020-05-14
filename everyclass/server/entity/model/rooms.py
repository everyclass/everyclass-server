from dataclasses import dataclass
from typing import List, Dict

from everyclass.rpc import ensure_slots
from everyclass.server.utils import JSONSerializable
from everyclass.server.utils.encryption import encrypt, RTYPE_ROOM


@dataclass
class Building(JSONSerializable):
    name: str
    rooms: List[str]
    rooms_encoded: List[str]

    def __json_encode__(self):
        return {'name': self.name, 'rooms_encoded': self.rooms_encoded}

    @classmethod
    def make(cls, name: str, rooms: List[str]) -> "Building":
        dct_new = {"name": name, "rooms": rooms, 'rooms_encoded': [encrypt(RTYPE_ROOM, room) for room in rooms]}
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
