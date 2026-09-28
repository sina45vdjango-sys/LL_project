"""
Tests for exercise generation and integrity.
Verifies that exercises, questions, answers and targets are wired correctly.
"""
import json
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from exercises.grading import grade
from exercises.history import exercise_history
from exercises.models import Exercise, ExerciseAttempt, Question, QuestionTarget, Answer
from exercises.runner import build_runner
from lessons.models import Course, LanguageLevel, Lesson, LessonSentence
from vocabulary.models import Sentence, Word, WordProgress


class ExerciseIntegrityTest(TestCase):
    """Data integrity checks after auto-generation."""

    def setUp(self):
        # Use real DB data; skip if no exercises exist
        pass

    def test_exercises_belong_to_lessons(self):
        """Every exercise must have a non-null lesson FK."""
        for ex in Exercise.objects.all():
            self.assertIsNotNone(ex.lesson, f"Exercise '{ex.title}' has no lesson")

    def test_exercises_have_questions(self):
        """Every exercise must have at least one question."""
        for ex in Exercise.objects.all():
            self.assertGreaterEqual(
                Question.objects.filter(exercise=ex).count(), 1,
                f"Exercise '{ex.title}' (lesson {ex.lesson}) has no questions"
            )

    def test_questions_have_exactly_one_correct_answer(self):
        """Every MULTIPLE_CHOICE / TRUE_FALSE question must have exactly one correct answer."""
        multi_choice_types = {"MULTIPLE_CHOICE", "TRUE_FALSE"}
        for q in Question.objects.filter(exercise__type__in=multi_choice_types):
            correct = Answer.objects.filter(question=q, is_correct=True)
            self.assertEqual(
                correct.count(), 1,
                f"Question {q.pk} ({q.prompt[:40]}...) should have exactly 1 correct answer, found {correct.count()}"
            )

    def test_questions_have_at_least_two_answers(self):
        """Multiple-choice-style questions must have at least 2 answers."""
        multi_choice_types = {"MULTIPLE_CHOICE", "TRUE_FALSE"}
        for q in Question.objects.filter(exercise__type__in=multi_choice_types):
            self.assertGreaterEqual(
                Answer.objects.filter(question=q).count(), 2,
                f"Question {q.pk} needs at least 2 answers"
            )

    def test_answers_order_is_unique_per_question(self):
        """Answer orders within a question should be unique (1, 2, 3, ...)."""
        for q in Question.objects.all():
            orders = list(Answer.objects.filter(question=q).values_list("order", flat=True))
            self.assertEqual(
                len(orders), len(set(orders)),
                f"Question {q.pk} has duplicate answer orders: {orders}"
            )

    def test_question_targets_reference_existing_data(self):
        """QuestionTarget references must point to real words/sentences/grammars."""
        for t in QuestionTarget.objects.all():
            if t.word:
                self.assertTrue(t.word.is_published, f"Target word {t.word} should be published")
            if t.sentence:
                self.assertTrue(t.sentence.is_published, f"Target sentence should be published")
            if t.grammar:
                self.assertTrue(t.grammar.is_published, f"Target grammar {t.grammar} should be published")

    def test_question_targets_mutually_exclusive(self):
        """QuestionTarget: exactly one of word/grammar/sentence must be set."""
        for t in QuestionTarget.objects.all():
            count = sum([bool(t.word), bool(t.grammar), bool(t.sentence)])
            self.assertEqual(count, 1, f"QuestionTarget {t.pk} must reference exactly one target")

    def test_exercise_order_unique_per_lesson(self):
        """Each lesson's exercises must have unique orders."""
        for lesson in Lesson.objects.all():
            orders = list(
                Exercise.objects.filter(lesson=lesson).values_list("order", flat=True)
            )
            self.assertEqual(
                len(orders), len(set(orders)),
                f"Lesson {lesson.pk} has duplicate exercise orders: {orders}"
            )

    def test_lookup_url_resolves(self):
        """The vocabulary:word-lookup URL must resolve and return JSON."""
        response = self.client.get(reverse("vocabulary:word-lookup"), {"q": "hallo"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)


class LessonExerciseDisplayTest(TestCase):
    """Verify exercises appear on the lesson detail page.

    Phase 5 turned the lesson into a journey, and the exercises moved from the old
    reader panel into its practice step — the assertions below follow that markup.
    """

    def test_lesson_detail_page_offers_its_exercises(self):
        lesson = Lesson.objects.first()
        if not lesson:
            self.skipTest("No lessons in database")
        exercises = list(Exercise.objects.filter(lesson=lesson, is_published=True))
        response = self.client.get(reverse("lessons:lesson-detail", kwargs={"pk": lesson.pk}))
        self.assertEqual(response.status_code, 200)
        if not exercises:
            # A lesson with no exercises must not grow an empty practice step.
            self.assertNotContains(response, 'data-journey-step="practice"')
            return
        self.assertContains(response, 'data-journey-step="practice"')
        for exercise in exercises:
            self.assertContains(response, reverse("exercises:exercise-detail", args=[exercise.pk]))


class ExercisePageTestBase(TestCase):
    """Shared fixture: one published exercise per real type, plus the awkward cases.

    Exercises are DB-only (no seed command), so a test run starts with none of them.
    Rather than assert vacuous truths against an empty queryset, these tests build the
    rows they need. The types and answer shapes mirror the live database: 4 options for
    MULTIPLE_CHOICE, 2 for TRUE_FALSE and READING, 1–3 for FILL_BLANK (one of those is a
    plain typed answer), and exactly 1 for TRANSLATION.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", is_published=True, order=1, estimated_time=10
        )
        cls.lesson_two = Lesson.objects.create(
            course=cls.course, title="Lektion 2", is_published=True, order=2, estimated_time=10
        )
        cls.lesson_without_exercises = Lesson.objects.create(
            course=cls.course, title="Lektion 3", is_published=True, order=3, estimated_time=10
        )
        cls.sentence = Sentence.objects.create(
            text="Guten Morgen!", translation_fa="صبح بخیر!", level=cls.level, is_published=True
        )

        cls.multiple_choice = cls._exercise(
            cls.lesson, "واژگان — انتخاب معنی", Exercise.ExerciseType.MULTIPLE_CHOICE, 1
        )
        cls._choice_question(cls.multiple_choice, 1, "واژهٔ «hallo» به چه معنی است؟", [
            ("سلام", True), ("خوش آمدید", False), ("صفر", False), ("زیرا", False),
        ])
        cls._choice_question(cls.multiple_choice, 2, "واژهٔ «Tschüss» به چه معنی است؟", [
            ("خداحافظ", True), ("سلام", False), ("danke", False), ("bitte", False),
        ])

        # order 12, not 2: the live data numbers questions across the whole lesson, so a
        # 1-question exercise really can start at 12. The page must show position 1.
        cls.true_false = cls._exercise(
            cls.lesson, "درست / غلط", Exercise.ExerciseType.TRUE_FALSE, 2
        )
        cls._choice_question(
            cls.true_false, 12, "واژهٔ «hallo» به فارسی معادل سلام است.",
            [("درست", True), ("غلط", False)],
        )

        cls.fill_blank_choice = cls._exercise(
            cls.lesson, "تمرین تکمیل جمله", Exercise.ExerciseType.FILL_BLANK, 3
        )
        cls._choice_question(
            cls.fill_blank_choice, 20, 'جایگزین _____ در جمله زیر شود:\n"Wo _____ Sie?"',
            [("wohnen", True), ("lernen", False), ("Land", False)],
        )

        cls.fill_blank_text = cls._exercise(
            cls.lesson, "تمرین تکمیل جمله", Exercise.ExerciseType.FILL_BLANK, 4
        )
        cls._text_question(
            cls.fill_blank_text, 21, 'جایگزین _____ در جمله زیر شود:\n"Ich bin _____ßig."', "drei"
        )

        cls.translation = cls._exercise(
            cls.lesson, "واژگان — ترجمه به آلمانی", Exercise.ExerciseType.TRANSLATION, 5
        )
        cls._text_question(
            cls.translation, 22, "ترجمهٔ «شب بخیر» به آلمانی؟", "gute Nacht",
            explanation="واژهٔ درس: gute Nacht",
        )

        cls.reading = cls._exercise(
            cls.lesson, "خواندن و درک مطلب", Exercise.ExerciseType.READING, 6
        )
        reading_question = cls._choice_question(
            cls.reading, 23, 'در جملهٔ زیر، معادل فارسی کدام گزینه است؟\n"Guten Morgen!"',
            [("صبح بخیر!", True), ("شب بخیر!", False)],
        )
        QuestionTarget.objects.create(question=reading_question, sentence=cls.sentence, role="CONTEXT")

        cls.unchecked = cls._exercise(
            cls.lesson, "بدون پاسخ", Exercise.ExerciseType.MULTIPLE_CHOICE, 7
        )
        Question.objects.create(exercise=cls.unchecked, prompt="پرسش بدون پاسخ", order=24)

        cls.no_questions = cls._exercise(
            cls.lesson, "بدون پرسش", Exercise.ExerciseType.MULTIPLE_CHOICE, 8
        )

        cls.draft = cls._exercise(
            cls.lesson, "تمرین پیش‌نویس", Exercise.ExerciseType.MULTIPLE_CHOICE, 9, published=False
        )
        cls._choice_question(cls.draft, 30, "پیش‌نویس", [("آ", True), ("ب", False)])

        cls.other_lesson_exercise = cls._exercise(
            cls.lesson_two, "واژگان — انتخاب معنی", Exercise.ExerciseType.MULTIPLE_CHOICE, 1
        )
        cls._choice_question(cls.other_lesson_exercise, 40, "واژهٔ «Ja» به چه معنی است؟", [
            ("بله", True), ("نه", False),
        ])

    # ------------------------------------------------------------- builders ---

    @classmethod
    def _exercise(cls, lesson, title, exercise_type, order, published=True):
        return Exercise.objects.create(
            lesson=lesson,
            title=title,
            instruction="دستور تمرین.",
            type=exercise_type,
            difficulty=Exercise.Difficulty.EASY,
            order=order,
            is_published=published,
        )

    @classmethod
    def _choice_question(cls, exercise, order, prompt, options):
        question = Question.objects.create(exercise=exercise, prompt=prompt, order=order)
        for position, (text, is_correct) in enumerate(options, start=1):
            Answer.objects.create(
                question=question, text=text, is_correct=is_correct, order=position
            )
        return question

    @classmethod
    def _text_question(cls, exercise, order, prompt, answer, explanation=""):
        question = Question.objects.create(
            exercise=exercise, prompt=prompt, order=order, explanation=explanation
        )
        Answer.objects.create(question=question, text=answer, is_correct=True, order=1)
        return question


class ExerciseListViewTests(ExercisePageTestBase):
    """The exercise index: published rows only, grouped by lesson, honest counts."""

    def setUp(self):
        self.url = reverse("exercises:exercise-list")

    def test_index_renders_anonymously(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.multiple_choice.title)

    def test_index_loads_its_own_stylesheet(self):
        """The list used to borrow the retired reader_modern.css and six undefined classes."""
        response = self.client.get(self.url)
        self.assertContains(response, "exercises/css/exercise_list.css")
        self.assertNotContains(response, "reader_modern.css")
        self.assertNotContains(response, "reader-exercise-card")
        self.assertNotContains(response, "nav-back-link")

    def test_index_hides_drafts(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, self.draft.title)

    def test_index_groups_every_lesson_once(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse("lessons:lesson-detail", args=[self.lesson.pk]))
        self.assertContains(response, reverse("lessons:lesson-detail", args=[self.lesson_two.pk]))
        self.assertContains(response, f'id="ex-group-{self.lesson.pk}"')
        self.assertContains(response, f'id="ex-group-{self.lesson_two.pk}"')

    def test_index_shows_the_size_of_each_exercise(self):
        response = self.client.get(self.url)
        self.assertContains(response, "2 پرسش")  # the two-question exercise
        # 8 questions in lesson 1 + 1 in lesson 2;
        # the unpublished draft's question is not counted.
        self.assertEqual(response.context["question_total"], 9)
        self.assertEqual(response.context["lesson_count"], 2)

    def test_index_can_be_scoped_to_one_lesson(self):
        response = self.client.get(self.url, {"lesson": self.lesson.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.multiple_choice.title)
        self.assertNotContains(
            response, reverse("exercises:exercise-detail", args=[self.other_lesson_exercise.pk])
        )
        self.assertEqual(response.context["lesson"], self.lesson)

    def test_scoped_index_shows_the_instruction(self):
        response = self.client.get(self.url, {"lesson": self.lesson.pk})
        self.assertContains(response, self.multiple_choice.instruction)

    def test_scoped_index_of_a_lesson_without_exercises_is_empty(self):
        response = self.client.get(self.url, {"lesson": self.lesson_without_exercises.pk})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "ex-card")
        self.assertContains(response, "ex-empty")

    def test_unpublished_lesson_is_not_reachable_through_the_filter(self):
        lesson = Lesson.objects.create(
            course=self.course, title="Draft", is_published=False, order=9, estimated_time=5
        )
        response = self.client.get(self.url, {"lesson": lesson.pk})
        self.assertEqual(response.status_code, 404)


class ExerciseRunnerTests(ExercisePageTestBase):
    """The runner page: real question kinds, inline feedback markup, no dead controls."""

    def get(self, exercise):
        response = self.client.get(
            reverse("exercises:exercise-detail", args=[exercise.pk])
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_each_real_type_renders_its_own_answer_area(self):
        self.assertContains(self.get(self.multiple_choice), 'data-kind="choice"')
        self.assertContains(self.get(self.true_false), 'data-kind="choice"')
        self.assertContains(self.get(self.fill_blank_choice), 'data-kind="choice"')
        self.assertContains(self.get(self.fill_blank_text), 'data-kind="text"')
        self.assertContains(self.get(self.translation), 'data-kind="text"')
        self.assertContains(self.get(self.reading), 'data-kind="choice"')

    def test_choice_questions_render_the_options_without_the_answer(self):
        """The verdict is the server's now, so no option may come marked as correct."""
        html = self.get(self.multiple_choice).content.decode()
        self.assertNotIn("data-correct", html)
        self.assertEqual(html.count('type="radio"'), 8)  # 4 options × 2 questions

    def test_typed_questions_render_an_input_and_keep_the_answer_off_the_page(self):
        """The expected answer arrives with the verdict, not before it."""
        response = self.get(self.translation)
        self.assertContains(response, 'class="runner-answer__input"')
        self.assertContains(response, 'data-expected-value lang="de" dir="ltr"></span>')
        self.assertNotContains(response, self.translation.questions.first().answers.first().text)
        self.assertIn("data-expected hidden", response.content.decode())

    def test_reading_renders_its_passage_as_german(self):
        response = self.get(self.reading)
        self.assertContains(response, f'<p class="runner-q__passage" lang="de" dir="ltr">{self.sentence.text}</p>', html=False)

    def test_question_number_is_the_position_not_the_stored_order(self):
        response = self.get(self.true_false)
        self.assertContains(response, "سؤال 1 از 1")
        self.assertNotContains(response, "سؤال 12")

    def test_progress_semantics_are_real(self):
        response = self.get(self.multiple_choice)
        self.assertContains(response, 'role="progressbar"')
        self.assertContains(response, 'aria-valuemin="1"')
        self.assertContains(response, 'aria-valuemax="2"')
        self.assertContains(response, 'aria-valuenow="1"')

    def test_controls_start_hidden_so_a_no_javascript_page_has_no_dead_buttons(self):
        response = self.get(self.multiple_choice)
        self.assertContains(response, "data-runner-actions hidden")
        self.assertContains(response, "data-runner-progress hidden")
        self.assertContains(response, "exercises/js/exercise_runner.js")
        self.assertContains(response, "<noscript>")

    def test_feedback_is_inline_and_never_an_alert(self):
        response = self.get(self.multiple_choice)
        self.assertNotContains(response, "alert(")
        self.assertContains(response, 'data-runner-feedback role="status" aria-live="polite"')
        self.assertContains(response, 'data-runner-hint role="alert" hidden')

    def test_a_question_without_answers_is_labelled_and_not_scored(self):
        response = self.get(self.unchecked)
        self.assertContains(response, 'data-kind="none"')
        self.assertContains(response, "runner-note")  # the "cannot be checked" note
        self.assertEqual(response.context["scoreable_questions"], 0)

    def test_an_exercise_without_questions_has_an_empty_state(self):
        response = self.get(self.no_questions)
        self.assertContains(response, "exercise-empty")
        self.assertNotContains(response, "data-runner")

    def test_results_state_reports_only_counts(self):
        response = self.get(self.multiple_choice)
        self.assertContains(response, "data-runner-results hidden")
        self.assertContains(response, "data-results-correct")
        self.assertContains(response, "data-results-total")
        self.assertContains(response, "data-results-accuracy")
        self.assertContains(response, "data-runner-retry")
        self.assertNotContains(response, "تسلط")

    def test_the_next_exercise_is_the_next_published_one(self):
        response = self.get(self.multiple_choice)
        self.assertContains(response, reverse("exercises:exercise-detail", args=[self.true_false.pk]))
        self.assertNotContains(response, reverse("exercises:exercise-detail", args=[self.draft.pk]))

    def test_the_lesson_is_always_one_step_away(self):
        response = self.get(self.translation)
        self.assertContains(response, reverse("lessons:lesson-detail", args=[self.lesson.pk]))

    def test_the_runner_ships_the_submission_endpoint(self):
        response = self.get(self.multiple_choice)
        endpoint = reverse("exercises:exercise-submit", args=[self.multiple_choice.pk])
        self.assertContains(response, f'data-submit-url="{endpoint}"')

    def test_an_anonymous_visitor_is_told_nothing_is_saved(self):
        """The old copy promised in-browser grading; the server grades now, so say so."""
        response = self.get(self.multiple_choice)
        self.assertContains(response, "جایی ذخیره نمی‌شود")
        self.assertNotContains(response, "مرورگر")

    def test_a_signed_in_learner_is_told_the_answers_are_recorded(self):
        self.client.force_login(User.objects.create_user(username="sina", password="a-strong-password"))
        response = self.get(self.multiple_choice)
        self.assertContains(response, "روی حساب کاربری‌ات ثبت می‌شود")


class ExerciseRunnerBuilderTests(ExercisePageTestBase):
    """`build_runner` decides the kind from the real answer rows, not from the type label."""

    def kinds(self, exercise):
        return [question["kind"] for question in build_runner(exercise)]

    def test_kind_comes_from_the_answers(self):
        self.assertEqual(self.kinds(self.multiple_choice), ["choice", "choice"])
        self.assertEqual(self.kinds(self.true_false), ["choice"])
        # Same exercise type, two different shapes: distractors → options, none → typed.
        self.assertEqual(self.kinds(self.fill_blank_choice), ["choice"])
        self.assertEqual(self.kinds(self.fill_blank_text), ["text"])
        self.assertEqual(self.kinds(self.translation), ["text"])
        self.assertEqual(self.kinds(self.reading), ["choice"])
        self.assertEqual(self.kinds(self.unchecked), ["none"])

    def test_numbering_follows_position(self):
        questions = build_runner(self.true_false)
        self.assertEqual([question["number"] for question in questions], [1])

    def test_passage_comes_from_the_context_sentence_only(self):
        self.assertEqual(build_runner(self.reading)[0]["passage"], self.sentence.text)
        self.assertEqual(build_runner(self.multiple_choice)[0]["passage"], "")

    def test_options_are_the_real_rows_and_only_choice_questions_have_them(self):
        question = build_runner(self.multiple_choice)[0]
        self.assertEqual(len(question["options"]), 4)
        self.assertEqual([answer.text for answer in question["options"]], ["سلام", "خوش آمدید", "صفر", "زیرا"])
        # Nothing to reveal before the learner submits.
        self.assertNotIn("expected", question)
        self.assertNotIn("explanation", question)

        typed = build_runner(self.translation)[0]
        self.assertEqual(typed["options"], [])


class ExerciseSubmissionTests(ExercisePageTestBase):
    """Submitting an answer: the verdict, the attempt row, and what gets stored.

    The fixture gives the first multiple-choice question a real TESTED_ITEM word and a
    real CONTEXT word, which ``WordProgressTests`` below then leans on.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = User.objects.create_user(username="sina", password="a-strong-password")
        cls.tested_word = Word.objects.create(
            word="bestellen", word_type="VERB", meaning_fa="سفارش دادن",
            level=cls.level, is_published=True,
        )
        cls.context_word = Word.objects.create(
            word="Geld", word_type="NOUN", article="das", gender="N", meaning_fa="پول",
            level=cls.level, is_published=True,
        )
        cls.choice_question = cls.multiple_choice.questions.order_by("order").first()
        QuestionTarget.objects.create(
            question=cls.choice_question, word=cls.tested_word, role="TESTED_ITEM"
        )
        QuestionTarget.objects.create(
            question=cls.choice_question, word=cls.context_word, role="CONTEXT"
        )

    def submit(self, exercise, question, **payload):
        body = {"question": question.pk}
        body.update(payload)
        return self.client.post(
            reverse("exercises:exercise-submit", args=[exercise.pk]),
            data=json.dumps(body),
            content_type="application/json",
        )

    def test_an_anonymous_visitor_is_graded_but_nothing_is_stored(self):
        correct = self.choice_question.answers.get(is_correct=True)

        body = self.submit(
            self.multiple_choice, self.choice_question, answer=correct.pk, response_time=4.7
        ).json()

        self.assertTrue(body["correct"])
        self.assertFalse(body["recorded"])
        self.assertFalse(ExerciseAttempt.objects.exists())
        self.assertFalse(WordProgress.objects.exists())

    def test_a_correct_answer_is_stored_as_one_attempt(self):
        self.client.force_login(self.user)
        correct = self.choice_question.answers.get(is_correct=True)

        body = self.submit(
            self.multiple_choice, self.choice_question, answer=correct.pk, response_time=4.7
        ).json()

        self.assertTrue(body["correct"])
        self.assertTrue(body["recorded"])

        attempt = ExerciseAttempt.objects.get()
        self.assertEqual(attempt.user, self.user)
        self.assertEqual(attempt.exercise, self.multiple_choice)
        self.assertEqual(attempt.question, self.choice_question)
        self.assertEqual(attempt.answer, correct)
        self.assertEqual(attempt.response_text, "")
        self.assertTrue(attempt.is_correct)
        self.assertAlmostEqual(attempt.response_time, 4.7)

    def test_a_wrong_answer_points_at_the_right_option(self):
        self.client.force_login(self.user)
        wrong = self.choice_question.answers.filter(is_correct=False).first()
        right = self.choice_question.answers.get(is_correct=True)

        body = self.submit(self.multiple_choice, self.choice_question, answer=wrong.pk).json()

        self.assertFalse(body["correct"])
        self.assertEqual(body["correct_answer"], right.pk)
        self.assertEqual(body["expected"], [right.text])
        self.assertFalse(ExerciseAttempt.objects.get().is_correct)

    def test_a_typed_answer_is_stored_exactly_as_it_was_typed(self):
        self.client.force_login(self.user)
        question = self.translation.questions.first()

        body = self.submit(self.translation, question, response_text="  Gute Nacht!  ").json()

        self.assertTrue(body["correct"], "case, spacing and trailing punctuation are forgiven")
        attempt = ExerciseAttempt.objects.get()
        self.assertIsNone(attempt.answer)
        self.assertEqual(attempt.response_text, "Gute Nacht!")

    def test_a_wrong_typed_answer_keeps_what_was_typed(self):
        self.client.force_login(self.user)
        question = self.translation.questions.first()

        body = self.submit(self.translation, question, response_text="guten Abend").json()

        self.assertFalse(body["correct"])
        self.assertEqual(ExerciseAttempt.objects.get().response_text, "guten Abend")

    def test_the_explanation_comes_back_with_the_verdict(self):
        self.client.force_login(self.user)
        question = self.translation.questions.first()

        body = self.submit(self.translation, question, response_text="gute Nacht").json()

        self.assertEqual(body["explanation"], "واژهٔ درس: gute Nacht")

    def test_every_submission_is_a_new_row(self):
        self.client.force_login(self.user)
        correct = self.choice_question.answers.get(is_correct=True)

        self.submit(self.multiple_choice, self.choice_question, answer=correct.pk)
        self.submit(self.multiple_choice, self.choice_question, answer=correct.pk)

        self.assertEqual(ExerciseAttempt.objects.filter(user=self.user).count(), 2)

    def test_response_time_is_optional_and_unusable_values_are_dropped(self):
        self.client.force_login(self.user)
        correct = self.choice_question.answers.get(is_correct=True)

        self.submit(self.multiple_choice, self.choice_question, answer=correct.pk)
        self.assertIsNone(ExerciseAttempt.objects.latest("created_at").response_time)

        for value in ("soon", None, -3, 9999):
            self.submit(
                self.multiple_choice, self.choice_question, answer=correct.pk, response_time=value
            )
            self.assertIsNone(ExerciseAttempt.objects.latest("created_at").response_time)

    def test_a_question_of_another_exercise_is_refused(self):
        self.client.force_login(self.user)
        foreign = self.other_lesson_exercise.questions.first()

        response = self.submit(self.multiple_choice, foreign, answer=foreign.answers.first().pk)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ExerciseAttempt.objects.exists())

    def test_an_option_of_another_question_is_refused(self):
        self.client.force_login(self.user)
        foreign = self.true_false.questions.first().answers.first()

        response = self.submit(self.multiple_choice, self.choice_question, answer=foreign.pk)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ExerciseAttempt.objects.exists())

    def test_a_question_with_no_authored_answer_cannot_be_graded(self):
        """The runner shows such a question as unchecked, and so does the endpoint."""
        self.client.force_login(self.user)
        question = self.unchecked.questions.first()

        response = self.submit(self.unchecked, question, response_text="irgendwas")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ExerciseAttempt.objects.exists())


class WordProgressTests(ExercisePageTestBase):
    """Which word a submitted answer counts against — and which it must not."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = User.objects.create_user(username="sina", password="a-strong-password")
        cls.tested_word = Word.objects.create(
            word="bestellen", word_type="VERB", meaning_fa="سفارش دادن",
            level=cls.level, is_published=True,
        )
        cls.context_word = Word.objects.create(
            word="Geld", word_type="NOUN", article="das", gender="N", meaning_fa="پول",
            level=cls.level, is_published=True,
        )
        cls.question = cls.multiple_choice.questions.order_by("order").first()
        QuestionTarget.objects.create(question=cls.question, word=cls.tested_word, role="TESTED_ITEM")
        QuestionTarget.objects.create(question=cls.question, word=cls.context_word, role="CONTEXT")

    def submit(self, correct=True):
        self.client.force_login(self.user)
        answers = self.question.answers
        answer = answers.get(is_correct=True) if correct else answers.filter(is_correct=False).first()
        return self.client.post(
            reverse("exercises:exercise-submit", args=[self.multiple_choice.pk]),
            data=json.dumps({"question": self.question.pk, "answer": answer.pk}),
            content_type="application/json",
        )

    def test_the_first_correct_answer_creates_the_row(self):
        self.submit(correct=True)

        row = WordProgress.objects.get(user=self.user, word=self.tested_word)
        self.assertEqual((row.attempt_count, row.correct_count, row.wrong_count), (1, 1, 0))
        self.assertIsNotNone(row.last_attempted_at)
        self.assertIsNotNone(row.last_correct_at)
        self.assertIsNone(row.last_wrong_at)

    def test_a_wrong_answer_counts_as_wrong(self):
        self.submit(correct=False)

        row = WordProgress.objects.get(user=self.user, word=self.tested_word)
        self.assertEqual((row.attempt_count, row.correct_count, row.wrong_count), (1, 0, 1))
        self.assertIsNotNone(row.last_wrong_at)
        self.assertIsNone(row.last_correct_at)

    def test_repeated_attempts_add_up_on_one_row(self):
        self.submit(correct=True)
        self.submit(correct=False)
        self.submit(correct=True)

        rows = WordProgress.objects.filter(user=self.user, word=self.tested_word)
        self.assertEqual(rows.count(), 1)
        self.assertEqual(
            (rows.get().attempt_count, rows.get().correct_count, rows.get().wrong_count), (3, 2, 1)
        )

    def test_a_context_word_is_never_counted(self):
        """Answering about `bestellen` says nothing about the `Geld` that appears in it."""
        self.submit(correct=True)
        self.assertFalse(WordProgress.objects.filter(word=self.context_word).exists())

    def test_a_question_that_tests_no_word_still_records_the_attempt(self):
        question = self.true_false.questions.first()
        self.client.force_login(self.user)

        self.client.post(
            reverse("exercises:exercise-submit", args=[self.true_false.pk]),
            data=json.dumps(
                {"question": question.pk, "answer": question.answers.get(is_correct=True).pk}
            ),
            content_type="application/json",
        )

        self.assertFalse(WordProgress.objects.exists())
        self.assertEqual(ExerciseAttempt.objects.count(), 1)

    def test_progress_is_kept_per_learner(self):
        other = User.objects.create_user(username="other", password="a-strong-password")
        self.submit(correct=True)
        self.assertFalse(WordProgress.objects.filter(user=other).exists())


class GradingTests(ExercisePageTestBase):
    """`exercises/grading.py`: what counts as right, and what never gets a verdict."""

    def test_a_typed_answer_forgives_case_spacing_and_trailing_punctuation(self):
        question = self.translation.questions.first()
        for typed in ("gute Nacht", "Gute nacht", "  gute   Nacht!  ", "gute Nacht."):
            with self.subTest(typed=typed):
                self.assertTrue(grade(question, None, typed)["is_correct"])

    def test_a_typed_answer_must_be_the_whole_answer(self):
        question = self.translation.questions.first()
        for typed in ("guten Abend", "Nacht", "gute", ""):
            with self.subTest(typed=typed):
                self.assertFalse(grade(question, None, typed)["is_correct"])

    def test_choosing_an_option_uses_the_stored_row(self):
        question = self.multiple_choice.questions.order_by("order").first()
        right = question.answers.get(is_correct=True)
        wrong = question.answers.filter(is_correct=False).first()

        self.assertTrue(grade(question, right.pk, None)["is_correct"])
        self.assertFalse(grade(question, wrong.pk, None)["is_correct"])

    def test_the_chosen_row_is_what_an_attempt_keeps(self):
        question = self.multiple_choice.questions.order_by("order").first()
        wrong = question.answers.filter(is_correct=False).first()

        verdict = grade(question, wrong.pk, None)

        self.assertEqual(verdict["answer"], wrong)
        self.assertEqual(verdict["response_text"], "")
        self.assertEqual(verdict["correct_answer_id"], question.answers.get(is_correct=True).pk)

    def test_a_typed_answer_longer_than_the_field_is_cut_to_fit(self):
        question = self.translation.questions.first()
        self.assertEqual(len(grade(question, None, "x" * 600)["response_text"]), 500)

    def test_an_ungradeable_question_returns_no_verdict(self):
        question = self.unchecked.questions.first()
        self.assertIsNone(grade(question, None, "irgendwas"))

    def test_an_option_of_another_question_returns_no_verdict(self):
        question = self.multiple_choice.questions.order_by("order").first()
        foreign = self.true_false.questions.first().answers.first()
        self.assertIsNone(grade(question, foreign.pk, None))


class ExerciseHistoryTests(ExercisePageTestBase):
    """Reading ExerciseAttempt back, so a result survives a reload."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = User.objects.create_user(username="sina", password="a-strong-password")
        questions = list(cls.multiple_choice.questions.order_by("order", "pk"))
        cls.first = questions[0]
        cls.second = questions[1]

    def setUp(self):
        self.client.force_login(self.user)

    def record(self, question, is_correct, exercise=None):
        if exercise is None:
            exercise = self.multiple_choice
        return ExerciseAttempt.objects.create(
            user=self.user,
            exercise=exercise,
            question=question,
            is_correct=is_correct,
            response_text="",
        )

    def test_no_attempts_means_no_history(self):
        self.assertIsNone(exercise_history(self.user, self.multiple_choice))

    def test_only_the_latest_attempt_at_a_question_counts(self):
        self.record(self.first, False)
        self.record(self.first, True)  # tried again and got it right
        history = exercise_history(self.user, self.multiple_choice)
        self.assertEqual(history["answered"], 1)
        self.assertEqual(history["correct"], 1)
        self.assertEqual(history["missed"], [])

    def test_a_later_wrong_answer_replaces_an_earlier_right_one(self):
        self.record(self.first, True)
        self.record(self.first, False)
        history = exercise_history(self.user, self.multiple_choice)
        self.assertEqual(history["correct"], 0)
        self.assertEqual(len(history["missed"]), 1)

    def test_missed_questions_are_numbered_by_position(self):
        # Question.order is lesson-wide, so the page must number by position instead.
        self.record(self.first, False)
        self.record(self.second, False)
        history = exercise_history(self.user, self.multiple_choice)
        self.assertEqual([row["position"] for row in history["missed"]], [1, 2])
        self.assertEqual(history["total"], 2)

    def test_another_exercises_attempts_are_ignored(self):
        other_question = self.true_false.questions.order_by("order").first()
        self.record(other_question, False, exercise=self.true_false)
        self.assertIsNone(exercise_history(self.user, self.multiple_choice))

    def test_another_learners_attempts_are_ignored(self):
        other = User.objects.create_user(username="other", password="a-strong-password")
        ExerciseAttempt.objects.create(
            user=other, exercise=self.multiple_choice, question=self.first,
            is_correct=False, response_text="",
        )
        self.assertIsNone(exercise_history(self.user, self.multiple_choice))

    def test_the_page_shows_the_past_result(self):
        self.record(self.first, True)
        self.record(self.second, False)
        response = self.client.get(
            reverse("exercises:exercise-detail", args=[self.multiple_choice.pk])
        )
        self.assertContains(response, "این تمرین را قبلاً انجام داده‌ای")
        self.assertContains(response, "1</b> از <b>2")

    def test_the_page_shows_which_questions_to_revisit(self):
        self.record(self.first, True)
        self.record(self.second, False)
        response = self.client.get(
            reverse("exercises:exercise-detail", args=[self.multiple_choice.pk])
        )
        self.assertContains(response, "پرسش‌هایی که آخرین بار اشتباه بود")
        self.assertContains(response, "پرسش 2")

    def test_a_clean_run_says_so_instead_of_listing_nothing(self):
        self.record(self.first, True)
        self.record(self.second, True)
        response = self.client.get(
            reverse("exercises:exercise-detail", args=[self.multiple_choice.pk])
        )
        self.assertContains(response, "آخرین بار همهٔ پرسش‌هایی که پاسخ دادی درست بود.")
        self.assertNotContains(response, "پرسش‌هایی که آخرین بار اشتباه بود")

    def test_the_page_omits_the_panel_when_there_is_no_history(self):
        response = self.client.get(
            reverse("exercises:exercise-detail", args=[self.multiple_choice.pk])
        )
        self.assertNotContains(response, "exercise-history")

    def test_an_anonymous_visitor_never_gets_the_panel(self):
        # Attempts exist, but they belong to a learner this visitor is not.
        self.record(self.first, False)
        self.client.logout()
        response = self.client.get(
            reverse("exercises:exercise-detail", args=[self.multiple_choice.pk])
        )
        self.assertNotContains(response, "exercise-history")


class SeedA1ExercisesTests(TestCase):
    """``seed_a1_exercises``: listening content built from the sentences' own audio."""

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", is_published=True, order=1, estimated_time=10
        )

        # An authored exercise, numbered like the live data. The command must never touch it.
        cls.authored = Exercise.objects.create(
            lesson=cls.lesson, title="واژگان", instruction="",
            type=Exercise.ExerciseType.MULTIPLE_CHOICE, difficulty=Exercise.Difficulty.EASY,
            order=1, is_published=True,
        )
        authored_question = Question.objects.create(
            exercise=cls.authored, prompt="واژهٔ «hallo»؟", order=1
        )
        Answer.objects.create(question=authored_question, text="سلام", is_correct=True, order=1)

        cls.sentences = []
        for i in range(6):
            sentence = Sentence.objects.create(
                text=f"Guten Tag {i}", translation_fa=f"روز بخیر {i}",
                level=cls.level, is_published=True, audio=f"sentences/audio/s{i}.mp3",
            )
            cls.sentences.append(sentence)
            LessonSentence.objects.create(
                lesson=cls.lesson, sentence=sentence, role="EXAMPLE", order=i + 1
            )

    def run_command(self, *args):
        out = StringIO()
        call_command("seed_a1_exercises", *args, stdout=out)
        return out.getvalue()

    def listening_questions(self):
        return Question.objects.filter(exercise__type=Exercise.ExerciseType.LISTENING)

    def test_it_builds_one_exercise_for_the_lesson(self):
        self.run_command()
        exercises = Exercise.objects.filter(type=Exercise.ExerciseType.LISTENING)
        self.assertEqual(exercises.count(), 1)
        self.assertEqual(exercises.first().lesson, self.lesson)

    def test_each_sentence_becomes_two_questions(self):
        self.run_command()
        self.assertEqual(self.listening_questions().count(), 6)

    def test_every_question_carries_the_sentence_audio(self):
        self.run_command()
        for question in self.listening_questions():
            self.assertTrue(question.audio)
            self.assertTrue(question.audio.name.startswith("sentences/audio/"))

    def test_each_question_has_four_options_and_exactly_one_right_answer(self):
        self.run_command()
        for question in self.listening_questions():
            self.assertEqual(question.answers.count(), 4)
            self.assertEqual(question.answers.filter(is_correct=True).count(), 1)

    def test_both_question_styles_are_asked(self):
        self.run_command()
        prompts = set(self.listening_questions().values_list("prompt", flat=True))
        self.assertEqual(len(prompts), 2)

    def test_the_right_answer_is_one_of_the_lessons_own_sentences(self):
        self.run_command()
        question = self.listening_questions().filter(prompt__endswith="معنی درست را انتخاب کن.").first()
        correct = question.answers.get(is_correct=True).text
        self.assertIn(correct, [sentence.translation_fa for sentence in self.sentences])
        # and no wrong option repeats it
        self.assertEqual(question.answers.filter(text=correct).count(), 1)

    def test_rerunning_replaces_instead_of_duplicating(self):
        self.run_command()
        first_ids = list(
            Exercise.objects.filter(type=Exercise.ExerciseType.LISTENING).values_list("id", flat=True)
        )
        self.run_command()
        second_ids = list(
            Exercise.objects.filter(type=Exercise.ExerciseType.LISTENING).values_list("id", flat=True)
        )
        self.assertEqual(len(second_ids), 1)
        self.assertNotEqual(first_ids, second_ids)

    def test_it_never_touches_the_authored_exercises(self):
        self.run_command()
        self.assertTrue(Exercise.objects.filter(pk=self.authored.pk).exists())
        self.assertEqual(Question.objects.filter(exercise=self.authored).count(), 1)
        self.assertTrue(Answer.objects.filter(question__exercise=self.authored).exists())

    def test_a_lesson_with_too_few_sentences_is_skipped(self):
        for sentence in self.sentences[:4]:
            Sentence.objects.filter(pk=sentence.pk).update(is_published=False)
        self.run_command()
        self.assertEqual(Exercise.objects.filter(type=Exercise.ExerciseType.LISTENING).count(), 0)

    def test_dry_run_writes_nothing(self):
        output = self.run_command("--dry-run")
        self.assertIn("Dry run", output)
        self.assertEqual(Exercise.objects.filter(type=Exercise.ExerciseType.LISTENING).count(), 0)

    def test_the_new_questions_continue_the_lessons_numbering(self):
        self.run_command()
        orders = sorted(
            Question.objects.filter(exercise__lesson=self.lesson).values_list("order", flat=True)
        )
        # The authored question is order 1, so the generated six run 2..7 with no gap.
        self.assertEqual(orders, list(range(1, 8)))

    def test_it_refuses_a_sentence_count_that_cannot_fill_the_options(self):
        with self.assertRaises(CommandError):
            self.run_command("--sentences", "1")
