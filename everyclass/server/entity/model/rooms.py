from dataclasses import dataclass
from typing import List, Dict

from everyclass.rpc import ensure_slots
from everyclass.server.utils import JSONSerializable


@dataclass
class Building(JSONSerializable):
    name: str
    rooms: List[str]

    def __json_encode__(self):
        return {'name': self.name, 'rooms': self.rooms}

    @classmethod
    def make(cls, name: str, rooms: List[str]) -> "Building":
        dct_new = {"name": name, "rooms": rooms}
        return cls(**ensure_slots(cls, dct_new))


@dataclass
class Campus(JSONSerializable):
    name: str
    buildings: Dict[str, Building]

    def __json_encode__(self):
        return {'name': self.name, 'buildings': self.buildings}

    @classmethod
    def make(cls, name: str, dct: Dict) -> "Campus":
        dct_new = dict()
        dct_new["buildings"] = dict()

        for k, v in dct.items():
            dct_new["buildings"][k] = Building(k, v)
        dct_new["name"] = name
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
            dct_new["campuses"][k] = Campus(k, v)
        return cls(**ensure_slots(cls, dct_new))
