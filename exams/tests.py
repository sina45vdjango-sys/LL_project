"""The exam mode: the official numbers, the paper, the score, and the pages.

The fixture builds the smallest content that can produce a real exam — 15 questions with a
recording, 15 with a passage behind them and 15 answered by typing, plus a draft exercise
that must stay invisible — so every section can be checked on its own and no assertion
depends on the seeded course.

What the tests pin is what would be expensive to get wrong: the official arithmetic (one
rounding, in one place), a paper that is stored rather than re-derived, a deadline the
server enforces rather than the browser, and a score that belongs to the sitting and not to
whatever the learner practised afterwards.
"""

import io
import json
import tempfile
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from exercises.generated import DICTATION_DRILL_PREFIX, LISTENING_DRILL_PREFIX, READING_DRILL_PREFIX
from exercises.models import Answer, Exercise, ExerciseAttempt, Question, QuestionTarget
from lessons.models import Course, LanguageLevel, Lesson
from vocabulary.models import Sentence, Word, WordProgress

from .models import ExamRun, ExamRunQuestion
from .sections import Section
from .paper import (
    build_paper,
    instruction_rows,
    is_typed,
    markable,
    open_run,
    paper_problems,
    remaining_minutes,
    score,
    section_of,
    section_pools,
    spoken_practice,
    time_is_up,
)
from .management.commands.export_a1_exam_items import MARKED_PER_SECTION
from .step import PER_SECTION, STEP_SIZE, step_questions
from .spec import (
    INSTRUCTIONS,
    ITEMS_PER_SECTION,
    MAX_POINTS,
    PASS_POINTS,
    SCORE_FACTOR,
    SECTION_FACTS,
    SECTION_ORDER,
    SPOKEN_MAX_POINTS,
    SPRECHEN,
    WRITTEN_MAX_POINTS,
    WRITTEN_MINIMUM,
)


class ExamSpecTests(SimpleTestCase):
    """The official facts, pinned so a typed-in number cannot drift.

    They come from the exam's own Durchführungsbestimmungen, and the mock's whole promise —
    the same shape, scored the same way — rests on them still being those numbers.
    """

    def test_the_written_sections_are_the_official_three(self):
        self.assertEqual(len(SECTION_ORDER), 3)
        self.assertEqual(SECTION_ORDER[0], Section.HOEREN)
        self.assertEqual(SECTION_ORDER[1], Section.LESEN)
        self.assertEqual(SECTION_ORDER[2], Section.SCHREIBEN)

    def test_every_written_section_asks_the_official_fifteen_items(self):
        for code in SECTION_ORDER:
            self.assertEqual(SECTION_FACTS[code]["items"], ITEMS_PER_SECTION)
        self.assertEqual(ITEMS_PER_SECTION, 15)

    def test_a_perfect_written_paper_is_worth_the_official_seventy_five(self):
        # 3 sections × 15 raw points × 1.66, rounded once at the end.
        self.assertEqual(round(3 * ITEMS_PER_SECTION * SCORE_FACTOR), WRITTEN_MAX_POINTS)
        self.assertEqual(WRITTEN_MAX_POINTS, 75)

    def test_the_four_sections_add_up_to_one_hundred_points(self):
        self.assertEqual(WRITTEN_MAX_POINTS + SPOKEN_MAX_POINTS, MAX_POINTS)
        self.assertEqual(SPOKEN_MAX_POINTS, 25)
        # 15 raw points scale to 25, exactly as a written section's do.
        self.assertEqual(round(SPRECHEN["points"] * SCORE_FACTOR), SPOKEN_MAX_POINTS)

    def test_the_written_minimum_is_the_exams_own_rule(self):
        # 34 written points plus a perfect oral section is 59; 35 plus 25 is exactly the
        # pass mark. That is why the exam states 35 and the page repeats it.
        self.assertEqual(WRITTEN_MINIMUM + SPOKEN_MAX_POINTS, PASS_POINTS)
        self.assertEqual(PASS_POINTS, 60)

    def test_the_spoken_part_is_three_parts_of_five_minutes(self):
        total_minutes = 0
        total_points = 0
        for part in SPRECHEN["parts"]:
            total_minutes += part["minutes"]
            total_points += part["points"]
        self.assertEqual(len(SPRECHEN["parts"]), 3)
        self.assertEqual(total_minutes, SPRECHEN["minutes"])
        self.assertEqual(total_points, SPRECHEN["points"])

    def test_every_instruction_word_has_a_persian_meaning(self):
        self.assertTrue(INSTRUCTIONS)
        for entry in INSTRUCTIONS:
            self.assertTrue(entry["german"].strip())
            self.assertTrue(entry["fa"].strip())


