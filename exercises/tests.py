"""
Tests for exercise generation and integrity.
Verifies that exercises, questions, answers and targets are wired correctly.
"""
import json
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import AnonymousUser, User
from django.core.management import call_command
from django.db.models import Q
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from exercises import generated
from exercises.eligibility import eligible_lesson_ids, eligible_lessons
from exercises.grading import grade
from exercises.hints import hint_for, hint_strength, masked_text
from exercises.history import exercise_history, wrong_counts
from exercises.management.commands import (
    seed_a1_dictation_drills,
    seed_a1_exercises,
    seed_a1_pronunciation_drills,
    seed_a1_reading_drills,
    seed_a1_sentence_drills,
    seed_a1_word_drills,
)
from exercises.models import Exercise, ExerciseAttempt, Question, QuestionTarget, Answer
from exercises.runner import CHOICE, ORDER, PUNCTUATION, TEXT, build_runner, extract_sentence_words
from exercises.session import (
    SESSION_SIZE,
    build_session,
    pick_questions,
    session_lesson,
    session_progress,
    session_skills,
)
from lessons.models import (
    Course,
    LanguageLevel,
    Lesson,
    LessonGrammar,
    LessonProgress,
    LessonSentence,
    LessonWord,
)
from vocabulary.models import Grammar, Sentence, Word, WordProgress
from vocabulary.review import exercises_for_words, last_used_type
from vocabulary.schedule import review_queue
from vocabulary.status import MISTAKE_LIMIT


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
    """One lesson's exercise list, and the old bare URL as a redirect.

    The bare URL used to print every card, then one row per lesson. Both were still a wall
    of exercises, so the practice path took its place — and that page already lives at
    ``lessons:practice-path``, so this URL no longer renders a second copy of it. The
    ``?lesson=<pk>`` shape is unchanged, because it is where the lesson journey, the
    session footer and the runner link.
    """

    def setUp(self):
        self.url = reverse("exercises:exercise-list")

    def test_the_bare_url_redirects_to_the_practice_path(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("lessons:practice-path"))

    def test_the_redirect_leaves_the_lesson_filter_alone(self):
        response = self.client.get(self.url, {"lesson": self.lesson.pk})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "exercises/exercise_list.html")

    def test_a_lesson_filter_lists_that_lessons_cards(self):
        response = self.client.get(self.url, {"lesson": self.lesson.pk})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "exercises/exercise_list.html")
        self.assertContains(response, "ex-card")
        self.assertContains(response, self.multiple_choice.title)
        self.assertNotContains(
            response, reverse("exercises:exercise-detail", args=[self.other_lesson_exercise.pk])
        )
        self.assertEqual(response.context["lesson"], self.lesson)
        self.assertEqual(response.context["exercise_total"], 8)
        self.assertEqual(response.context["question_total"], 8)

    def test_the_lesson_list_loads_its_own_stylesheet(self):
        """The list used to borrow the retired reader_modern.css and six undefined classes."""
        response = self.client.get(self.url, {"lesson": self.lesson.pk})

        self.assertContains(response, "exercises/css/exercise_list.css")
        self.assertNotContains(response, "reader_modern.css")
        self.assertNotContains(response, "reader-exercise-card")
        self.assertNotContains(response, "nav-back-link")

    def test_the_lesson_list_shows_each_exercises_instruction(self):
        response = self.client.get(self.url, {"lesson": self.lesson.pk})
        self.assertContains(response, self.multiple_choice.instruction)

    def test_the_lesson_list_hides_drafts(self):
        """Neither the draft exercise nor the draft lesson it lives in may be counted."""
        draft_lesson = Lesson.objects.create(
            course=self.course, title="Entwurf", is_published=False, order=9, estimated_time=5
        )
        self._exercise(
            draft_lesson, "تمرین پیش‌نویس درس", Exercise.ExerciseType.MULTIPLE_CHOICE, 1
        )
        response = self.client.get(self.url, {"lesson": self.lesson.pk})

        self.assertNotContains(response, self.draft.title)
        self.assertNotContains(response, "Entwurf")
        self.assertEqual(response.context["question_total"], 8)

    def test_a_lesson_without_exercises_gets_an_empty_state(self):
        response = self.client.get(self.url, {"lesson": self.lesson_without_exercises.pk})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "ex-card")
        self.assertContains(response, "ex-empty")

    def test_an_unpublished_lesson_is_not_reachable_through_the_filter(self):
        lesson = Lesson.objects.create(
            course=self.course, title="Draft", is_published=False, order=9, estimated_time=5
        )
        response = self.client.get(self.url, {"lesson": lesson.pk})
        self.assertEqual(response.status_code, 404)


class PracticeChatViewTests(ExercisePageTestBase):
    """Concept 9's delivery mode: the lesson's own dialogue, its assets, its visibility.

    The conversation is played client-side (``exercises/js/conversation.js``), so what a
    server test pins is the content: that the page shows the lesson's dialogue rather than
    an exercise's quiz questions, that both speakers are named, that nothing is graded
    here, and that a draft stays a 404.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # A two-line scene: the learner (the first speaker) opens it, the partner answers.
        cls.reply = Sentence.objects.create(
            text="Wie heißt du?", translation_fa="اسمت چیه؟", level=cls.level, is_published=True
        )
        LessonSentence.objects.create(
            lesson=cls.lesson, sentence=cls.sentence, role="DIALOGUE", speaker="Anna", order=1
        )
        LessonSentence.objects.create(
            lesson=cls.lesson, sentence=cls.reply, role="DIALOGUE", speaker="Ben", order=2
        )

    def get(self, exercise):
        response = self.client.get(reverse("exercises:exercise-chat", args=[exercise.pk]))
        self.assertEqual(response.status_code, 200)
        return response

    def test_the_page_plays_the_lessons_own_dialogue(self):
        response = self.get(self.multiple_choice)
        self.assertTemplateUsed(response, "exercises/chat.html")
        self.assertContains(response, "گفت‌وگو با معلم")
        self.assertContains(response, "Guten Morgen!")
        self.assertContains(response, "Wie heißt du?")

    def test_the_page_does_not_show_the_exercises_quiz(self):
        """The page used to say an exercise's own questions in chat bubbles, which is
        exactly why it read like a form rather than a conversation."""
        self.assertNotContains(self.get(self.multiple_choice), "به چه معنی است؟")

    def test_both_speakers_are_named_and_one_side_is_yours(self):
        response = self.get(self.multiple_choice)
        self.assertContains(response, "Anna")
        self.assertContains(response, "Ben")
        # The learner takes the first speaker's part, so exactly one turn is theirs.
        self.assertContains(response, "data-mine", count=1)

    def test_nothing_is_graded_on_the_page(self):
        """A spoken line cannot be marked, so there is no answer and no submit endpoint."""
        html = self.get(self.multiple_choice).content.decode()
        self.assertNotIn("data-correct", html)
        self.assertNotIn("exercise-submit", html)

    def test_the_page_needs_no_account(self):
        # The content is public, exactly as the plain runner is.
        self.assertContains(self.get(self.multiple_choice), "گفت‌وگو با معلم")

    def test_the_page_loads_the_runner_widget_and_its_own_assets(self):
        response = self.get(self.multiple_choice)
        # The answer widget is the runner's — exercise.css styles it once.
        self.assertContains(response, "exercises/css/exercise.css")
        self.assertContains(response, "exercises/css/chat.css")
        self.assertContains(response, "exercises/js/conversation.js")

    def test_the_header_names_the_skill(self):
        # A plain MULTIPLE_CHOICE is a vocabulary drill (lessons/skill_path.py).
        self.assertContains(self.get(self.multiple_choice), "واژگان")

    def test_a_grammar_tagged_drill_is_labelled_grammar(self):
        # The tag, not the shape, is what moves a drill to another skill.
        grammar = Grammar.objects.create(
            title="Artikel", explanation="", level=self.level, is_published=True
        )
        QuestionTarget.objects.create(
            question=self.multiple_choice.questions.first(),
            grammar=grammar,
            role=QuestionTarget.Role.GRAMMAR,
        )
        self.assertContains(self.get(self.multiple_choice), "گرامر")

    def test_a_draft_exercise_is_not_reachable(self):
        response = self.client.get(reverse("exercises:exercise-chat", args=[self.draft.pk]))
        self.assertEqual(response.status_code, 404)

    def test_an_exercise_in_a_draft_lesson_is_not_reachable(self):
        lesson = Lesson.objects.create(
            course=self.course, title="Entwurf", is_published=False, order=9, estimated_time=5
        )
        exercise = self._exercise(
            lesson, "پیش‌نویس", Exercise.ExerciseType.MULTIPLE_CHOICE, 1
        )
        self._choice_question(exercise, 1, "پرسش", [("آ", True), ("ب", False)])
        response = self.client.get(reverse("exercises:exercise-chat", args=[exercise.pk]))
        self.assertEqual(response.status_code, 404)

    def test_a_lesson_without_a_dialogue_gets_an_empty_state(self):
        # The two review lessons have no scene of their own.
        self.assertContains(self.get(self.other_lesson_exercise), "exercise-empty")


class PracticeDialogueViewTests(ExercisePageTestBase):
    """Concept 13's delivery mode: the role-play page, its scene and its visibility rule.

    The thread is concept 9's (the shared partial and ``exercises/js/conversation.js``), so
    what is pinned here is the framing the page adds — the scene, the partner's name, and
    that nothing is graded — rather than the conversation, which is client-side.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.reply = Sentence.objects.create(
            text="Wie heißt du?", translation_fa="اسمت چیه؟", level=cls.level, is_published=True
        )
        LessonSentence.objects.create(
            lesson=cls.lesson, sentence=cls.sentence, role="DIALOGUE", speaker="Anna", order=1
        )
        LessonSentence.objects.create(
            lesson=cls.lesson, sentence=cls.reply, role="DIALOGUE", speaker="Ben", order=2
        )

    def get(self, exercise):
        response = self.client.get(reverse("exercises:exercise-dialogue", args=[exercise.pk]))
        self.assertEqual(response.status_code, 200)
        return response

    def test_the_page_sets_the_scene_and_plays_the_lessons_dialogue(self):
        response = self.get(self.multiple_choice)
        self.assertTemplateUsed(response, "exercises/dialogue.html")
        self.assertContains(response, "گفت‌وگوی روز")
        # The scene is the lesson the exercise belongs to.
        self.assertContains(response, self.lesson.title)
        self.assertContains(response, "Guten Morgen!")
        self.assertContains(response, "Wie heißt du?")

    def test_the_page_does_not_show_the_exercises_quiz(self):
        self.assertNotContains(self.get(self.multiple_choice), "به چه معنی است؟")

    def test_nothing_is_graded_on_the_page(self):
        html = self.get(self.multiple_choice).content.decode()
        self.assertNotIn("data-correct", html)
        self.assertNotIn("exercise-submit", html)

    def test_the_page_needs_no_account(self):
        self.assertContains(self.get(self.multiple_choice), "گفت‌وگوی روز")

    def test_the_page_reuses_the_chat_thread_and_its_own_script(self):
        response = self.get(self.multiple_choice)
        self.assertContains(response, "exercises/js/conversation.js")
        self.assertContains(response, "exercises/css/chat.css")
        self.assertContains(response, "exercises/css/exercise.css")

    def test_a_draft_exercise_is_not_reachable(self):
        response = self.client.get(reverse("exercises:exercise-dialogue", args=[self.draft.pk]))
        self.assertEqual(response.status_code, 404)

    def test_a_lesson_without_a_dialogue_gets_an_empty_state(self):
        self.assertContains(self.get(self.other_lesson_exercise), "exercise-empty")


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

    def test_a_practice_page_offers_one_second_try(self):
        """A miss is answered again before the answer is shown, so the runner is told the
        page is a practice page. The step test deliberately does not pass the flag."""
        response = self.get(self.multiple_choice)
        self.assertContains(response, "data-second-try")
        self.assertContains(response, "data-runner-second-try")

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

    def test_the_display_number_is_the_position_not_the_stored_order(self):
        # `order` is a lesson-wide counter the generators keep appending to, so a rebuild
        # can push an authored exercise from 5 to 61 (the reported bug). What the learner
        # sees is the exercise's place in the lesson's ordered list.
        lesson = Lesson.objects.create(
            course=self.course, title="Lektion mit Ordnung", is_published=True,
            order=8, estimated_time=10,
        )
        self._exercise(lesson, "اول", Exercise.ExerciseType.MULTIPLE_CHOICE, 5)
        second = self._exercise(lesson, "دوم", Exercise.ExerciseType.MULTIPLE_CHOICE, 61)

        response = self.client.get(reverse("exercises:exercise-detail", args=[second.pk]))

        self.assertContains(response, "تمرین 2")
        self.assertNotContains(response, "تمرین 61")

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

    def test_a_draft_exercise_is_not_reachable_by_url(self):
        """The index hides it, so the runner must hide it too."""
        response = self.client.get(reverse("exercises:exercise-detail", args=[self.draft.pk]))
        self.assertEqual(response.status_code, 404)

    def test_a_published_exercise_of_a_draft_lesson_is_not_reachable(self):
        lesson = Lesson.objects.create(
            course=self.course, title="Draft", is_published=False, order=9, estimated_time=5
        )
        exercise = self._exercise(
            lesson, "تمرین درس پیش‌نویس", Exercise.ExerciseType.MULTIPLE_CHOICE, 1
        )
        response = self.client.get(reverse("exercises:exercise-detail", args=[exercise.pk]))
        self.assertEqual(response.status_code, 404)

    def test_a_published_exercise_of_a_draft_course_is_not_reachable(self):
        level = LanguageLevel.objects.create(level="B1", title="B1", order=3)
        course = Course.objects.create(
            language_level=level, title="Entwurf", is_published=False
        )
        lesson = Lesson.objects.create(
            course=course, title="Lektion 1", is_published=True, order=1, estimated_time=5
        )
        exercise = self._exercise(
            lesson, "تمرین دورهٔ پیش‌نویس", Exercise.ExerciseType.MULTIPLE_CHOICE, 1
        )
        response = self.client.get(reverse("exercises:exercise-detail", args=[exercise.pk]))
        self.assertEqual(response.status_code, 404)


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
        # The options are shuffled, so the set is what is checked, not the stored order.
        self.assertEqual(
            sorted(answer.text for answer in question["options"]),
            sorted(["سلام", "خوش آمدید", "صفر", "زیرا"]),
        )
        # Nothing to reveal before the learner submits.
        self.assertNotIn("expected", question)
        self.assertNotIn("explanation", question)

        typed = build_runner(self.translation)[0]
        self.assertEqual(typed["options"], [])

    def test_the_option_shuffle_is_the_same_on_every_load(self):
        """A reload must not rearrange the options under the learner, so the shuffle is
        seeded from the question id rather than from a fresh random draw."""
        first = [answer.pk for answer in build_runner(self.multiple_choice)[0]["options"]]
        second = [answer.pk for answer in build_runner(self.multiple_choice)[0]["options"]]
        self.assertEqual(first, second)

    def test_the_correct_option_is_not_locked_to_the_first_position(self):
        """Every authored question stored its correct option first, so without a shuffle the
        learner could pass by always picking option 1. The position has to vary between
        questions, and it is the shuffled list — not the stored order — that is measured."""
        exercise = self._exercise(
            self.lesson, "shuffle", Exercise.ExerciseType.MULTIPLE_CHOICE, 40
        )
        for order in range(1, 13):
            question = Question.objects.create(
                exercise=exercise, prompt=f"پرسش {order}", order=order
            )
            for position, text in enumerate(["الف", "ب", "پ", "ت"], start=1):
                Answer.objects.create(
                    question=question,
                    text=f"{text}{order}",
                    is_correct=(position == 1),
                    order=position,
                )

        positions = []
        for row in build_runner(exercise):
            for index, option in enumerate(row["options"]):
                if option.is_correct:
                    positions.append(index)

        self.assertEqual(len(positions), 12)
        self.assertGreater(len(set(positions)), 1)
        self.assertNotEqual(set(positions), {0})

    def test_the_shuffle_keeps_exactly_one_correct_option(self):
        for exercise in [self.multiple_choice, self.true_false, self.reading]:
            for row in build_runner(exercise):
                correct = [option for option in row["options"] if option.is_correct]
                self.assertEqual(len(correct), 1)
                self.assertTrue(
                    Answer.objects.filter(pk=correct[0].pk, is_correct=True).exists()
                )


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
            pronunciation="bəˈʃtɛlən", level=cls.level, is_published=True,
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

    def test_a_draft_exercise_cannot_be_submitted_to(self):
        """Nothing to grade: the exercise is not visible in the first place."""
        response = self.submit(self.draft, self.draft.questions.first())
        self.assertEqual(response.status_code, 404)

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

    def test_grading_uses_the_option_id_not_its_shuffled_position(self):
        """The page renders the options in a shuffled order; the verdict is decided from the
        ``Answer`` rows, so the position the learner saw cannot change it."""
        self.client.force_login(self.user)
        row = build_runner(self.multiple_choice)[0]
        correct = [option for option in row["options"] if option.is_correct][0]

        body = self.submit(self.multiple_choice, self.choice_question, answer=correct.pk).json()

        self.assertTrue(body["correct"])

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

    def test_a_correct_answer_earns_no_hint(self):
        self.client.force_login(self.user)
        correct = self.choice_question.answers.get(is_correct=True)

        body = self.submit(self.multiple_choice, self.choice_question, answer=correct.pk).json()

        self.assertEqual(body["hint_strength"], 0)

    def test_a_wrong_answer_earns_a_hint_and_a_second_miss_strengthens_it(self):
        """The strength is read back after recording, so the mistake just made already
        counts — repeating it makes the stronger hint available at once."""
        self.client.force_login(self.user)
        wrong = self.choice_question.answers.filter(is_correct=False).first()

        first = self.submit(self.multiple_choice, self.choice_question, answer=wrong.pk).json()
        self.assertEqual(first["hint_strength"], 1)

        second = self.submit(self.multiple_choice, self.choice_question, answer=wrong.pk).json()
        self.assertEqual(second["hint_strength"], 2)

    def test_an_anonymous_visitor_earns_no_hint(self):
        wrong = self.choice_question.answers.filter(is_correct=False).first()

        body = self.submit(self.multiple_choice, self.choice_question, answer=wrong.pk).json()

        self.assertEqual(body["hint_strength"], 0)

    def test_a_missed_answer_reports_the_teaching_card(self):
        """The card teaches the missed word, and the results screen also builds its
        weak-word list from the same payload (TODO item C)."""
        self.client.force_login(self.user)
        wrong = self.choice_question.answers.filter(is_correct=False).first()

        body = self.submit(self.multiple_choice, self.choice_question, answer=wrong.pk).json()

        tested = body["tested_word"]
        self.assertEqual(tested["id"], self.tested_word.pk)
        self.assertEqual(tested["word"], "bestellen")
        self.assertEqual(tested["meaning_fa"], "سفارش دادن")
        self.assertEqual(tested["pronunciation"], "bəˈʃtɛlən")
        self.assertEqual(tested["word_type"], "فعل")
        self.assertEqual(tested["wrong_count"], 1)
        self.assertFalse(tested["repeated"])
        self.assertEqual(
            tested["url"], reverse("vocabulary:word-detail", args=[self.tested_word.pk])
        )

    def test_only_the_tested_item_is_reported_not_a_context_word(self):
        """A word that merely appears in the question was never tested, so it is not a
        word the learner failed (vocabulary/progress.py)."""
        self.client.force_login(self.user)
        wrong = self.choice_question.answers.filter(is_correct=False).first()

        body = self.submit(self.multiple_choice, self.choice_question, answer=wrong.pk).json()

        self.assertNotEqual(body["tested_word"]["id"], self.context_word.pk)

    def test_a_correct_answer_reports_no_word_to_review(self):
        self.client.force_login(self.user)
        correct = self.choice_question.answers.get(is_correct=True)

        body = self.submit(self.multiple_choice, self.choice_question, answer=correct.pk).json()

        self.assertIsNone(body["tested_word"])

    def test_an_anonymous_visitor_still_gets_the_teaching_card(self):
        """The word is public lesson content, so a visitor is taught the same facts; only
        the personal counters are withheld, because a visitor has no ``WordProgress``."""
        wrong = self.choice_question.answers.filter(is_correct=False).first()

        body = self.submit(self.multiple_choice, self.choice_question, answer=wrong.pk).json()

        card = body["tested_word"]
        self.assertEqual(card["id"], self.tested_word.pk)
        self.assertEqual(card["meaning_fa"], "سفارش دادن")
        self.assertEqual(
            card["url"], reverse("vocabulary:word-detail", args=[self.tested_word.pk])
        )
        self.assertEqual(card["wrong_count"], 0)
        self.assertFalse(card["repeated"])

    def test_a_question_that_tests_no_word_reports_none(self):
        self.client.force_login(self.user)
        question = self.translation.questions.first()

        body = self.submit(self.translation, question, response_text="guten Abend").json()

        self.assertFalse(body["correct"])
        self.assertIsNone(body["tested_word"])

    def test_a_repeatedly_missed_word_is_flagged_at_the_threshold(self):
        """The same ``MISTAKE_LIMIT`` the lesson rows use decides «اشتباه پرتکرار»
        (vocabulary/status.py), so the word and the lesson row agree."""
        self.client.force_login(self.user)
        wrong = self.choice_question.answers.filter(is_correct=False).first()

        for _ in range(MISTAKE_LIMIT):
            body = self.submit(self.multiple_choice, self.choice_question, answer=wrong.pk).json()

        self.assertEqual(body["tested_word"]["wrong_count"], MISTAKE_LIMIT)
        self.assertTrue(body["tested_word"]["repeated"])


