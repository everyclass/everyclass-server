from typing import List, Optional

from everyclass.server.utils import JSONSerializable


class Option(JSONSerializable):
    def __init__(self, option_id: int, description: str):
        self.option_id = option_id
        self.description = description

    def __json_encode__(self):
        return {'optionID': self.option_id,
                'description': self.description}


class Question(JSONSerializable):
    question_id: int
    description: str
    options: List[Option]
    multiple: bool
    condition: str

    def __json_encode__(self):
        return {'questionID': self.question_id,
                'description': self.description,
                'options': self.options,
                'multiple': self.multiple,
                'condition': self.condition}

    def __init__(self, description: str, options: List[str], multiple: bool = False, condition: str = None):
        self.description = description
        self.multiple = multiple
        self.condition = condition
        self.options = []
        for option in options:
            self.options.append(Option(len(self.options), option))


class Questionnaire(JSONSerializable):
    questions: List[Question]

    def __json_encode__(self):
        return {'questions': self.questions}

    def add_questions(self, questions: List[Question]):
        self.questions = []
        for question in questions:
            question.question_id = len(self.questions)
            self.questions.append(question)


class Answer:
    def __init__(self, question_id: int, answer: List[int]):
        self.question_id = question_id
        self.answer = answer


class AnswerSheet:
    def __init__(self, answers: List[Answer]):
        self.answers = answers

        self.answers.sort(key=lambda a: a.question_id)

    def get_answer(self, question_id: int) -> Optional[List[int]]:
        if question_id < len(self.answers):
            if self.answers[question_id].question_id == question_id:
                return self.answers[question_id].answer
            else:
                for i in range(question_id + 1, len(self.answers)):
                    if self.answers[i].question_id == question_id:
                        return self.answers[i].answer
                return None
        return None