class ExamFixture(TestCase):
    """A course with exactly enough published questions for one full paper."""

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="دورهٔ آلمانی A1", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", order=1, estimated_time=60, is_published=True
        )

        cls.word = Word.objects.create(
            word="Haus", word_type="NOUN", article="das", gender="N", plural="die Häuser",
            meaning_fa="خانه", level=cls.level, is_published=True,
        )
        # One instruction word the course teaches, so the glossary's two chip states can
        # both be checked against real rows.
        cls.losung = Word.objects.create(
            word="Lösung", word_type="NOUN", article="die", gender="F",
            meaning_fa="پاسخ", level=cls.level, is_published=True,
        )
        cls.sentence = Sentence.objects.create(
            text="Ich heiße Ali.", translation_fa="اسمم علی است.", level=cls.level,
            is_published=True,
        )

        cls.exercise = Exercise.objects.create(
            lesson=cls.lesson, title="تمرین آزمون", type="MULTIPLE_CHOICE", order=1, is_published=True
        )
        cls.draft_exercise = Exercise.objects.create(
            lesson=cls.lesson, title="تمرین پیش‌نویس", type="MULTIPLE_CHOICE", order=2, is_published=False
        )

        cls.audio_questions = []
        cls.passage_questions = []
        cls.typed_questions = []

        order = 0

        # The exam set is a stored mark, so the fixture marks what it creates exactly the
        # way `export_a1_exam_items` would: this is the curated set, not a classification
        # recomputed from the questions' shape.
        for index in range(ITEMS_PER_SECTION):
            order += 1
            question = Question.objects.create(
                exercise=cls.exercise, prompt=f"صوت {index}", order=order,
                audio="questions/audio/prompt.mp3", exam_section=Section.HOEREN,
            )
            Answer.objects.create(question=question, text="richtig", is_correct=True, order=1)
            Answer.objects.create(question=question, text="falsch", is_correct=False, order=2)
            QuestionTarget.objects.create(question=question, word=cls.word, role="TESTED_ITEM")
            cls.audio_questions.append(question)

        for index in range(ITEMS_PER_SECTION):
            order += 1
            question = Question.objects.create(
                exercise=cls.exercise, prompt=f"متن {index}", order=order,
                exam_section=Section.LESEN,
            )
            Answer.objects.create(question=question, text="درست", is_correct=True, order=1)
            Answer.objects.create(question=question, text="نادرست", is_correct=False, order=2)
            QuestionTarget.objects.create(
                question=question, sentence=cls.sentence, role="CONTEXT"
            )
            cls.passage_questions.append(question)

        for index in range(ITEMS_PER_SECTION):
            order += 1
            question = Question.objects.create(
                exercise=cls.exercise, prompt=f"بنویس {index}", order=order,
                exam_section=Section.SCHREIBEN,
            )
            Answer.objects.create(question=question, text="Haus", is_correct=True, order=1)
            cls.typed_questions.append(question)

        # A scramble: one answer row (the sentence), so the typing rule alone would put it
        # in SCHREIBEN — but the exam renders a paper's questions from many exercises at
        # once and cannot show the word bank, so it must never enter a pool.
        cls.scramble_exercise = Exercise.objects.create(
            lesson=cls.lesson, title="تمرین جمله — مرتب کردن",
            type=Exercise.ExerciseType.SCRAMBLE, order=3, is_published=True,
        )
        cls.scramble_question = Question.objects.create(
            exercise=cls.scramble_exercise, prompt="جمله را مرتب کن", order=1,
        )
        Answer.objects.create(
            question=cls.scramble_question, text="Ich heiße Ali.", is_correct=True, order=1
        )

        # Two questions that may never be asked, both *marked* so the tests prove the
        # mark alone is not enough: one sits in a draft exercise, one has no authored
        # correct answer at all.
        cls.draft_question = Question.objects.create(
            exercise=cls.draft_exercise, prompt="پیش‌نویس", order=1,
            audio="questions/audio/draft.mp3", exam_section=Section.HOEREN,
        )
        Answer.objects.create(question=cls.draft_question, text="richtig", is_correct=True, order=1)

        cls.unanswerable = Question.objects.create(
            exercise=cls.exercise, prompt="بی‌پاسخ", order=order + 1,
            audio="questions/audio/none.mp3", exam_section=Section.HOEREN,
        )
        Answer.objects.create(question=cls.unanswerable, text="نادرست", is_correct=False, order=1)

        # Perfectly exam-shaped and deliberately left out of the set: nothing may pull a
        # question into a paper that nobody marked (audit P-20).
        cls.unmarked = Question.objects.create(
            exercise=cls.exercise, prompt="علامت‌نخورده", order=order + 2,
            audio="questions/audio/unmarked.mp3",
        )
        Answer.objects.create(question=cls.unmarked, text="richtig", is_correct=True, order=1)

        cls.user = User.objects.create_user(username="examlernt", password="a-strong-password")
        cls.other = User.objects.create_user(username="examfremd", password="a-strong-password")

    def start_run(self, user=None):
        """A run with a paper on it, built the way the view builds one."""
        if user is None:
            user = self.user
        run = ExamRun.objects.create(user=user)
        build_paper(run)
        return run

    def answer_run(self, run, correct_count, answered=True):
        """Mark the first ``correct_count`` questions right, optionally answer the rest wrong."""
        rows = list(run.questions.order_by("order"))

        for position, row in enumerate(rows):
            if position < correct_count:
                row.is_correct = True
            elif answered:
                row.is_correct = False
            row.save(update_fields=["is_correct"])

    def answer_all(self, run):
        """Every section answered right — one whole correct paper."""
        run.questions.update(is_correct=True)


