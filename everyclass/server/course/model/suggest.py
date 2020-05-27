from everyclass.server.utils import JSONSerializable


class Score(JSONSerializable):
    def __init__(self):
        self.score = 0
        self.details = {}
        self.reasons = []

    def __json_encode__(self):
        return {'score': self.score,
                'details': self.details,
                'reasons': self.reasons}

    def add_score(self, score: int, processor_name: str, reason: str = None):
        self.score += score
        self.details[processor_name] = score
        if reason:
            self.reasons.append(reason)
