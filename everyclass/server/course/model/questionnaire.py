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

    @classmethod
    def get(cls):
        """获得选修课推荐问卷"""
        from everyclass.server.course.model import CourseMeta

        questionnaire = Questionnaire()

        q0 = Question("你选修课程的主要目的是什么？", ['学习专业外感兴趣的知识', '尽可能提升加权成绩', '结识具有相同兴趣的同学'])
        # KnowledgeProcessor: 使用课程评价中"是否学到了新的知识"进行打分
        # 如果选了'学习专业外感兴趣的知识'，加权为20；
        # 如果选了'结识具有相同兴趣的同学'，加权为10；
        # 如果选了'尽可能提升加权成绩'，加权为5；

        q1 = Question("你期望的成绩区间是？", ['>95', '>90', '>80', '成绩无所谓，学到东西就好'])
        # ScoreProcessor:
        # 如果q0选了'尽可能提升加权成绩'，作为过滤器使用，不符合要求直接过滤；
        # 否则：当满足成绩要求时，满足度=100，每低于要求一档，满足度-20

        q2 = Question("你感兴趣的课程主题是？",
                      CourseMeta.CATEGORIES, multiple=True)
        # ThemeProcessor：
        # 如果q0选了'学习专业外感兴趣的知识'，表明有非常强的选题倾向性，满足所选分类的课程给100满足度，否则给20
        # 如果q0选择了'结识具有相同兴趣的同学'，满足所选分类给100满足度，否则给50
        # 如果q0选择了'尽可能提升加权成绩'，满足所选分类课程给100满足度，否则给80

        q3 = Question("你希望通过这门课认识更多朋友吗？", ['希望认识更多朋友，无论性别', '希望认识更多异性朋友', '随缘', '不用，我听课就好'])
        q4 = Question("你希望结交", ['男生', '女生'], condition="3:1")
        # FriendProcessor：如果q0选了3，且q3选了2，则过滤男女比例过于不协调的课程

        q5 = Question("对课堂考勤有什么想法吗？", ['无所谓，反正我每节课都会来', '希望偶尔能请假', '希望老师要求松一点，偶尔不来也问题不大'])
        # AttendanceProcessor：
        # 如果选择了'无所谓，反正我每节课都会来'，加权为0（考勤rate不对class的评分有影响）；
        # 如果选择了'希望偶尔能请假'，给4、5惩罚加权-20；
        # 如果选择了'希望老师要求松一点，偶尔不来也不会被发现'，4、5过滤，3惩罚加权-20

        questionnaire.add_questions([q0, q1, q2, q3, q4, q5])

        return questionnaire


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

    def get_advice(self):
        """根据选修课推荐问卷获得推荐结果"""
        from everyclass.server.course.model import Score, KlassMeta, CourseMeta
        from everyclass.server.utils.base_exceptions import InvalidRequestException

        # 获得教学班与score二元组的列表
        classes = [(klass, Score()) for klass in KlassMeta.get_all()]
        print("classes get")

        q0a = self.get_answer(0)
        q1a = self.get_answer(1)
        q2a = self.get_answer(2)
        q3a = self.get_answer(3)
        q4a = self.get_answer(4)
        q5a = self.get_answer(5)
        for klass, score in classes:
            # KnowledgeProcessor: 使用课程评价中"是否学到了新的知识"进行打分
            processor_name = 'KnowledgeProcessor'
            reason = f"课堂收获{klass.rating_knowledge}/5"
            if q0a == [0]:
                score.add_score(klass.rating_knowledge * 20, processor_name, reason)
            elif q0a == [1]:
                score.add_score(klass.rating_knowledge * 10, processor_name, reason)
            elif q0a == [2]:
                score.add_score(klass.rating_knowledge * 5, processor_name, reason)
            else:
                raise InvalidRequestException(f"answer of question 0 ({q0a}) is not expected")

            # ScoreProcessor
            processor_name = 'ScoreProcessor'
            if q0a == [2]:
                # 为了成绩的严格筛选成绩
                if q1a == [0]:
                    wanted_score = 95
                elif q1a == [1]:
                    wanted_score = 90
                elif q1a == [2]:
                    wanted_score = 80
                else:
                    wanted_score = 60
                if klass.final_score < wanted_score:
                    score.add_score(-1000, processor_name)
            else:
                # 不需严格按照成绩筛选课程，但期望和现实的差异影响满意度
                if klass.final_score >= 95:
                    score_level = 1
                elif klass.final_score >= 90:
                    score_level = 2
                elif klass.final_score >= 80:
                    score_level = 3
                else:
                    score_level = 4

                if q1a == [0]:
                    wanted_level = 1
                elif q1a == [1]:
                    wanted_level = 2
                elif q1a == [2]:
                    wanted_level = 3
                else:
                    wanted_level = 4

                if score_level <= wanted_level:
                    satisfaction = 100
                else:
                    satisfaction = 100 - (score_level - wanted_level) * 20

                score.add_score(satisfaction, processor_name, f"平均期末成绩：{klass.final_score}")

            # ThemeProcessor：
            processor_name = 'ThemeProcessor'
            if q0a == [0]:
                satisfaction_hit = 100
                satisfaction_miss = 20
            elif q0a == [1]:
                satisfaction_hit = 100
                satisfaction_miss = 50
            else:
                satisfaction_hit = 100
                satisfaction_miss = 80
            interested_categories = [CourseMeta.CATEGORIES[i] for i in q2a]
            if klass.course.main_category in interested_categories:
                score.add_score(satisfaction_hit, processor_name)
            else:
                score.add_score(satisfaction_miss, processor_name)

            processor_name = 'FriendProcessor'
            # FriendProcessor：如果q0选了2，且q3选了1，则过滤男女比例过于不协调的课程
            if q0a == [2] and q3a == [1]:
                if (q4a == [0] and klass.gender_rate <= 2) or (q4a == [1] and klass.gender_rate >= 8):
                    # 想认识男生、课程80%以上为女生，或想认识女生，课程80%以上为男生
                    score.add_score(-1000, processor_name, f"男女比{klass.gender_rate}:{10 - klass.gender_rate}")
                else:
                    score.add_score(0, processor_name, f"男女比{klass.gender_rate}:{10 - klass.gender_rate}")

            processor_name = 'AttendanceProcessor'
            # AttendanceProcessor：
            # 如果选择了'无所谓，反正我每节课都会来'，加权为0（考勤rate不对class的评分有影响）；
            # 如果选择了'希望偶尔能请假'，给4、5惩罚加权-20；
            # 如果选择了'希望老师要求松一点，偶尔不来也不会被发现'，4、5过滤，3惩罚加权-20
            if q5a == [1] and klass.rating_attendance >= 4:
                score.add_score(-20 * klass.rating_attendance, processor_name)
            if q5a == [2]:
                if klass.rating_attendance >= 4:
                    score.add_score(-1000, processor_name)
                elif klass.rating_attendance >= 3:
                    score.add_score(-20 * klass.rating_attendance, processor_name)

        print("scored")

        classes.sort(key=lambda t: t[1].score, reverse=True)
        print("sorted")
        return {'classes': classes[:10]}