class ExamPaperTests(ExamFixture):
    """``exams.paper``: which questions a section may ask, and how the paper is written."""

    def test_the_listening_section_is_drawn_from_questions_that_carry_a_recording(self):
        pool = section_pools()[Section.HOEREN]
        self.assertEqual(len(pool), ITEMS_PER_SECTION)
        for question in pool:
            self.assertTrue(question.audio)

    def test_the_reading_section_is_drawn_from_questions_with_a_passage(self):
        pool = section_pools()[Section.LESEN]
        self.assertEqual(len(pool), ITEMS_PER_SECTION)
        for question in pool:
            self.assertEqual(question.targets.first().sentence, self.sentence)

    def test_the_writing_section_is_drawn_from_questions_answered_by_typing(self):
        pool = section_pools()[Section.SCHREIBEN]
        self.assertEqual(len(pool), ITEMS_PER_SECTION)
        for question in pool:
            self.assertEqual(question.answers.count(), 1)

    def test_a_question_that_fits_two_skills_belongs_to_exactly_one_section(self):
        # A dictation: a recording *and* a single typed answer, so both the HÖREN shape and
        # the SCHREIBEN shape fit it. It must land in one section alone, or a paper can draw
        # the same question twice and break `unique_question_per_exam_run` — the 500 this
        # test pins. One column holds one value, so the answer is structural now, and the
        # test still checks it end to end.
        question = Question.objects.create(
            exercise=self.exercise, prompt="بشنو و بنویس", order=900,
            audio="questions/audio/dictation.mp3", exam_section=Section.HOEREN,
        )
        Answer.objects.create(question=question, text="Haus", is_correct=True, order=1)

        self.assertIn(question, section_pools()[Section.HOEREN])
        self.assertNotIn(question, section_pools()[Section.SCHREIBEN])
        self.assertNotIn(question, section_pools()[Section.LESEN])

    def test_the_three_section_pools_never_share_a_question(self):
        seen = {}
        for section in SECTION_ORDER:
            for question in section_pools()[section]:
                self.assertNotIn(question.pk, seen)
                seen[question.pk] = section

    def test_a_paper_over_crossing_questions_asks_each_question_once(self):
        # The real content has over a thousand dictation questions that fit HÖREN and
        # SCHREIBEN at once. With disjoint pools a paper is always buildable and never
        # repeats a question.
        for index in range(ITEMS_PER_SECTION):
            question = Question.objects.create(
                exercise=self.exercise, prompt="دیکته %d" % index, order=1000 + index,
                audio="questions/audio/dictation.mp3", exam_section=Section.HOEREN,
            )
            Answer.objects.create(question=question, text="Haus", is_correct=True, order=1)

        run = self.start_run()
        questions = [row.question_id for row in run.questions.all()]
        self.assertEqual(len(questions), 3 * ITEMS_PER_SECTION)
        self.assertEqual(len(questions), len(set(questions)))

    def test_an_unmarked_question_can_never_enter_a_paper(self):
        """The audit's P-20: adding content must not change the exam by itself.

        This question is exactly what a HÖREN item looks like — a recording, one right
        answer, published — and it is still never asked, because nobody marked it. Before
        the set was curated this question *would* have been drawn, which is how a reading
        generator ended up supplying a third of LESEN.
        """
        for section in SECTION_ORDER:
            self.assertNotIn(self.unmarked, section_pools()[section])

        run = self.start_run()
        asked = []
        for row in run.questions.all():
            asked.append(row.question_id)
        self.assertNotIn(self.unmarked.pk, asked)

    def test_a_draft_exercise_contributes_nothing(self):
        for section in SECTION_ORDER:
            pool = section_pools()[section]
            self.assertNotIn(self.draft_question, pool)

    def test_a_question_with_no_correct_answer_is_never_asked(self):
        self.assertFalse(markable(self.unanswerable))
        for section in SECTION_ORDER:
            self.assertNotIn(self.unanswerable, section_pools()[section])

    def test_a_scramble_is_never_drawn_into_a_section(self):
        """By its answer count it looks typed, so it is excluded by its type: a scramble
        without its word bank on screen is just a translation."""
        self.assertTrue(is_typed(self.scramble_question))
        for section in SECTION_ORDER:
            self.assertNotIn(self.scramble_question, section_pools()[section])

    def test_a_paper_is_forty_five_questions_fifteen_per_section(self):
        run = self.start_run()
        rows = list(run.questions.order_by("order"))

        self.assertEqual(len(rows), 3 * ITEMS_PER_SECTION)

        orders = []
        counts = {}
        for row in rows:
            orders.append(row.order)
            if row.section not in counts:
                counts[row.section] = 0
            counts[row.section] += 1

        self.assertEqual(orders, list(range(1, 3 * ITEMS_PER_SECTION + 1)))
        for section in SECTION_ORDER:
            self.assertEqual(counts[section], ITEMS_PER_SECTION)

    def test_every_question_of_a_paper_comes_from_its_own_section_pool(self):
        run = self.start_run()
        for row in run.questions.all():
            self.assertIn(row.question, section_pools()[row.section])

    def test_a_paper_asks_a_question_once(self):
        run = self.start_run()
        questions = []
        for row in run.questions.all():
            questions.append(row.question_id)
        self.assertEqual(len(questions), len(set(questions)))

    def test_two_sittings_are_two_whole_papers(self):
        first = self.start_run()
        second = self.start_run()
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(first.questions.count(), second.questions.count())

    def test_a_thin_section_stops_the_paper_from_being_built(self):
        self.assertEqual(paper_problems(), [])
        Question.objects.filter(pk__in=[q.pk for q in self.audio_questions[:3]]).delete()

        problems = paper_problems()
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["section"], Section.HOEREN)
        self.assertEqual(problems[0]["available"], ITEMS_PER_SECTION - 3)


class ExamScoringTests(ExamFixture):
    """The official arithmetic, including the rule that decides whether it is still passable."""

    def test_a_perfect_paper_is_seventy_five_points(self):
        run = self.start_run()
        self.answer_all(run)
        result = score(run)

        self.assertEqual(result["raw_total"], 45)
        self.assertEqual(result["raw_max"], 45)
        self.assertEqual(result["points"], WRITTEN_MAX_POINTS)
        self.assertEqual(result["max_points"], WRITTEN_MAX_POINTS)
        self.assertEqual(result["needed_from_spoken"], 0)
        self.assertTrue(result["spoken_can_reach"])
        self.assertTrue(result["written_above_minimum"])

    def test_an_empty_paper_is_zero_and_cannot_reach_the_pass_mark(self):
        run = self.start_run()
        self.answer_run(run, 0, answered=False)
        result = score(run)

        self.assertEqual(result["points"], 0)
        self.assertEqual(result["answered_total"], 0)
        self.assertEqual(result["needed_from_spoken"], PASS_POINTS)
        self.assertFalse(result["spoken_can_reach"])
        self.assertFalse(result["written_above_minimum"])

    def test_each_section_is_scored_after_the_official_factor(self):
        run = self.start_run()
        self.answer_all(run)
        result = score(run)

        for section in result["sections"]:
            self.assertEqual(section["correct"], ITEMS_PER_SECTION)
            self.assertEqual(section["points"], 25)

    def test_a_section_fewer_than_fifteen_right_is_worth_less_than_twenty_five(self):
        run = self.start_run()
        self.answer_run(run, 12)
        result = score(run)

        self.assertEqual(result["raw_total"], 12)
        self.assertEqual(result["points"], round(12 * SCORE_FACTOR))

    def test_thirty_five_written_points_still_leave_the_oral_part_a_chance(self):
        # 21 right answers is the first score that scales to the exam's 35-point minimum.
        run = self.start_run()
        self.answer_run(run, 21)
        result = score(run)

        self.assertEqual(result["points"], 35)
        self.assertTrue(result["written_above_minimum"])
        self.assertEqual(result["needed_from_spoken"], PASS_POINTS - 35)
        self.assertTrue(result["spoken_can_reach"])

    def test_below_the_minimum_the_oral_part_cannot_save_the_exam(self):
        run = self.start_run()
        self.answer_run(run, 20)
        result = score(run)

        self.assertEqual(result["points"], 33)
        self.assertFalse(result["written_above_minimum"])
        self.assertFalse(result["spoken_can_reach"])
        self.assertEqual(result["needed_from_spoken"], PASS_POINTS - 33)

    def test_unanswered_questions_count_for_nothing_but_are_still_asked(self):
        run = self.start_run()
        self.answer_run(run, 5, answered=False)
        result = score(run)

        self.assertEqual(result["asked_total"], 45)
        self.assertEqual(result["answered_total"], 5)
        self.assertEqual(result["points"], round(5 * SCORE_FACTOR))

    def test_the_clock_is_the_runs_own_started_at(self):
        run = self.start_run()
        self.assertEqual(remaining_minutes(run), 65)
        self.assertFalse(time_is_up(run))

        ExamRun.objects.filter(pk=run.pk).update(
            started_at=timezone.now() - timedelta(minutes=64)
        )
        run.refresh_from_db()
        self.assertEqual(remaining_minutes(run), 1)
        self.assertFalse(time_is_up(run))

        ExamRun.objects.filter(pk=run.pk).update(
            started_at=timezone.now() - timedelta(minutes=66)
        )
        run.refresh_from_db()
        self.assertEqual(remaining_minutes(run), 0)
        self.assertTrue(time_is_up(run))