class ExerciseHintEndpointTests(ExercisePageTestBase):
    """``ExerciseHintView``: a hint must be earned, and it still hides the answer.

    The hint text is computed by the server on demand rather than rendered into the page,
    because the answer it hides must stay off the page. The unit rules live in
    ``HintTests``; these tests pin the endpoint around them.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = User.objects.create_user(username="sina", password="a-strong-password")
        cls.choice_question = cls.multiple_choice.questions.order_by("order").first()

    def submit(self, answer):
        return self.client.post(
            reverse("exercises:exercise-submit", args=[self.multiple_choice.pk]),
            data=json.dumps({"question": self.choice_question.pk, "answer": answer.pk}),
            content_type="application/json",
        )

    def url(self, exercise, question):
        return reverse("exercises:exercise-hint", args=[exercise.pk]) + f"?question={question.pk}"

    def test_an_anonymous_visitor_is_refused(self):
        response = self.client.get(self.url(self.multiple_choice, self.choice_question))
        self.assertEqual(response.status_code, 403)

    def test_a_question_never_missed_has_no_hint_yet(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url(self.multiple_choice, self.choice_question))
        self.assertEqual(response.status_code, 404)

    def test_a_missed_question_returns_a_hint_that_hides_the_answer(self):
        self.client.force_login(self.user)
        wrong = self.choice_question.answers.filter(is_correct=False).first()
        self.submit(wrong)

        body = self.client.get(
            self.url(self.multiple_choice, self.choice_question)
        ).json()

        self.assertEqual(body["strength"], 1)
        self.assertTrue(body["hint"])
        correct = self.choice_question.answers.get(is_correct=True).text
        self.assertNotIn(correct, body["hint"])

    def test_an_unknown_question_is_refused(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("exercises:exercise-hint", args=[self.multiple_choice.pk]) + "?question=0"
        )
        self.assertEqual(response.status_code, 400)

    def test_a_draft_exercise_is_not_reachable(self):
        self.client.force_login(self.user)
        response = self.client.get(
            self.url(self.draft, self.draft.questions.first())
        )
        self.assertEqual(response.status_code, 404)

    def test_the_page_offers_a_hint_once_one_is_earned(self):
        """The page carries only the *strength*; the hint text is fetched on demand, so the
        answer it hides never becomes part of the HTML."""
        self.client.force_login(self.user)
        wrong = self.choice_question.answers.filter(is_correct=False).first()
        self.submit(wrong)

        response = self.client.get(
            reverse("exercises:exercise-detail", args=[self.multiple_choice.pk])
        )

        self.assertContains(response, "data-runner-hint-request")
        self.assertContains(response, 'data-hint-strength="1"')


class HintTests(TestCase):
    """``exercises/hints.py``: a nudge that still hides the answer.

    The strength is chosen from how many times a question was missed, and each step hides
    less — but no hint ever spells the answer out, because the page is built so the answer
    is not in it (``exercises/runner.py``).
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion", is_published=True, order=1, estimated_time=10
        )

        cls.choice = Exercise.objects.create(
            lesson=cls.lesson, title="انتخاب", type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            order=1, is_published=True,
        )
        cls.choice_question = Question.objects.create(exercise=cls.choice, prompt="؟", order=1)
        Answer.objects.create(
            question=cls.choice_question, text="die Abende", is_correct=True, order=1
        )
        Answer.objects.create(
            question=cls.choice_question, text="die Abenden", is_correct=False, order=2
        )

        cls.typed = Exercise.objects.create(
            lesson=cls.lesson, title="نوشتن", type=Exercise.ExerciseType.TRANSLATION,
            order=2, is_published=True,
        )
        cls.typed_question = Question.objects.create(exercise=cls.typed, prompt="؟", order=1)
        Answer.objects.create(question=cls.typed_question, text="Hallo", is_correct=True, order=1)

        cls.scramble = Exercise.objects.create(
            lesson=cls.lesson, title="مرتب کردن", type=Exercise.ExerciseType.SCRAMBLE,
            order=3, is_published=True,
        )
        cls.order_question = Question.objects.create(exercise=cls.scramble, prompt="؟", order=1)
        Answer.objects.create(
            question=cls.order_question, text="Guten Morgen", is_correct=True, order=1
        )

    def test_strength_grows_with_the_misses(self):
        self.assertEqual(hint_strength(0), 0)
        self.assertEqual(hint_strength(1), 1)
        self.assertEqual(hint_strength(2), 2)
        self.assertEqual(hint_strength(9), 2)

    def test_a_masked_word_shows_the_ends_first(self):
        self.assertEqual(masked_text("Hallo", 1), "H _ _ _ o")

    def test_a_stronger_mask_shows_every_second_letter(self):
        self.assertEqual(masked_text("Hallo", 2), "H _ l _ o")

    def test_no_hint_before_the_first_mistake(self):
        self.assertEqual(hint_for(self.choice_question, CHOICE, 0), "")
        self.assertEqual(hint_for(self.typed_question, TEXT, 0), "")

    def test_a_choice_hint_names_a_wrong_option_then_masks_the_correct_one(self):
        weak = hint_for(self.choice_question, CHOICE, 1)
        self.assertIn("die Abenden", weak)         # a wrong option, so the field narrows
        self.assertNotIn("«die Abende»", weak)     # …but the answer is still hidden

        strong = hint_for(self.choice_question, CHOICE, 2)
        self.assertIn("_", strong)                 # masked, never spelled out
        self.assertNotIn("die Abende", strong)

    def test_a_typed_hint_counts_the_letters_then_masks_them(self):
        weak = hint_for(self.typed_question, TEXT, 1)
        self.assertIn("5 حرف", weak)             # "Hallo" has five letters
        self.assertNotIn("Hallo", weak)

        strong = hint_for(self.typed_question, TEXT, 2)
        self.assertEqual(strong, "پاسخ این شکل است: H _ l _ o")

    def test_a_scramble_hint_gives_the_opening_words(self):
        self.assertEqual(
            hint_for(self.order_question, ORDER, 1),
            "جمله با واژهٔ «Guten» شروع می‌شود.",
        )
        self.assertEqual(
            hint_for(self.order_question, ORDER, 2),
            "جمله با «Guten Morgen» شروع می‌شود.",
        )


