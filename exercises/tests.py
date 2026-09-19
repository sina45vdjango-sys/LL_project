"""
Tests for exercise generation and integrity.
Verifies that exercises, questions, answers and targets are wired correctly.
"""
from django.test import TestCase
from django.urls import reverse

from exercises.models import Exercise, Question, QuestionTarget, Answer
from lessons.models import Lesson


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
    """Verify exercises appear on the lesson detail page."""

    def test_lesson_detail_page_contains_exercises(self):
        """Lesson detail page should render exercise section if exercises exist."""
        lesson = Lesson.objects.first()
        if not lesson:
            self.skipTest("No lessons in database")
        url = reverse("lessons:lesson-detail", kwargs={"pk": lesson.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check that exercises are rendered if any exist
        if Exercise.objects.filter(lesson=lesson, is_published=True).exists():
            self.assertContains(response, "lesson-exercises")
            self.assertContains(response, "exercise-block")