class ExamIndexTests(ExamFixture):
    """The index: public shape, personal sittings, and the instruction words."""

    def setUp(self):
        self.url = reverse("exams:exam-index")

    def test_the_official_shape_is_public(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HÖREN")
        self.assertContains(response, "LESEN")
        self.assertContains(response, "SCHREIBEN")
        self.assertContains(response, "SPRECHEN")
        self.assertContains(response, "Durchführungsbestimmungen")

    def test_the_numbers_the_page_shows_are_the_official_ones(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["written_max_points"], WRITTEN_MAX_POINTS)
        self.assertEqual(response.context["pass_points"], PASS_POINTS)
        self.assertEqual(response.context["max_points"], MAX_POINTS)
        self.assertEqual(response.context["score_factor"], SCORE_FACTOR)
        self.assertEqual(response.context["written_minimum"], WRITTEN_MINIMUM)
        self.assertContains(response, "قبولی: <b>60</b> امتیاز از 100")

    def test_a_visitor_is_told_what_an_account_is_for(self):
        response = self.client.get(self.url)
        self.assertContains(response, "ساخت حساب")
        self.assertNotContains(response, "آزمون‌های تو")

    def test_a_learner_sees_their_own_past_sittings(self):
        run = self.start_run()
        self.answer_run(run, 30)
        run.finished_at = timezone.now()
        run.save(update_fields=["finished_at"])

        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "آزمون‌های تو")
        self.assertEqual(len(response.context["finished"]), 1)
        self.assertEqual(response.context["finished"][0]["score"]["points"], 50)

    def test_another_learners_sittings_are_not_listed(self):
        run = self.start_run(self.other)
        self.answer_run(run, 30)
        run.finished_at = timezone.now()
        run.save(update_fields=["finished_at"])

        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.context["finished"], [])

    def test_the_instruction_words_say_which_ones_the_course_teaches(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        rows = response.context["instructions"]

        taught = []
        gaps = []
        for row in rows:
            if row["taught"] is None:
                gaps.append(row["german"])
            else:
                taught.append(row["german"])

        # The fixture teaches `Lösung` and nothing else on the list, so the glossary's two
        # states are both real rather than decorative.
        self.assertIn("die Lösung", taught)
        self.assertIn("ergänzen", gaps)


class ExamStartTests(ExamFixture):
    """Starting a sitting: needs an account, never stacks, and refuses a thin content pool."""

    def setUp(self):
        self.url = reverse("exams:exam-start")

    def test_a_visitor_is_sent_to_the_login_page(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
        self.assertEqual(ExamRun.objects.count(), 0)

    def test_starting_builds_a_paper_and_opens_it(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)

        run = ExamRun.objects.get(user=self.user)
        self.assertRedirects(response, reverse("exams:exam-run", args=[run.pk]))
        self.assertEqual(run.questions.count(), 45)

    def test_an_open_sitting_is_resumed_instead_of_stacked(self):
        self.client.force_login(self.user)
        self.client.post(self.url)
        self.client.post(self.url)

        self.assertEqual(ExamRun.objects.filter(user=self.user).count(), 1)

    def test_a_thin_content_pool_refuses_to_start(self):
        Question.objects.filter(pk__in=[q.pk for q in self.audio_questions[:3]]).delete()
        self.client.force_login(self.user)
        response = self.client.post(self.url)

        self.assertRedirects(response, reverse("exams:exam-index"))
        self.assertEqual(ExamRun.objects.count(), 0)


class ExamRunPageTests(ExamFixture):
    """The sitting itself: whose it is, what it renders, and what a closed one shows."""

    def test_the_run_belongs_to_one_learner(self):
        run = self.start_run()
        self.client.force_login(self.other)
        response = self.client.get(reverse("exams:exam-run", args=[run.pk]))
        self.assertEqual(response.status_code, 404)

    def test_a_visitor_is_sent_to_the_login_page(self):
        run = self.start_run()
        response = self.client.get(reverse("exams:exam-run", args=[run.pk]))
        self.assertEqual(response.status_code, 302)

    def test_an_open_sitting_renders_the_whole_paper_without_the_answers(self):
        run = self.start_run()
        self.client.force_login(self.user)
        response = self.client.get(reverse("exams:exam-run", args=[run.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-runner')
        self.assertContains(response, 'data-kind="choice"')
        self.assertContains(response, 'data-kind="text"')
        self.assertContains(response, reverse("exams:exam-submit", args=[run.pk]))
        # The runner's rule: the page may show options, never which one is right.
        self.assertNotContains(response, "data-correct")
        self.assertNotContains(response, "is-correct")
        self.assertEqual(response.context["total_questions"], 45)

    def test_the_page_carries_the_sections_and_the_deadline(self):
        run = self.start_run()
        self.client.force_login(self.user)
        response = self.client.get(reverse("exams:exam-run", args=[run.pk]))

        self.assertEqual(response.context["minutes_left"], 65)
        self.assertFalse(response.context["expired"])
        self.assertContains(response, "HÖREN")
        self.assertContains(response, "SCHREIBEN")

    def test_a_paper_past_its_deadline_shows_no_runner(self):
        run = self.start_run()
        ExamRun.objects.filter(pk=run.pk).update(
            started_at=timezone.now() - timedelta(minutes=70)
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("exams:exam-run", args=[run.pk]))

        self.assertTrue(response.context["expired"])
        self.assertContains(response, "زمان تمام شد")
        self.assertNotContains(response, 'data-runner')

    def test_a_closed_sitting_shows_the_score_and_what_was_missed(self):
        run = self.start_run()
        self.answer_run(run, 21)
        run.finished_at = timezone.now()
        run.save(update_fields=["finished_at"])

        self.client.force_login(self.user)
        response = self.client.get(reverse("exams:exam-run", args=[run.pk]))

        self.assertContains(response, "نتیجهٔ این آزمون")
        self.assertContains(response, "پرسش‌هایی که نادرست بود")
        self.assertEqual(response.context["result"]["points"], 35)
        self.assertEqual(len(response.context["missed"]), 24)
        self.assertNotContains(response, "data-correct")

    def test_the_score_of_a_closed_sitting_does_not_move_when_practice_changes(self):
        # The snapshot is the point: the exam mode writes ExerciseAttempt rows like any
        # other practice, and a later answer to the same question must not rewrite the run.
        run = self.start_run()
        self.answer_run(run, 21)
        run.finished_at = timezone.now()
        run.save(update_fields=["finished_at"])
        before = score(run)

        row = run.questions.order_by("order").first()
        row.is_correct = False
        row.save(update_fields=["is_correct"])

        self.assertEqual(score(run)["points"], before["points"] - 2)


class ExamSubmitTests(ExamFixture):
    """One answer inside a sitting: graded, recorded on the paper and in the learner's history."""

    def setUp(self):
        self.run = self.start_run()
        self.client.force_login(self.user)
        self.url = reverse("exams:exam-submit", args=[self.run.pk])

    def post_answer(self, question, answer=None, response_text=""):
        return self.client.post(
            self.url,
            data=json.dumps({
                "question": question.pk,
                "answer": answer,
                "response_text": response_text,
            }),
            content_type="application/json",
        )

    def test_a_correct_choice_is_graded_recorded_and_written_on_the_paper(self):
        row = self.run.questions.filter(section=Section.HOEREN).order_by("order").first()
        question = row.question
        correct = question.answers.get(is_correct=True)

        response = self.post_answer(question, answer=correct.pk)
        data = response.json()

        self.assertTrue(data["correct"])
        self.assertTrue(data["recorded"])
        row.refresh_from_db()
        self.assertTrue(row.is_correct)
        self.assertEqual(ExerciseAttempt.objects.filter(user=self.user).count(), 1)

    def test_a_wrong_answer_is_stored_as_wrong(self):
        row = self.run.questions.filter(section=Section.HOEREN).order_by("order").first()
        question = row.question
        wrong = question.answers.get(is_correct=False)

        data = self.post_answer(question, answer=wrong.pk).json()

        self.assertFalse(data["correct"])
        self.assertEqual(data["expected"], ["richtig"])
        row.refresh_from_db()
        self.assertFalse(row.is_correct)

    def test_a_typed_answer_moves_the_words_counters(self):
        row = self.run.questions.filter(section=Section.SCHREIBEN).order_by("order").first()

        response = self.post_answer(row.question, response_text="Haus")
        self.assertTrue(response.json()["correct"])

    def test_an_answer_to_a_question_this_paper_does_not_ask_is_refused(self):
        other = Question.objects.create(exercise=self.exercise, prompt="بیرون از آزمون", order=99)
        Answer.objects.create(question=other, text="Haus", is_correct=True, order=1)

        response = self.post_answer(other, response_text="Haus")
        self.assertEqual(response.status_code, 400)

    def test_answering_after_the_deadline_is_refused(self):
        ExamRun.objects.filter(pk=self.run.pk).update(
            started_at=timezone.now() - timedelta(minutes=70)
        )
        row = self.run.questions.order_by("order").first()

        response = self.post_answer(row.question, answer=row.question.answers.first().pk)
        self.assertEqual(response.status_code, 400)

    def test_answering_a_closed_sitting_is_refused(self):
        self.run.finished_at = timezone.now()
        self.run.save(update_fields=["finished_at"])
        row = self.run.questions.order_by("order").first()

        response = self.post_answer(row.question, answer=row.question.answers.first().pk)
        self.assertEqual(response.status_code, 400)

    def test_another_learners_sitting_cannot_be_answered(self):
        self.client.force_login(self.other)
        row = self.run.questions.order_by("order").first()

        response = self.post_answer(row.question, answer=row.question.answers.first().pk)
        self.assertEqual(response.status_code, 404)


class ExamFinishTests(ExamFixture):
    """Closing a sitting: idempotent, and the only thing that turns a paper into a record."""

    def test_finishing_stamps_the_run_and_hands_back_its_url(self):
        run = self.start_run()
        self.client.force_login(self.user)
        response = self.client.post(reverse("exams:exam-finish", args=[run.pk]))

        self.assertTrue(response.json()["finished"])
        self.assertEqual(response.json()["url"], reverse("exams:exam-run", args=[run.pk]))
        run.refresh_from_db()
        self.assertIsNotNone(run.finished_at)

    def test_finishing_twice_does_not_move_the_timestamp(self):
        run = self.start_run()
        self.client.force_login(self.user)
        self.client.post(reverse("exams:exam-finish", args=[run.pk]))
        run.refresh_from_db()
        first = run.finished_at

        self.client.post(reverse("exams:exam-finish", args=[run.pk]))
        run.refresh_from_db()
        self.assertEqual(run.finished_at, first)

    def test_a_closed_sitting_is_never_found_by_another_learner(self):
        run = self.start_run()
        self.client.force_login(self.other)
        response = self.client.post(reverse("exams:exam-finish", args=[run.pk]))
        self.assertEqual(response.status_code, 404)


class SpokenPracticeTests(ExamFixture):
    """The rehearsal: real sentences, or an honest gap."""

    def test_a_phrase_the_course_teaches_points_at_the_questions_about_it(self):
        parts = spoken_practice(SPRECHEN["parts"])
        first_part = parts[0]

        matched = None
        for phrase in first_part["phrases"]:
            if phrase["de"].startswith("Ich heiße"):
                matched = phrase
                break

        self.assertIsNotNone(matched)
        self.assertEqual(matched["sentence"], self.sentence)
        self.assertEqual(matched["practice"], [self.exercise])

    def test_a_phrase_the_course_does_not_teach_has_no_practice(self):
        parts = spoken_practice(SPRECHEN["parts"])
        last_part = parts[2]

        unmatched = None
        for phrase in last_part["phrases"]:
            if phrase["de"].startswith("Tut mir leid"):
                unmatched = phrase
                break

        self.assertIsNotNone(unmatched)
        self.assertIsNone(unmatched["sentence"])
        self.assertEqual(unmatched["practice"], [])

    def test_a_draft_exercise_is_never_offered_as_practice(self):
        Exercise.objects.filter(pk=self.exercise.pk).update(is_published=False)
        parts = spoken_practice(SPRECHEN["parts"])

        for part in parts:
            for phrase in part["phrases"]:
                self.assertEqual(phrase["practice"], [])


class SprechenPageTests(ExamFixture):
    """The page itself: three parts, the official points, and no invented score."""

    def setUp(self):
        self.url = reverse("exams:sprechen")

    def test_the_rehearsal_is_public(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sich vorstellen")
        self.assertContains(response, "Fragen stellen und darauf reagieren")
        self.assertContains(response, "Bitten formulieren und darauf reagieren")

    def test_every_part_shows_its_minutes_and_points(self):
        response = self.client.get(self.url)
        for part in response.context["parts"]:
            self.assertContains(response, f"{part['points']} امتیاز")

    def test_the_page_says_the_part_is_not_graded(self):
        response = self.client.get(self.url)
        self.assertContains(response, "چرا نمره نمی‌گیرد")
        self.assertContains(response, "بدون تمرین در دوره")
        self.assertContains(response, "تمرین همین جمله")

    def test_the_rehearsal_needs_no_account(self):
        response = self.client.get(self.url)
        self.assertContains(response, "بخش گفتن")

    def test_the_pass_arithmetic_is_linked_from_here(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse("exams:exam-index"))


class ExamOpenRunTests(ExamFixture):
    """``exams.paper.open_run``: how a half-finished exam is found again."""

    def test_a_fresh_learner_has_no_open_sitting(self):
        self.assertIsNone(open_run(self.user))

    def test_an_unfinished_sitting_is_found(self):
        run = self.start_run()
        self.assertEqual(open_run(self.user), run)

    def test_a_finished_sitting_is_not_open(self):
        run = self.start_run()
        run.finished_at = timezone.now()
        run.save(update_fields=["finished_at"])
        self.assertIsNone(open_run(self.user))

    def test_another_learners_sitting_is_not_mine(self):
        self.start_run(self.other)
        self.assertIsNone(open_run(self.user))


class SprechenRecorderTests(ExamFixture):
    """Concept 24 («بلند بگو»): the record-and-listen control on the speaking page.

    The control is deliberately optional, so the tests check that it is *present and
    optional* — the page still reads completely without it, and nothing here promises a
    score for speaking.
    """

    def setUp(self):
        self.url = reverse("exams:sprechen")

    def test_every_phrase_gets_a_record_control(self):
        """One button per phrase — the control is offered wherever a phrase is."""
        response = self.client.get(self.url)

        expected = 0
        for part in response.context["parts"]:
            expected += len(part["phrases"])

        self.assertEqual(response.content.decode().count("js-record"), expected)

    def test_the_recorder_script_is_loaded(self):
        response = self.client.get(self.url)
        self.assertContains(response, "sprechen_recorder.js")

    def test_the_page_still_says_speaking_is_not_graded(self):
        response = self.client.get(self.url)
        self.assertContains(response, "چرا نمره نمی‌گیرد")
        self.assertContains(response, "بخش گفتن، بدون نمرهٔ الکی")


class StepTestTests(ExamFixture):
    """Concept 20 («آزمون گام»): the short station, and what it refuses to claim.

    The selection is checked against ``paper.section_of`` — the one rule that says which
    skill a question stands in for — so a step test and a full exam can never disagree
    about it, and the page is checked for the two honest properties: no answer on it, and
    no official score claimed.
    """

    def setUp(self):
        self.url = reverse("exams:step-test")

    def test_the_step_test_needs_an_account(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_the_selection_is_four_questions_per_written_skill(self):
        questions = step_questions(self.user, timezone.localdate())

        self.assertEqual(len(questions), STEP_SIZE)

        counts = {}
        for question in questions:
            section = section_of(question)
            if section not in counts:
                counts[section] = 0
            counts[section] += 1

        for section in SECTION_ORDER:
            self.assertEqual(counts[section], PER_SECTION)

    def test_a_question_answered_today_is_left_out(self):
        question = step_questions(self.user, timezone.localdate())[0]
        ExerciseAttempt.objects.create(
            user=self.user, exercise=question.exercise, question=question, is_correct=True
        )

        again = step_questions(self.user, timezone.localdate())
        ids = []
        for row in again:
            ids.append(row.pk)

        self.assertNotIn(question.pk, ids)

    def test_nothing_left_today_selects_nothing(self):
        for question in Question.objects.all():
            ExerciseAttempt.objects.create(
                user=self.user, exercise=question.exercise, question=question, is_correct=True
            )

        self.assertIsNone(step_questions(self.user, timezone.localdate()))

    def test_the_page_runs_through_the_ordinary_runner(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "exams/step_test.html")
        self.assertContains(response, 'data-runner')
        self.assertContains(response, "exercises/js/exercise_runner.js")
        self.assertContains(response, "exercises/css/exercise.css")
        self.assertContains(
            response, reverse("exercises:exercise-submit", args=[self.exercise.pk])
        )
        self.assertEqual(response.context["total_questions"], STEP_SIZE)

    def test_a_test_does_not_offer_a_second_try(self):
        """A second try would inflate the score, and every question here stands in for one
        in the real exam, so the runner is never told to offer one."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertNotContains(response, "data-second-try")

    def test_no_answer_is_on_the_page(self):
        self.client.force_login(self.user)
        html = self.client.get(self.url).content.decode()
        self.assertNotIn("data-correct", html)

    def test_the_page_claims_no_official_score(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertContains(response, "نمرهٔ رسمی ندارد")
        self.assertContains(response, reverse("exams:exam-index"))

    def test_an_empty_step_test_is_a_page_not_an_error(self):
        for question in Question.objects.all():
            ExerciseAttempt.objects.create(
                user=self.user, exercise=question.exercise, question=question, is_correct=True
            )

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "پرسشی نمانده")
        self.assertNotContains(response, "data-runner")


class SpeakingNodeTests(ExamFixture):
    """Concept 24's node: the model recording, the self-report, and no invented score.

    The self-report is the part that makes the page a bounded node instead of a reference
    list, and it must work with no microphone at all — so it is checked for being present
    *and* independent of the recorder, not just for existing.
    """

    def setUp(self):
        self.url = reverse("exams:sprechen")

    def phrases_of(self, response):
        rows = []
        for part in response.context["parts"]:
            for phrase in part["phrases"]:
                rows.append(phrase)
        return rows

    def test_every_phrase_can_be_marked_said_without_a_microphone(self):
        response = self.client.get(self.url)
        html = response.content.decode()
        expected = len(self.phrases_of(response))

        self.assertEqual(html.count("js-said"), expected)
        self.assertEqual(html.count("js-not-said"), expected)

    def test_the_page_shows_how_far_the_learner_got(self):
        response = self.client.get(self.url)

        self.assertContains(response, "data-said-count")
        self.assertContains(response, "data-said-progress")
        self.assertEqual(response.context["phrase_total"], len(self.phrases_of(response)))

    def test_a_phrase_with_a_course_sentence_gets_the_model_audio(self):
        """«Ich heiße …» matches the fixture's sentence, so its recording is offered."""
        self.sentence.audio = "sentences/audio/model.mp3"
        self.sentence.save(update_fields=["audio"])

        response = self.client.get(self.url)
        self.assertContains(response, "sentences/audio/model.mp3")

    def test_a_phrase_without_a_course_sentence_offers_no_model_audio(self):
        """No sentence means no clip rather than an unrelated one."""
        response = self.client.get(self.url)
        self.assertEqual(response.content.decode().count("sentences/audio"), 0)


class ExamCurationTests(TestCase):
    """The curated exam content set: what may be marked, and what the file means.

    The fixture builds one exercise per curation family, using the same title prefixes the
    generators write (``exercises/generated.py``), so the export command's rules are
    exercised the way the live content exercises them: 15 listening items, 15 reading
    items, 15 written items, and two families that must never be marked.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="دورهٔ آلمانی A1", is_published=True
        )
        # Three lessons, because the round-robin spreads the set across the lessons and one
        # lesson could not show that.
        cls.lessons = []
        for number in range(1, 4):
            cls.lessons.append(
                Lesson.objects.create(
                    course=cls.course, title=f"Lektion {number}", order=number,
                    estimated_time=60, is_published=True,
                )
            )
        cls.sentence = Sentence.objects.create(
            text="Ich heiße Ali.", translation_fa="اسمم علی است.", level=cls.level,
            is_published=True,
        )

        # Enough of each family for a full marked set: the command marks
        # MARKED_PER_SECTION per section, three sittings' worth.
        per_family = MARKED_PER_SECTION
        per_lesson = per_family // len(cls.lessons)

        cls.listening = []
        cls.reading = []
        cls.writing = []

        for lesson in cls.lessons:
            listening = Exercise.objects.create(
                lesson=lesson, title=LISTENING_DRILL_PREFIX, type="LISTENING", order=1,
                is_published=True,
            )
            reading = Exercise.objects.create(
                lesson=lesson, title=f"{READING_DRILL_PREFIX} — متن کوتاه", type="READING",
                order=2, is_published=True,
            )
            writing = Exercise.objects.create(
                lesson=lesson, title="تمرین نوشتن — واژه (1)", type="TRANSLATION", order=3,
                is_published=True,
            )
            cls.listening.append(listening)
            cls.reading.append(reading)
            cls.writing.append(writing)

            for index in range(per_lesson):
                question = Question.objects.create(
                    exercise=listening, prompt=f"بشنو {index}", order=index + 1,
                    audio="sentences/audio/sentence-1-abcd.mp3",
                )
                Answer.objects.create(question=question, text="درست", is_correct=True, order=1)
                Answer.objects.create(question=question, text="نادرست", is_correct=False, order=2)

                question = Question.objects.create(
                    exercise=reading, prompt=f"بخوان {index}", order=index + 1
                )
                Answer.objects.create(question=question, text="درست", is_correct=True, order=1)
                Answer.objects.create(question=question, text="نادرست", is_correct=False, order=2)
                QuestionTarget.objects.create(
                    question=question, sentence=cls.sentence, role="CONTEXT"
                )

                question = Question.objects.create(
                    exercise=writing, prompt=f"بنویس {index}", order=index + 1
                )
                Answer.objects.create(question=question, text="Haus", is_correct=True, order=1)

        # A scramble fits the writing shape by its answer count and must still be refused:
        # on the exam page there is no word bank to arrange.
        cls.scramble = Exercise.objects.create(
            lesson=cls.lessons[0], title="تمرین جمله — مرتب کردن", type="SCRAMBLE", order=4,
            is_published=True,
        )
        scramble_question = Question.objects.create(
            exercise=cls.scramble, prompt="مرتب کن", order=1
        )
        Answer.objects.create(
            question=scramble_question, text="Ich heiße Ali.", is_correct=True, order=1
        )

        # A dictation: a recording *and* one typed answer, so it belongs to HÖREN by shape.
        # It must not be marked twice, and its audio must keep it out of SCHREIBEN.
        cls.dictation = Exercise.objects.create(
            lesson=cls.lessons[0], title=f"{DICTATION_DRILL_PREFIX} — شنیدن و نوشتن (1)",
            type="LISTENING", order=5, is_published=True,
        )
        for index in range(ITEMS_PER_SECTION):
            question = Question.objects.create(
                exercise=cls.dictation, prompt=f"دیکته {index}", order=index + 1,
                audio="words/audio/haus-abcd.mp3",
            )
            Answer.objects.create(question=question, text="Haus", is_correct=True, order=1)

    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.path = Path(self.directory) / "a1_exam_items.json"

    def export(self):
        call_command(
            "export_a1_exam_items", "--output", str(self.path),
            stdout=io.StringIO(), stderr=io.StringIO(),
        )

    def import_items(self, *extra):
        call_command(
            "import_a1_exam_items", "--data", str(self.path), *extra,
            stdout=io.StringIO(),
        )

    def marked(self):
        return Question.objects.exclude(exam_section="")

    def test_export_marks_three_sittings_worth_per_section(self):
        self.export()
        self.import_items()

        for section in SECTION_ORDER:
            self.assertEqual(
                self.marked().filter(exam_section=section).count(), MARKED_PER_SECTION
            )
        # More than one paper, or every sitting would ask the same 45 questions.
        self.assertGreater(MARKED_PER_SECTION, ITEMS_PER_SECTION)

    def test_two_sittings_of_the_same_set_are_not_the_same_paper(self):
        """A mock exam a learner can only take once is not a mock."""
        self.export()
        self.import_items()

        first = ExamRun.objects.create(user=User.objects.create_user(username="erste", password="a-strong-password"))
        second = ExamRun.objects.create(user=User.objects.create_user(username="zweite", password="a-strong-password"))
        build_paper(first)
        build_paper(second)

        asked_first = set(first.questions.values_list("question_id", flat=True))
        asked_second = set(second.questions.values_list("question_id", flat=True))

        self.assertEqual(len(asked_first), 3 * ITEMS_PER_SECTION)
        self.assertNotEqual(asked_first, asked_second)

    def test_the_set_spreads_across_the_lessons(self):
        """Round-robin, so a paper is the course and not the first three lessons."""
        self.export()
        self.import_items()

        used = set()
        for question in self.marked():
            used.add(question.exercise.lesson_id)

        self.assertEqual(used, {lesson.pk for lesson in self.lessons})

    def test_the_exported_file_is_a_plain_reviewable_payload(self):
        self.export()

        with self.path.open(encoding="utf-8") as handle:
            payload = json.load(handle)

        self.assertEqual(payload["level"], "A1")
        self.assertEqual(payload["items_per_section"], MARKED_PER_SECTION)
        self.assertEqual(sorted(payload["sections"]), sorted(SECTION_ORDER))

        for section in SECTION_ORDER:
            entries = payload["sections"][section]
            self.assertEqual(len(entries), MARKED_PER_SECTION)
            for entry in entries:
                self.assertEqual(
                    sorted(entry), ["exercise_order", "lesson_order", "question_order"]
                )

    def test_every_marked_question_stands_in_for_its_own_section(self):
        """``section_of`` is the practice-side rule and the marks are the exam-side one.

        They must agree, or a paper would ask a question that on the page stands in for a
        different skill — the reading question with a recording, the writing question with
        options. This is the check that keeps the two rules from drifting apart.
        """
        self.export()
        self.import_items()

        for question in self.marked():
            self.assertEqual(section_of(question), question.exam_section)

    def test_a_question_with_no_authored_answer_is_never_marked(self):
        question = Question.objects.create(
            exercise=self.writing[0], prompt="بی‌پاسخ", order=99
        )
        Answer.objects.create(question=question, text="falsch", is_correct=False, order=1)

        self.export()
        self.import_items()

        self.assertEqual(question.exam_section, "")

    def test_a_scramble_and_a_dictation_are_never_marked_writing(self):
        self.export()
        self.import_items()

        self.assertEqual(Question.objects.get(exercise=self.scramble).exam_section, "")
        for question in Question.objects.filter(exercise=self.dictation):
            self.assertNotEqual(question.exam_section, Section.SCHREIBEN)

    def test_importing_twice_changes_nothing(self):
        self.export()
        self.import_items()
        first = sorted(self.marked().values_list("pk", "exam_section"))

        self.import_items()
        second = sorted(self.marked().values_list("pk", "exam_section"))

        self.assertEqual(first, second)

    def test_a_mark_that_is_not_in_the_file_is_cleared(self):
        """The set is the file, so dropping a line from the file drops the item."""
        self.export()
        self.import_items()
        stray = self.writing[0].questions.create(
            prompt="سرگردان", order=98, exam_section=Section.SCHREIBEN
        )
        Answer.objects.create(question=stray, text="Haus", is_correct=True, order=1)

        self.import_items()

        stray.refresh_from_db()
        self.assertEqual(stray.exam_section, "")

    def test_check_reports_and_writes_nothing(self):
        self.export()
        self.import_items()

        out = io.StringIO()
        call_command("import_a1_exam_items", "--data", str(self.path), "--check", stdout=out)

        self.assertIn("Check only", out.getvalue())
        self.assertEqual(self.marked().count(), 3 * MARKED_PER_SECTION)

    def test_an_entry_that_does_not_resolve_is_an_error(self):
        self.export()

        with self.path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        payload["sections"][Section.HOEREN][0]["question_order"] = 9999
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        with self.assertRaises(CommandError):
            self.import_items()

    def test_an_unknown_section_in_the_file_is_an_error(self):
        self.export()

        with self.path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        payload["sections"]["SPRECHEN"] = payload["sections"][Section.HOEREN]
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        with self.assertRaises(CommandError):
            self.import_items()