class WrongCountsTests(ExercisePageTestBase):
    """``exercises/history.wrong_counts``: every miss counts, not only the newest one.

    ``latest_attempts`` keeps one row per question to answer "where does the learner stand
    now"; a hint's strength instead wants the misses added up, so the two rules differ on
    purpose.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = User.objects.create_user(username="sina", password="a-strong-password")
        questions = list(cls.multiple_choice.questions.order_by("order", "pk"))
        cls.first = questions[0]
        cls.second = questions[1]

    def record(self, question, is_correct):
        return ExerciseAttempt.objects.create(
            user=self.user,
            exercise=self.multiple_choice,
            question=question,
            is_correct=is_correct,
            response_text="",
        )

    def test_no_attempts_means_no_counts(self):
        self.assertEqual(wrong_counts(self.user, self.multiple_choice), {})

    def test_every_wrong_attempt_adds_up(self):
        self.record(self.first, False)
        self.record(self.first, False)
        self.record(self.first, True)  # right now, but the two misses still happened
        self.assertEqual(wrong_counts(self.user, self.multiple_choice)[self.first.pk], 2)

    def test_a_question_only_answered_right_has_no_count(self):
        self.record(self.first, True)
        self.assertNotIn(self.first.pk, wrong_counts(self.user, self.multiple_choice))

    def test_another_learners_misses_are_ignored(self):
        other = User.objects.create_user(username="other", password="a-strong-password")
        ExerciseAttempt.objects.create(
            user=other, exercise=self.multiple_choice, question=self.first,
            is_correct=False, response_text="",
        )
        self.assertEqual(wrong_counts(self.user, self.multiple_choice), {})


class EligibilityTests(TestCase):
    """``exercises/eligibility.py``: how far a learner has come decides what they may practise.

    A visitor sees the whole course. A learner who has opened lesson 2 gets lessons 1 and 2 —
    never lesson 3. The rule is shared by the review plan and today's plan, so it is checked
    here once instead of twice.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lessons = []
        for number in range(1, 5):
            lesson = Lesson.objects.create(
                course=cls.course, title=f"Lektion {number}", is_published=True,
                order=number, estimated_time=10,
            )
            cls.lessons.append(lesson)
        cls.draft_lesson = Lesson.objects.create(
            course=cls.course, title="Entwurf", is_published=False, order=9, estimated_time=10
        )

        # One word and one exercise per lesson, so a filtered exercise list is visible.
        cls.words = []
        cls.exercises = []
        for index, lesson in enumerate(cls.lessons):
            word = Word.objects.create(
                word=f"Wort{index}", word_type="OTHER", meaning_fa=f"معنی {index}",
                level=cls.level, is_published=True,
            )
            cls.words.append(word)
            exercise = Exercise.objects.create(
                lesson=lesson, title=f"واژگان {index}",
                type=Exercise.ExerciseType.MULTIPLE_CHOICE, order=1, is_published=True,
            )
            question = Question.objects.create(exercise=exercise, prompt=f"پرسش {index}", order=1)
            Answer.objects.create(question=question, text="richtig", is_correct=True, order=1)
            QuestionTarget.objects.create(question=question, word=word, role="TESTED_ITEM")
            cls.exercises.append(exercise)

        cls.user = User.objects.create_user(username="lernt", password="a-strong-password")

    def test_a_visitor_sees_the_whole_course(self):
        self.assertEqual(
            [lesson.pk for lesson in eligible_lessons(AnonymousUser())],
            [lesson.pk for lesson in self.lessons],
        )

    def test_a_learner_with_no_progress_gets_the_first_lesson(self):
        self.assertEqual(eligible_lessons(self.user), [self.lessons[0]])

    def test_opening_a_lesson_makes_everything_up_to_it_eligible(self):
        LessonProgress.objects.create(
            user=self.user, lesson=self.lessons[2], status=LessonProgress.Status.IN_PROGRESS
        )
        self.assertEqual(
            eligible_lesson_ids(self.user),
            [self.lessons[0].pk, self.lessons[1].pk, self.lessons[2].pk],
        )

    def test_practising_a_lesson_counts_as_reaching_it(self):
        """A learner who answered a lesson's exercise from the list, without ever opening
        the lesson, has still reached it."""
        question = self.exercises[1].questions.first()
        ExerciseAttempt.objects.create(
            user=self.user, exercise=self.exercises[1], question=question,
            is_correct=True, response_text="",
        )
        self.assertIn(self.lessons[1].pk, eligible_lesson_ids(self.user))

    def test_a_draft_lesson_is_never_eligible(self):
        for lesson in self.lessons:
            LessonProgress.objects.create(
                user=self.user, lesson=lesson, status=LessonProgress.Status.COMPLETED
            )
        self.assertNotIn(self.draft_lesson.pk, eligible_lesson_ids(self.user))

    def test_practice_from_words_is_limited_to_eligible_lessons(self):
        LessonProgress.objects.create(
            user=self.user, lesson=self.lessons[1], status=LessonProgress.Status.IN_PROGRESS
        )
        rows = exercises_for_words([self.words[0], self.words[3]], self.user)
        returned = [row["exercise"].pk for row in rows]
        self.assertIn(self.exercises[0].pk, returned)
        self.assertNotIn(self.exercises[3].pk, returned)

    def test_without_a_learner_practice_is_not_limited(self):
        rows = exercises_for_words([self.words[0], self.words[3]])
        returned = [row["exercise"].pk for row in rows]
        self.assertIn(self.exercises[0].pk, returned)
        self.assertIn(self.exercises[3].pk, returned)


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

    def test_a_correct_answer_starts_the_schedule(self):
        self.submit(correct=True)

        row = WordProgress.objects.get(user=self.user, word=self.tested_word)
        self.assertEqual(row.state, WordProgress.State.LEARNING)
        self.assertEqual(row.interval_days, 1)
        self.assertEqual(row.repetitions, 1)
        self.assertEqual(row.consecutive_correct, 1)
        self.assertEqual(row.due_at, row.last_correct_at + timedelta(days=1))

    def test_a_wrong_answer_is_due_tomorrow(self):
        self.submit(correct=False)

        row = WordProgress.objects.get(user=self.user, word=self.tested_word)
        self.assertEqual(row.state, WordProgress.State.LEARNING)
        self.assertEqual(row.interval_days, 1)
        self.assertEqual(row.consecutive_wrong, 1)
        self.assertEqual(row.due_at, row.last_wrong_at + timedelta(days=1))

    def test_a_wrong_answer_after_success_shrinks_the_interval(self):
        self.submit(correct=True)
        self.submit(correct=True)
        grown = WordProgress.objects.get(user=self.user, word=self.tested_word).interval_days
        self.assertGreater(grown, 1)

        self.submit(correct=False)

        row = WordProgress.objects.get(user=self.user, word=self.tested_word)
        self.assertEqual(row.interval_days, 1)
        self.assertEqual(row.due_at, row.last_wrong_at + timedelta(days=1))
        self.assertEqual(row.consecutive_correct, 0)
        self.assertEqual(row.consecutive_wrong, 1)

    def test_a_response_time_reaches_the_schedule(self):
        """A fast correct answer is scheduled further out than a slow one."""
        self.client.force_login(self.user)
        answer = self.question.answers.get(is_correct=True)
        url = reverse("exercises:exercise-submit", args=[self.multiple_choice.pk])

        self.client.post(
            url,
            data=json.dumps({"question": self.question.pk, "answer": answer.pk, "response_time": 1.0}),
            content_type="application/json",
        )
        fast = WordProgress.objects.get(user=self.user, word=self.tested_word).interval_days

        WordProgress.objects.all().delete()

        self.client.post(
            url,
            data=json.dumps({"question": self.question.pk, "answer": answer.pk, "response_time": 30.0}),
            content_type="application/json",
        )
        slow = WordProgress.objects.get(user=self.user, word=self.tested_word).interval_days

        self.assertGreaterEqual(fast, slow)

    def test_a_refused_submission_leaves_the_schedule_untouched(self):
        self.client.force_login(self.user)
        self.submit(correct=True)
        before = WordProgress.objects.get(user=self.user, word=self.tested_word).interval_days

        foreign = self.other_lesson_exercise.questions.first()
        response = self.client.post(
            reverse("exercises:exercise-submit", args=[self.multiple_choice.pk]),
            data=json.dumps({"question": foreign.pk, "answer": foreign.answers.first().pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        after = WordProgress.objects.get(user=self.user, word=self.tested_word).interval_days
        self.assertEqual(before, after)


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
        # stderr is captured too, so the command's warnings do not spill into the test output.
        out = StringIO()
        err = StringIO()
        call_command("seed_a1_exercises", *args, stdout=out, stderr=err)
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

    def test_it_leaves_another_generators_listening_drill_alone(self):
        """The pronunciation and dictation drills are ``LISTENING`` too, and are not this
        command's content: rebuilding by exercise type used to delete them."""
        drill = Exercise.objects.create(
            lesson=self.lesson, title="تمرین تلفظ — تمایز صدا (1)", instruction="",
            type=Exercise.ExerciseType.LISTENING, difficulty=Exercise.Difficulty.EASY,
            order=2, is_published=True,
        )
        question = Question.objects.create(
            exercise=drill, prompt="کدام واژه را شنیدی؟", order=2, audio="words/audio/schon.mp3"
        )
        Answer.objects.create(question=question, text="schon", is_correct=True, order=1)

        self.run_command()

        self.assertTrue(Exercise.objects.filter(pk=drill.pk).exists())
        self.assertEqual(Question.objects.filter(exercise=drill).count(), 1)

    def test_an_attempt_on_another_generators_drill_does_not_block_the_rebuild(self):
        drill = Exercise.objects.create(
            lesson=self.lesson, title="تمرین املا — شنیدن و نوشتن (1)", instruction="",
            type=Exercise.ExerciseType.LISTENING, difficulty=Exercise.Difficulty.EASY,
            order=2, is_published=True,
        )
        question = Question.objects.create(
            exercise=drill, prompt="به فایل گوش کن و بنویس.", order=2,
            audio="words/audio/hallo.mp3",
        )
        user = User.objects.create_user(username="learner", password="test-pass-123")
        ExerciseAttempt.objects.create(
            user=user, exercise=drill, question=question, is_correct=True
        )

        self.run_command()

        # Neither the other generator's drill nor the history on it is this command's to touch.
        self.assertTrue(Exercise.objects.filter(pk=drill.pk).exists())
        self.assertTrue(ExerciseAttempt.objects.filter(exercise=drill).exists())

    # ------------------------------------------------- protecting learner history

    def make_attempt_on_a_listening_exercise(self):
        """Store one attempt on this command's own listening exercise, the way the server would."""
        exercise = Exercise.objects.create(
            lesson=self.lesson, title=seed_a1_exercises.EXERCISE_TITLE, instruction="",
            type=Exercise.ExerciseType.LISTENING, difficulty=Exercise.Difficulty.MEDIUM,
            order=2, is_published=True,
        )
        question = Question.objects.create(exercise=exercise, prompt="؟", order=2)
        answer = Answer.objects.create(
            question=question, text="روز بخیر", is_correct=True, order=1
        )
        user = User.objects.create_user(username="learner", password="test-pass-123")
        return ExerciseAttempt.objects.create(
            user=user, exercise=exercise, question=question, answer=answer, is_correct=True
        )

    def test_it_refuses_to_replace_attempts_without_the_flag(self):
        attempt = self.make_attempt_on_a_listening_exercise()

        with self.assertRaises(CommandError) as caught:
            self.run_command()

        # The refusal names the flag, and nothing was deleted.
        self.assertIn("--yes-replace-history", str(caught.exception))
        self.assertTrue(ExerciseAttempt.objects.filter(pk=attempt.pk).exists())
        self.assertTrue(Exercise.objects.filter(pk=attempt.exercise_id).exists())

    def test_the_flag_allows_replacing_the_history_on_purpose(self):
        attempt = self.make_attempt_on_a_listening_exercise()

        self.run_command("--yes-replace-history")

        self.assertFalse(ExerciseAttempt.objects.filter(pk=attempt.pk).exists())
        self.assertEqual(
            Exercise.objects.filter(type=Exercise.ExerciseType.LISTENING).count(), 1
        )
        # The authored exercise is never part of what gets replaced.
        self.assertTrue(Exercise.objects.filter(pk=self.authored.pk).exists())

    def test_dry_run_reports_the_history_it_would_delete(self):
        attempt = self.make_attempt_on_a_listening_exercise()

        output = self.run_command("--dry-run")

        self.assertIn("would be deleted as well", output)
        self.assertTrue(ExerciseAttempt.objects.filter(pk=attempt.pk).exists())
        self.assertEqual(
            Exercise.objects.filter(type=Exercise.ExerciseType.LISTENING).count(), 1
        )


class ImportA1ExercisesTests(TestCase):
    """``import_a1_exercises``: the file ``export_a1_exercises`` writes is read back."""

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", is_published=True, order=1, estimated_time=10
        )
        cls.word = Word.objects.create(
            word="hallo", word_type="OTHER", meaning_fa="سلام", level=cls.level, is_published=True
        )

    def payload(self):
        return {
            "level": "A1",
            "topic": "test file",
            "exercises": [
                {
                    "lesson_order": 1,
                    "lesson_title": "Lektion 1",
                    "title": "واژگان",
                    "instruction": "گزینهٔ درست را انتخاب کن.",
                    "type": "MULTIPLE_CHOICE",
                    "difficulty": "EASY",
                    "order": 1,
                    "is_published": True,
                    "questions": [
                        {
                            "order": 1,
                            "prompt": "واژهٔ «hallo»؟",
                            "explanation": "درود",
                            "audio": "",
                            "image": "",
                            "targets": [
                                {"role": "TESTED_ITEM", "kind": "word", "ref": "hallo::OTHER"}
                            ],
                            "answers": [
                                {"order": 1, "text": "سلام", "is_correct": True, "match_type": "EXACT"},
                                {"order": 2, "text": "خداحافظ", "is_correct": False, "match_type": "EXACT"},
                            ],
                        }
                    ],
                }
            ],
        }

    def make_payload_file(self, payload):
        directory = tempfile.mkdtemp()
        path = Path(directory) / "a1_exercises.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        return path

    def run_import(self, path):
        call_command("import_a1_exercises", "--data", str(path), stdout=StringIO())

    def test_it_rebuilds_the_exercise_from_the_file(self):
        self.run_import(self.make_payload_file(self.payload()))

        exercise = Exercise.objects.get(lesson=self.lesson, order=1)
        self.assertEqual(exercise.type, "MULTIPLE_CHOICE")
        self.assertEqual(exercise.difficulty, "EASY")
        self.assertTrue(exercise.is_published)

        question = exercise.questions.get(order=1)
        self.assertEqual(question.prompt, "واژهٔ «hallo»؟")
        self.assertEqual(question.explanation, "درود")
        self.assertEqual(question.answers.count(), 2)
        self.assertEqual(question.answers.get(is_correct=True).text, "سلام")

        target = question.targets.get()
        self.assertEqual(target.role, "TESTED_ITEM")
        self.assertEqual(target.word, self.word)

    def test_importing_twice_updates_instead_of_duplicating(self):
        path = self.make_payload_file(self.payload())
        self.run_import(path)
        first_ids = sorted(Exercise.objects.values_list("pk", flat=True))

        self.run_import(path)

        self.assertEqual(Exercise.objects.count(), 1)
        self.assertEqual(Question.objects.count(), 1)
        self.assertEqual(Answer.objects.count(), 2)
        self.assertEqual(QuestionTarget.objects.count(), 1)
        # Matched on the natural key, so the rows were corrected where they stood.
        self.assertEqual(sorted(Exercise.objects.values_list("pk", flat=True)), first_ids)

    def test_a_stored_attempt_survives_an_import(self):
        path = self.make_payload_file(self.payload())
        self.run_import(path)

        question = Question.objects.get()
        answer = Answer.objects.get(question=question, is_correct=True)
        user = User.objects.create_user(username="learner", password="test-pass-123")
        attempt = ExerciseAttempt.objects.create(
            user=user,
            exercise=Exercise.objects.get(),
            question=question,
            answer=answer,
            is_correct=True,
        )

        self.run_import(path)

        attempt.refresh_from_db()
        self.assertTrue(attempt.is_correct)
        self.assertEqual(attempt.answer_id, answer.pk)
        self.assertTrue(Answer.objects.filter(pk=answer.pk).exists())

    def test_it_refuses_a_file_for_a_lesson_that_does_not_exist(self):
        payload = self.payload()
        payload["exercises"][0]["lesson_order"] = 99

        with self.assertRaises(CommandError):
            self.run_import(self.make_payload_file(payload))

    def test_it_refuses_a_file_that_is_not_an_export(self):
        with self.assertRaises(CommandError):
            self.run_import(self.make_payload_file({"level": "A1"}))


class SeedA1WordDrillsTests(TestCase):
    """``seed_a1_word_drills``: every word a lesson introduces becomes answerable.

    Only 138 of the 1,008 words were the tested item of a question, so for the rest
    ``WordProgress`` could never move and the review plan had nothing to offer. These tests
    are about the rules that close that gap: a word that already has an *authored* question
    is left alone, the drills built on stored word facts (article, plural, perfect
    auxiliary) skip nothing because nothing asked before them, and a question is tagged
    with a grammar topic only when it really asks about that rule.
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
        # A review lesson: it introduces no word, so it drills the words it revisits.
        cls.review_lesson = Lesson.objects.create(
            course=cls.course, title="Wiederholung", is_published=True, order=2, estimated_time=10
        )
        # A lesson with no word links at all: neither introduced nor revisited, so no drill.
        cls.empty_lesson = Lesson.objects.create(
            course=cls.course, title="Leer", is_published=True, order=5, estimated_time=10
        )
        # A second lesson that introduces enough words for honest wrong options.
        cls.other_lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 2", is_published=True, order=3, estimated_time=10
        )
        # …and one that does not: three options cannot be found among one word.
        cls.tiny_lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 3", is_published=True, order=4, estimated_time=10
        )

        # The grammar the drills are tagged with, by the exact titles the command looks up.
        cls.artikel = Grammar.objects.create(
            title="Artikel: der, die, das und ein, eine, ein",
            explanation="…", level=cls.level, is_published=True,
        )
        cls.plural = Grammar.objects.create(
            title="Der Plural der Nomen",
            explanation="…", level=cls.level, is_published=True,
        )
        cls.perfekt_haben = Grammar.objects.create(
            title="Perfekt mit „haben“",
            explanation="…", level=cls.level, is_published=True,
        )
        cls.perfekt_sein = Grammar.objects.create(
            title="Perfekt mit „sein“: Reisen in der Vergangenheit",
            explanation="…", level=cls.level, is_published=True,
        )

        # What the lesson teaches, read from the same links the lesson page renders its
        # grammar block from. A lesson is only drilled on the rules it teaches, so without
        # these the whole grammar half of the plan would be (correctly) empty.
        for index, topic in enumerate(
            [cls.artikel, cls.plural, cls.perfekt_haben, cls.perfekt_sein], start=1
        ):
            LessonGrammar.objects.create(lesson=cls.lesson, grammar=topic, order=index)

        cls.hallo = cls.word("hallo", Word.WordType.OTHER, "سلام")
        cls.abend = cls.word(
            "Abend", Word.WordType.NOUN, "عصر، شب", article="der", gender="M",
            plural="die Abende",
        )
        cls.frau = cls.word(
            "Frau", Word.WordType.NOUN, "زن", article="die", gender="F", plural="die Frauen"
        )
        cls.kind = cls.word(
            "Kind", Word.WordType.NOUN, "کودک", article="das", gender="N", plural="die Kinder"
        )
        cls.kommen = cls.word("kommen", Word.WordType.VERB, "آمدن", perfect_auxiliary="SEIN")
        cls.gut = cls.word("gut", Word.WordType.ADJECTIVE, "خوب")
        # A noun nobody gave an article (its plural is known all the same), a verb on the
        # other auxiliary, and a draft: the article question is the one that must skip.
        cls.auto = cls.word("Auto", Word.WordType.NOUN, "ماشین", plural="die Autos")
        cls.gehen = cls.word("gehen", Word.WordType.VERB, "رفتن", perfect_auxiliary="SEIN")
        cls.machen = cls.word("machen", Word.WordType.VERB, "انجام دادن", perfect_auxiliary="HABEN")

        cls.new_words = [
            cls.hallo, cls.abend, cls.frau, cls.kind,
            cls.kommen, cls.gut, cls.auto, cls.gehen, cls.machen,
        ]
        for index, word in enumerate(cls.new_words, start=1):
            LessonWord.objects.create(
                lesson=cls.lesson, word=word, role=LessonWord.Role.NEW, order=index
            )

        cls.draft = cls.word(
            "Entwurf", Word.WordType.NOUN, "پیش‌نویس", article="der", gender="M",
            plural="die Entwürfe", is_published=False,
        )
        LessonWord.objects.create(
            lesson=cls.lesson, word=cls.draft, role=LessonWord.Role.NEW,
            order=len(cls.new_words) + 1,
        )

        # The same word, linked again as review in another lesson. Only the lesson that
        # introduces a word drills it.
        LessonWord.objects.create(
            lesson=cls.review_lesson, word=cls.kommen, role=LessonWord.Role.REVIEW, order=1
        )

        for index, word in enumerate(
            [cls.word("danke", Word.WordType.OTHER, "متشکرم"),
             cls.word("bitte", Word.WordType.OTHER, "خواهش می‌کنم"),
             cls.word("ja", Word.WordType.OTHER, "بله"),
             cls.word("nein", Word.WordType.OTHER, "نه")],
            start=1,
        ):
            LessonWord.objects.create(
                lesson=cls.other_lesson, word=word, role=LessonWord.Role.NEW, order=index
            )

        cls.tschuess = cls.word("tschüss", Word.WordType.OTHER, "خداحافظ")
        LessonWord.objects.create(
            lesson=cls.tiny_lesson, word=cls.tschuess, role=LessonWord.Role.NEW, order=1
        )

        # Authored content, numbered like the live data. It already asks about the meaning
        # of two of the lesson's words: the command must leave those questions alone — and
        # still ask about Abend's article.
        cls.authored = Exercise.objects.create(
            lesson=cls.lesson, title="واژگان — انتخاب معنی", instruction="",
            type=Exercise.ExerciseType.MULTIPLE_CHOICE, difficulty=Exercise.Difficulty.EASY,
            order=1, is_published=True,
        )
        for order, word in enumerate([cls.hallo, cls.abend], start=1):
            question = Question.objects.create(
                exercise=cls.authored, prompt=f"واژهٔ «{word.word}»؟", order=order
            )
            Answer.objects.create(
                question=question, text=word.meaning_fa, is_correct=True, order=1
            )
            QuestionTarget.objects.create(
                question=question, word=word, role=QuestionTarget.Role.TESTED_ITEM
            )

        # An authored *typed* question, like the live «ترجمهٔ … به آلمانی؟» ones: the writing
        # drill asks for the same thing, so it must leave this word's writing question out.
        cls.authored_writing = Exercise.objects.create(
            lesson=cls.lesson, title="ترجمه", instruction="",
            type=Exercise.ExerciseType.TRANSLATION, difficulty=Exercise.Difficulty.EASY,
            order=2, is_published=True,
        )
        cls.authored_typed_question = Question.objects.create(
            exercise=cls.authored_writing, prompt="ترجمهٔ «خوب» به آلمانی؟", order=3
        )
        Answer.objects.create(
            question=cls.authored_typed_question, text="gut", is_correct=True, order=1
        )
        QuestionTarget.objects.create(
            question=cls.authored_typed_question, word=cls.gut,
            role=QuestionTarget.Role.TESTED_ITEM,
        )

    @classmethod
    def word(cls, text, word_type, meaning_fa, article="", gender=None, plural=None,
             perfect_auxiliary=None, is_published=True):
        return Word.objects.create(
            word=text, word_type=word_type, meaning_fa=meaning_fa, article=article,
            gender=gender, plural=plural, perfect_auxiliary=perfect_auxiliary,
            level=cls.level, is_published=is_published,
        )

    def run_command(self, *args):
        # stderr is captured too, so the command's warnings do not spill into the test output.
        out = StringIO()
        err = StringIO()
        call_command("seed_a1_word_drills", *args, stdout=out, stderr=err)
        return out.getvalue()

    def generated(self):
        return Exercise.objects.filter(
            Q(title__startswith="تمرین واژگان")
            | Q(title__startswith="تمرین گرامر")
            | Q(title__startswith="تمرین نوشتن")
        )

    def generated_questions(self):
        return Question.objects.filter(exercise__in=self.generated())

    def meaning_questions(self):
        return Question.objects.filter(exercise__title__startswith="تمرین واژگان — معنی")

    def article_questions(self):
        return Question.objects.filter(exercise__title__startswith="تمرین گرامر — آرتیکل")

    def plural_questions(self):
        return Question.objects.filter(exercise__title__startswith="تمرین گرامر — جمع")

    def perfect_questions(self):
        return Question.objects.filter(exercise__title__startswith="تمرین گرامر — Perfekt")

    def writing_questions(self):
        return Question.objects.filter(exercise__title__startswith="تمرین نوشتن — واژه")

    def questions_about(self, word):
        return Question.objects.filter(
            targets__role=QuestionTarget.Role.TESTED_ITEM, targets__word=word
        )

    def question_word(self, question):
        """The word a question is about."""
        return question.targets.get(role=QuestionTarget.Role.TESTED_ITEM).word

    def topics_of(self, questions):
        """The grammar topics a group of questions is tagged with."""
        topics = set()
        for question in questions:
            topics.add(question.targets.get(role=QuestionTarget.Role.GRAMMAR).grammar)
        return topics

    def words_asked(self, questions):
        """The words a group of questions is about.

        The role filter matters: a grammar question has two targets, and the join would
        otherwise also walk the grammar row, whose ``word`` is empty.
        """
        return set(
            questions.filter(targets__role=QuestionTarget.Role.TESTED_ITEM)
            .values_list("targets__word__word", flat=True)
        )

    def test_every_word_a_lesson_introduces_becomes_answerable(self):
        self.run_command()
        for word in self.new_words:
            self.assertGreater(self.questions_about(word).count(), 0, word.word)

    def test_the_meaning_questions_cover_exactly_the_words_nothing_asked_about(self):
        self.run_command()
        asked = self.words_asked(self.meaning_questions().filter(exercise__lesson=self.lesson))
        # `gut` has an authored question of its own (a typed one), so it is left alone too.
        self.assertEqual(asked, {"Frau", "Kind", "kommen", "Auto", "gehen", "machen"})

    def test_a_word_that_already_has_a_question_gets_no_meaning_question(self):
        self.run_command()
        # The authored meaning question, and the writing question it never had.
        self.assertEqual(self.questions_about(self.hallo).count(), 2)
        self.assertFalse(
            self.questions_about(self.hallo)
            .filter(exercise__title__startswith="تمرین واژگان")
            .exists()
        )

    def test_a_noun_whose_meaning_is_asked_about_still_gets_its_article_question(self):
        self.run_command()
        # The authored meaning question, the article question nothing else asked, the plural
        # question, and the writing question.
        self.assertEqual(self.questions_about(self.abend).count(), 4)
        self.assertEqual(self.article_questions().filter(targets__word=self.abend).count(), 1)

    def test_every_noun_with_an_article_gets_one_article_question(self):
        self.run_command()
        self.assertEqual(self.words_asked(self.article_questions()), {"Abend", "Frau", "Kind"})

    def test_the_article_options_are_der_die_das_with_the_words_own_article_right(self):
        self.run_command()
        for question in self.article_questions():
            options = sorted(question.answers.values_list("text", flat=True))
            self.assertEqual(options, ["das", "der", "die"])
            self.assertEqual(question.answers.filter(is_correct=True).count(), 1)
            self.assertEqual(
                question.answers.get(is_correct=True).text,
                self.question_word(question).article,
            )

    def test_a_noun_without_an_article_is_not_asked_about_its_article(self):
        self.run_command()
        # Meaning, plural and writing, and no article question.
        self.assertEqual(self.questions_about(self.auto).count(), 3)
        self.assertFalse(self.article_questions().filter(targets__word=self.auto).exists())

    def test_every_meaning_question_has_four_options_and_one_right_answer(self):
        self.run_command()
        for question in self.meaning_questions():
            self.assertEqual(question.answers.count(), 4)
            self.assertEqual(question.answers.filter(is_correct=True).count(), 1)

    def test_the_correct_meaning_is_the_word_and_appears_only_once(self):
        self.run_command()
        for question in self.meaning_questions():
            correct = question.answers.get(is_correct=True).text
            self.assertEqual(correct, question.targets.get().word.meaning_fa)
            self.assertEqual(question.answers.filter(text=correct).count(), 1)

    def test_one_lessons_wrong_meanings_are_not_the_same_set_every_time(self):
        """Reading the pool from the front would hand every question the same three wrong
        meanings, which a learner can learn to pattern-match instead of learning the word."""
        self.run_command()
        seen = set()
        for question in self.meaning_questions():
            wrong = frozenset(
                question.answers.filter(is_correct=False).values_list("text", flat=True)
            )
            seen.add(wrong)
        self.assertGreater(len(seen), 1)

    def test_every_choice_question_points_at_the_word_it_names(self):
        self.run_command()
        for question in self.generated_questions().exclude(
            exercise__title__startswith="تمرین نوشتن"
        ).exclude(exercise__title__contains="وارون"):
            target = question.targets.get(role=QuestionTarget.Role.TESTED_ITEM)
            self.assertIn(target.word.word, question.prompt)

    def test_the_new_questions_continue_the_lessons_numbering(self):
        self.run_command()
        orders = sorted(
            Question.objects.filter(exercise__lesson=self.lesson).values_list("order", flat=True)
        )
        # The three authored questions are orders 1..3, so the generated 24 run 4..27.
        self.assertEqual(orders, list(range(1, 28)))

    def test_a_review_lesson_with_too_few_words_writes_nothing(self):
        """A turned-around drill still needs three honest wrong options, and one reviewed word
        cannot supply them; the lesson is skipped rather than asked about with repeated
        options."""
        self.run_command()
        self.assertFalse(self.generated().filter(lesson=self.review_lesson).exists())

    def test_a_review_lesson_asks_its_words_the_other_way(self):
        """The words a review lesson revisits already have their forward drills from the
        lesson that introduced them, so the review asks the turned-around question instead —
        never the same question a second time."""
        for index, word in enumerate(
            [self.abend, self.frau, self.kind, self.kommen, self.gehen, self.machen], start=1
        ):
            # ``kommen`` is already reviewed by the review lesson in the fixture.
            LessonWord.objects.get_or_create(
                lesson=self.review_lesson,
                word=word,
                defaults={"role": LessonWord.Role.REVIEW, "order": index},
            )

        self.run_command()

        review = self.generated().filter(lesson=self.review_lesson)
        self.assertTrue(review.exists())
        # Only the turned-around titles are written for a review lesson.
        self.assertFalse(review.filter(title__startswith="تمرین واژگان — معنی (").exists())
        self.assertTrue(review.filter(title__startswith="تمرین واژگان — معنی وارون").exists())

        reverse_meaning = Question.objects.filter(
            exercise__lesson=self.review_lesson,
            exercise__title__startswith="تمرین واژگان — معنی وارون",
        )
        self.assertTrue(reverse_meaning.exists())
        for question in reverse_meaning:
            target = question.targets.get(role=QuestionTarget.Role.TESTED_ITEM).word
            correct = question.answers.get(is_correct=True).text
            # The answer is the German word and the prompt is its Persian meaning: the
            # opposite of the forward drill.
            self.assertEqual(correct, target.word)
            self.assertIn(target.meaning_fa, question.prompt)
            self.assertEqual(question.answers.count(), 4)

    def test_a_lesson_that_neither_introduces_nor_revisits_a_word_gets_no_exercise(self):
        self.run_command()
        self.assertFalse(self.generated().filter(lesson=self.empty_lesson).exists())

    def test_a_lesson_with_too_few_words_for_wrong_options_gets_no_choice_drill(self):
        """One word cannot supply three honest wrong ideas, so the lesson is skipped rather
        than asked about — but writing needs no distractors, so it still gets that."""
        self.run_command()
        self.assertFalse(
            self.generated()
            .filter(Q(lesson=self.tiny_lesson) & Q(title__startswith="تمرین گرامر"))
            .exists()
        )
        self.assertFalse(
            self.generated()
            .filter(Q(lesson=self.tiny_lesson) & Q(title__startswith="تمرین واژگان"))
            .exists()
        )
        self.assertEqual(self.generated().filter(lesson=self.tiny_lesson).count(), 1)

    def test_a_draft_word_is_not_asked_about(self):
        self.run_command()
        self.assertFalse(self.questions_about(self.draft).exists())

    def test_rerunning_replaces_instead_of_duplicating(self):
        self.run_command()
        first_ids = sorted(self.generated().values_list("id", flat=True))

        self.run_command()

        second_ids = sorted(self.generated().values_list("id", flat=True))
        self.assertEqual(len(second_ids), len(first_ids))
        self.assertNotEqual(first_ids, second_ids)

    def test_it_never_touches_the_authored_exercises(self):
        self.run_command()
        self.assertTrue(Exercise.objects.filter(pk=self.authored.pk).exists())
        self.assertEqual(Question.objects.filter(exercise=self.authored).count(), 2)
        self.assertEqual(Answer.objects.filter(question__exercise=self.authored).count(), 2)

    def test_dry_run_writes_nothing(self):
        output = self.run_command("--dry-run")
        self.assertIn("Dry run", output)
        self.assertFalse(self.generated().exists())

    def test_the_lesson_option_limits_the_run_to_one_lesson(self):
        self.run_command("--lesson", str(self.other_lesson.pk))
        lessons = set(self.generated().values_list("lesson_id", flat=True))
        self.assertEqual(lessons, {self.other_lesson.pk})

    def test_batch_only_changes_how_the_questions_are_split(self):
        self.run_command()
        questions = self.generated_questions().count()
        exercises = self.generated().count()

        self.run_command("--batch", "2")

        self.assertEqual(self.generated_questions().count(), questions)
        self.assertGreater(self.generated().count(), exercises)
        for exercise in self.generated():
            self.assertLessEqual(exercise.questions.count(), 2)

    def test_a_batch_below_one_is_refused(self):
        with self.assertRaises(CommandError):
            self.run_command("--batch", "0")

    def test_it_refuses_while_a_generated_drill_has_attempts(self):
        self.run_command()
        exercise = self.generated().first()
        user = User.objects.create_user(username="learner", password="test-pass-123")
        ExerciseAttempt.objects.create(
            user=user, exercise=exercise, question=exercise.questions.first(), is_correct=True
        )

        with self.assertRaises(CommandError):
            self.run_command()

    def test_yes_replace_history_deletes_those_attempts_on_purpose(self):
        self.run_command()
        exercise = self.generated().first()
        user = User.objects.create_user(username="learner", password="test-pass-123")
        ExerciseAttempt.objects.create(
            user=user, exercise=exercise, question=exercise.questions.first(), is_correct=True
        )

        self.run_command("--yes-replace-history")

        self.assertEqual(ExerciseAttempt.objects.count(), 0)
        self.assertTrue(self.generated().exists())

    def test_an_attempt_on_an_authored_exercise_neither_blocks_nor_goes_away(self):
        question = self.authored.questions.first()
        user = User.objects.create_user(username="learner", password="test-pass-123")
        attempt = ExerciseAttempt.objects.create(
            user=user, exercise=self.authored, question=question, is_correct=True
        )

        self.run_command()

        self.assertTrue(ExerciseAttempt.objects.filter(pk=attempt.pk).exists())
        self.assertTrue(self.generated().exists())

    def test_every_noun_with_a_plural_gets_one_plural_question(self):
        self.run_command()
        self.assertEqual(self.words_asked(self.plural_questions()), {"Abend", "Frau", "Kind", "Auto"})

    def test_the_plural_options_are_four_with_the_words_own_plural_right(self):
        self.run_command()
        for question in self.plural_questions():
            self.assertEqual(question.answers.count(), 4)
            self.assertEqual(question.answers.filter(is_correct=True).count(), 1)
            word = self.question_word(question)
            self.assertEqual(question.answers.get(is_correct=True).text, word.plural)
            self.assertIn(word.word, question.prompt)

    def test_every_verb_with_an_auxiliary_gets_one_perfekt_question(self):
        self.run_command()
        self.assertEqual(self.words_asked(self.perfect_questions()), {"kommen", "gehen", "machen"})

    def test_the_perfekt_options_are_haben_and_sein(self):
        self.run_command()
        for question in self.perfect_questions():
            options = sorted(question.answers.values_list("text", flat=True))
            self.assertEqual(options, ["haben", "sein"])
            self.assertEqual(question.answers.filter(is_correct=True).count(), 1)
            word = self.question_word(question)
            self.assertEqual(
                question.answers.get(is_correct=True).text, word.perfect_auxiliary.lower()
            )

    def test_a_grammar_drill_is_tagged_with_the_topic_it_really_tests(self):
        self.run_command()
        self.assertEqual(self.topics_of(self.article_questions()), {self.artikel})
        self.assertEqual(self.topics_of(self.plural_questions()), {self.plural})

    def test_the_perfekt_question_is_tagged_with_the_rule_its_answer_belongs_to(self):
        self.run_command()
        sein_words = self.words_asked(
            self.perfect_questions().filter(targets__grammar=self.perfekt_sein)
        )
        haben_words = self.words_asked(
            self.perfect_questions().filter(targets__grammar=self.perfekt_haben)
        )
        self.assertEqual(sein_words, {"kommen", "gehen"})
        self.assertEqual(haben_words, {"machen"})

    def test_a_meaning_question_carries_no_grammar_target(self):
        """A meaning question tests a word and no rule, so it must not claim one: a guessed
        tag would count a vocabulary mistake as a grammar mistake."""
        self.run_command()
        for question in self.meaning_questions():
            self.assertEqual(question.targets.count(), 1)
            self.assertFalse(
                question.targets.filter(role=QuestionTarget.Role.GRAMMAR).exists()
            )

    def test_every_grammar_question_carries_exactly_one_grammar_topic(self):
        self.run_command()
        for question in Question.objects.filter(exercise__title__startswith="تمرین گرامر"):
            targets = question.targets.filter(role=QuestionTarget.Role.GRAMMAR)
            self.assertEqual(targets.count(), 1)
            self.assertIsNotNone(targets.get().grammar)

    def test_neither_word_nor_writing_drills_carry_a_grammar_target(self):
        self.run_command()
        self.assertFalse(
            QuestionTarget.objects.filter(
                role=QuestionTarget.Role.GRAMMAR,
            )
            .filter(
                Q(question__exercise__title__startswith="تمرین واژگان")
                | Q(question__exercise__title__startswith="تمرین نوشتن")
            )
            .exists()
        )

    def test_every_word_gets_a_typed_question(self):
        """Recognition is not production: picking an answer out of four options does not
        prove the learner can write the word."""
        self.run_command()
        self.assertEqual(
            self.words_asked(self.writing_questions().filter(exercise__lesson=self.lesson)),
            {"hallo", "Abend", "Frau", "Kind", "kommen", "Auto", "gehen", "machen"},
        )

    def test_a_word_that_already_has_a_typed_question_gets_no_writing_question(self):
        self.run_command()
        # `gut` has the authored typed question, so only that one asks for typing — and
        # because it already has a question at all, it gets no meaning question either.
        self.assertFalse(self.writing_questions().filter(targets__word=self.gut).exists())
        self.assertEqual(self.questions_about(self.gut).count(), 1)

    def test_a_writing_question_is_a_typed_translation_with_one_answer(self):
        self.run_command()
        for question in self.writing_questions():
            self.assertEqual(question.exercise.type, Exercise.ExerciseType.TRANSLATION)
            # One answer row is exactly what makes the runner ask for typing.
            self.assertEqual(question.answers.count(), 1)
            answer = question.answers.get()
            self.assertTrue(answer.is_correct)
            self.assertEqual(answer.text, self.question_word(question).word)

    def test_a_writing_question_shows_the_meaning_not_the_german_word(self):
        self.run_command()
        for question in self.writing_questions():
            word = self.question_word(question)
            self.assertIn(word.meaning_fa, question.prompt)
            self.assertNotIn(word.word, question.prompt)

    def test_the_two_answer_shapes_do_not_mix(self):
        """The runner decides typed-vs-choice from the answer rows alone, so a choice
        question must have several and a typed one exactly one."""
        self.run_command()
        for question in self.generated_questions():
            if question.exercise.type == Exercise.ExerciseType.TRANSLATION:
                self.assertEqual(question.answers.count(), 1)
            else:
                self.assertGreater(question.answers.count(), 1)

    def test_a_plural_or_article_question_still_moves_the_words_own_counters(self):
        """The grammar drills are about a word too, so they keep a ``TESTED_ITEM`` target:
        a learner who misses ``die Abende`` has missed a fact about ``Abend``."""
        self.run_command()
        for question in self.generated_questions():
            self.assertTrue(
                question.targets.filter(role=QuestionTarget.Role.TESTED_ITEM).exists()
            )

    def test_a_generated_drill_does_not_count_as_an_authored_question(self):
        """A word with a dictation drill has still not been asked what it means.

        The dictation drills tag the word they play — a miss has to be reviewable — so
        without this the word drills would read "this word already has a question" and
        quietly stop writing meaning questions for nearly every word.
        """
        # Order 3: the fixture's own two authored exercises already use 1 and 2.
        exercise = Exercise.objects.create(
            lesson=self.lesson, title="تمرین املا — شنیدن و نوشتن (1)", instruction="",
            type=Exercise.ExerciseType.LISTENING, difficulty=Exercise.Difficulty.EASY,
            order=3, is_published=True,
        )
        question = Question.objects.create(
            exercise=exercise, prompt="به فایل گوش کن و بنویس.", order=4,
            audio="words/audio/kind.mp3",
        )
        Answer.objects.create(question=question, text=self.kind.word, is_correct=True, order=1)
        QuestionTarget.objects.create(
            question=question, word=self.kind, role=QuestionTarget.Role.TESTED_ITEM
        )

        self.run_command()

        meaning = Question.objects.filter(
            exercise__title__startswith="تمرین واژگان — معنی", targets__word=self.kind
        )
        self.assertTrue(meaning.exists())

    def test_it_refuses_when_a_grammar_topic_is_not_in_the_database(self):
        """A tag naming a rule the content does not teach would put an invented number on
        the readiness page, so the command stops instead of writing the word drills alone."""
        self.perfekt_sein.delete()

        with self.assertRaises(CommandError):
            self.run_command()

        self.assertFalse(self.generated().exists())

    def test_a_lesson_is_drilled_on_the_rules_it_teaches(self):
        """Lesson 1 links all four topics, so it gets both grammar drills and the Perfekt one."""
        self.run_command()

        self.assertTrue(self.article_questions().exists())
        self.assertTrue(self.plural_questions().exists())
        self.assertTrue(self.perfect_questions().exists())

    def test_a_lesson_that_teaches_no_rule_is_not_asked_about_one(self):
        """The whole point of the rule: practice matches teaching.

        ``other_lesson`` teaches no grammar at all (it has no ``LessonGrammar`` link), so
        asking its words for their article or their Perfekt auxiliary would be a question
        about a rule the learner was never taught in this course at that point. The words
        themselves are still drilled, in both directions.
        """
        self.run_command()

        self.assertFalse(self.generated().filter(lesson=self.other_lesson).filter(
            title__startswith="تمرین گرامر"
        ).exists())
        self.assertTrue(self.generated().filter(lesson=self.other_lesson).filter(
            title__startswith="تمرین واژگان"
        ).exists())
        self.assertTrue(self.generated().filter(lesson=self.other_lesson).filter(
            title__startswith="تمرین نوشتن"
        ).exists())

    def test_a_review_lesson_reviews_the_rules_its_own_course_already_taught(self):
        """Lesson 12 revisits A1.1, where articles and the plural were taught in lesson 4.

        Built in its own course, because the rules a review lesson may be asked about are
        exactly the rules the lessons *before it* taught.
        """
        level = LanguageLevel.objects.create(level="A2", title="A2", order=2)
        course = Course.objects.create(language_level=level, title="Kurs A2", is_published=True)
        teaching = Lesson.objects.create(
            course=course, title="Artikel und Plural", is_published=True, order=1,
            estimated_time=10,
        )
        review = Lesson.objects.create(
            course=course, title="Wiederholung", is_published=True, order=2, estimated_time=10
        )

        # The first lesson of this course teaches the two rules the review lesson must
        # later ask about, and introduces the nouns it asks about them with.
        LessonGrammar.objects.create(lesson=teaching, grammar=self.artikel, order=1)
        LessonGrammar.objects.create(lesson=teaching, grammar=self.plural, order=2)

        nouns = [self.abend, self.frau, self.kind, self.auto]
        for index, noun in enumerate(nouns, start=1):
            LessonWord.objects.create(
                lesson=teaching, word=noun, role=LessonWord.Role.NEW, order=index
            )
            LessonWord.objects.create(
                lesson=review, word=noun, role=LessonWord.Role.REVIEW, order=index
            )

        self.run_command()

        drills = self.generated().filter(lesson=review)

        self.assertTrue(drills.filter(title__startswith="تمرین گرامر — آرتیکل وارون").exists())
        self.assertTrue(drills.filter(title__startswith="تمرین گرامر — جمع وارون").exists())

    def test_a_review_lesson_is_not_asked_about_a_rule_it_has_not_reached(self):
        """A review lesson reviews what came before it, so a rule the course reaches later
        is not asked — and the rules of another course do not count as this course's
        teaching either."""
        level = LanguageLevel.objects.create(level="A2", title="A2", order=2)
        course = Course.objects.create(language_level=level, title="Kurs A2", is_published=True)
        opening = Lesson.objects.create(
            course=course, title="Erste Lektion", is_published=True, order=1, estimated_time=10
        )
        later = Lesson.objects.create(
            course=course, title="Spätere Lektion", is_published=True, order=2, estimated_time=10
        )

        # The opening lesson only revisits two words, so it is a review lesson…
        LessonWord.objects.create(
            lesson=opening, word=self.kommen, role=LessonWord.Role.REVIEW, order=1
        )
        LessonWord.objects.create(
            lesson=opening, word=self.frau, role=LessonWord.Role.REVIEW, order=2
        )

        # …and the lesson after it is the first one in this course to teach the Perfekt.
        LessonGrammar.objects.create(lesson=later, grammar=self.perfekt_haben, order=1)
        LessonWord.objects.create(
            lesson=later, word=self.machen, role=LessonWord.Role.NEW, order=1
        )
        LessonWord.objects.create(
            lesson=later, word=self.kommen, role=LessonWord.Role.NEW, order=2
        )
        LessonWord.objects.create(
            lesson=later, word=self.abend, role=LessonWord.Role.NEW, order=3
        )
        LessonWord.objects.create(
            lesson=later, word=self.kind, role=LessonWord.Role.NEW, order=4
        )

        self.run_command()

        self.assertFalse(
            self.generated().filter(lesson=opening, title__startswith="تمرین گرامر").exists()
        )
        self.assertTrue(
            self.generated().filter(lesson=later, title__startswith="تمرین گرامر").exists()
        )


class SeedA1DictationDrillsTests(TestCase):
    """``seed_a1_dictation_drills``: hear a word, write it.

    Every audio question in the product asks the learner to *choose*; none asks them to write
    what they heard, which is the one exercise that trains German spelling by ear (``ü``,
    ``ö``, ``ä``, ``ß``, ``ie`` against ``ei``). These tests pin the rules that keep it
    honest: the question is answered by typing (exactly one answer row), it plays the word's
    own recording, a word with no recording is skipped rather than asked in silence — and,
    unlike the sound-pair drill, it **does** carry a target, because the learner heard exactly
    one word and spelling it is a fact about that word.
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
        # Introduces no word, so it dictates the word it revisits.
        cls.review_lesson = Lesson.objects.create(
            course=cls.course, title="Wiederholung", is_published=True, order=2, estimated_time=10
        )
        # Every word here has no recording, so there is nothing to dictate.
        cls.quiet_lesson = Lesson.objects.create(
            course=cls.course, title="Leer", is_published=True, order=3, estimated_time=10
        )
        # A draft lesson: never reached.
        cls.draft_lesson = Lesson.objects.create(
            course=cls.course, title="Entwurf", is_published=False, order=4, estimated_time=10
        )

        cls.hallo = cls.word("hallo", "سلام", audio="words/audio/hallo.mp3")
        cls.danke = cls.word("danke", "متشکرم", audio="words/audio/danke.mp3")
        cls.tschuess = cls.word("tschüss", "خداحافظ", audio="words/audio/tschuess.mp3")
        # No recording: a question about it would be silent.
        cls.dann = cls.word("dann", "بعداً")

        for index, word in enumerate([cls.hallo, cls.danke, cls.tschuess, cls.dann], start=1):
            LessonWord.objects.create(
                lesson=cls.lesson, word=word, role=LessonWord.Role.NEW, order=index
            )

        cls.draft = cls.word(
            "Entwurf", "پیش‌نویس", audio="words/audio/entwurf.mp3", is_published=False
        )
        LessonWord.objects.create(
            lesson=cls.lesson, word=cls.draft, role=LessonWord.Role.NEW, order=5
        )

        # `lieben` is taught by no lesson; only the review lesson revisits it.
        cls.lieben = cls.word("lieben", "دوست داشتن", audio="words/audio/lieben.mp3")
        LessonWord.objects.create(
            lesson=cls.review_lesson, word=cls.lieben, role=LessonWord.Role.REVIEW, order=1
        )

        # Recorded, but its lesson is not published: nothing may be built there.
        cls.verloren = cls.word("verloren", "گمشده", audio="words/audio/verloren.mp3")
        LessonWord.objects.create(
            lesson=cls.draft_lesson, word=cls.verloren, role=LessonWord.Role.NEW, order=1
        )

        # A published lesson whose only word is silent.
        cls.still = cls.word("still", "ساکت")
        LessonWord.objects.create(
            lesson=cls.quiet_lesson, word=cls.still, role=LessonWord.Role.NEW, order=1
        )

        # Authored content, numbered like the live data. The command must never touch it.
        cls.authored = Exercise.objects.create(
            lesson=cls.lesson, title="واژگان — انتخاب معنی", instruction="",
            type=Exercise.ExerciseType.MULTIPLE_CHOICE, difficulty=Exercise.Difficulty.EASY,
            order=1, is_published=True,
        )
        authored_question = Question.objects.create(
            exercise=cls.authored, prompt="واژهٔ «hallo»؟", order=1
        )
        Answer.objects.create(
            question=authored_question, text="سلام", is_correct=True, order=1
        )

    @classmethod
    def word(cls, text, meaning_fa, audio="", is_published=True):
        return Word.objects.create(
            word=text, word_type=Word.WordType.OTHER, meaning_fa=meaning_fa,
            level=cls.level, is_published=is_published, audio=audio,
        )

    def run_command(self, *args):
        out = StringIO()
        err = StringIO()
        call_command("seed_a1_dictation_drills", *args, stdout=out, stderr=err)
        return out.getvalue()

    def generated(self):
        return Exercise.objects.filter(title__startswith="تمرین املا")

    def generated_questions(self):
        return Question.objects.filter(exercise__in=self.generated()).order_by("order")

    def question_for(self, text):
        """The generated question whose played word is ``text``.

        Read from the accepted answer rather than from the file name: the recordings are
        named with transliterated spellings (``tschuess.mp3``), and the word is what the
        question is about.
        """
        for question in self.generated_questions():
            if question.answers.get(is_correct=True).text == text:
                return question
        return None

    def submit(self, question, response_text):
        return self.client.post(
            reverse("exercises:exercise-submit", args=[question.exercise_id]),
            data=json.dumps({"question": question.pk, "response_text": response_text}),
            content_type="application/json",
        )

    # ------------------------------------------------------------------- shape

    def test_a_word_becomes_a_question_answered_by_typing(self):
        self.run_command()

        question = self.question_for("hallo")
        self.assertIsNotNone(question)
        # One answer row is exactly what makes the runner ask for typing instead of options.
        self.assertEqual(question.answers.count(), 1)
        self.assertTrue(question.answers.first().is_correct)

        row = None
        for item in build_runner(question.exercise):
            if item["id"] == question.pk:
                row = item
        self.assertEqual(row["kind"], "text")
        self.assertEqual(row["options"], [])

    def test_the_accepted_answer_is_the_word_itself(self):
        self.run_command()

        self.assertEqual(self.question_for("hallo").answers.get(is_correct=True).text, "hallo")

    def test_the_question_plays_the_recording_the_word_already_has(self):
        """Nothing is generated and nothing is copied: the word's own file is pointed at."""
        self.run_command()

        self.assertEqual(self.question_for("hallo").audio.name, "words/audio/hallo.mp3")

    def test_the_prompt_asks_the_learner_to_write_what_was_played(self):
        self.run_command()

        prompt = self.question_for("hallo").prompt
        self.assertIn("گوش کن", prompt)
        self.assertIn("بنویس", prompt)

    def test_every_question_targets_the_word_it_plays(self):
        """Unlike the sound-pair drill, a dictation is about exactly one word."""
        self.run_command()

        self.assertTrue(self.generated_questions().exists())
        for question in self.generated_questions():
            target = question.targets.get()
            self.assertEqual(target.role, QuestionTarget.Role.TESTED_ITEM)
            self.assertEqual(target.word.word, question.answers.get(is_correct=True).text)

    def test_the_exercises_are_published_listening_content(self):
        self.run_command()

        for exercise in self.generated():
            self.assertEqual(exercise.type, Exercise.ExerciseType.LISTENING)
            self.assertTrue(exercise.is_published)

    def test_a_wrong_typing_moves_that_words_progress(self):
        """The whole point of the target: a miss by ear has to be reviewable later."""
        self.run_command()
        question = self.question_for("hallo")
        user = User.objects.create_user(username="learner", password="test-pass-123")
        self.client.force_login(user)

        body = self.submit(question, "halo").json()

        self.assertFalse(body["correct"])
        self.assertTrue(body["recorded"])
        progress = WordProgress.objects.get(user=user, word=self.hallo)
        self.assertEqual(progress.attempt_count, 1)
        self.assertEqual(progress.wrong_count, 1)
        self.assertEqual(progress.correct_count, 0)

    def test_a_correct_typing_is_forgiving_about_case_and_punctuation(self):
        self.run_command()
        question = self.question_for("tschüss")
        user = User.objects.create_user(username="learner", password="test-pass-123")
        self.client.force_login(user)

        body = self.submit(question, "  TSCHÜSS!  ").json()

        self.assertTrue(body["correct"])
        progress = WordProgress.objects.get(user=user, word=self.tschuess)
        self.assertEqual(progress.correct_count, 1)

    # ------------------------------------------------------------------- scope

    def test_a_word_with_no_recording_is_not_asked(self):
        self.run_command()

        self.assertIsNone(self.question_for("dann"))
        played = Question.objects.filter(exercise__in=self.generated(), audio__contains="dann")
        self.assertFalse(played.exists())

    def test_a_draft_word_is_never_asked(self):
        self.run_command()

        self.assertIsNone(self.question_for("Entwurf"))

    def test_a_draft_lesson_is_never_dictated(self):
        self.run_command()

        self.assertFalse(self.generated().filter(lesson=self.draft_lesson).exists())
        self.assertIsNone(self.question_for("verloren"))

    def test_a_lesson_whose_words_are_all_silent_gets_no_exercise(self):
        self.run_command()

        self.assertFalse(self.generated().filter(lesson=self.quiet_lesson).exists())

    def test_a_review_lesson_gets_no_dictation_of_its_own(self):
        """A review lesson introduces no word, and the words it revisits were dictated when
        they were introduced. A second dictation would be the same question twice, so it is
        left out; the review lesson's practice is the turned-around word drills instead."""
        self.run_command()

        self.assertFalse(self.generated().filter(lesson=self.review_lesson).exists())

    def test_the_same_spelling_is_asked_once_per_lesson(self):
        """`sie` and `Sie` sound identical, and grading ignores case: one question, not two."""
        lowercase = self.word("sie", "او", audio="words/audio/sie.mp3")
        formal = self.word("Sie", "شما", audio="words/audio/sie-formal.mp3")
        for index, word in enumerate([lowercase, formal], start=10):
            LessonWord.objects.create(
                lesson=self.lesson, word=word, role=LessonWord.Role.NEW, order=index
            )

        self.run_command("--lesson", str(self.lesson.pk))

        asked = Question.objects.filter(
            exercise__in=self.generated(), audio__startswith="words/audio/sie"
        )
        self.assertEqual(asked.count(), 1)

    # ------------------------------------------------------------- safe rebuild

    def test_it_never_touches_the_authored_exercises(self):
        self.run_command()

        self.assertTrue(Exercise.objects.filter(pk=self.authored.pk).exists())
        self.assertTrue(Answer.objects.filter(question__exercise=self.authored).exists())

    def test_the_new_questions_continue_the_lessons_numbering(self):
        self.run_command()

        orders = sorted(
            Question.objects.filter(exercise__lesson=self.lesson).values_list("order", flat=True)
        )

        # The authored question is order 1, so the generated ones carry on without a gap.
        self.assertEqual(orders, list(range(1, len(orders) + 1)))

    def test_rerunning_replaces_instead_of_duplicating(self):
        self.run_command()
        first_ids = sorted(self.generated().values_list("id", flat=True))
        question_total = self.generated_questions().count()

        self.run_command()

        second_ids = sorted(self.generated().values_list("id", flat=True))
        self.assertEqual(len(second_ids), len(first_ids))
        self.assertNotEqual(first_ids, second_ids)
        self.assertEqual(self.generated_questions().count(), question_total)

    def test_dry_run_writes_nothing(self):
        output = self.run_command("--dry-run")

        self.assertIn("Dry run", output)
        self.assertFalse(self.generated().exists())

    def test_the_lesson_flag_limits_what_is_written(self):
        self.run_command("--lesson", str(self.lesson.pk))

        self.assertTrue(self.generated().filter(lesson=self.lesson).exists())
        self.assertFalse(self.generated().exclude(lesson=self.lesson).exists())

    def test_batch_only_changes_how_the_questions_are_split(self):
        self.run_command("--batch", "1")
        many = self.generated().count()
        questions = self.generated_questions().count()

        self.run_command("--batch", "20")

        self.assertLess(self.generated().count(), many)
        self.assertEqual(self.generated_questions().count(), questions)

    def test_a_batch_below_one_is_refused(self):
        with self.assertRaises(CommandError):
            self.run_command("--batch", "0")

    def test_it_refuses_while_a_dictation_drill_has_attempts(self):
        self.run_command()
        exercise = self.generated().first()
        user = User.objects.create_user(username="learner", password="test-pass-123")
        ExerciseAttempt.objects.create(
            user=user, exercise=exercise, question=exercise.questions.first(), is_correct=True
        )

        with self.assertRaises(CommandError):
            self.run_command()

    def test_yes_replace_history_deletes_those_attempts_on_purpose(self):
        self.run_command()
        exercise = self.generated().first()
        user = User.objects.create_user(username="learner", password="test-pass-123")
        ExerciseAttempt.objects.create(
            user=user, exercise=exercise, question=exercise.questions.first(), is_correct=True
        )

        self.run_command("--yes-replace-history")

        self.assertEqual(ExerciseAttempt.objects.count(), 0)
        self.assertTrue(self.generated().exists())


class GeneratedContentTests(TestCase):
    """``exercises/generated.py``: the one place that decides what a command wrote.

    Two rules read it, and both fail silently if it is incomplete: the word drills must not
    treat a generated drill as an authored question (the dictation drills would cost them
    their meaning questions), and the listening generator must not rebuild by exercise type
    (it would delete the pronunciation and dictation drills).
    """

    def test_every_generator_prefix_is_declared_as_generated(self):
        prefixes = []
        for prefix in seed_a1_word_drills.TITLE_PREFIXES:
            prefixes.append(prefix)
        prefixes.append(seed_a1_sentence_drills.TITLE_PREFIX)
        prefixes.append(seed_a1_pronunciation_drills.TITLE_PREFIX)
        prefixes.append(seed_a1_dictation_drills.TITLE_PREFIX)
        prefixes.append(seed_a1_exercises.EXERCISE_TITLE)

        for prefix in prefixes:
            self.assertIn(prefix, generated.TITLE_PREFIXES)

    def test_generated_exercises_matches_the_generators_output_only(self):
        level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        course = Course.objects.create(
            language_level=level, title="Kurs", is_published=True
        )
        lesson = Lesson.objects.create(
            course=course, title="Lektion 1", is_published=True, order=1, estimated_time=10
        )
        authored = Exercise.objects.create(
            lesson=lesson, title="واژگان — انتخاب معنی", instruction="",
            type=Exercise.ExerciseType.MULTIPLE_CHOICE, difficulty=Exercise.Difficulty.EASY,
            order=1, is_published=True,
        )
        dictation = Exercise.objects.create(
            lesson=lesson, title=seed_a1_dictation_drills.DICTATION_TITLE + " (1)",
            instruction="", type=Exercise.ExerciseType.LISTENING,
            difficulty=Exercise.Difficulty.EASY, order=2, is_published=True,
        )

        found = list(generated.generated_exercises())

        self.assertIn(dictation, found)
        self.assertNotIn(authored, found)


class ExplainA1DrillsTests(TestCase):
    """``explain_a1_drills``: a generated question gets the reason it was built from.

    The field is written only from the same ``Word`` or ``Sentence`` row the question is
    about, so the two things that matter are that the reason matches that row, and that a
    question the command cannot derive a reason for is left **empty** rather than given an
    invented one — an invented reason is worse than none, because a learner cannot tell
    which kind they are reading.
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
        cls.word = Word.objects.create(
            word="Name", word_type="NOUN", gender="M", article="der",
            plural="die Namen", meaning_fa="نام", level=cls.level, is_published=True,
        )
        # A plural-only noun: it has an article but no gender, so no honest gender sentence
        # exists for it. The article drill still asks about it.
        cls.plural_only = Word.objects.create(
            word="Eltern", word_type="NOUN", article="die",
            plural="die Eltern", meaning_fa="والدین", level=cls.level, is_published=True,
        )

    def drill(self, title, order):
        return Exercise.objects.create(
            lesson=self.lesson, title=title, instruction="",
            type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            difficulty=Exercise.Difficulty.EASY, order=order, is_published=True,
        )

    def question(self, exercise, word):
        question = Question.objects.create(exercise=exercise, prompt="پرسش", order=1)
        QuestionTarget.objects.create(
            question=question, word=word, role=QuestionTarget.Role.TESTED_ITEM
        )
        return question

    def explain(self):
        out = StringIO()
        call_command("explain_a1_drills", stdout=out)
        return out.getvalue()

    def test_the_reason_is_the_fact_the_question_was_built_from(self):
        exercise = self.drill("تمرین واژگان — معنی (1)", 1)
        question = self.question(exercise, self.word)

        self.explain()
        question.refresh_from_db()

        self.assertEqual(question.explanation, "«Name» یعنی «نام».")

    def test_each_word_drill_gets_its_own_fact(self):
        cases = (
            ("تمرین گرامر — آرتیکل (1)", "«Name» مذکر است، پس «der Name»."),
            ("تمرین گرامر — جمع (1)", "جمعِ «der Name» می‌شود «die Namen»."),
            ("تمرین نوشتن — واژه (1)", "ترجمهٔ «نام» به آلمانی «Name» است."),
        )

        questions = []
        for number, case in enumerate(cases, start=1):
            title = case[0]
            expected = case[1]
            exercise = self.drill(title, number)
            questions.append((self.question(exercise, self.word), expected))

        self.explain()

        for question, expected in questions:
            question.refresh_from_db()
            self.assertEqual(question.explanation, expected)

    def test_a_question_with_no_word_target_and_no_sentence_is_left_alone(self):
        exercise = self.drill("تمرین واژگان — معنی (1)", 1)
        question = Question.objects.create(exercise=exercise, prompt="پرسش", order=1)

        self.explain()
        question.refresh_from_db()

        self.assertEqual(question.explanation, "")

    def test_a_word_with_no_gender_gets_no_invented_gender(self):
        """``die Eltern`` is plural-only; calling it feminine would be a false claim."""
        exercise = self.drill("تمرین گرامر — آرتیکل (1)", 1)
        question = self.question(exercise, self.plural_only)

        self.explain()
        question.refresh_from_db()

        self.assertEqual(question.explanation, "")

    def test_an_explanation_a_person_wrote_is_not_touched(self):
        exercise = self.drill("تمرین واژگان — معنی (1)", 1)
        question = self.question(exercise, self.word)
        question.explanation = "خودم نوشتم"
        question.save()

        self.explain()
        question.refresh_from_db()

        self.assertEqual(question.explanation, "خودم نوشتم")

    def test_an_authored_question_is_not_touched(self):
        authored = Exercise.objects.create(
            lesson=self.lesson, title="واژگان — انتخاب معنی", instruction="",
            type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            difficulty=Exercise.Difficulty.EASY, order=9, is_published=True,
        )
        question = self.question(authored, self.word)

        self.explain()
        question.refresh_from_db()

        self.assertEqual(question.explanation, "")

    def test_running_twice_writes_nothing_the_second_time(self):
        exercise = self.drill("تمرین واژگان — معنی (1)", 1)
        self.question(exercise, self.word)

        self.explain()
        second = self.explain()

        self.assertIn("Wrote 0 explanation(s).", second)
        self.assertIn("Already had an explanation: 1.", second)


class ExplainAuthoredExercisesTests(TestCase):
    """``explain_authored_exercises``: authored questions get structured Persian explanations."""

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", is_published=True, order=1, estimated_time=10
        )
        cls.word = Word.objects.create(
            word="Name", word_type="NOUN", gender="M", article="der",
            plural="die Namen", meaning_fa="نام", level=cls.level, is_published=True,
        )
        cls.plural_only = Word.objects.create(
            word="Eltern", word_type="NOUN", article="die",
            plural="die Eltern", meaning_fa="والدین", level=cls.level, is_published=True,
        )
        cls.sentence = Sentence.objects.create(
            text="Guten Morgen!", translation_fa="صبح بخیر!", level=cls.level, is_published=True
        )

    def explain(self, dry_run=False):
        out = StringIO()
        args = ["explain_authored_exercises"]
        if dry_run:
            args.append("--dry-run")
        call_command(*args, stdout=out)
        return out.getvalue()

    def test_authored_vocabulary_choice_explanation(self):
        ex = Exercise.objects.create(
            lesson=self.lesson, title="واژگان — انتخاب معنی", instruction="",
            type=Exercise.ExerciseType.MULTIPLE_CHOICE, difficulty=Exercise.Difficulty.EASY,
            order=1, is_published=True,
        )
        q = Question.objects.create(exercise=ex, prompt="واژهٔ «Name» به چه معنی است؟", order=1)
        Answer.objects.create(question=q, text="نام", is_correct=True, order=1)
        QuestionTarget.objects.create(question=q, word=self.word, role=QuestionTarget.Role.TESTED_ITEM)

        self.explain()
        q.refresh_from_db()
        self.assertEqual(
            q.explanation,
            "«Name» اسم (مذکر) با آرتیکل «der» است و جمع آن «die Namen» است؛ یعنی «نام»."
        )

    def test_authored_translation_explanation(self):
        ex = Exercise.objects.create(
            lesson=self.lesson, title="واژگان — ترجمه به آلمانی", instruction="",
            type=Exercise.ExerciseType.TRANSLATION, difficulty=Exercise.Difficulty.EASY,
            order=2, is_published=True,
        )
        q = Question.objects.create(exercise=ex, prompt="ترجمهٔ «نام» به آلمانی؟", order=1)
        Answer.objects.create(question=q, text="Name", is_correct=True, order=1)
        QuestionTarget.objects.create(question=q, word=self.word, role=QuestionTarget.Role.TESTED_ITEM)

        self.explain()
        q.refresh_from_db()
        self.assertEqual(q.explanation, "معادل «نام» در آلمانی «der Name» است.")

    def test_reading_comprehension_explanation(self):
        ex = Exercise.objects.create(
            lesson=self.lesson, title="خواندن و درک مطلب", instruction="",
            type=Exercise.ExerciseType.READING, difficulty=Exercise.Difficulty.EASY,
            order=3, is_published=True,
        )
        q = Question.objects.create(
            exercise=ex,
            prompt='در جملهٔ زیر، معادل فارسی کدام گزینه است؟\n"Guten Morgen!"',
            order=1,
        )
        Answer.objects.create(question=q, text="صبح بخیر!", is_correct=True, order=1)
        QuestionTarget.objects.create(question=q, sentence=self.sentence, role=QuestionTarget.Role.CONTEXT)

        self.explain()
        q.refresh_from_db()
        self.assertEqual(q.explanation, "معادل «Guten Morgen!» به فارسی «صبح بخیر!» است.")

    def test_plural_only_noun_explanation(self):
        ex = Exercise.objects.create(
            lesson=self.lesson, title="تمرین گرامر — آرتیکل (1)", instruction="",
            type=Exercise.ExerciseType.MULTIPLE_CHOICE, difficulty=Exercise.Difficulty.EASY,
            order=4, is_published=True,
        )
        q = Question.objects.create(exercise=ex, prompt="آرتیکل درست کدام است؟ «___ Eltern»", order=1)
        Answer.objects.create(question=q, text="die", is_correct=True, order=1)
        QuestionTarget.objects.create(question=q, word=self.plural_only, role=QuestionTarget.Role.TESTED_ITEM)

        self.explain()
        q.refresh_from_db()
        self.assertEqual(
            q.explanation,
            "«Eltern» اسمی است که فقط در حالت جمع به کار می‌رود و آرتیکل جمع آن «die» است؛ یعنی «والدین»."
        )

    def test_dry_run_leaves_database_untouched(self):
        ex = Exercise.objects.create(
            lesson=self.lesson, title="واژگان — ترجمه به آلمانی", instruction="",
            type=Exercise.ExerciseType.TRANSLATION, difficulty=Exercise.Difficulty.EASY,
            order=5, is_published=True,
        )
        q = Question.objects.create(exercise=ex, prompt="ترجمهٔ «نام» به آلمانی؟", order=1)
        Answer.objects.create(question=q, text="Name", is_correct=True, order=1)
        QuestionTarget.objects.create(question=q, word=self.word, role=QuestionTarget.Role.TESTED_ITEM)

        out = self.explain(dry_run=True)
        q.refresh_from_db()
        self.assertEqual(q.explanation, "")
        self.assertIn("Would write 1 explanation(s).", out)

    def test_already_explained_question_is_untouched(self):
        ex = Exercise.objects.create(
            lesson=self.lesson, title="واژگان — ترجمه به آلمانی", instruction="",
            type=Exercise.ExerciseType.TRANSLATION, difficulty=Exercise.Difficulty.EASY,
            order=6, is_published=True,
        )
        q = Question.objects.create(
            exercise=ex, prompt="ترجمهٔ «نام» به آلمانی؟", order=1, explanation="توضیح از قبل موجود"
        )
        Answer.objects.create(question=q, text="Name", is_correct=True, order=1)
        QuestionTarget.objects.create(question=q, word=self.word, role=QuestionTarget.Role.TESTED_ITEM)

        self.explain()
        q.refresh_from_db()
        self.assertEqual(q.explanation, "توضیح از قبل موجود")

    def test_running_twice_is_idempotent(self):
        ex = Exercise.objects.create(
            lesson=self.lesson, title="واژگان — ترجمه به آلمانی", instruction="",
            type=Exercise.ExerciseType.TRANSLATION, difficulty=Exercise.Difficulty.EASY,
            order=7, is_published=True,
        )
        q = Question.objects.create(exercise=ex, prompt="ترجمهٔ «نام» به آلمانی؟", order=1)
        Answer.objects.create(question=q, text="Name", is_correct=True, order=1)
        QuestionTarget.objects.create(question=q, word=self.word, role=QuestionTarget.Role.TESTED_ITEM)

        first = self.explain()
        self.assertIn("Wrote 1 explanation(s).", first)
        second = self.explain()
        self.assertIn("Wrote 0 explanation(s).", second)


class SeedA1ActiveProductionTests(TestCase):
    """``seed_a1_active_production``: promotes pseudo-cloze and adds targeted active production."""

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(language_level=cls.level, title="A1 Kurs", is_published=True)
        cls.lesson2 = Lesson.objects.create(course=cls.course, title="L2", order=2, is_published=True, estimated_time=15)
        cls.lesson4 = Lesson.objects.create(course=cls.course, title="L4", order=4, is_published=True, estimated_time=15)
        cls.lesson12 = Lesson.objects.create(course=cls.course, title="L12", order=12, is_published=True, estimated_time=15)
        cls.lesson19 = Lesson.objects.create(course=cls.course, title="L19", order=19, is_published=True, estimated_time=15)
        cls.lesson20 = Lesson.objects.create(course=cls.course, title="L20", order=20, is_published=True, estimated_time=15)

    def test_action1_cloze_distractors_removed(self):
        ex = Exercise.objects.create(
            lesson=self.lesson2, title="تمرین تکمیل جمله", instruction="",
            type=Exercise.ExerciseType.FILL_BLANK, difficulty=Exercise.Difficulty.MEDIUM,
            order=3, is_published=True,
        )
        q = Question.objects.create(exercise=ex, prompt='Wo _____ Sie?', order=1)
        Answer.objects.create(question=q, text="wohnen", is_correct=True, order=1)
        Answer.objects.create(question=q, text="lernen", is_correct=False, order=2)
        Answer.objects.create(question=q, text="Land", is_correct=False, order=3)

        out = StringIO()
        call_command("seed_a1_active_production", stdout=out)
        self.assertEqual(q.answers.count(), 1)
        self.assertEqual(q.answers.first().text, "wohnen")

    def test_action2_and_3_exercises_created(self):
        out = StringIO()
        call_command("seed_a1_active_production", stdout=out)

        # L12
        l12_scramble = Exercise.objects.filter(lesson=self.lesson12, type=Exercise.ExerciseType.SCRAMBLE).first()
        self.assertIsNotNone(l12_scramble)
        self.assertEqual(l12_scramble.questions.count(), 8)
        l12_cloze = Exercise.objects.filter(lesson=self.lesson12, type=Exercise.ExerciseType.FILL_BLANK).first()
        self.assertIsNotNone(l12_cloze)
        self.assertEqual(l12_cloze.questions.count(), 6)

        # L04, L19, L20
        self.assertEqual(
            Exercise.objects.filter(lesson=self.lesson4, type=Exercise.ExerciseType.SCRAMBLE).first().questions.count(),
            6,
        )
        self.assertEqual(
            Exercise.objects.filter(lesson=self.lesson19, type=Exercise.ExerciseType.SCRAMBLE).first().questions.count(),
            6,
        )
        self.assertEqual(
            Exercise.objects.filter(lesson=self.lesson20, type=Exercise.ExerciseType.SCRAMBLE).first().questions.count(),
            6,
        )

    def test_dry_run_leaves_database_untouched(self):
        ex = Exercise.objects.create(
            lesson=self.lesson2, title="تمرین تکمیل جمله", instruction="",
            type=Exercise.ExerciseType.FILL_BLANK, difficulty=Exercise.Difficulty.MEDIUM,
            order=3, is_published=True,
        )
        q = Question.objects.create(exercise=ex, prompt='Wo _____ Sie?', order=1)
        Answer.objects.create(question=q, text="wohnen", is_correct=True, order=1)
        Answer.objects.create(question=q, text="lernen", is_correct=False, order=2)

        out = StringIO()
        call_command("seed_a1_active_production", dry_run=True, stdout=out)
        self.assertEqual(q.answers.count(), 2)
        self.assertFalse(Exercise.objects.filter(lesson=self.lesson12).exists())

    def test_command_is_idempotent(self):
        out = StringIO()
        call_command("seed_a1_active_production", stdout=out)
        first_q_count = Question.objects.count()

        call_command("seed_a1_active_production", stdout=out)
        second_q_count = Question.objects.count()

        self.assertEqual(first_q_count, second_q_count)


class SeedA1ListeningDiscriminationTests(TestCase):
    """``seed_a1_listening_discrimination``: seeds Goethe A1 auditory discrimination exercises."""

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(language_level=cls.level, title="A1 Kurs", is_published=True)
        cls.lessons = [
            Lesson.objects.create(course=cls.course, title=f"L{num}", order=num, is_published=True, estimated_time=15)
            for num in (3, 6, 9, 15, 17)
        ]
        cls.sentence = Sentence.objects.create(
            id=34,
            text="Meine Telefonnummer ist null-eins-sieben-sechs...",
            translation_fa="شماره تلفن من...",
            level=cls.level,
            audio="sentences/audio/s34.mp3",
            is_published=True,
        )

    def test_dry_run_leaves_database_untouched(self):
        out = StringIO()
        call_command("seed_a1_listening_discrimination", dry_run=True, stdout=out)
        self.assertIn("[DRY-RUN]", out.getvalue())
        self.assertFalse(Exercise.objects.filter(type=Exercise.ExerciseType.LISTENING).exists())

    def test_command_creates_exercises_questions_and_answers(self):
        out = StringIO()
        call_command("seed_a1_listening_discrimination", stdout=out)

        listening_exercises = Exercise.objects.filter(type=Exercise.ExerciseType.LISTENING)
        self.assertEqual(listening_exercises.count(), 5)

        total_questions = Question.objects.filter(exercise__in=listening_exercises).count()
        self.assertEqual(total_questions, 26)

        q1_l3 = Question.objects.filter(exercise__lesson__order=3, order=1).first()
        self.assertIsNotNone(q1_l3)
        self.assertEqual(q1_l3.audio, "sentences/audio/s34.mp3")
        self.assertTrue(len(q1_l3.explanation) > 0)
        self.assertEqual(q1_l3.answers.count(), 4)
        self.assertEqual(q1_l3.answers.filter(is_correct=True).count(), 1)

    def test_command_is_idempotent(self):
        out = StringIO()
        call_command("seed_a1_listening_discrimination", stdout=out)
        first_q_count = Question.objects.count()
        first_a_count = Answer.objects.count()

        call_command("seed_a1_listening_discrimination", stdout=out)
        second_q_count = Question.objects.count()
        second_a_count = Answer.objects.count()

        self.assertEqual(first_q_count, second_q_count)
        self.assertEqual(first_a_count, second_a_count)


class SchreibenLabCommandTests(TestCase):
    """``seed_a1_schreiben_lab``: seeds authentic Goethe A1 Schreiben Lab exercises."""

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(language_level=cls.level, title="A1 Kurs", is_published=True)
        cls.lesson21 = Lesson.objects.create(
            course=cls.course, title="Telefonieren, E-Mail und Post", order=21, is_published=True, estimated_time=15
        )
        cls.lesson23 = Lesson.objects.create(
            course=cls.course, title="Amt, Bank und Formulare", order=23, is_published=True, estimated_time=15
        )

    def test_dry_run_leaves_database_untouched(self):
        out = StringIO()
        call_command("seed_a1_schreiben_lab", dry_run=True, stdout=out)
        self.assertIn("[DRY-RUN]", out.getvalue())
        self.assertFalse(Exercise.objects.filter(type=Exercise.ExerciseType.WRITING).exists())

    def test_command_creates_exercises_and_questions(self):
        out = StringIO()
        call_command("seed_a1_schreiben_lab", stdout=out)

        writing_exercises = Exercise.objects.filter(type=Exercise.ExerciseType.WRITING)
        self.assertEqual(writing_exercises.count(), 7)

        l23_exercises = writing_exercises.filter(lesson=self.lesson23)
        self.assertEqual(l23_exercises.count(), 3)
        self.assertEqual(Question.objects.filter(exercise__in=l23_exercises).count(), 15)

        l21_exercises = writing_exercises.filter(lesson=self.lesson21)
        self.assertEqual(l21_exercises.count(), 4)
        self.assertEqual(Question.objects.filter(exercise__in=l21_exercises).count(), 16)

        total_questions = Question.objects.filter(exercise__in=writing_exercises).count()
        self.assertEqual(total_questions, 31)

        for q in Question.objects.filter(exercise__in=writing_exercises):
            self.assertTrue(len(q.explanation) > 0)
            self.assertTrue(q.answers.filter(is_correct=True).exists())

    def test_command_is_idempotent(self):
        out = StringIO()
        call_command("seed_a1_schreiben_lab", stdout=out)
        first_q_count = Question.objects.count()
        first_a_count = Answer.objects.count()

        call_command("seed_a1_schreiben_lab", stdout=out)
        second_q_count = Question.objects.count()
        second_a_count = Answer.objects.count()

        self.assertEqual(first_q_count, second_q_count)
        self.assertEqual(first_a_count, second_a_count)


class SeedA1PronunciationDrillsTests(TestCase):
    """``seed_a1_pronunciation_drills``: hear one word, tell it from one sound away.

    Every other question in the product plays a whole sentence and asks what it means; none
    of them asks whether the learner can *hear* the words. These tests pin the rules that
    keep this drill honest: the wrong option is the word one sound away rather than a random
    one, the question plays the word's own recording instead of a new file, a word with no
    recording is skipped rather than asked in silence, the partner may come from another
    lesson — and the rule that is easiest to get wrong: the question carries no
    ``QuestionTarget`` at all, because a learner who confuses two words has not told us which
    of the two they do not know.
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
        # Teaches the partner of a word lesson 1 teaches: the pool is the level, not the lesson.
        cls.other_lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 2", is_published=True, order=2, estimated_time=10
        )
        # Introduces no word, so it drills the word it revisits.
        cls.review_lesson = Lesson.objects.create(
            course=cls.course, title="Wiederholung", is_published=True, order=3, estimated_time=10
        )
        # Words and recordings, but nothing to tell apart.
        cls.quiet_lesson = Lesson.objects.create(
            course=cls.course, title="Leer", is_published=True, order=4, estimated_time=10
        )

        cls.schon = cls.word("schon", "قبلاً", audio="words/audio/schon.mp3")
        cls.schoen = cls.word("schön", "زیبا", audio="words/audio/schoen.mp3")
        cls.wer = cls.word("wer", "کی", audio="words/audio/wer.mp3")
        cls.hallo = cls.word("hallo", "سلام", audio="words/audio/hallo.mp3")
        # Its partner `denn` is published and has a recording, but this word has none: the
        # question would be silent, so it must be skipped.
        cls.dann = cls.word("dann", "بعداً")

        for index, word in enumerate(
            [cls.schon, cls.schoen, cls.wer, cls.hallo, cls.dann], start=1
        ):
            LessonWord.objects.create(
                lesson=cls.lesson, word=word, role=LessonWord.Role.NEW, order=index
            )

        cls.draft = cls.word(
            "Entwurf", "پیش‌نویس", audio="words/audio/entwurf.mp3", is_published=False
        )
        LessonWord.objects.create(
            lesson=cls.lesson, word=cls.draft, role=LessonWord.Role.NEW, order=6
        )

        # Lesson 2's own words, one of which is the partner lesson 1 needs from the level pool.
        cls.wir = cls.word("wir", "ما", audio="words/audio/wir.mp3")
        cls.denn = cls.word("denn", "چون", audio="words/audio/denn.mp3")
        for index, word in enumerate([cls.wir, cls.denn], start=1):
            LessonWord.objects.create(
                lesson=cls.other_lesson, word=word, role=LessonWord.Role.NEW, order=index
            )

        # `leben` is taught by no lesson; only the review lesson revisits `lieben`.
        cls.leben = cls.word("leben", "زندگی کردن", audio="words/audio/leben.mp3")
        cls.lieben = cls.word("lieben", "دوست داشتن", audio="words/audio/lieben.mp3")
        LessonWord.objects.create(
            lesson=cls.review_lesson, word=cls.lieben, role=LessonWord.Role.REVIEW, order=1
        )

        cls.danke = cls.word("danke", "متشکرم", audio="words/audio/danke.mp3")
        LessonWord.objects.create(
            lesson=cls.quiet_lesson, word=cls.danke, role=LessonWord.Role.NEW, order=1
        )

        # Authored content, numbered like the live data. The command must never touch it.
        cls.authored = Exercise.objects.create(
            lesson=cls.lesson, title="واژگان — انتخاب معنی", instruction="",
            type=Exercise.ExerciseType.MULTIPLE_CHOICE, difficulty=Exercise.Difficulty.EASY,
            order=1, is_published=True,
        )
        authored_question = Question.objects.create(
            exercise=cls.authored, prompt="واژهٔ «hallo»؟", order=1
        )
        Answer.objects.create(
            question=authored_question, text="سلام", is_correct=True, order=1
        )

    @classmethod
    def word(cls, text, meaning_fa, audio="", is_published=True):
        return Word.objects.create(
            word=text, word_type=Word.WordType.OTHER, meaning_fa=meaning_fa,
            level=cls.level, is_published=is_published, audio=audio,
        )

    def run_command(self, *args):
        out = StringIO()
        err = StringIO()
        call_command("seed_a1_pronunciation_drills", *args, stdout=out, stderr=err)
        return out.getvalue()

    def generated(self):
        return Exercise.objects.filter(title__startswith="تمرین تلفظ")

    def generated_questions(self):
        return Question.objects.filter(exercise__in=self.generated()).order_by("order")

    def question_for(self, text):
        """The generated question whose played word is ``text``.

        Read from the correct answer rather than from the file name: the recordings are
        named with transliterated spellings (``schoen.mp3``), and the word is what the
        question is about.
        """
        for question in self.generated_questions():
            correct = question.answers.get(is_correct=True)
            if correct.text == text:
                return question
        return None

    # ------------------------------------------------------------------- shape

    def test_a_pair_becomes_a_two_option_question(self):
        self.run_command()

        question = self.question_for("schon")
        self.assertIsNotNone(question)
        self.assertEqual(question.answers.count(), 2)
        self.assertEqual(question.answers.filter(is_correct=True).count(), 1)
        self.assertEqual(question.answers.get(is_correct=True).text, "schon")

    def test_the_wrong_option_is_the_word_one_sound_away(self):
        self.run_command()

        wrong = self.question_for("schon").answers.get(is_correct=False)

        self.assertEqual(wrong.text, "schön")

    def test_both_words_of_a_pair_are_asked_when_the_lesson_teaches_both(self):
        self.run_command()

        first = self.question_for("schon")
        second = self.question_for("schön")

        # Each direction plays a different word, so both are real questions.
        self.assertIsNotNone(second)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(first.answers.get(is_correct=True).text, "schon")
        self.assertEqual(second.answers.get(is_correct=True).text, "schön")
        self.assertEqual(first.answers.get(is_correct=False).text, "schön")
        self.assertEqual(second.answers.get(is_correct=False).text, "schon")

    def test_the_prompt_names_the_sound_the_two_options_differ_in(self):
        self.run_command()

        prompt = self.question_for("schon").prompt

        self.assertIn("کدام واژه را شنیدی", prompt)
        self.assertIn("ö گرد در برابر o", prompt)

    def test_the_question_plays_the_recording_the_word_already_has(self):
        """Nothing is generated and nothing is copied: the word's own file is pointed at."""
        self.run_command()

        self.assertEqual(self.question_for("schon").audio.name, "words/audio/schon.mp3")

    def test_the_correct_option_is_not_always_the_first(self):
        self.run_command()

        slots = []
        for question in self.generated_questions():
            slots.append(question.answers.order_by("order").first().is_correct)

        self.assertIn(True, slots)
        self.assertIn(False, slots)

    def test_the_exercises_are_listening_content(self):
        self.run_command()

        for exercise in self.generated():
            self.assertEqual(exercise.type, Exercise.ExerciseType.LISTENING)
            self.assertTrue(exercise.is_published)

    # ------------------------------------------------------------------- scope

    def test_the_partner_may_come_from_another_lesson(self):
        """A minimal pair is about the sound, not the chapter: lesson 1's `wer` pairs with `wir`."""
        self.run_command()

        question = self.question_for("wer")

        self.assertIsNotNone(question)
        self.assertEqual(question.answers.get(is_correct=False).text, "wir")

    def test_a_word_with_no_recording_is_not_asked(self):
        self.run_command()

        self.assertIsNone(self.question_for("dann"))
        played = Question.objects.filter(exercise__in=self.generated(), audio__contains="dann")
        self.assertFalse(played.exists())

    def test_a_word_with_no_partner_is_not_asked(self):
        self.run_command()

        self.assertIsNone(self.question_for("hallo"))

    def test_a_draft_word_is_never_played(self):
        self.run_command()

        self.assertIsNone(self.question_for("Entwurf"))

    def test_a_lesson_with_nothing_to_tell_apart_gets_no_exercise(self):
        self.run_command()

        self.assertFalse(self.generated().filter(lesson=self.quiet_lesson).exists())

    def test_a_review_lesson_gets_no_sound_drill_of_its_own(self):
        """A review lesson introduces no word, and its sound pairs were taught with the words
        when they were introduced. A second listening would be the same question twice, so it
        is left out; the review lesson's practice is the turned-around word drills instead."""
        self.run_command()

        self.assertFalse(self.generated().filter(lesson=self.review_lesson).exists())

    def test_the_same_sound_is_asked_once_per_lesson(self):
        """`sie` and `Sie` are two words with one pronunciation, and both can be in a lesson."""
        lowercase = self.word("sie", "او", audio="words/audio/sie.mp3")
        formal = self.word("Sie", "شما", audio="words/audio/sie-formal.mp3")
        see = self.word("See", "دریاچه", audio="words/audio/see.mp3")
        for index, word in enumerate([lowercase, formal, see], start=10):
            LessonWord.objects.create(
                lesson=self.other_lesson, word=word, role=LessonWord.Role.NEW, order=index
            )

        self.run_command("--lesson", str(self.other_lesson.pk))

        asked = Question.objects.filter(
            exercise__in=self.generated(), audio__startswith="words/audio/sie"
        )
        self.assertEqual(asked.count(), 1)

    # -------------------------------------------------------------- no targets

    def test_no_question_carries_a_target(self):
        """A confusion is about two words at once, so it may not move either one's progress."""
        self.run_command()

        self.assertTrue(self.generated_questions().exists())
        self.assertFalse(QuestionTarget.objects.exists())

    # ------------------------------------------------------------- safe rebuild

    def test_it_never_touches_the_authored_exercises(self):
        self.run_command()

        self.assertTrue(Exercise.objects.filter(pk=self.authored.pk).exists())
        self.assertTrue(Answer.objects.filter(question__exercise=self.authored).exists())

    def test_the_new_questions_continue_the_lessons_numbering(self):
        self.run_command()

        orders = sorted(
            Question.objects.filter(exercise__lesson=self.lesson).values_list("order", flat=True)
        )

        # The authored question is order 1, so the generated ones carry on without a gap.
        self.assertEqual(orders, list(range(1, len(orders) + 1)))

    def test_rerunning_replaces_instead_of_duplicating(self):
        self.run_command()
        first_ids = sorted(self.generated().values_list("id", flat=True))
        question_total = self.generated_questions().count()

        self.run_command()

        second_ids = sorted(self.generated().values_list("id", flat=True))
        self.assertEqual(len(second_ids), len(first_ids))
        self.assertNotEqual(first_ids, second_ids)
        self.assertEqual(self.generated_questions().count(), question_total)

    def test_dry_run_writes_nothing(self):
        output = self.run_command("--dry-run")

        self.assertIn("Dry run", output)
        self.assertFalse(self.generated().exists())

    def test_the_lesson_flag_limits_what_is_written(self):
        self.run_command("--lesson", str(self.lesson.pk))

        self.assertTrue(self.generated().filter(lesson=self.lesson).exists())
        self.assertFalse(self.generated().exclude(lesson=self.lesson).exists())

    def test_batch_only_changes_how_the_questions_are_split(self):
        self.run_command("--batch", "1")
        many = self.generated().count()
        questions = self.generated_questions().count()

        self.run_command("--batch", "20")

        self.assertLess(self.generated().count(), many)
        self.assertEqual(self.generated_questions().count(), questions)

    def test_a_batch_below_one_is_refused(self):
        with self.assertRaises(CommandError):
            self.run_command("--batch", "0")

    def test_it_refuses_while_a_pronunciation_drill_has_attempts(self):
        self.run_command()
        exercise = self.generated().first()
        user = User.objects.create_user(username="learner", password="test-pass-123")
        ExerciseAttempt.objects.create(
            user=user, exercise=exercise, question=exercise.questions.first(), is_correct=True
        )

        with self.assertRaises(CommandError):
            self.run_command()

    def test_yes_replace_history_deletes_those_attempts_on_purpose(self):
        self.run_command()
        exercise = self.generated().first()
        user = User.objects.create_user(username="learner", password="test-pass-123")
        ExerciseAttempt.objects.create(
            user=user, exercise=exercise, question=exercise.questions.first(), is_correct=True
        )

        self.run_command("--yes-replace-history")

        self.assertEqual(ExerciseAttempt.objects.count(), 0)
        self.assertTrue(self.generated().exists())


class SeedA1SentenceDrillsTests(TestCase):
    """``seed_a1_sentence_drills``: each lesson's own sentences become reading questions.

    The course publishes 339 sentences and asks about three per lesson — by ear, in the
    listening exercise, which plays the file and asks what it means. The rest were shown in
    the lesson and never asked about again, so a learner could know every word and still
    never be asked about a whole sentence. These tests are about the rules that close that
    gap: a sentence another exercise already asks about is left alone, whether it is marked
    by a target or by its audio; the wrong options come from the whole level, so four options
    are not obviously one text; and no sentence question claims to know which *word* a
    learner misread.
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
        cls.other_lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 2", is_published=True, order=2, estimated_time=10
        )
        # Every sentence it teaches is asked about elsewhere, so it gets no exercise.
        cls.asked_lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 3", is_published=True, order=3, estimated_time=10
        )
        cls.draft_lesson = Lesson.objects.create(
            course=cls.course, title="Entwurf", is_published=False, order=4, estimated_time=10
        )

        cls.morgen = cls.sentence("Guten Morgen!", "صبح بخیر!")
        cls.dir = cls.sentence("Wie geht es dir?", "حالت چطور است؟")
        cls.anna = cls.sentence("Ich heiße Anna.", "اسم من آناست.")
        cls.woher = cls.sentence("Woher kommst du?", "اهل کجایی؟")
        cls.drilled = [cls.morgen, cls.dir, cls.anna, cls.woher]

        # Asked about by the listening exercise. Not by a target — the listening questions
        # were written before question targets existed — but by the file they play.
        cls.listened = cls.sentence(
            "Ich komme aus dem Iran.", "من اهل ایرانم.", audio="sentences/audio/listened.mp3"
        )
        cls.draft_sentence = cls.sentence("Entwurf.", "پیش‌نویس.", is_published=False)
        # Asked about by an authored reading question, which points at it with a target.
        cls.read = cls.sentence("Das ist Frau Schmidt.", "این خانم اشمیت است.")

        for index, sentence in enumerate(
            cls.drilled + [cls.listened, cls.read, cls.draft_sentence], start=1
        ):
            LessonSentence.objects.create(lesson=cls.lesson, sentence=sentence, order=index)

        LessonSentence.objects.create(lesson=cls.asked_lesson, sentence=cls.read, order=1)
        LessonSentence.objects.create(
            lesson=cls.draft_lesson, sentence=cls.draft_sentence, order=1
        )

        cls.single = cls.sentence("Ich wohne in Hamburg.", "من در هامبورگ زندگی می‌کنم.")
        LessonSentence.objects.create(lesson=cls.other_lesson, sentence=cls.single, order=1)

        # The listening exercise: an audio file, and no target at all.
        cls.listening = Exercise.objects.create(
            lesson=cls.lesson, title="شنیدن: جمله‌های این درس", instruction="",
            type=Exercise.ExerciseType.LISTENING, difficulty=Exercise.Difficulty.MEDIUM,
            order=1, is_published=True,
        )
        Question.objects.create(
            exercise=cls.listening, prompt="به فایل گوش کن و معنی درست را انتخاب کن.",
            audio="sentences/audio/listened.mp3", order=1,
        )

        # An authored reading question: the same task as the meaning drill, so its sentence
        # has to be left alone too.
        cls.authored = Exercise.objects.create(
            lesson=cls.lesson, title="خواندن و درک مطلب", instruction="",
            type=Exercise.ExerciseType.READING, difficulty=Exercise.Difficulty.EASY,
            order=2, is_published=True,
        )
        cls.authored_question = Question.objects.create(
            exercise=cls.authored, prompt="در جملهٔ زیر، معادل فارسی کدام گزینه است؟", order=2
        )
        Answer.objects.create(
            question=cls.authored_question, text="این خانم اشمیت است.", is_correct=True, order=1
        )
        Answer.objects.create(
            question=cls.authored_question, text="این آقای وبر است.", is_correct=False, order=2
        )
        QuestionTarget.objects.create(
            question=cls.authored_question, sentence=cls.read, role=QuestionTarget.Role.CONTEXT
        )

        # A course of its own with three sentences: too few to offer three wrong translations.
        cls.small_level = LanguageLevel.objects.create(level="A2", title="A2", order=2)
        cls.small_course = Course.objects.create(
            language_level=cls.small_level, title="Kleiner Kurs", is_published=True
        )
        cls.small_lesson = Lesson.objects.create(
            course=cls.small_course, title="Lektion A2", is_published=True, order=1,
            estimated_time=10,
        )
        cls.eins = cls.sentence("Eins.", "یک.", level=cls.small_level)
        cls.zwei = cls.sentence("Zwei.", "دو.", level=cls.small_level)
        cls.drei = cls.sentence("Drei.", "سه.", level=cls.small_level)
        for index, sentence in enumerate([cls.eins, cls.zwei, cls.drei], start=1):
            LessonSentence.objects.create(lesson=cls.small_lesson, sentence=sentence, order=index)

    @classmethod
    def sentence(cls, text, translation_fa, audio="", is_published=True, level=None):
        if level is None:
            level = cls.level
        return Sentence.objects.create(
            text=text, translation_fa=translation_fa, level=level, audio=audio,
            is_published=is_published,
        )

    def run_command(self, *args):
        # stderr is captured too, so the command's warnings do not spill into the test output.
        out = StringIO()
        err = StringIO()
        call_command("seed_a1_sentence_drills", *args, stdout=out, stderr=err)
        return out.getvalue()

    def generated(self):
        return Exercise.objects.filter(title__startswith="تمرین جمله")

    def generated_questions(self):
        return Question.objects.filter(exercise__in=self.generated())

    def meaning_questions(self):
        return Question.objects.filter(exercise__title__startswith="تمرین جمله — معنی")

    def german_questions(self):
        return Question.objects.filter(exercise__title__startswith="تمرین جمله — کدام جمله")

    def scramble_questions(self):
        return Question.objects.filter(exercise__title__startswith="تمرین جمله — مرتب کردن")

    def reading_questions_for(self, sentence):
        return self.meaning_questions().filter(targets__sentence=sentence)

    def german_questions_for(self, sentence):
        return self.german_questions().filter(prompt__contains=sentence.translation_fa)

    def test_every_sentence_a_lesson_teaches_becomes_answerable(self):
        self.run_command()
        for sentence in self.drilled:
            self.assertEqual(self.reading_questions_for(sentence).count(), 1, sentence.text)
            self.assertEqual(self.german_questions_for(sentence).count(), 1, sentence.text)

    def test_a_sentence_the_listening_exercise_asks_about_is_left_alone(self):
        """The listening questions have no targets and are recognised by the audio file they
        play; asking the same sentence again by reading would be duplicate content."""
        self.run_command()
        self.assertFalse(self.reading_questions_for(self.listened).exists())
        self.assertFalse(self.german_questions_for(self.listened).exists())

    def test_a_sentence_an_authored_reading_question_asks_about_is_left_alone(self):
        self.run_command()
        self.assertFalse(self.reading_questions_for(self.read).exists())
        self.assertFalse(self.german_questions_for(self.read).exists())

    def test_every_sentence_a_lesson_teaches_also_becomes_a_scramble(self):
        self.run_command()
        for sentence in self.drilled:
            self.assertEqual(
                self.scramble_questions().filter(
                    exercise__lesson=self.lesson, answers__text=sentence.text
                ).count(),
                1,
                sentence.text,
            )

    def test_a_scramble_has_one_answer_the_sentence_itself(self):
        """The words are derived from this answer and their order is the task, so there are no
        wrong options to author — one row holds the whole sentence."""
        self.run_command()
        for question in self.scramble_questions():
            self.assertEqual(question.answers.count(), 1)
            self.assertTrue(question.answers.get().is_correct)
            self.assertTrue(question.prompt.endswith("»"))

    def test_a_scramble_never_carries_the_sentence_as_a_passage(self):
        """A ``CONTEXT`` target would render the sentence in the right order — the answer."""
        self.run_command()
        for question in self.scramble_questions():
            self.assertFalse(question.targets.exists())

    def test_a_one_word_sentence_is_left_out_of_the_scramble_only(self):
        self.run_command()
        self.assertFalse(
            self.generated().filter(
                lesson=self.small_lesson, type=Exercise.ExerciseType.SCRAMBLE
            ).exists()
        )

    def test_the_scramble_runner_shows_the_words_shuffled_not_in_order(self):
        self.run_command()
        question = self.scramble_questions().filter(exercise__lesson=self.lesson).first()
        words = question.answers.get().text.split()
        tokens = extract_sentence_words(question)
        # The tray shows the words without their punctuation, so the sentence's own words
        # are compared bare too: the same words, in a different order.
        bare = []
        for word in words:
            bare.append(PUNCTUATION.sub("", word))
        self.assertEqual(sorted(tokens), sorted(bare))
        self.assertNotEqual(tokens, bare)

    def test_the_scramble_page_renders_the_word_bank_and_never_the_order(self):
        self.run_command()
        exercise = self.generated().filter(
            Q(title__startswith="تمرین جمله — مرتب کردن") & Q(lesson=self.lesson)
        ).first()
        response = self.client.get(reverse("exercises:exercise-detail", args=[exercise.pk]))
        self.assertContains(response, 'data-kind="order"')
        self.assertContains(response, 'class="runner-order__token"')
        self.assertNotContains(response, "data-correct")

    def test_typing_the_sentence_in_the_right_order_is_correct(self):
        self.run_command("--lesson", str(self.other_lesson.pk))
        question = self.scramble_questions().first()
        sentence = question.answers.get().text

        user = User.objects.create_user(username="ordner", password="test-pass-123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("exercises:exercise-submit", args=[question.exercise.pk]),
            data=json.dumps(
                {"question": question.pk, "answer": None, "response_text": sentence}
            ),
            content_type="application/json",
        )

        self.assertTrue(response.json()["correct"])

    def test_a_wrong_word_order_is_wrong(self):
        self.run_command("--lesson", str(self.other_lesson.pk))
        question = self.scramble_questions().first()
        words = question.answers.get().text.split()
        scrambled = " ".join(reversed(words))

        user = User.objects.create_user(username="wirrer", password="test-pass-123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("exercises:exercise-submit", args=[question.exercise.pk]),
            data=json.dumps(
                {"question": question.pk, "answer": None, "response_text": scrambled}
            ),
            content_type="application/json",
        )

        self.assertFalse(response.json()["correct"])

    def test_typing_the_words_without_the_punctuation_is_correct(self):
        """The tray shows bare words, so bare words are what the scramble accepts: the
        comma and the full stop are the sentence's, not something the learner was shown."""
        self.run_command()
        question = self.scramble_questions().first()
        sentence = question.answers.get().text
        bare = PUNCTUATION.sub("", sentence)
        self.assertNotEqual(bare, sentence, "the fixture sentence should carry punctuation")

        user = User.objects.create_user(username="ohnezeichen", password="test-pass-123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("exercises:exercise-submit", args=[question.exercise.pk]),
            data=json.dumps(
                {"question": question.pk, "answer": None, "response_text": bare}
            ),
            content_type="application/json",
        )

        self.assertTrue(response.json()["correct"])

    def test_a_scramble_tray_shows_the_words_without_their_punctuation(self):
        self.run_command()
        question = self.scramble_questions().first()
        sentence = question.answers.get().text
        tokens = extract_sentence_words(question)

        # The same words as the sentence, in a different order, with no mark left on any
        # of them.
        bare = PUNCTUATION.sub("", sentence).split()
        self.assertEqual(sorted(tokens), sorted(bare))
        for token in tokens:
            with self.subTest(token=token):
                self.assertFalse(PUNCTUATION.search(token))

        # The sentence itself is what is stored, punctuation and all.
        self.assertEqual(question.answers.get().text, sentence)

    def test_a_lesson_whose_sentences_are_all_asked_about_gets_no_exercise(self):
        self.run_command()
        self.assertFalse(self.generated().filter(lesson=self.asked_lesson).exists())

    def test_a_draft_sentence_and_a_draft_lesson_are_not_asked_about(self):
        self.run_command()
        self.assertFalse(self.reading_questions_for(self.draft_sentence).exists())
        self.assertFalse(self.generated().filter(lesson=self.draft_lesson).exists())

    def test_each_direction_is_its_own_exercise_type(self):
        self.run_command()
        for exercise in self.generated():
            if exercise.title.startswith("تمرین جمله — معنی"):
                self.assertEqual(exercise.type, Exercise.ExerciseType.READING)
            elif exercise.title.startswith("تمرین جمله — کدام جمله"):
                self.assertEqual(exercise.type, Exercise.ExerciseType.MULTIPLE_CHOICE)
            else:
                self.assertEqual(exercise.type, Exercise.ExerciseType.SCRAMBLE)

    def test_every_choice_question_has_four_options_and_one_right_answer(self):
        self.run_command()
        for question in self.generated_questions().exclude(
            exercise__type=Exercise.ExerciseType.SCRAMBLE
        ):
            self.assertEqual(question.answers.count(), 4)
            self.assertEqual(question.answers.filter(is_correct=True).count(), 1)

    def test_the_correct_meaning_is_the_sentences_own_translation(self):
        self.run_command()
        for question in self.meaning_questions():
            sentence = question.targets.get().sentence
            correct = question.answers.get(is_correct=True).text
            self.assertEqual(correct, sentence.translation_fa)
            self.assertEqual(question.answers.filter(text=correct).count(), 1)

    def test_the_reverse_question_shows_the_meaning_and_never_the_sentence(self):
        """This direction carries no sentence target on purpose: the passage would be the
        correct option itself."""
        self.run_command()
        for question in self.german_questions():
            self.assertFalse(question.targets.exists())
            self.assertNotIn(question.answers.get(is_correct=True).text, question.prompt)

    def test_a_reading_question_renders_its_sentence_as_the_passage(self):
        """The sentence reaches the page as the LTR passage, through the same ``CONTEXT``
        target the authored reading questions use."""
        self.run_command()
        exercise = self.generated().filter(
            Q(title__startswith="تمرین جمله — معنی") & Q(lesson=self.lesson)
        ).first()
        rows = build_runner(exercise)
        self.assertEqual(len(rows), len(self.drilled))
        self.assertEqual(sorted(row["passage"] for row in rows), sorted(s.text for s in self.drilled))
        for row in rows:
            self.assertEqual(row["kind"], "choice")

    def test_the_reading_drill_page_shows_the_sentence_and_never_the_answer(self):
        self.run_command()
        exercise = self.generated().filter(
            Q(title__startswith="تمرین جمله — معنی") & Q(lesson=self.lesson)
        ).first()
        response = self.client.get(reverse("exercises:exercise-detail", args=[exercise.pk]))
        self.assertContains(response, self.morgen.text)
        self.assertContains(response, 'class="runner-q__passage" lang="de" dir="ltr"')
        self.assertNotContains(response, "data-correct")

    def test_a_sentence_question_never_claims_to_know_which_word_was_missed(self):
        """No word target, so ``WordProgress`` cannot move for a sentence question: a learner
        who misreads a sentence has not said which word they misread."""
        self.run_command()
        for question in self.generated_questions():
            self.assertFalse(question.targets.filter(word__isnull=False).exists())
            self.assertFalse(question.targets.filter(grammar__isnull=False).exists())

    def test_the_wrong_options_are_not_the_same_set_every_time(self):
        """Reading the pool from the front would hand every question the same three wrong
        translations, which a learner can learn to pattern-match instead of reading."""
        self.run_command()
        seen = set()
        for question in self.meaning_questions().filter(exercise__lesson=self.lesson):
            seen.add(
                frozenset(question.answers.filter(is_correct=False).values_list("text", flat=True))
            )
        self.assertGreater(len(seen), 1)

    def test_the_questions_are_numbered_across_the_whole_lesson(self):
        self.run_command()
        orders = sorted(
            Question.objects.filter(exercise__lesson=self.lesson).values_list("order", flat=True)
        )
        # The listening question is 1 and the authored reading question is 2, so the generated
        # ones — four sentences in three directions — run 3..14.
        self.assertEqual(orders, list(range(1, 15)))

    def test_a_question_is_dropped_rather_than_written_without_honest_wrong_options(self):
        """Three sentences cannot offer three wrong translations, so that course gets no drill
        at all instead of four options where two of them cannot be wrong."""
        self.run_command()
        self.assertFalse(self.generated().filter(lesson=self.small_lesson).exists())

    def test_rerunning_replaces_instead_of_duplicating(self):
        self.run_command()
        first_ids = sorted(self.generated().values_list("id", flat=True))

        self.run_command()

        second_ids = sorted(self.generated().values_list("id", flat=True))
        self.assertEqual(len(second_ids), len(first_ids))
        self.assertNotEqual(first_ids, second_ids)
        # Four sentences in three directions for this lesson, one sentence for the other —
        # on the second run exactly as on the first.
        self.assertEqual(self.generated_questions().count(), 15)

    def test_it_never_touches_the_authored_exercises(self):
        self.run_command()
        self.assertEqual(Question.objects.filter(exercise=self.authored).count(), 1)
        self.assertEqual(Answer.objects.filter(question__exercise=self.authored).count(), 2)
        self.assertEqual(Question.objects.filter(exercise=self.listening).count(), 1)

    def test_dry_run_writes_nothing(self):
        output = self.run_command("--dry-run")
        self.assertIn("Dry run", output)
        self.assertFalse(self.generated().exists())

    def test_the_lesson_option_limits_the_run_to_one_lesson(self):
        self.run_command("--lesson", str(self.other_lesson.pk))
        lessons = set(self.generated().values_list("lesson_id", flat=True))
        self.assertEqual(lessons, {self.other_lesson.pk})

    def test_batch_only_changes_how_the_questions_are_split(self):
        self.run_command()
        questions = self.generated_questions().count()
        exercises = self.generated().count()

        self.run_command("--batch", "2")

        self.assertEqual(self.generated_questions().count(), questions)
        self.assertGreater(self.generated().count(), exercises)
        for exercise in self.generated():
            self.assertLessEqual(exercise.questions.count(), 2)

    def test_a_batch_below_one_is_refused(self):
        with self.assertRaises(CommandError):
            self.run_command("--batch", "0")

    def test_it_refuses_while_a_sentence_drill_has_attempts(self):
        self.run_command()
        exercise = self.generated().first()
        user = User.objects.create_user(username="learner", password="test-pass-123")
        ExerciseAttempt.objects.create(
            user=user, exercise=exercise, question=exercise.questions.first(), is_correct=True
        )

        with self.assertRaises(CommandError):
            self.run_command()

    def test_yes_replace_history_deletes_those_attempts_on_purpose(self):
        self.run_command()
        exercise = self.generated().first()
        user = User.objects.create_user(username="learner", password="test-pass-123")
        ExerciseAttempt.objects.create(
            user=user, exercise=exercise, question=exercise.questions.first(), is_correct=True
        )

        self.run_command("--yes-replace-history")

        self.assertEqual(ExerciseAttempt.objects.count(), 0)
        self.assertTrue(self.generated().exists())

    def test_an_attempt_on_an_authored_exercise_neither_blocks_nor_goes_away(self):
        question = self.authored.questions.first()
        user = User.objects.create_user(username="learner", password="test-pass-123")
        attempt = ExerciseAttempt.objects.create(
            user=user, exercise=self.authored, question=question, is_correct=True
        )

        self.run_command()

        self.assertTrue(ExerciseAttempt.objects.filter(pk=attempt.pk).exists())
        self.assertTrue(self.generated().exists())


class SubmitAwardsXpTests(TestCase):
    """A recorded answer moves XP and the streak (``accounts/xp.py``).

    XP is the practice path's feedback layer, and the rule that matters is that the
    *server* decides it: the page is only told the new totals, never asked to add them.
    """

    @classmethod
    def setUpTestData(cls):
        level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        course = Course.objects.create(
            language_level=level, title="Kurs", is_published=True
        )
        lesson = Lesson.objects.create(
            course=course, title="Lektion 1", is_published=True, order=1, estimated_time=10
        )
        cls.exercise = Exercise.objects.create(
            lesson=lesson, title="واژگان", type="MULTIPLE_CHOICE", order=1, is_published=True
        )
        cls.question = Question.objects.create(
            exercise=cls.exercise, prompt="واژهٔ «hallo» به چه معنی است؟", order=1
        )
        Answer.objects.create(
            question=cls.question, text="سلام", is_correct=True, order=1
        )
        Answer.objects.create(
            question=cls.question, text="خداحافظ", is_correct=False, order=2
        )
        cls.user = User.objects.create_user(
            username="xp-learner", password="a-strong-password"
        )

    def submit(self, **payload):
        body = {"question": self.question.pk}
        body.update(payload)
        return self.client.post(
            reverse("exercises:exercise-submit", args=[self.exercise.pk]),
            data=json.dumps(body),
            content_type="application/json",
        )

    def test_a_correct_answer_returns_the_new_totals(self):
        self.client.force_login(self.user)
        body = self.submit(answer=self.question.answers.get(is_correct=True).pk).json()

        self.assertTrue(body["correct"])
        self.assertEqual(body["xp_gained"], 10)
        self.assertEqual(body["xp"]["xp"], 10)
        self.assertEqual(body["xp"]["level"], 1)
        self.assertEqual(body["xp"]["streak_days"], 1)

    def test_a_second_try_earns_nothing_even_when_it_is_right(self):
        """A retry cannot be farmed by guessing once and then answering again with the
        answer in hand: the points for this question were already decided."""
        self.client.force_login(self.user)
        wrong = self.question.answers.get(is_correct=False).pk
        right = self.question.answers.get(is_correct=True).pk

        self.submit(answer=wrong)
        body = self.submit(answer=right, retry=True).json()

        self.assertTrue(body["correct"])
        self.assertEqual(body["xp_gained"], 0)
        self.assertEqual(body["xp"]["xp"], 0)

    def test_a_wrong_answer_earns_nothing_but_still_marks_the_day(self):
        self.client.force_login(self.user)
        body = self.submit(answer=self.question.answers.get(is_correct=False).pk).json()

        self.assertFalse(body["correct"])
        self.assertEqual(body["xp_gained"], 0)
        self.assertEqual(body["xp"]["xp"], 0)
        self.assertEqual(body["xp"]["streak_days"], 1)

    def test_a_visitor_is_graded_without_any_xp(self):
        """The verdict is still the server's, but there is nobody to credit."""
        body = self.submit(answer=self.question.answers.get(is_correct=True).pk).json()

        self.assertTrue(body["correct"])
        self.assertIsNone(body["xp"])
        self.assertEqual(body["xp_gained"], 0)


class SessionTests(TestCase):
    """«جلسهٔ امروز»: bounded, one question per topic, kinds varied.

    This is section M of TODO.md made real. A lesson's exercise list was a wall — lesson 1
    is 31 exercises and 183 questions, and one word is asked by three to five of them — so
    a session is *composed* instead: at most SESSION_SIZE questions, one per word, with the
    kind of question changing from one to the next.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", is_published=True, order=1,
            estimated_time=10,
        )

        # Two words, each asked by two drills of different kinds: the repetition the
        # session has to collapse, and the two kinds it has to alternate between.
        cls.words = []
        for index in range(2):
            cls.words.append(
                Word.objects.create(
                    word=f"Wort{index}", word_type="OTHER", meaning_fa=f"معنی {index}",
                    level=cls.level, is_published=True,
                )
            )

        cls.meaning = Exercise.objects.create(
            lesson=cls.lesson, title="معنی", type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            order=1, is_published=True,
        )
        cls.spelling = Exercise.objects.create(
            lesson=cls.lesson, title="نوشتن", type=Exercise.ExerciseType.WRITING,
            order=2, is_published=True,
        )

        for index, word in enumerate(cls.words):
            choice = Question.objects.create(
                exercise=cls.meaning, prompt=f"معنی {word.word}؟", order=index + 1
            )
            QuestionTarget.objects.create(
                question=choice, word=word, role=QuestionTarget.Role.TESTED_ITEM
            )
            Answer.objects.create(question=choice, text=word.meaning_fa, is_correct=True, order=1)
            Answer.objects.create(question=choice, text="چیز دیگری", is_correct=False, order=2)

            typed = Question.objects.create(
                exercise=cls.spelling, prompt=f"بنویس: {word.meaning_fa}", order=index + 1
            )
            QuestionTarget.objects.create(
                question=typed, word=word, role=QuestionTarget.Role.TESTED_ITEM
            )
            Answer.objects.create(question=typed, text=word.word, is_correct=True, order=1)

        cls.user = User.objects.create_user(
            username="session-learner", password="a-strong-password"
        )

    def build(self, user=None):
        if user is None:
            user = self.user
        return build_session(user, timezone.localdate(), self.lesson)

    def word_of(self, question):
        return question.targets.get(role=QuestionTarget.Role.TESTED_ITEM).word_id

    def test_a_word_asked_by_two_drills_is_asked_once(self):
        session = self.build()
        self.assertEqual(session["goal"], 2)

        word_ids = []
        for question in session["questions"]:
            word_ids.append(self.word_of(question))

        self.assertEqual(len(word_ids), len(set(word_ids)))

    def test_the_kind_changes_from_one_question_to_the_next(self):
        session = self.build()
        types = []
        for question in session["questions"]:
            types.append(question.exercise.type)

        self.assertEqual(len(types), 2)
        self.assertNotEqual(types[0], types[1])

    def test_the_goal_is_capped_at_the_session_size(self):
        extra = Exercise.objects.create(
            lesson=self.lesson, title="بزرگ", type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            order=3, is_published=True,
        )
        for index in range(SESSION_SIZE + 5):
            word = Word.objects.create(
                word=f"Viel{index}", word_type="OTHER", meaning_fa=f"معنی {index}",
                level=self.level, is_published=True,
            )
            question = Question.objects.create(
                exercise=extra, prompt=f"معنی {word.word}؟", order=index + 1
            )
            QuestionTarget.objects.create(
                question=question, word=word, role=QuestionTarget.Role.TESTED_ITEM
            )
            Answer.objects.create(question=question, text=word.meaning_fa, is_correct=True, order=1)
            Answer.objects.create(question=question, text="چیز دیگری", is_correct=False, order=2)

        self.assertEqual(self.build()["goal"], SESSION_SIZE)

    def test_a_topic_done_today_is_left_out_whole(self):
        # One drill about the first word is answered; the *other* drill about that same
        # word must not come back in its place.
        choice = self.meaning.questions.get(order=1)
        ExerciseAttempt.objects.create(
            user=self.user, exercise=self.meaning, question=choice,
            answer=choice.answers.get(is_correct=True), is_correct=True,
        )

        session = self.build()

        self.assertEqual(session["goal"], 1)
        self.assertEqual(self.word_of(session["questions"][0]), self.words[1].pk)

    def test_a_question_with_no_authored_answer_is_left_out(self):
        word = Word.objects.create(
            word="Ohne", word_type="OTHER", meaning_fa="بی‌پاسخ",
            level=self.level, is_published=True,
        )
        question = Question.objects.create(exercise=self.spelling, prompt="بی‌پاسخ", order=90)
        QuestionTarget.objects.create(
            question=question, word=word, role=QuestionTarget.Role.TESTED_ITEM
        )

        session = self.build()

        # The topic exists but nothing in it can be marked, so it is not asked.
        self.assertEqual(session["goal"], 2)
        for row in session["questions"]:
            self.assertNotEqual(row.pk, question.pk)

    def test_a_draft_exercise_contributes_nothing(self):
        draft = Exercise.objects.create(
            lesson=self.lesson, title="پیش‌نویس", type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            order=4, is_published=False,
        )
        word = Word.objects.create(
            word="Entwurf", word_type="OTHER", meaning_fa="پیش‌نویس",
            level=self.level, is_published=True,
        )
        question = Question.objects.create(exercise=draft, prompt="پیش‌نویس", order=1)
        QuestionTarget.objects.create(
            question=question, word=word, role=QuestionTarget.Role.TESTED_ITEM
        )
        Answer.objects.create(question=question, text="پیش‌نویس", is_correct=True, order=1)

        session = self.build()

        self.assertEqual(session["goal"], 2)

    def test_a_scramble_is_not_rendered_as_a_bare_typed_question(self):
        scramble = Exercise.objects.create(
            lesson=self.lesson, title="چیدن", type=Exercise.ExerciseType.SCRAMBLE,
            order=5, is_published=True,
        )
        word = Word.objects.create(
            word="Scramble", word_type="OTHER", meaning_fa="چیدن",
            level=self.level, is_published=True,
        )
        question = Question.objects.create(exercise=scramble, prompt="جمله را بچین", order=1)
        QuestionTarget.objects.create(
            question=question, word=word, role=QuestionTarget.Role.TESTED_ITEM
        )
        Answer.objects.create(question=question, text="Ich bin Sina", is_correct=True, order=1)

        session = self.build()

        for row in session["questions"]:
            self.assertNotEqual(row.pk, question.pk)

    def test_a_visitor_gets_a_session_from_the_first_published_lesson(self):
        anonymous = AnonymousUser()

        self.assertEqual(session_lesson(anonymous).pk, self.lesson.pk)
        session = build_session(anonymous, timezone.localdate(), self.lesson)
        self.assertEqual(session["goal"], 2)

    def test_the_skills_line_names_the_kinds_in_the_session(self):
        session = self.build()

        self.assertEqual(
            session_skills(session["questions"]),
            [self.meaning.type_label, self.spelling.type_label],
        )

    def test_a_lesson_with_nothing_left_today_has_no_questions(self):
        for question in Question.objects.filter(exercise__lesson=self.lesson):
            ExerciseAttempt.objects.create(
                user=self.user, exercise=question.exercise, question=question,
                is_correct=True,
            )

        session = self.build()

        self.assertEqual(session["goal"], 0)
        self.assertEqual(session["questions"], [])


class SessionProgressTests(SessionTests):
    """What «امروز» means by practice being done (``exercises/session.py::session_progress``).

    The day's practice step and «جلسهٔ امروز» are the same thing, so the verdict about it
    lives here, beside the rules that compose a session, instead of being counted by a page.
    The flaw this replaces: the day ticked its practice step once every skill had been
    touched — about five answers — while the session page still had ten questions to give.
    """

    def progress(self):
        return session_progress(self.user, timezone.localdate(), self.lesson)

    def answer(self, question):
        ExerciseAttempt.objects.create(
            user=self.user, exercise=question.exercise, question=question,
            answer=question.answers.get(is_correct=True), is_correct=True,
        )

    def work_through_a_sitting(self, topics):
        """Answer one question per topic, the way a learner works through a session."""
        for _ in range(topics):
            session = self.build()
            if not session["questions"]:
                break
            self.answer(session["questions"][0])

    def test_a_short_lesson_is_one_sitting_of_what_it_has(self):
        # Two topics, both untouched: the sitting is the two of them and it is not done, and
        # its size is the real one rather than the session ceiling.
        progress = self.progress()

        self.assertFalse(progress["done"])
        self.assertEqual(progress["size"], 2)

    def test_a_lesson_with_nothing_left_today_has_nothing_to_ask(self):
        self.work_through_a_sitting(2)

        progress = self.progress()

        self.assertTrue(progress["done"])
        # The sitting was exactly as long as the lesson had material for.
        self.assertEqual(progress["size"], 2)

    def test_a_sitting_is_done_once_a_whole_session_of_topics_is_behind_it(self):
        extra = Exercise.objects.create(
            lesson=self.lesson, title="بزرگ", type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            order=3, is_published=True,
        )
        for index in range(SESSION_SIZE + 5):
            word = Word.objects.create(
                word=f"Viel{index}", word_type="OTHER", meaning_fa=f"معنی {index}",
                level=self.level, is_published=True,
            )
            question = Question.objects.create(
                exercise=extra, prompt=f"معنی {word.word}؟", order=index + 1
            )
            QuestionTarget.objects.create(
                question=question, word=word, role=QuestionTarget.Role.TESTED_ITEM
            )
            Answer.objects.create(question=question, text=word.meaning_fa, is_correct=True, order=1)
            Answer.objects.create(question=question, text="چیز دیگری", is_correct=False, order=2)

        # One short of a sitting: the lesson still has eight topics left, so the step is not
        # finished and its size is what is really left.
        self.work_through_a_sitting(SESSION_SIZE - 1)

        short = self.progress()

        self.assertFalse(short["done"])
        self.assertEqual(short["size"], 8)

        # The question that completes the sitting finishes the day's step, even though the
        # lesson has more to give — more practice is allowed, it is just not owed.
        self.work_through_a_sitting(1)

        done = self.progress()

        self.assertTrue(done["done"])
        self.assertEqual(done["size"], SESSION_SIZE)


class SessionPageTests(TestCase):
    """The session page runs the shared runner, aimed at several exercises at once."""

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", is_published=True, order=1,
            estimated_time=10,
        )
        cls.word = Word.objects.create(
            word="hallo", word_type="OTHER", meaning_fa="سلام",
            level=cls.level, is_published=True,
        )
        cls.exercise = Exercise.objects.create(
            lesson=cls.lesson, title="معنی", type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            order=1, is_published=True,
        )
        cls.question = Question.objects.create(
            exercise=cls.exercise, prompt="معنی hallo؟", order=1
        )
        QuestionTarget.objects.create(
            question=cls.question, word=cls.word, role=QuestionTarget.Role.TESTED_ITEM
        )
        Answer.objects.create(question=cls.question, text="سلام", is_correct=True, order=1)
        Answer.objects.create(question=cls.question, text="خداحافظ", is_correct=False, order=2)

        cls.user = User.objects.create_user(
            username="page-learner", password="a-strong-password"
        )

    def test_the_page_renders_the_runner(self):
        response = self.client.get(reverse("exercises:session"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-runner")
        self.assertContains(response, "جلسهٔ امروز")

    def test_each_question_carries_the_exercise_it_came_from(self):
        response = self.client.get(reverse("exercises:session"))

        submit_url = reverse("exercises:exercise-submit", args=[self.exercise.pk])
        self.assertContains(response, f'data-submit-url="{submit_url}"')

    def test_a_visitor_gets_a_session_without_signing_in(self):
        response = self.client.get(reverse("exercises:session"))

        self.assertContains(response, "data-runner")

    def test_a_finished_day_shows_the_empty_state_instead_of_the_runner(self):
        self.client.force_login(self.user)
        ExerciseAttempt.objects.create(
            user=self.user, exercise=self.exercise, question=self.question,
            answer=self.question.answers.get(is_correct=True), is_correct=True,
        )

        response = self.client.get(reverse("exercises:session"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "exercise-empty")
        self.assertNotContains(response, "data-runner")

    def test_the_path_page_offers_the_session(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("lessons:practice-path"))

        self.assertContains(response, reverse("exercises:session"))

    def test_a_lesson_exercise_list_offers_the_session(self):
        response = self.client.get(
            reverse("exercises:exercise-list"), {"lesson": self.lesson.pk}
        )

        self.assertContains(response, reverse("exercises:session"))


class TypedAnswerSynonymTests(TestCase):
    """A typed question accepts every taught spelling of its Persian gloss.

    ``مادربزرگ`` is both ``Oma`` and ``Großmutter``. The question used to accept one and
    mark the other wrong, which is the failure that makes a learner stop writing. The
    runner's rule is now "typed means there are no wrong options", so a question can carry
    both spellings and still render an input.
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

        for title in [
            "Artikel: der, die, das und ein, eine, ein",
            "Der Plural der Nomen",
            "Perfekt mit „haben“",
            "Perfekt mit „sein“: Reisen in der Vergangenheit",
        ]:
            Grammar.objects.create(
                title=title, explanation="…", level=cls.level, is_published=True
            )

        cls.oma = Word.objects.create(
            word="Oma", word_type="NOUN", article="die", gender="F",
            meaning_fa="مادربزرگ", level=cls.level, is_published=True,
        )
        cls.grossmutter = Word.objects.create(
            word="Großmutter", word_type="NOUN", article="die", gender="F",
            meaning_fa="مادربزرگ", level=cls.level, is_published=True,
        )
        cls.buch = Word.objects.create(
            word="Buch", word_type="NOUN", article="das", gender="N",
            meaning_fa="کتاب", level=cls.level, is_published=True,
        )
        cls.lernen = Word.objects.create(
            word="lernen", word_type="VERB", meaning_fa="یاد گرفتن",
            level=cls.level, is_published=True,
        )

        words = [cls.oma, cls.grossmutter, cls.buch, cls.lernen]
        for index, word in enumerate(words, start=1):
            LessonWord.objects.create(lesson=cls.lesson, word=word, role="NEW", order=index)

        call_command("seed_a1_word_drills", stdout=StringIO())

    def writing_question(self, word):
        for question in Question.objects.filter(exercise__type="TRANSLATION"):
            for target in question.targets.all():
                if target.word_id == word.pk:
                    return question
        return None

    def test_the_question_accepts_every_spelling_of_the_gloss(self):
        question = self.writing_question(self.oma)
        accepted = [answer.text for answer in question.answers.all()]
        self.assertEqual(sorted(accepted), ["Großmutter", "Oma"])
        for answer in question.answers.all():
            self.assertTrue(answer.is_correct)

    def test_a_multi_spelling_question_still_renders_as_typed(self):
        question = self.writing_question(self.oma)
        rows = build_runner(question.exercise)
        row = None
        for candidate in rows:
            if candidate["id"] == question.pk:
                row = candidate
        self.assertEqual(row["kind"], TEXT)
        self.assertEqual(row["options"], [])

    def test_both_spellings_are_graded_correct_and_another_word_is_not(self):
        question = self.writing_question(self.oma)
        self.assertTrue(grade(question, None, "Oma")["is_correct"])
        self.assertTrue(grade(question, None, "Großmutter")["is_correct"])
        # Case is still ignored, the way every typed answer is compared.
        self.assertTrue(grade(question, None, "großmutter")["is_correct"])
        self.assertFalse(grade(question, None, "Buch")["is_correct"])


class TrueFalseRepairTests(TestCase):
    """``fix_a1_true_false_drills`` rebuilds the statements from Persian glosses.

    The authored item asserted "German X means <English gloss>" and keyed it غلط, so a
    learner who knew the word was marked wrong in 23 lessons. The repair writes both
    statements from Persian glosses, makes the false one false by its content, and swaps
    which statement is true every other lesson.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        # Order 2 (even), so the repair puts the false statement first.
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", is_published=True, order=2, estimated_time=10
        )
        cls.vater = Word.objects.create(
            word="Vater", word_type="NOUN", article="der", gender="M",
            meaning_fa="پدر", meaning_en="father", level=cls.level, is_published=True,
        )
        cls.mutter = Word.objects.create(
            word="Mutter", word_type="NOUN", article="die", gender="F",
            meaning_fa="مادر", level=cls.level, is_published=True,
        )
        for index, word in enumerate([cls.vater, cls.mutter], start=1):
            LessonWord.objects.create(lesson=cls.lesson, word=word, role="NEW", order=index)

        cls.exercise = Exercise.objects.create(
            lesson=cls.lesson, title="درست / غلط", instruction="گزارهٔ زیر درست است یا غلط؟",
            type=Exercise.ExerciseType.TRUE_FALSE, order=1, is_published=True,
        )
        cls._statement(1, "واژهٔ آلمانی «Vater» به فارسی معادل پدر است.", cls.vater)
        cls._statement(2, "واژهٔ آلمانی «Mutter» به فارسی معادل father است.", cls.mutter)

    @classmethod
    def _statement(cls, order, prompt, word):
        question = Question.objects.create(exercise=cls.exercise, prompt=prompt, order=order)
        Answer.objects.create(question=question, text="درست", is_correct=True, order=1)
        Answer.objects.create(question=question, text="غلط", is_correct=False, order=2)
        QuestionTarget.objects.create(question=question, word=word, role="TESTED_ITEM")
        return question

    def statements(self):
        return list(Question.objects.filter(exercise=self.exercise))

    def test_the_english_gloss_is_gone_and_the_key_is_right(self):
        call_command("fix_a1_true_false_drills", stdout=StringIO())

        for question in self.statements():
            self.assertNotIn("father", question.prompt)
            verdict = {}
            for answer in question.answers.all():
                verdict[answer.text] = answer.is_correct
            self.assertNotEqual(verdict["درست"], verdict["غلط"])

    def test_exactly_one_statement_is_true(self):
        call_command("fix_a1_true_false_drills", stdout=StringIO())

        true_count = 0
        for question in self.statements():
            for answer in question.answers.all():
                if answer.text == "درست" and answer.is_correct:
                    true_count += 1
        self.assertEqual(true_count, 1)

    def test_the_false_statement_borrows_another_words_gloss(self):
        call_command("fix_a1_true_false_drills", stdout=StringIO())

        false_question = None
        for question in self.statements():
            for answer in question.answers.all():
                if answer.text == "غلط" and answer.is_correct:
                    false_question = question
        self.assertIsNotNone(false_question)
        self.assertIn("معادل «", false_question.prompt)
        # The word it names does not get its own meaning back as the statement.
        for answer in false_question.answers.all():
            self.assertIn(answer.text, ["درست", "غلط"])


class ExportExcludesGeneratedTests(TestCase):
    """The authored export must not carry generated exercises.

    The listening exercise was exported *and* generated, so two owners wrote it and every
    lesson ended up with two identical copies. ``export_a1_exercises`` now leaves the
    generated families out, and the import refuses a file that still carries one.
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
        cls.authored = Exercise.objects.create(
            lesson=cls.lesson, title="واژگان — انتخاب معنی", instruction="…",
            type=Exercise.ExerciseType.MULTIPLE_CHOICE, order=1, is_published=True,
        )
        question = Question.objects.create(exercise=cls.authored, prompt="…", order=1)
        Answer.objects.create(question=question, text="سلام", is_correct=True, order=1)
        Answer.objects.create(question=question, text="خداحافظ", is_correct=False, order=2)

        cls.generated_exercise = Exercise.objects.create(
            lesson=cls.lesson, title=generated.LISTENING_DRILL_PREFIX, instruction="…",
            type=Exercise.ExerciseType.LISTENING, order=2, is_published=True,
        )
        question = Question.objects.create(exercise=cls.generated_exercise, prompt="…", order=1)
        Answer.objects.create(question=question, text="الف", is_correct=True, order=1)

    def test_generated_exercises_are_not_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "out.json"
            call_command("export_a1_exercises", output=str(path), stdout=StringIO())
            payload = json.loads(path.read_text(encoding="utf-8"))

        titles = []
        for entry in payload["exercises"]:
            titles.append(entry["title"])
        self.assertEqual(titles, ["واژگان — انتخاب معنی"])

    def test_a_file_carrying_a_generated_exercise_is_refused(self):
        payload = {
            "level": "A1",
            "topic": "…",
            "exercises": [
                {
                    "lesson_order": 1,
                    "lesson_title": "Lektion 1",
                    "title": generated.LISTENING_DRILL_PREFIX,
                    "instruction": "…",
                    "type": "LISTENING",
                    "difficulty": "MEDIUM",
                    "order": 9,
                    "is_published": True,
                    "questions": [],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "stale.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(CommandError):
                call_command(
                    "import_a1_exercises",
                    data=str(path),
                    stdout=StringIO(),
                    stderr=StringIO(),
                )


class SeedA1ReadingDrillsTests(TestCase):
    """``seed_a1_reading_drills``: a lesson's own dialogue becomes a short text to read.

    The course practised reading with one line at a time — a single German sentence and its
    meaning on offer — which is a translation question with a reading label. A1 LESEN asks
    the learner to hold a text together and find something in it. These tests are about the
    rules that make a real task out of content that already exists: the text is the lesson's
    own dialogue, the wrong options are the text's own lines, one question asks what the text
    does *not* say, and a question never claims to know which word a learner misread.
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
        # A lesson with a dialogue to read, and sentences the text does not carry.
        cls.speaking_lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 2", is_published=True, order=2, estimated_time=10
        )
        # Too short for a text: two lines are not a text.
        cls.short_lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 3", is_published=True, order=3, estimated_time=10
        )

        cls.lines = [
            cls.sentence("Guten Tag. Ich suche eine Wohnung.", "روز بخیر. دنبال یک آپارتمان هستم."),
            cls.sentence("Die Wohnung hat zwei Zimmer.", "آپارتمان دو اتاق دارد."),
            cls.sentence("Was kostet die Miete?", "اجاره چند است؟"),
            cls.sentence("Die Miete kostet 600 Euro.", "اجاره ۶۰۰ یورو است."),
        ]
        for index, sentence in enumerate(cls.lines, start=1):
            LessonSentence.objects.create(
                lesson=cls.lesson, sentence=sentence,
                role=LessonSentence.Role.DIALOGUE, order=index,
            )

        # The lesson's other sentences: the source of wrong options and of the sentence that
        # is not in the text.
        cls.outsider = cls.sentence("Ich wohne in Hamburg.", "من در هامبورگ زندگی می‌کنم.")
        LessonSentence.objects.create(
            lesson=cls.lesson, sentence=cls.outsider,
            role=LessonSentence.Role.EXAMPLE, order=5,
        )

        # A dialogue that repeats itself: ``Guten Morgen!`` sits inside the next line, so
        # asking which line carries its meaning has two answers unless it is left out.
        cls.contained = cls.sentence("Guten Morgen!", "صبح بخیر!")
        cls.container = cls.sentence("Guten Morgen! Wie geht's?", "صبح بخیر! چطوری؟")
        cls.third = cls.sentence("Danke, gut.", "ممنون، خوبم.")
        cls.fourth = cls.sentence("Und dir?", "تو چطوری؟")
        for index, sentence in enumerate(
            [cls.contained, cls.container, cls.third, cls.fourth], start=1
        ):
            LessonSentence.objects.create(
                lesson=cls.speaking_lesson, sentence=sentence,
                role=LessonSentence.Role.DIALOGUE, order=index,
            )

        cls.one = cls.sentence("Ja.", "بله.")
        cls.two = cls.sentence("Nein.", "نه.")
        for index, sentence in enumerate([cls.one, cls.two], start=1):
            LessonSentence.objects.create(lesson=cls.short_lesson, sentence=sentence, order=index)

    @classmethod
    def sentence(cls, text, translation_fa):
        return Sentence.objects.create(
            text=text, translation_fa=translation_fa, level=cls.level, is_published=True
        )

    def run_command(self, *args):
        out = StringIO()
        err = StringIO()
        call_command("seed_a1_reading_drills", *args, stdout=out, stderr=err)
        return out.getvalue()

    def exercise_for(self, lesson):
        return Exercise.objects.filter(
            title__startswith=seed_a1_reading_drills.TITLE_PREFIX, lesson=lesson
        ).first()

    def test_every_lesson_with_a_text_gets_one_exercise(self):
        self.run_command()

        first = self.exercise_for(self.lesson)
        second = self.exercise_for(self.speaking_lesson)

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.type, Exercise.ExerciseType.READING)
        self.assertTrue(first.is_published)
        self.assertIsNone(self.exercise_for(self.short_lesson))

    def test_the_passage_is_the_whole_text_not_one_line(self):
        self.run_command()

        rows = build_runner(self.exercise_for(self.lesson))
        wanted = "\n".join(sentence.text for sentence in self.lines)

        self.assertEqual(len(rows), len(self.lines) + 1)
        for row in rows:
            self.assertEqual(row["passage"], wanted)

    def test_a_meaning_question_is_answered_from_the_text(self):
        self.run_command()

        lines = set()
        for sentence in self.lines:
            lines.add(sentence.text)

        rows = build_runner(self.exercise_for(self.lesson))
        asked = 0

        for row in rows:
            if row["prompt"] != seed_a1_reading_drills.ABSENT_PROMPT:
                asked += 1
                correct = None
                for option in row["options"]:
                    if option.is_correct:
                        correct = option.text
                self.assertIn(correct, lines)
                self.assertEqual(len(row["options"]), seed_a1_reading_drills.OPTIONS)

        self.assertEqual(asked, len(self.lines))

    def test_the_last_question_asks_what_the_text_does_not_say(self):
        self.run_command()

        rows = build_runner(self.exercise_for(self.lesson))
        row = rows[-1]

        self.assertEqual(row["prompt"], seed_a1_reading_drills.ABSENT_PROMPT)

        correct = None
        for option in row["options"]:
            if option.is_correct:
                correct = option.text
        self.assertEqual(correct, self.outsider.text)

    def test_a_line_that_sits_inside_another_is_left_out(self):
        """``Guten Morgen!`` is inside ``Guten Morgen! Wie geht's?`` — one line, not two.

        Offering both would make "which line carries this meaning?" a question with two
        defensible answers.
        """
        self.run_command()

        rows = build_runner(self.exercise_for(self.speaking_lesson))
        passage = rows[0]["passage"].split("\n")

        self.assertEqual(len(passage), 3)
        for line in passage:
            for other in passage:
                if line == other:
                    continue
                self.assertNotIn(line, other)

    def test_a_line_the_text_almost_has_is_not_offered_as_absent(self):
        """The lesson's only other sentence repeats a line, so it is not a fair answer.

        A reader who sees ``Guten Morgen!`` in the text would be right to say the sentence is
        there, so the lesson gets no "which sentence is not in the text?" question at all.
        """
        self.run_command()

        rows = build_runner(self.exercise_for(self.speaking_lesson))

        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertNotEqual(row["prompt"], seed_a1_reading_drills.ABSENT_PROMPT)

    def test_no_question_moves_word_progress(self):
        self.run_command()

        questions = Question.objects.filter(
            exercise__title__startswith=seed_a1_reading_drills.TITLE_PREFIX
        )
        self.assertFalse(
            QuestionTarget.objects.filter(question__in=questions, word__isnull=False).exists()
        )

    def test_the_rebuild_is_refused_while_a_learner_has_answered(self):
        self.run_command()

        exercise = self.exercise_for(self.lesson)
        learner = User.objects.create_user(username="sara", password="geheim123")
        question = exercise.questions.first()
        ExerciseAttempt.objects.create(
            user=learner, exercise=exercise, question=question, is_correct=True
        )

        with self.assertRaises(CommandError):
            self.run_command()

        self.run_command("--yes-replace-history")
        self.assertEqual(
            Exercise.objects.filter(
                title__startswith=seed_a1_reading_drills.TITLE_PREFIX
            ).count(),
            2,
        )


class LessonDrillCapTests(TestCase):
    """The word-drill cap: a lesson may teach more words than its batteries ask about.

    Lesson 24 taught 148 new words and asked 576 questions about them — a wall at the end of
    the course rather than practice. The cap decides how much a lesson asks in one sitting;
    the words past it stay on the lesson page and still reach the learner, because
    ``vocabulary/schedule.py::new_words`` offers every linked word the learner has reached and
    never practised. These tests pin the cap where the rule lives, so it cannot quietly grow
    back.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Gross", is_published=True, order=1, estimated_time=10
        )
        cls.review_lesson = Lesson.objects.create(
            course=cls.course, title="Wiederholung", is_published=True, order=2,
            estimated_time=10,
        )

        cls.over = seed_a1_word_drills.MAX_DRILL_WORDS + 3

        for index in range(1, cls.over + 1):
            word = Word.objects.create(
                word=f"wort{index}", word_type=Word.WordType.ADJECTIVE,
                meaning_fa=f"معنی {index}", level=cls.level, is_published=True,
            )
            LessonWord.objects.create(
                lesson=cls.lesson, word=word, role=LessonWord.Role.NEW, order=index
            )
            # The review lesson revisits the same words and introduces none.
            LessonWord.objects.create(
                lesson=cls.review_lesson, word=word, role=LessonWord.Role.REVIEW, order=index
            )

        Grammar.objects.create(
            title="Artikel: der, die, das und ein, eine, ein", explanation="…",
            level=cls.level, is_published=True,
        )
        Grammar.objects.create(
            title="Der Plural der Nomen", explanation="…", level=cls.level, is_published=True,
        )
        Grammar.objects.create(
            title="Perfekt mit „haben“", explanation="…", level=cls.level, is_published=True,
        )
        Grammar.objects.create(
            title="Perfekt mit „sein“: Reisen in der Vergangenheit", explanation="…",
            level=cls.level, is_published=True,
        )

    def test_a_lesson_that_teaches_more_drills_less(self):
        drilled = seed_a1_word_drills.Command().published_words(self.lesson)

        self.assertEqual(len(drilled), seed_a1_word_drills.MAX_DRILL_WORDS)
        self.assertEqual(drilled[0].word, "wort1")
        self.assertEqual(
            drilled[-1].word, f"wort{seed_a1_word_drills.MAX_DRILL_WORDS}"
        )

    def test_a_review_lesson_is_capped_too(self):
        self.run_command()

        asked = QuestionTarget.objects.filter(
            question__exercise__lesson=self.review_lesson,
            role=QuestionTarget.Role.TESTED_ITEM,
            word__isnull=False,
        ).values("word").distinct().count()

        self.assertLessEqual(asked, seed_a1_word_drills.MAX_DRILL_WORDS)

    def test_the_cap_does_not_orphan_a_word(self):
        """Every word past the cap is still linked, so the review queue can still offer it."""
        self.run_command()

        asked = set(
            QuestionTarget.objects.filter(
                question__exercise__lesson=self.lesson,
                role=QuestionTarget.Role.TESTED_ITEM,
                word__isnull=False,
            ).values_list("word_id", flat=True)
        )
        linked = set(
            LessonWord.objects.filter(lesson=self.lesson).values_list("word_id", flat=True)
        )

        self.assertTrue(asked.issubset(linked))
        self.assertEqual(len(linked), self.over)
        self.assertLess(len(asked), len(linked))

    def run_command(self):
        out = StringIO()
        err = StringIO()
        call_command("seed_a1_word_drills", stdout=out, stderr=err)
        return out.getvalue()


class SeedA1DictationCapTests(TestCase):
    """``seed_a1_dictation_drills``: a lesson that teaches a lot dictates a little.

    The audit measured lesson 24's dictation battery at 25 exercises and 154 questions — the
    heaviest block in the course, and the last thing between a learner and the end of the
    lesson. The cap is the same one the word drills use, and these tests pin both halves of
    the promise: the lesson asks less, and no word is taken away from the learner by it.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Gross", is_published=True, order=1, estimated_time=10
        )
        cls.second = Lesson.objects.create(
            course=cls.course, title="Klein", is_published=True, order=2, estimated_time=10
        )

        cls.over = seed_a1_dictation_drills.MAX_DRILL_WORDS + 3

        for index in range(1, cls.over + 1):
            word = Word.objects.create(
                word=f"wort{index}", word_type=Word.WordType.OTHER,
                meaning_fa=f"معنی {index}", level=cls.level, is_published=True,
                audio=f"words/audio/wort{index}.mp3",
            )
            LessonWord.objects.create(
                lesson=cls.lesson, word=word, role=LessonWord.Role.NEW, order=index
            )

        cls.small = Word.objects.create(
            word="klein", word_type=Word.WordType.ADJECTIVE, meaning_fa="کوچک",
            level=cls.level, is_published=True, audio="words/audio/klein.mp3",
        )
        LessonWord.objects.create(
            lesson=cls.second, word=cls.small, role=LessonWord.Role.NEW, order=1
        )

    def run_command(self):
        out = StringIO()
        err = StringIO()
        call_command("seed_a1_dictation_drills", stdout=out, stderr=err)
        return out.getvalue()

    def test_a_lesson_that_teaches_more_dictates_less(self):
        dictated = seed_a1_dictation_drills.Command().published_words(self.lesson)

        self.assertEqual(len(dictated), seed_a1_dictation_drills.MAX_DRILL_WORDS)
        self.assertEqual(dictated[0].word, "wort1")
        self.assertEqual(
            dictated[-1].word, f"wort{seed_a1_dictation_drills.MAX_DRILL_WORDS}"
        )

    def test_no_lesson_asks_more_than_the_cap(self):
        self.run_command()

        counts = {}
        for question in Question.objects.filter(exercise__lesson=self.lesson).exclude(audio=""):
            counts[question.exercise_id] = counts.get(question.exercise_id, 0) + 1

        self.assertTrue(counts)
        for count in counts.values():
            self.assertLessEqual(count, seed_a1_dictation_drills.MAX_DRILL_WORDS)

    def test_the_cap_does_not_orphan_a_word(self):
        """Every word past the cap is still linked, so the review queue can still offer it."""
        self.run_command()

        asked = set(
            QuestionTarget.objects.filter(
                question__exercise__lesson=self.lesson,
                role=QuestionTarget.Role.TESTED_ITEM,
                word__isnull=False,
            ).values_list("word_id", flat=True)
        )
        linked = set(
            LessonWord.objects.filter(lesson=self.lesson).values_list("word_id", flat=True)
        )

        self.assertTrue(asked.issubset(linked))
        self.assertEqual(len(linked), self.over)
        self.assertLess(len(asked), len(linked))

    def test_a_small_lesson_is_untouched_by_the_cap(self):
        self.run_command()

        asked = QuestionTarget.objects.filter(
            question__exercise__lesson=self.second,
            role=QuestionTarget.Role.TESTED_ITEM,
            word=self.small,
        ).count()

        self.assertEqual(asked, 1)
