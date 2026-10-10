"""Structural tests for the A1 course content.

A Django test database starts empty, while the course content lives in the data
modules (``lessons/data/*``) and the vocabulary JSON files (``vocabulary/data/*``).
``A1ContentTestCase`` therefore builds the same content in the test database once per
test class:

1. ``import_a1_words --no-audio`` creates the A1 level and all 1008 words.
2. ``seed_a1_course`` creates the course, lessons, blocks, links, grammar, sentences.

The tests then check the real structure: ordering, duplicates, REVIEW-before-NEW,
level consistency, and the German word data itself (article vs. gender, capitalisation,
plural forms, perfect auxiliary).

Run with::

    python manage.py test lessons -v 2
"""

import io
import json
import re
from datetime import date, timedelta
from pathlib import Path

from django.contrib.auth.models import AnonymousUser, User
from django.core.management import call_command
from django.db.models import Count
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from exercises.models import Answer, Exercise, ExerciseAttempt, Question, QuestionTarget
from lessons.models import (
    Course,
    LanguageLevel,
    Lesson,
    LessonContent,
    LessonGrammar,
    LessonProgress,
    LessonSentence,
    LessonWord,
)
from lessons.progress import complete_lesson, progress_state, record_step
from lessons.check import CHECK_SIZE, check_questions, pass_needed
from lessons.skill_path import MIN_ANSWERS, XP_PER_NODE, build_path, day_steps, lesson_practice, skill_of
from lessons.readiness import (
    course_progress,
    exercise_progress,
    goal_of,
    grammar_coverage,
    grammar_practice,
    grammar_progress,
    grammar_review,
    learning_pace,
    missed_grammar,
    percent,
    readiness,
    vocabulary_progress,
    word_coverage,
)
from lessons.today import (
    day_summary,
    exercises_done_today,
    last_activity,
    lesson_to_work_on,
    next_lesson,
    started_lesson,
)
from lessons.views import WORDS_PER_STEP
from vocabulary.models import Grammar, Sentence, Word, WordProgress

LEVEL = "A1"


class A1ContentTestCase(TestCase):
    """Loads the A1 wordlist and the course into the test database."""

    @classmethod
    def setUpTestData(cls):
        quiet = {"stdout": io.StringIO(), "stderr": io.StringIO()}
        call_command("import_a1_words", "--no-audio", **quiet)
        call_command("seed_a1_course", **quiet)
        cls.level = LanguageLevel.objects.get(level=LEVEL)
        cls.course = Course.objects.get(language_level=cls.level)


class CourseStructureTests(A1ContentTestCase):
    """The course, its lessons and their ordering."""

    def test_course_exists_once_per_level(self):
        self.assertEqual(Course.objects.filter(language_level=self.level).count(), 1)

    def test_lesson_count_and_contiguous_order(self):
        orders = list(self.course.lessons.order_by("order").values_list("order", flat=True))
        self.assertEqual(orders, list(range(1, len(orders) + 1)), "lesson order must be 1…n without gaps")

    def test_lessons_have_metadata(self):
        for lesson in self.course.lessons.all():
            with self.subTest(lesson=lesson.order):
                self.assertTrue(lesson.title.strip())
                self.assertTrue(lesson.description.strip())
                self.assertGreater(lesson.estimated_time, 0)

    def test_every_lesson_has_a_persian_title_and_summary(self):
        # The Persian pages show these, so a lesson without one would fall back to its
        # German name on every learner screen (Lesson.display_title).
        for lesson in self.course.lessons.all():
            with self.subTest(lesson=lesson.order):
                self.assertTrue(lesson.title_fa.strip(), "the lesson has no Persian title")
                self.assertTrue(lesson.description_fa.strip(), "the lesson has no Persian summary")
                self.assertEqual(lesson.display_title, lesson.title_fa)
                self.assertEqual(lesson.display_description, lesson.description_fa)

    def test_a_lesson_without_a_persian_title_falls_back_to_its_german_one(self):
        lesson = Lesson.objects.get(course=self.course, order=1)
        lesson.title_fa = ""
        lesson.description_fa = ""
        self.assertEqual(lesson.display_title, lesson.title)
        self.assertEqual(lesson.display_description, lesson.description)

    def test_every_lesson_has_ordered_content_blocks(self):
        for lesson in self.course.lessons.all():
            with self.subTest(lesson=lesson.order):
                blocks = list(lesson.contents.order_by("order"))
                self.assertTrue(blocks, "a lesson without content blocks is empty")
                self.assertEqual([b.order for b in blocks], list(range(1, len(blocks) + 1)))
                for block in blocks:
                    self.assertIn(block.type, dict(LessonContent.ContentType.choices))
                    self.assertTrue(block.title.strip())
                    self.assertTrue(block.body.strip())
                    self.assertIn("English:", block.body, "every block carries a one-line English gloss")

    def test_content_block_orders_are_unique_per_lesson(self):
        duplicates = (
            LessonContent.objects.values("lesson", "order").annotate(total=Count("id")).filter(total__gt=1)
        )
        self.assertFalse(duplicates.exists(), "unique_content_order_per_lesson is violated")


class LessonWordLinkTests(A1ContentTestCase):
    """LessonWord links: order, duplicates, roles and coverage."""

    def test_word_orders_are_contiguous_including_review(self):
        for lesson in self.course.lessons.all():
            links = list(lesson.lesson_words.order_by("order"))
            with self.subTest(lesson=lesson.order):
                self.assertEqual(
                    [link.order for link in links],
                    list(range(1, len(links) + 1)),
                    "NEW and REVIEW links share one continuous order per lesson",
                )

    def test_words_are_not_repeated_in_a_lesson(self):
        duplicates = (
            LessonWord.objects.values("lesson", "word").annotate(total=Count("id")).filter(total__gt=1)
        )
        self.assertFalse(duplicates.exists(), "unique_word_per_lesson is violated")

    def test_review_words_were_introduced_as_new_earlier(self):
        introduced = set()
        for lesson in self.course.lessons.order_by("order"):
            for link in lesson.lesson_words.all():
                if link.role == LessonWord.Role.REVIEW:
                    self.assertIn(
                        link.word_id,
                        introduced,
                        f"{link.word} is REVIEW in lesson {lesson.order} but was never NEW before",
                    )
            introduced |= set(
                lesson.lesson_words.filter(role=LessonWord.Role.NEW).values_list("word_id", flat=True)
            )

    def test_linked_words_belong_to_the_level(self):
        wrong = LessonWord.objects.exclude(word__level=self.level)
        self.assertFalse(wrong.exists(), "a lesson links a word from another level")

    def test_every_level_word_is_linked_somewhere(self):
        linked = LessonWord.objects.values_list("word_id", flat=True).distinct()
        unlinked = Word.objects.filter(level=self.level).exclude(id__in=linked).order_by("word")
        self.assertFalse(
            unlinked.exists(),
            f"{unlinked.count()} words are not linked to any lesson: "
            + ", ".join(unlinked.values_list("word", flat=True)[:20]),
        )

    def test_review_links_carry_earlier_vocabulary_forward(self):
        total = LessonWord.objects.count()
        reviews = LessonWord.objects.filter(role=LessonWord.Role.REVIEW).count()
        self.assertGreater(reviews, 0, "review links should exist")
        self.assertLess(reviews, total / 2, "most links introduce new vocabulary")


class GrammarAndSentenceTests(A1ContentTestCase):
    """Grammar topics and sentences attached to lessons."""

    def test_grammar_orders_are_contiguous(self):
        for lesson in self.course.lessons.all():
            links = list(lesson.lesson_grammars.order_by("order"))
            with self.subTest(lesson=lesson.order):
                self.assertEqual([link.order for link in links], list(range(1, len(links) + 1)))

    def test_grammar_is_not_repeated_in_a_lesson(self):
        duplicates = (
            LessonGrammar.objects.values("lesson", "grammar").annotate(total=Count("id")).filter(total__gt=1)
        )
        self.assertFalse(duplicates.exists(), "unique_grammar_per_lesson is violated")

    def test_grammar_topics_are_complete_and_linked(self):
        for grammar in Grammar.objects.all():
            with self.subTest(grammar=grammar.title):
                self.assertEqual(grammar.level, self.level)
                self.assertTrue(grammar.explanation.strip())
                self.assertIn("English:", grammar.explanation)
        linked = LessonGrammar.objects.values_list("grammar_id", flat=True).distinct()
        orphans = Grammar.objects.exclude(id__in=linked)
        self.assertFalse(
            orphans.exists(),
            f"unlinked grammar topics: {list(orphans.values_list('title', flat=True))}",
        )

    def test_sentence_orders_are_contiguous(self):
        for lesson in self.course.lessons.all():
            links = list(lesson.lesson_sentences.order_by("order"))
            with self.subTest(lesson=lesson.order):
                self.assertEqual([link.order for link in links], list(range(1, len(links) + 1)))

    def test_sentence_is_not_repeated_in_a_lesson(self):
        duplicates = (
            LessonSentence.objects.values("lesson", "sentence").annotate(total=Count("id")).filter(total__gt=1)
        )
        self.assertFalse(duplicates.exists(), "unique_sentence_per_lesson is violated")

    def test_sentences_have_german_text_and_persian_translation(self):
        for sentence in Sentence.objects.all():
            with self.subTest(sentence=sentence.text):
                self.assertTrue(sentence.text.strip())
                self.assertTrue(sentence.translation_fa.strip())
                self.assertEqual(sentence.level, self.level)

    def test_dialogue_lines_have_speakers_and_examples_do_not(self):
        for link in LessonSentence.objects.select_related("sentence"):
            with self.subTest(sentence=link.sentence.text):
                if link.role == LessonSentence.Role.DIALOGUE:
                    self.assertTrue(link.speaker.strip(), "dialogue lines name their speaker")
                else:
                    self.assertEqual(link.speaker, "", "only dialogue lines carry a speaker")
                self.assertIn(link.role, dict(LessonSentence.Role.choices))

    def test_no_orphan_sentences(self):
        linked = LessonSentence.objects.values_list("sentence_id", flat=True).distinct()
        orphans = Sentence.objects.exclude(id__in=linked)
        self.assertFalse(orphans.exists(), f"{orphans.count()} sentences are unused")


class WordDataTests(A1ContentTestCase):
    """The German of the vocabulary itself."""

    def test_nouns_have_article_gender_and_capitalisation(self):
        expected = {
            "der": Word.Gender.MASCULINE,
            "die": Word.Gender.FEMININE,
            "das": Word.Gender.NEUTER,
        }
        for word in Word.objects.filter(level=self.level, word_type=Word.WordType.NOUN):
            with self.subTest(word=word.word):
                self.assertTrue(word.word[:1].isupper(), "German nouns are capitalised")

                # A few German nouns exist only in the plural (die Eltern, die Ferien,
                # die Leute ...). There is no singular, so there is no gender to store;
                # the data keeps those with gender = null and the plural article "die".
                # Every other noun still has to carry der/die/das, with a gender that
                # agrees with the article.
                if word.gender is None:
                    self.assertEqual(word.article, "die", f"{word.word} is plural-only and takes die")
                    continue

                self.assertIn(word.article, expected, f"{word.word} needs der/die/das")
                self.assertEqual(word.gender, expected[word.article], "article must match gender")

    def test_non_nouns_carry_no_article_or_gender(self):
        for word in Word.objects.filter(level=self.level).exclude(word_type=Word.WordType.NOUN):
            with self.subTest(word=word.word):
                self.assertEqual(word.article, "")
                self.assertIsNone(word.gender)

    def test_verbs_declare_a_perfect_auxiliary(self):
        for word in Word.objects.filter(level=self.level, word_type=Word.WordType.VERB):
            with self.subTest(word=word.word):
                self.assertIn(word.perfect_auxiliary, dict(Word.PerfectAuxiliary.choices))

    def test_every_word_has_a_persian_meaning(self):
        missing = Word.objects.filter(level=self.level, meaning_fa="")
        self.assertFalse(missing.exists(), f"words without a Persian meaning: {missing.count()}")

    def test_plural_forms_are_written_with_their_article(self):
        nouns = Word.objects.filter(level=self.level, word_type=Word.WordType.NOUN).exclude(plural=None)
        for word in nouns.exclude(plural=""):
            with self.subTest(word=word.word):
                self.assertTrue(word.plural.startswith("die "), f"{word.word} → {word.plural}")

    def test_the_exam_important_flag_is_read_off_the_word_itself(self):
        # `import_a1_words` sets it from the entry's own fields, so a re-import keeps it in
        # step. Every flagged word must satisfy the rule, and ordinary words must not.
        flagged = Word.objects.filter(level=self.level, is_exam_important=True)
        self.assertTrue(flagged.exists(), "no word is marked exam-important")
        self.assertLess(flagged.count(), Word.objects.filter(level=self.level).count() / 2)

        for word in flagged:
            with self.subTest(word=word.word):
                plural = word.plural or ""
                has_umlaut = "ä" in plural or "ö" in plural or "ü" in plural
                self.assertTrue(
                    word.is_separable or word.perfect_auxiliary == "SEIN" or has_umlaut,
                    f"{word.word} is flagged but is none of the three forms the exam tests",
                )


class SeedCommandTests(A1ContentTestCase):
    """The seed command must be idempotent."""

    def counts(self):
        return (
            Course.objects.count(),
            LessonContent.objects.count(),
            LessonWord.objects.count(),
            LessonGrammar.objects.count(),
            LessonSentence.objects.count(),
            Grammar.objects.count(),
            Sentence.objects.count(),
        )

    def test_reseeding_creates_no_duplicates(self):
        from lessons.data import a1_lessons_a, a1_lessons_b

        before = self.counts()
        quiet = {"stdout": io.StringIO(), "stderr": io.StringIO()}
        call_command("seed_a1_course", **quiet)
        call_command("seed_a1_course", **quiet)
        self.assertEqual(before, self.counts(), "re-running the seed command must not duplicate anything")
        self.assertEqual(
            self.course.lessons.count(),
            len(a1_lessons_a.LESSONS) + len(a1_lessons_b.LESSONS),
        )

    def test_data_modules_validate_cleanly(self):
        quiet = {"stdout": io.StringIO(), "stderr": io.StringIO()}
        call_command("seed_a1_course", "--check", **quiet)


class DashboardTests(TestCase):
    """The product home: useful without a login, honest about what it knows.

    Unlike the content classes above this one builds its own small course
    instead of seeding the real one, so it is fast, independent of the
    vocabulary data and runnable on its own::

        python manage.py test lessons.tests.DashboardTests

    (The structural classes above cannot complete while the vocabulary data
    mismatch described in AGENT_MEMORY.md §5 stands.)
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level,
            title="دورهٔ آلمانی A1",
            description="از صفر تا A1.",
            is_published=True,
        )
        cls.lessons = [
            Lesson.objects.create(
                course=cls.course,
                title=f"درس شماره {number}",
                order=number,
                estimated_time=10 + number,
                is_published=True,
            )
            for number in range(1, 7)
        ]
        cls.unpublished = Lesson.objects.create(
            course=cls.course, title="درس منتشرنشده", order=99, estimated_time=5, is_published=False
        )
        Word.objects.create(
            word="Buch", word_type="NOUN", article="das", gender="N",
            meaning_fa="کتاب", level=cls.level, is_published=True,
        )
        Word.objects.create(
            word="versteckt", word_type="OTHER", meaning_fa="پنهان", level=cls.level, is_published=False
        )
        Exercise.objects.create(
            lesson=cls.lessons[0], title="تمرین نمونه", type="MULTIPLE_CHOICE", order=1, is_published=True
        )
        Exercise.objects.create(
            lesson=cls.lessons[0], title="تمرین پیش‌نویس", type="TRUE_FALSE", order=2, is_published=False
        )

    def test_renders_for_anonymous_visitors(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard.html")

    def test_offers_the_first_lesson_as_the_next_step(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, self.lessons[0].title)
        self.assertContains(response, reverse("lessons:lesson-detail", args=[self.lessons[0].pk]))

    def test_only_published_lessons_and_content_are_counted(self):
        """The advertised numbers are the course's own live rows, not the whole database."""
        LessonWord.objects.create(
            lesson=self.lessons[0], word=Word.objects.get(word="Buch"), role="NEW", order=1
        )
        # A published word that only a draft lesson links to is not part of the course yet,
        # so it must not be advertised either (the dashboard used to count every word row,
        # including the thousands that belong to no lesson at all).
        draft_word = Word.objects.create(
            word="Entwurfswort", word_type="NOUN", article="das", gender="N",
            meaning_fa="واژهٔ پیش‌نویس", level=self.level, is_published=True,
        )
        LessonWord.objects.create(
            lesson=self.unpublished, word=draft_word, role="NEW", order=1
        )

        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["lesson_total"], len(self.lessons))
        self.assertEqual(response.context["word_total"], 1)
        self.assertEqual(response.context["exercise_total"], 1)
        self.assertNotContains(response, self.unpublished.title)
        self.assertNotContains(response, "پیش‌نویس")

    def test_hands_the_lesson_list_to_the_browser(self):
        """The client needs id -> title/url to resolve what localStorage knows."""
        response = self.client.get(reverse("home"))
        payload = response.context["lessons_payload"]
        self.assertEqual([entry["id"] for entry in payload], [lesson.pk for lesson in self.lessons])
        self.assertContains(response, 'id="dashboard-lessons"')

    def test_does_not_claim_server_side_learning_history(self):
        """No progress model exists: the page must say so, not imply otherwise."""
        response = self.client.get(reverse("home"))
        self.assertContains(response, "همین مرورگر")
        self.assertNotContains(response, "روز پیاپی")

    def test_anonymous_visitors_see_an_optional_account_prompt(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("accounts:signup"))
        self.assertContains(response, reverse("accounts:login"))

    def test_signed_in_visitors_are_greeted_and_not_upsold(self):
        user = User.objects.create_user(username="sina", password="a-strong-password")
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "sina")
        self.assertNotContains(response, "حساب کاربری (اختیاری)")

    def test_empty_state_when_no_course_is_published(self):
        Course.objects.update(is_published=False)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هنوز دوره‌ای منتشر نشده است")

    def test_lesson_page_tells_the_browser_which_lesson_was_opened(self):
        """The visit script reads data-lesson-id; without it the dashboard is blind."""
        response = self.client.get(reverse("lessons:lesson-detail", args=[self.lessons[0].pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-lesson-id="{self.lessons[0].pk}"')


class DashboardReviewTests(TestCase):
    """The dashboard's personal review panel: the learner's own mistakes, and nothing
    invented.

    Builds its own tiny course rather than seeding the real content, so it runs on its
    own::

        python manage.py test lessons.tests.DashboardReviewTests

    The panel exists only when there is something to review. A learner with a clean
    record, and a visitor we cannot identify, both get no panel at all — never a
    summary written to fill the space.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="دورهٔ آلمانی A1", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", order=1, estimated_time=10, is_published=True
        )
        cls.word = Word.objects.create(
            word="Buch", word_type="NOUN", article="das", gender="N",
            meaning_fa="کتاب", level=cls.level, is_published=True,
        )
        cls.word_that_was_never_missed = Word.objects.create(
            word="Tisch", word_type="NOUN", article="der", gender="M",
            meaning_fa="میز", level=cls.level, is_published=True,
        )
        cls.exercise = Exercise.objects.create(
            lesson=cls.lesson, title="واژگان درس ۱", type="MULTIPLE_CHOICE",
            order=1, is_published=True,
        )
        question = Question.objects.create(exercise=cls.exercise, prompt="معنی Buch؟", order=1)
        Answer.objects.create(question=question, text="کتاب", is_correct=True, order=1)
        QuestionTarget.objects.create(question=question, word=cls.word, role="TESTED_ITEM")

    def sign_in(self, username):
        user = User.objects.create_user(username=username, password="a-strong-password")
        self.client.force_login(user)
        return user

    def test_an_anonymous_visitor_gets_no_review_panel(self):
        response = self.client.get(reverse("home"))
        self.assertIsNone(response.context["review"])
        self.assertNotContains(response, "مرور شخصی")

    def test_a_learner_without_mistakes_gets_no_review_panel(self):
        user = self.sign_in("sauber")
        WordProgress.objects.create(
            user=user, word=self.word, attempt_count=4, wrong_count=0, correct_count=4
        )
        response = self.client.get(reverse("home"))
        self.assertIsNone(response.context["review"])
        self.assertNotContains(response, "مرور شخصی")

    def test_a_missed_word_is_named_with_its_own_counters(self):
        user = self.sign_in("lernt")
        WordProgress.objects.create(
            user=user, word=self.word, attempt_count=3, wrong_count=2, correct_count=1
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "مرور شخصی")
        self.assertContains(response, "Buch")
        self.assertContains(response, "کتاب")
        self.assertContains(response, "غلط: 2")
        self.assertContains(response, "درست: 1")
        # The words that were never missed are not part of the panel.
        self.assertNotContains(response, "Tisch")

    def test_the_panel_leads_to_the_review_page_and_the_real_exercise(self):
        user = self.sign_in("weiter")
        WordProgress.objects.create(
            user=user, word=self.word, attempt_count=2, wrong_count=2, correct_count=0
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("vocabulary:word-review"))
        self.assertContains(response, reverse("exercises:exercise-detail", args=[self.exercise.pk]))
        self.assertContains(response, self.exercise.title)

    def test_another_learners_mistakes_stay_off_the_page(self):
        other = User.objects.create_user(username="andere", password="a-strong-password")
        WordProgress.objects.create(
            user=other, word=self.word, attempt_count=3, wrong_count=3, correct_count=0
        )
        self.sign_in("sauber2")
        response = self.client.get(reverse("home"))
        self.assertIsNone(response.context["review"])
        self.assertNotContains(response, "مرور شخصی")


class ReadinessFixture(TestCase):
    """A small course and two learners, so the readiness rules can be checked alone.

    No content seeding, so it is fast and runnable on its own::

        python manage.py test lessons.tests.ReadinessCalculationTests

    The fixture is built to have an honest answer for every count: three published
    lessons plus a draft one, four course words of which only two are tested by any
    question, one published exercise plus a draft one, and a word that belongs to no
    lesson at all.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.next_level = LanguageLevel.objects.create(level="A2", title="متوسط", order=2)
        cls.course = Course.objects.create(
            language_level=cls.level, title="دورهٔ آلمانی A1", is_published=True
        )

        cls.lessons = []
        for number in range(1, 4):
            lesson = Lesson.objects.create(
                course=cls.course, title=f"Lektion {number}", order=number,
                estimated_time=60, is_published=True,
            )
            cls.lessons.append(lesson)

        cls.draft_lesson = Lesson.objects.create(
            course=cls.course, title="درس منتشرنشده", order=9, estimated_time=60, is_published=False
        )

        cls.words = []
        for index in range(4):
            word = Word.objects.create(
                word=f"Wort{index}", word_type="OTHER", meaning_fa=f"معنی {index}",
                level=cls.level, is_published=True,
            )
            cls.words.append(word)
            LessonWord.objects.create(lesson=cls.lessons[0], word=word, role="NEW", order=index + 1)

        # A word no lesson teaches: it can never be part of "this course's vocabulary".
        cls.loose_word = Word.objects.create(
            word="fremd", word_type="OTHER", meaning_fa="غریبه", level=cls.level, is_published=True
        )
        cls.draft_word = Word.objects.create(
            word="Entwurf", word_type="OTHER", meaning_fa="پیش‌نویس", level=cls.level, is_published=False
        )

        # One published exercise, testing two of the four course words.
        cls.exercise = Exercise.objects.create(
            lesson=cls.lessons[0], title="واژگان ۱", type="MULTIPLE_CHOICE", order=1, is_published=True
        )
        cls.questions = []
        for index in range(2):
            question = Question.objects.create(
                exercise=cls.exercise, prompt=f"پرسش {index}", order=index + 1
            )
            Answer.objects.create(question=question, text="richtig", is_correct=True, order=1)
            Answer.objects.create(question=question, text="falsch", is_correct=False, order=2)
            QuestionTarget.objects.create(
                question=question, word=cls.words[index], role="TESTED_ITEM"
            )
            cls.questions.append(question)

        # A draft exercise testing the third word: anything stored against it must not
        # count, and it must not make that word look "covered".
        cls.draft_exercise = Exercise.objects.create(
            lesson=cls.lessons[1], title="تمرین پیش‌نویس", type="MULTIPLE_CHOICE",
            order=2, is_published=False,
        )
        cls.draft_question = Question.objects.create(
            exercise=cls.draft_exercise, prompt="پیش‌نویس", order=1
        )
        Answer.objects.create(question=cls.draft_question, text="richtig", is_correct=True, order=1)
        QuestionTarget.objects.create(
            question=cls.draft_question, word=cls.words[2], role="TESTED_ITEM"
        )

        # Two grammar topics the course teaches, one it does not, and a question asking about
        # one of them — so "grammar accuracy" can be told apart from "vocabulary accuracy".
        cls.grammar = Grammar.objects.create(
            title="Der Plural der Nomen", explanation="…", level=cls.level, is_published=True
        )
        cls.other_grammar = Grammar.objects.create(
            title="Der Akkusativ", explanation="…", level=cls.level, is_published=True
        )
        cls.loose_grammar = Grammar.objects.create(
            title="فعل جداشدنی", explanation="…", level=cls.level, is_published=True
        )
        LessonGrammar.objects.create(lesson=cls.lessons[0], grammar=cls.grammar, order=1)
        LessonGrammar.objects.create(lesson=cls.lessons[0], grammar=cls.other_grammar, order=2)

        # A drill of its own, so the vocabulary totals the other tests pin stay untouched.
        cls.grammar_exercise = Exercise.objects.create(
            lesson=cls.lessons[1], title="تمرین گرامر — جمع", type="MULTIPLE_CHOICE",
            order=3, is_published=True,
        )
        cls.grammar_question = Question.objects.create(
            exercise=cls.grammar_exercise, prompt="جمعِ «der Abend»؟", order=1
        )
        Answer.objects.create(
            question=cls.grammar_question, text="die Abende", is_correct=True, order=1
        )
        Answer.objects.create(
            question=cls.grammar_question, text="die Abenden", is_correct=False, order=2
        )
        # A grammar question is about a word *and* a rule, which is why it carries both.
        QuestionTarget.objects.create(
            question=cls.grammar_question, word=cls.words[0], role="TESTED_ITEM"
        )
        QuestionTarget.objects.create(
            question=cls.grammar_question, grammar=cls.grammar, role="GRAMMAR"
        )

        # A draft question asking about the other topic: it must stay out of every count.
        cls.draft_grammar_question = Question.objects.create(
            exercise=cls.draft_exercise, prompt="پیش‌نویس قواعد", order=2
        )
        QuestionTarget.objects.create(
            question=cls.draft_grammar_question, grammar=cls.other_grammar,
            role="GRAMMAR",
        )

        cls.user = User.objects.create_user(username="lernt", password="a-strong-password")
        cls.other = User.objects.create_user(username="andere", password="a-strong-password")

    def complete_lesson(self, user, lesson):
        return LessonProgress.objects.create(
            user=user, lesson=lesson, status=LessonProgress.Status.COMPLETED
        )

    def answer(self, user, question, is_correct, exercise=None):
        if exercise is None:
            exercise = self.exercise
        return ExerciseAttempt.objects.create(
            user=user, exercise=exercise, question=question,
            is_correct=is_correct, response_text="",
        )

    def word_score(self, user, word, correct, wrong):
        return WordProgress.objects.create(
            user=user, word=word, attempt_count=correct + wrong,
            correct_count=correct, wrong_count=wrong,
        )

    def answer_grammar(self, user, is_correct):
        return self.answer(
            user, self.grammar_question, is_correct, exercise=self.grammar_exercise
        )


class ReadinessCalculationTests(ReadinessFixture):
    """``lessons.readiness``: every number the page shows, and what it counts."""

    def test_percent_of_nothing_is_zero(self):
        self.assertEqual(percent(0, 0), 0)
        self.assertEqual(percent(1, 3), 33)
        self.assertEqual(percent(3, 3), 100)

    def test_a_fresh_learner_has_the_whole_course_ahead(self):
        stats = course_progress(self.user)
        self.assertEqual(stats["completed"], 0)
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["remaining"], 3)
        self.assertEqual(stats["minutes_remaining"], 180)
        self.assertEqual(stats["percent"], 0)

    def test_completed_lessons_are_counted_and_the_rest_measured(self):
        self.complete_lesson(self.user, self.lessons[0])
        self.complete_lesson(self.user, self.lessons[1])
        stats = course_progress(self.user)
        self.assertEqual(stats["completed"], 2)
        self.assertEqual(stats["remaining"], 1)
        self.assertEqual(stats["minutes_remaining"], 60)
        self.assertEqual(stats["percent"], 67)

    def test_a_draft_lesson_is_neither_counted_nor_measured(self):
        self.complete_lesson(self.user, self.draft_lesson)
        stats = course_progress(self.user)
        self.assertEqual(stats["completed"], 0)
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["minutes_remaining"], 180)

    def test_another_learners_completions_are_not_counted(self):
        self.complete_lesson(self.other, self.lessons[0])
        self.assertEqual(course_progress(self.user)["completed"], 0)

    def test_exercises_are_only_the_published_ones(self):
        stats = exercise_progress(self.user)
        # The vocabulary exercise and the grammar drill; the draft one is invisible.
        self.assertEqual(stats["exercises_total"], 2)
        self.assertEqual(stats["questions_total"], 3)
        self.assertEqual(stats["answered"], 0)
        self.assertEqual(stats["percent"], 0)

    def test_only_the_latest_attempt_at_a_question_counts(self):
        self.answer(self.user, self.questions[0], False)
        self.answer(self.user, self.questions[0], True)
        stats = exercise_progress(self.user)
        self.assertEqual(stats["answered"], 1)
        self.assertEqual(stats["correct"], 1)
        self.assertEqual(stats["percent"], 100)
        self.assertEqual(stats["exercises_attempted"], 1)

    def test_a_later_wrong_answer_replaces_an_earlier_right_one(self):
        self.answer(self.user, self.questions[0], True)
        self.answer(self.user, self.questions[0], False)
        stats = exercise_progress(self.user)
        self.assertEqual(stats["answered"], 1)
        self.assertEqual(stats["correct"], 0)

    def test_accuracy_is_about_answered_questions_not_the_whole_course(self):
        self.answer(self.user, self.questions[0], True)
        stats = exercise_progress(self.user)
        self.assertEqual(stats["percent"], 100)
        self.assertEqual(stats["questions_total"], 3)
        self.assertEqual(stats["questions_remaining"], 2)

    def test_an_attempt_on_a_draft_exercise_is_ignored(self):
        self.answer(self.user, self.draft_question, True, exercise=self.draft_exercise)
        stats = exercise_progress(self.user)
        self.assertEqual(stats["answered"], 0)
        self.assertEqual(stats["exercises_attempted"], 0)

    def test_another_learners_answers_are_not_counted(self):
        self.answer(self.other, self.questions[0], True)
        self.assertEqual(exercise_progress(self.user)["answered"], 0)

    def test_a_word_is_remembered_only_when_it_is_ahead_of_its_mistakes(self):
        self.word_score(self.user, self.words[0], correct=3, wrong=1)
        self.word_score(self.user, self.words[1], correct=1, wrong=1)
        stats = vocabulary_progress(self.user)
        self.assertEqual(stats["tested"], 2)
        self.assertEqual(stats["remembered"], 1)
        self.assertEqual(stats["percent"], 50)
        self.assertEqual(stats["words_total"], 4)
        self.assertEqual(stats["words_untested"], 2)

    def test_a_word_no_lesson_teaches_is_not_part_of_the_course(self):
        self.word_score(self.user, self.loose_word, correct=5, wrong=0)
        stats = vocabulary_progress(self.user)
        self.assertEqual(stats["tested"], 0)
        self.assertEqual(stats["words_total"], 4)

    def test_an_unpublished_word_is_not_counted(self):
        self.word_score(self.user, self.draft_word, correct=0, wrong=4)
        self.assertEqual(vocabulary_progress(self.user)["tested"], 0)

    def test_coverage_counts_only_words_a_published_question_tests(self):
        coverage = word_coverage()
        self.assertEqual(coverage["total"], 4)
        self.assertEqual(coverage["covered"], 2)
        self.assertEqual(coverage["uncovered"], 2)

    def test_a_fresh_learner_has_practised_no_grammar_topic(self):
        stats = grammar_progress(self.user)
        self.assertEqual(stats["answered"], 0)
        self.assertEqual(stats["correct"], 0)
        self.assertEqual(stats["topics_practised"], 0)
        self.assertEqual(stats["topics_total"], 2)
        self.assertEqual(stats["questions_total"], 1)

    def test_a_grammar_answer_counts_against_the_topic_it_was_about(self):
        self.answer_grammar(self.user, True)
        stats = grammar_progress(self.user)
        self.assertEqual(stats["answered"], 1)
        self.assertEqual(stats["correct"], 1)
        self.assertEqual(stats["percent"], 100)
        self.assertEqual(stats["topics_practised"], 1)
        self.assertEqual(stats["topics_total"], 2)

    def test_only_the_latest_grammar_attempt_counts(self):
        self.answer_grammar(self.user, False)
        self.answer_grammar(self.user, True)
        stats = grammar_progress(self.user)
        self.assertEqual(stats["answered"], 1)
        self.assertEqual(stats["correct"], 1)

    def test_a_vocabulary_question_is_not_grammar_practice(self):
        """The two sections must not be the same number under two names: answering a meaning
        question is not practising a rule."""
        self.answer(self.user, self.questions[0], True)
        stats = grammar_progress(self.user)
        self.assertEqual(stats["answered"], 0)
        self.assertEqual(stats["topics_practised"], 0)
        self.assertEqual(exercise_progress(self.user)["answered"], 1)

    def test_a_grammar_topic_no_lesson_teaches_is_not_part_of_the_course(self):
        loose = Question.objects.create(
            exercise=self.grammar_exercise, prompt="قواعد بیرون از درس", order=2
        )
        QuestionTarget.objects.create(
            question=loose, grammar=self.loose_grammar, role="GRAMMAR"
        )
        # The question exists and is counted as content, but the topic is not the course's.
        self.assertEqual(grammar_progress(self.user)["questions_total"], 2)
        self.assertEqual(grammar_progress(self.user)["topics_total"], 2)

    def test_a_draft_grammar_question_is_ignored(self):
        self.answer(self.user, self.draft_grammar_question, True, exercise=self.draft_exercise)
        stats = grammar_progress(self.user)
        self.assertEqual(stats["answered"], 0)
        self.assertEqual(stats["questions_total"], 1)

    def test_another_learners_grammar_answers_are_not_counted(self):
        self.answer_grammar(self.other, True)
        self.assertEqual(grammar_progress(self.user)["answered"], 0)

    def test_grammar_coverage_counts_the_topics_a_published_question_asks_about(self):
        coverage = grammar_coverage()
        self.assertEqual(coverage["total"], 2)
        self.assertEqual(coverage["covered"], 1)
        self.assertEqual(coverage["uncovered"], 1)

    def test_a_draft_grammar_question_does_not_cover_a_topic(self):
        self.assertEqual(grammar_coverage()["covered"], 1)

    def test_a_fresh_learner_has_no_rule_to_review(self):
        self.assertEqual(missed_grammar(self.user), [])

    def test_a_rule_comes_back_when_the_newest_answer_was_wrong(self):
        self.answer_grammar(self.user, False)
        rows = missed_grammar(self.user)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["grammar"], self.grammar)
        self.assertEqual(rows[0]["answered"], 1)
        self.assertEqual(rows[0]["correct"], 0)
        self.assertEqual(rows[0]["wrong"], 1)

    def test_a_rule_the_learner_got_right_is_not_a_rule_to_review(self):
        self.answer_grammar(self.user, True)
        self.assertEqual(missed_grammar(self.user), [])

    def test_a_rule_got_right_after_a_mistake_drops_out_of_the_list(self):
        # They missed it, then got it right: the newest answer is what counts, exactly as
        # grammar_progress counts it, so the two cannot disagree.
        self.answer_grammar(self.user, False)
        self.answer_grammar(self.user, True)
        self.assertEqual(missed_grammar(self.user), [])

    def test_a_rule_got_wrong_last_time_comes_back(self):
        self.answer_grammar(self.user, True)
        self.answer_grammar(self.user, False)
        self.assertEqual(len(missed_grammar(self.user)), 1)

    def test_the_worst_rule_comes_first_and_ties_go_to_the_least_known(self):
        # Two questions about the plural rule (one right, one wrong) and one about the
        # other course rule (wrong), so both sort keys are exercised: the tie on wrong
        # answers is broken by how often the rule was answered right.
        second = Question.objects.create(
            exercise=self.grammar_exercise, prompt="جمعِ «das Kind»؟", order=2
        )
        Answer.objects.create(question=second, text="die Kinder", is_correct=True, order=1)
        QuestionTarget.objects.create(question=second, grammar=self.grammar, role="GRAMMAR")

        other_question = Question.objects.create(
            exercise=self.grammar_exercise, prompt="حالت مفعولی", order=3
        )
        Answer.objects.create(question=other_question, text="den", is_correct=True, order=1)
        QuestionTarget.objects.create(
            question=other_question, grammar=self.other_grammar, role="GRAMMAR"
        )

        self.answer_grammar(self.user, False)
        self.answer(self.user, second, True, exercise=self.grammar_exercise)
        self.answer(self.user, other_question, False, exercise=self.grammar_exercise)

        rows = missed_grammar(self.user)
        self.assertEqual([row["grammar"] for row in rows], [self.other_grammar, self.grammar])
        self.assertEqual(rows[0]["wrong"], 1)
        self.assertEqual(rows[0]["correct"], 0)
        self.assertEqual(rows[1]["wrong"], 1)
        self.assertEqual(rows[1]["correct"], 1)

    def test_a_rule_the_course_does_not_teach_is_not_reviewed(self):
        loose = Question.objects.create(
            exercise=self.grammar_exercise, prompt="قواعد بیرون از درس", order=2
        )
        Answer.objects.create(question=loose, text="…", is_correct=True, order=1)
        QuestionTarget.objects.create(
            question=loose, grammar=self.loose_grammar, role="GRAMMAR"
        )
        self.answer(self.user, loose, False, exercise=self.grammar_exercise)
        self.assertEqual(missed_grammar(self.user), [])

    def test_a_draft_question_about_a_rule_is_not_reviewed(self):
        self.answer(
            self.user, self.draft_grammar_question, False, exercise=self.draft_exercise
        )
        self.assertEqual(missed_grammar(self.user), [])

    def test_another_learners_rule_mistakes_are_not_reviewed(self):
        self.answer_grammar(self.other, False)
        self.assertEqual(missed_grammar(self.user), [])

    def test_the_practice_is_the_real_exercise_that_asks_about_the_rule(self):
        self.answer_grammar(self.user, False)
        rows = grammar_practice(missed_grammar(self.user))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["exercise"], self.grammar_exercise)
        self.assertEqual(rows[0]["topics"], [self.grammar])
        self.assertEqual(rows[0]["question_count"], 1)

    def test_the_exercise_covering_more_wrong_rules_comes_first(self):
        # The fixture's drill asks about one rule; this one asks about both, so it is the
        # better place to review.
        both = Exercise.objects.create(
            lesson=self.lessons[1], title="تمرین هر دو قاعده", type="MULTIPLE_CHOICE",
            order=4, is_published=True,
        )
        first = Question.objects.create(exercise=both, prompt="جمع", order=1)
        QuestionTarget.objects.create(question=first, grammar=self.grammar, role="GRAMMAR")
        second = Question.objects.create(exercise=both, prompt="حالت مفعولی", order=2)
        QuestionTarget.objects.create(
            question=second, grammar=self.other_grammar, role="GRAMMAR"
        )

        # A drill of its own for the second rule, so each of the two one-rule exercises
        # really does cover only one of the learner's mistakes.
        single = Exercise.objects.create(
            lesson=self.lessons[2], title="تمرین حالت مفعولی", type="MULTIPLE_CHOICE",
            order=5, is_published=True,
        )
        other = Question.objects.create(exercise=single, prompt="حالت مفعولی", order=1)
        QuestionTarget.objects.create(
            question=other, grammar=self.other_grammar, role="GRAMMAR"
        )

        self.answer_grammar(self.user, False)
        self.answer(self.user, other, False, exercise=single)

        rows = grammar_practice(missed_grammar(self.user))
        self.assertEqual(
            [row["exercise"] for row in rows], [both, self.grammar_exercise, single]
        )
        self.assertEqual(len(rows[0]["topics"]), 2)
        self.assertEqual(rows[1]["question_count"], 1)
        self.assertEqual(rows[2]["question_count"], 1)

    def test_a_draft_exercise_is_never_offered_as_rule_practice(self):
        # The draft exercise at the fixture also asks about that rule; only the published
        # drill may be offered for it.
        published = Question.objects.create(
            exercise=self.grammar_exercise, prompt="حالت مفعولی", order=2
        )
        QuestionTarget.objects.create(
            question=published, grammar=self.other_grammar, role="GRAMMAR"
        )

        self.answer(self.user, published, False, exercise=self.grammar_exercise)
        rows = missed_grammar(self.user)
        self.assertEqual([row["grammar"] for row in rows], [self.other_grammar])
        practice = grammar_practice(rows)
        self.assertEqual([row["exercise"] for row in practice], [self.grammar_exercise])

    def test_a_visitor_we_cannot_identify_has_no_rule_review(self):
        self.assertIsNone(grammar_review(AnonymousUser()))

    def test_a_learner_who_got_every_rule_right_has_no_rule_review(self):
        self.answer_grammar(self.user, True)
        self.assertIsNone(grammar_review(self.user))

    def test_the_rule_review_limits_the_exercises_but_not_the_count(self):
        second = Exercise.objects.create(
            lesson=self.lessons[2], title="تمرین دیگرِ جمع", type="MULTIPLE_CHOICE",
            order=5, is_published=True,
        )
        question = Question.objects.create(exercise=second, prompt="جمع ۲", order=1)
        QuestionTarget.objects.create(question=question, grammar=self.grammar, role="GRAMMAR")
        self.answer_grammar(self.user, False)

        review = grammar_review(self.user, exercise_limit=1)
        self.assertEqual(review["wrong_topic_count"], 1)
        self.assertEqual(len(review["exercises"]), 1)
        self.assertEqual(review["exercise_count"], 2)
        self.assertIsNotNone(review["topics"][0]["practice_exercise"])

    def test_a_learner_with_no_goal_has_none(self):
        self.assertIsNone(goal_of(None))
        profile = UserProfile.objects.get(user=self.user)
        self.assertIsNone(goal_of(profile))

    def test_a_reason_alone_is_a_goal(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.reason = UserProfile.Reason.AUSBILDUNG
        profile.save()
        goal = goal_of(profile)
        self.assertIsNotNone(goal)
        self.assertEqual(goal["reason_label"], "آوسبیلدونگ")
        self.assertIsNone(goal["target_date"])

    def test_a_target_above_the_content_is_reported_as_not_covered(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.target_level = self.next_level
        profile.save()
        goal = goal_of(profile)
        self.assertFalse(goal["covers_target"])
        self.assertEqual(goal["content_level"], self.level)

    def test_a_target_the_content_reaches_is_covered(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.target_level = self.level
        profile.save()
        self.assertTrue(goal_of(profile)["covers_target"])

    def test_readiness_gathers_every_part_and_reuses_the_review_rule(self):
        self.complete_lesson(self.user, self.lessons[0])
        self.answer(self.user, self.questions[0], True)
        self.answer_grammar(self.user, False)
        self.word_score(self.user, self.words[0], correct=0, wrong=2)
        data = readiness(self.user, today=date(2026, 9, 29))
        self.assertEqual(data["course"]["completed"], 1)
        self.assertEqual(data["exercises"]["correct"], 1)
        self.assertEqual(data["vocabulary"]["tested"], 1)
        self.assertEqual(data["grammar"]["answered"], 1)
        self.assertEqual(data["grammar"]["topics_practised"], 1)
        self.assertEqual(data["coverage"]["covered"], 2)
        self.assertEqual(data["grammar_coverage"]["covered"], 1)
        # Same definition as the review page: a word with a wrong answer is a word to review.
        self.assertEqual(data["weak_word_count"], 1)
        self.assertEqual(data["weak_grammar_count"], 1)
        self.assertEqual(len(data["weak_grammar_topics"]), 1)
        self.assertEqual(data["weak_grammar_topics"][0]["practice_exercise"], self.grammar_exercise)
        self.assertIsNone(data["goal"])
        self.assertIsNone(data["pace"])


class LearningPaceTests(SimpleTestCase):
    """The deadline arithmetic: pure, so it needs no database at all."""

    today = date(2026, 9, 29)

    def stats(self, remaining, minutes_remaining):
        return {"remaining": remaining, "minutes_remaining": minutes_remaining}

    def goal(self, days):
        return {"target_date": self.today + timedelta(days=days)}

    def test_no_goal_means_no_pace(self):
        self.assertIsNone(learning_pace(self.stats(12, 720), None, self.today))

    def test_no_date_means_no_pace(self):
        goal = {"target_date": None}
        self.assertIsNone(learning_pace(self.stats(12, 720), goal, self.today))

    def test_twelve_weeks_and_twelve_lessons_is_one_a_week(self):
        pace = learning_pace(self.stats(12, 720), self.goal(84), self.today)
        self.assertEqual(pace["state"], "planned")
        self.assertEqual(pace["weeks_left"], 12)
        self.assertEqual(pace["lessons_per_week"], 1)
        self.assertEqual(pace["minutes_per_week"], 60)

    def test_the_weekly_numbers_round_up(self):
        pace = learning_pace(self.stats(25, 1500), self.goal(84), self.today)
        self.assertEqual(pace["lessons_per_week"], 3)   # 25 / 12 → 2.08
        self.assertEqual(pace["minutes_per_week"], 125)  # 1500 / 12 → 125

    def test_weeks_left_rounds_up_too(self):
        pace = learning_pace(self.stats(2, 120), self.goal(8), self.today)
        self.assertEqual(pace["weeks_left"], 2)
        self.assertEqual(pace["lessons_per_week"], 1)

    def test_a_passed_date_is_reported_rather_than_divided(self):
        pace = learning_pace(self.stats(5, 300), self.goal(-3), self.today)
        self.assertEqual(pace["state"], "passed")
        self.assertEqual(pace["days_left"], -3)
        self.assertEqual(pace["lessons_per_week"], 0)
        self.assertEqual(pace["remaining_lessons"], 5)

    def test_today_itself_counts_as_passed(self):
        pace = learning_pace(self.stats(5, 300), self.goal(0), self.today)
        self.assertEqual(pace["state"], "passed")
        self.assertEqual(pace["days_left"], 0)

    def test_a_finished_course_has_no_weekly_target(self):
        pace = learning_pace(self.stats(0, 0), self.goal(30), self.today)
        self.assertEqual(pace["state"], "done")
        self.assertEqual(pace["lessons_per_week"], 0)
        self.assertEqual(pace["minutes_per_week"], 0)


class DashboardGoalTests(ReadinessFixture):
    """The dashboard's goal line: the sentence that connects where the learner is to
    where they said they are going.

    It belongs to a signed-in learner only — nobody else has a goal to show — and it is
    written from ``lessons/readiness.py``, so «آمادگی من» and the dashboard cannot
    disagree about it.
    """

    def setUp(self):
        self.url = reverse("home")

    def test_an_anonymous_visitor_gets_no_goal_line_and_no_readiness_link(self):
        response = self.client.get(self.url)
        self.assertIsNone(response.context["goal"])
        self.assertNotContains(response, reverse("readiness"))
        self.assertNotContains(response, "هدف یادگیری‌ات را تعیین کن")

    def test_a_signed_in_learner_without_a_goal_is_invited_once(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "هدف یادگیری‌ات را تعیین کن")
        self.assertContains(response, reverse("readiness"))

    def test_a_goal_with_a_date_shows_the_target_and_the_pace(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.current_level = self.level
        profile.target_level = self.next_level
        profile.reason = UserProfile.Reason.AUSBILDUNG
        profile.target_date = timezone.localdate() + timedelta(days=84)
        profile.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "هدف")
        self.assertContains(response, "A2")
        self.assertContains(response, "آوسبیلدونگ")
        # Three lessons remain and there are twelve weeks: one a week.
        self.assertContains(response, "1 درس در هفته")

    def test_a_goal_without_a_date_gets_no_invented_pace(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.target_level = self.level
        profile.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "هدف")
        self.assertNotContains(response, "درس در هفته")

    def test_a_passed_date_is_admitted_rather_than_planned(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.target_date = timezone.localdate() - timedelta(days=1)
        profile.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "تاریخ هدفت گذشته است")
        self.assertNotContains(response, "درس در هفته")


class ReadinessPageTests(ReadinessFixture):
    """The page itself: honest numbers, and never anybody else's numbers."""

    def setUp(self):
        self.url = reverse("readiness")

    def test_an_anonymous_visitor_is_asked_for_an_account(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "این صفحه به حساب تو نیاز دارد.")
        self.assertIsNone(response.context["readiness"])
        # None of the personal panels is rendered at all.
        self.assertNotContains(response, "پیشرفت دوره")
        self.assertNotContains(response, "عملکرد تمرین‌ها")

    def test_the_onboarding_flag_shows_the_first_run_banner(self):
        # Step two of the first run. It is not a separate screen — it is this page saying what
        # it is for and where to go next; an ordinary visit never sees it.
        self.client.force_login(self.user)
        response = self.client.get(self.url + "?onboarding=1")
        self.assertContains(response, "قدم ۲ از ۲")
        self.assertContains(response, "هدفت ثبت شد")
        # The banner exists to carry the learner onward, so it must end in a real link home.
        self.assertContains(response, 'href="/"')

    def test_an_ordinary_visit_shows_no_onboarding_banner(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, "قدم ۲ از ۲")

    def test_a_new_learner_sees_zeroes_rather_than_nothing(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "0 از 3 درس")
        self.assertContains(response, "هنوز پاسخی ثبت نشده")
        self.assertContains(response, "هنوز در هیچ تمرینی روی واژه‌ای سنجیده نشده‌ای")
        self.assertContains(response, "الان کجای مسیری؟")

    def test_a_learner_with_a_history_sees_their_own_numbers(self):
        self.complete_lesson(self.user, self.lessons[0])
        self.answer(self.user, self.questions[0], True)
        self.word_score(self.user, self.words[0], correct=4, wrong=1)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "1 از 3 درس")
        self.assertContains(response, "دقت: 100٪")
        self.assertContains(response, "1 از 4 واژهٔ دوره")
        self.assertContains(response, "1 واژه (100٪)")

    def test_the_page_states_what_it_cannot_say(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "این صفحه چه چیزی را نمی‌گوید")
        # Both coverage gaps are computed, not decorative: the words no question tests, and
        # the grammar topics no question asks about.
        self.assertContains(response, "2 واژه از 4 واژهٔ این دوره")
        self.assertContains(response, "1 موضوع از 2 موضوع گرامرِ این دوره")
        self.assertContains(response, "هنوز 3 پرسش را پاسخ نداده‌ای")

    def test_the_page_has_a_grammar_section_of_its_own(self):
        """Grammar must be visible as grammar, and must say what it does not count."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "قواعد")
        self.assertContains(response, "0 از 2 موضوع")
        self.assertEqual(response.context["readiness"]["grammar"]["topics_practised"], 0)

    def test_the_grammar_section_shows_the_learners_own_grammar_answers(self):
        self.answer_grammar(self.user, True)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "1 از 2 موضوع")
        self.assertContains(response, "دقت قواعد 100٪ است")

    def test_another_learners_progress_is_not_shown(self):
        self.complete_lesson(self.other, self.lessons[0])
        self.complete_lesson(self.other, self.lessons[1])
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.context["readiness"]["course"]["completed"], 0)
        self.assertContains(response, "0 از 3 درس")
        self.assertNotContains(response, self.other.username)

    def test_signing_out_hides_the_numbers_again(self):
        self.complete_lesson(self.user, self.lessons[0])
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.url), "1 از 3 درس")
        self.client.logout()
        response = self.client.get(self.url)
        self.assertNotContains(response, "1 از 3 درس")

    def test_the_goal_panel_invites_when_there_is_no_goal(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "هنوز هدفی تعیین نکرده‌ای")
        self.assertContains(response, reverse("accounts:goal"))

    def test_the_gaps_say_what_is_true_about_writing_and_speaking(self):
        """The page must not claim there is no writing or speaking exercise.

        The course has typed-writing questions, scrambles and a speaking rehearsal page, so
        the old wording («هیچ تمرین گفتاری یا نوشتاری وجود ندارد») was simply false — on the
        one page whose whole value is honesty.
        """
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, "هیچ تمرین گفتاری یا نوشتاری وجود ندارد")
        self.assertContains(response, "تایپی")

    def test_a_date_turns_the_goal_into_a_weekly_pace(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.target_level = self.level
        profile.reason = UserProfile.Reason.AUSBILDUNG
        # Relative to today, not a fixed calendar date: the pace is measured against the
        # wall clock, so a hardcoded date made the expected week count drift with time
        # (it read 12 when the test was written and 11 a week later).
        profile.target_date = timezone.localdate() + timedelta(weeks=12)
        profile.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "درس در هفته")
        self.assertContains(response, "آوسبیلدونگ")
        self.assertContains(response, "12 هفته وقت داری")

    def test_a_passed_date_says_so_instead_of_inventing_a_plan(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.target_date = timezone.localdate() - timedelta(days=2)
        profile.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "تاریخ هدفت گذشته است")
        self.assertNotContains(response, "درس در هفته")

    def test_a_target_above_the_built_content_is_stated_plainly(self):
        profile = UserProfile.objects.get(user=self.user)
        profile.target_level = self.next_level
        profile.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "محتوای ساخته‌شده فعلاً تا")
        self.assertContains(response, "هنوز درسی ساخته نشده")

    def test_learner_with_grammar_mistakes_sees_weak_grammar_topics_with_practice_link(self):
        self.answer_grammar(self.user, False)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "قاعده‌های نیازمند مرور")
        self.assertContains(response, "قاعده‌هایی که اخیراً اشتباه زدی:")
        self.assertContains(response, self.grammar.title)
        self.assertContains(response, reverse("exercises:exercise-detail", args=[self.grammar_exercise.pk]))
        self.assertContains(response, reverse("vocabulary:word-review") + "#grammar")


class GrammarReviewPageTests(ReadinessFixture):
    """The review page's rule half: a mistake the product stored and never showed.

    It lives here rather than in ``vocabulary``'s tests because the fixture that has a
    course grammar topic and a question about it is this one — the same reason
    ``ReadinessPageTests`` renders its page from here.
    """

    def setUp(self):
        self.url = reverse("vocabulary:word-review")
        self.client.force_login(self.user)

    def test_a_rule_that_went_wrong_is_listed_with_its_counters(self):
        self.answer_grammar(self.user, False)
        response = self.client.get(self.url)
        self.assertContains(response, "قاعده‌هایی که اشتباه زده‌ای")
        self.assertContains(response, self.grammar.title)
        self.assertContains(response, "غلط: 1")
        self.assertEqual(response.context["grammar"]["wrong_topic_count"], 1)

    def test_the_page_offers_the_exercise_that_asks_about_the_rule(self):
        self.answer_grammar(self.user, False)
        response = self.client.get(self.url)
        self.assertContains(response, "تمرین همین قاعده‌ها")
        self.assertContains(
            response, reverse("exercises:exercise-detail", args=[self.grammar_exercise.pk])
        )
        self.assertContains(response, "تمرین این قاعده")

    def test_a_learner_who_got_every_rule_right_is_not_told_about_rules(self):
        self.answer_grammar(self.user, True)
        response = self.client.get(self.url)
        self.assertIsNone(response.context["grammar"])
        self.assertNotContains(response, "قاعده‌هایی که اشتباه زده‌ای")

    def test_rule_mistakes_reach_the_page_without_any_word_mistake(self):
        # No word was ever missed, so the word half is empty — the page must not show the
        # "nothing to review" state while there is a rule to review.
        self.answer_grammar(self.user, False)
        response = self.client.get(self.url)
        self.assertContains(response, self.grammar.title)
        self.assertNotContains(response, "هنوز اشتباهی ثبت نشده.")

    def test_a_visitor_is_asked_for_an_account_and_not_shown_rules(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertIsNone(response.context["grammar"])
        self.assertNotContains(response, "قاعده‌هایی که اشتباه زده‌ای")

    def test_another_learners_rule_mistakes_stay_off_the_page(self):
        self.answer_grammar(self.other, False)
        response = self.client.get(self.url)
        self.assertIsNone(response.context["grammar"])


class LearningPathTests(TestCase):
    """The learning path: a complete, ordered trail that works without a login.

    Builds its own small courses (no seeding), so it is runnable on its own:
        python manage.py test lessons.tests.LearningPathTests
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="دورهٔ آلمانی A1", description="از صفر تا A1.", is_published=True
        )
        cls.lessons = [
            Lesson.objects.create(
                course=cls.course, title=f"Hallo {number}", order=number, estimated_time=45, is_published=True
            )
            for number in range(1, 6)
        ]
        cls.draft = Lesson.objects.create(
            course=cls.course, title="درس پیش‌نویس", order=6, estimated_time=30, is_published=False
        )

        cls.level2 = LanguageLevel.objects.create(level="A2", title="متوسط", order=2)
        cls.course2 = Course.objects.create(language_level=cls.level2, title="دورهٔ آلمانی A2", is_published=True)
        cls.lesson2 = Lesson.objects.create(
            course=cls.course2, title="A2 Los", order=1, estimated_time=50, is_published=True
        )

        # A published course with no published lesson must not appear at all.
        cls.level3 = LanguageLevel.objects.create(level="B1", title="پیشرفته", order=3)
        cls.empty_course = Course.objects.create(language_level=cls.level3, title="دورهٔ خالی B1", is_published=True)

    def test_renders_the_whole_trail_for_anonymous_visitors(self):
        response = self.client.get(reverse("lessons:lesson-list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "lessons/lesson_list.html")
        self.assertContains(response, "js/path.js")

    def test_every_published_lesson_appears_exactly_once(self):
        response = self.client.get(reverse("lessons:lesson-list"))
        for lesson in [*self.lessons, self.lesson2]:
            self.assertContains(response, f'data-lesson="{lesson.pk}"', count=1)
        self.assertNotContains(response, f'data-lesson="{self.draft.pk}"')

    def test_is_not_paginated(self):
        """A path that breaks across pages stops being a path."""
        response = self.client.get(reverse("lessons:lesson-list"))
        self.assertNotContains(response, "?page=2")
        self.assertEqual(len(response.context["lessons_payload"]), len(self.lessons) + 1)

    def test_groups_lessons_by_course_in_level_order(self):
        response = self.client.get(reverse("lessons:lesson-list"))
        groups = response.context["groups"]
        self.assertEqual([group["course"].pk for group in groups], [self.course.pk, self.course2.pk])
        self.assertEqual([len(group["lessons"]) for group in groups], [len(self.lessons), 1])

    def test_courses_without_published_lessons_are_not_shown(self):
        response = self.client.get(reverse("lessons:lesson-list"))
        self.assertNotIn(self.empty_course, [group["course"] for group in response.context["groups"]])
        self.assertNotContains(response, "دورهٔ خالی B1")
        self.assertNotContains(response, reverse("lessons:course-detail", args=[self.empty_course.pk]))

    def test_the_title_link_is_itself_a_forty_four_pixel_target(self):
        """A geometry audit measured this link's own box at 17px tall on a phone.

        The stretched `::after` overlay has always made the whole card tappable — every
        point on a 312x180 card lands on this link — but the overlay is invisible to
        target-size checkers, which measure the link's box. So the box itself clears 44px.
        """
        stylesheet = Path(__file__).resolve().parent / "static" / "lessons" / "css" / "lesson_path.css"
        declaration = None
        for line in stylesheet.read_text(encoding="utf-8").splitlines():
            if line.startswith(".path-step__title a {"):
                declaration = line

        self.assertIsNotNone(declaration, "the path title link rule disappeared")
        self.assertIn("min-height: 44px", declaration)

    def test_hands_the_ordered_lesson_list_to_the_browser(self):
        """path.js resolves a stored lesson id through this payload."""
        response = self.client.get(reverse("lessons:lesson-list"))
        payload = response.context["lessons_payload"]
        self.assertEqual([entry["id"] for entry in payload], [lesson.pk for lesson in [*self.lessons, self.lesson2]])
        for entry in payload:
            self.assertEqual(set(entry), {"id", "order", "title", "minutes", "url"})
        self.assertContains(response, 'id="path-lessons"')

    def test_server_renders_every_step_as_not_started(self):
        """The server cannot know a visitor's history, so it must not imply any."""
        response = self.client.get(reverse("lessons:lesson-list"))
        self.assertContains(response, "شروع نشده", count=len(self.lessons) + 1)
        self.assertNotContains(response, "کامل‌شده")

    def test_shows_duration_and_a_clear_next_step(self):
        response = self.client.get(reverse("lessons:lesson-list"))
        self.assertContains(response, "45 دقیقه")
        self.assertContains(response, self.lessons[0].title)
        self.assertContains(response, reverse("lessons:lesson-detail", args=[self.lessons[0].pk]))
        self.assertContains(response, "قدم بعدی")

    def test_course_page_is_scoped_to_that_course(self):
        response = self.client.get(reverse("lessons:course-detail", args=[self.course.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "lessons/course_detail.html")
        self.assertContains(response, f'data-lesson="{self.lessons[0].pk}"')
        self.assertNotContains(response, f'data-lesson="{self.lesson2.pk}"')
        self.assertEqual(response.context["lesson_total"], len(self.lessons))

    def test_no_locked_or_premium_wording(self):
        """Entitlement does not exist yet; nothing may imply a locked lesson."""
        response = self.client.get(reverse("lessons:lesson-list"))
        for word in ("قفل", "پریمیوم", "اشتراک", "خرید"):
            self.assertNotContains(response, word)

    def test_empty_database_shows_an_empty_state(self):
        Course.objects.update(is_published=False)
        response = self.client.get(reverse("lessons:lesson-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هنوز درسی منتشر نشده است")


class LessonJourneyTests(TestCase):
    """The lesson as a guided journey: the steps follow the lesson's own content.

    Builds its own lessons (no seeding) so it is runnable on its own:
        python manage.py test lessons.tests.LessonJourneyTests
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.course = Course.objects.create(language_level=cls.level, title="دورهٔ آلمانی A1", is_published=True)

        # One lesson that carries every kind of step.
        # The Persian title and summary are what the page shows; the German ones stay
        # beside them, and the summary carries the English gloss every real one has.
        cls.rich = Lesson.objects.create(
            course=cls.course, title="Hallo", title_fa="سلام",
            description="سلام و احوال‌پرسی. English: greeting someone.",
            description_fa="سلام و احوال‌پرسی.",
            order=1, estimated_time=45, is_published=True,
        )
        cls.follow_up = Lesson.objects.create(
            course=cls.course, title="Tschüss", order=2, estimated_time=30, is_published=True
        )
        cls.bare = Lesson.objects.create(
            course=cls.course, title="Leer", order=3, estimated_time=10, is_published=True
        )
        cls.draft = Lesson.objects.create(
            course=cls.course, title="Entwurf", order=4, estimated_time=10, is_published=False
        )

        blocks = [
            ("EXPLANATION", "Was lernst du?"),
            ("NOTE", "Achtung"),
            ("GRAMMAR", "Grammatik"),
            ("VOCABULARY", "Wortschatz"),
            ("DIALOGUE", "Dialog"),
            ("EXAMPLE", "Beispiele"),
        ]
        for order, (kind, title) in enumerate(blocks, start=1):
            body = "متن توضیح.\nhallo"
            if kind == "VOCABULARY":
                # A `·` list and an English gloss: the two shapes every real vocabulary
                # block has, so the step's two filters are exercised by the fixture.
                body = "واژه‌های این درس:\nhallo (سلام) · Buch (کتاب)\n\nEnglish: the words of this lesson."
            if kind == "EXAMPLE":
                body = "مثال‌ها:\nIch bin Ali.\n\nEnglish: introducing yourself."
            LessonContent.objects.create(
                lesson=cls.rich, type=kind, title=title, body=body, order=order
            )

        cls.noun = Word.objects.create(
            word="Buch", word_type="NOUN", article="das", gender="N", plural="die Bücher",
            meaning_fa="کتاب", meaning_en="book", pronunciation="buːx", level=cls.level, is_published=True,
        )
        cls.verb = Word.objects.create(
            word="abfliegen", word_type="VERB", meaning_fa="پرواز کردن", meaning_en="to depart",
            pronunciation="ˈapfliːɡn̩", is_separable=True, perfect_auxiliary="SEIN",
            is_exam_important=True, level=cls.level, is_published=True,
        )
        cls.other = Word.objects.create(
            word="hallo", word_type="OTHER", meaning_fa="سلام", meaning_en="hello",
            level=cls.level, is_published=True,
        )
        for order, word in enumerate([cls.noun, cls.verb, cls.other], start=1):
            LessonWord.objects.create(lesson=cls.rich, word=word, role="NEW" if order < 3 else "REVIEW", order=order)

        cls.grammar = Grammar.objects.create(
            title="Personalpronomen",
            explanation="توضیح گرامر.\nich bin\n\nEnglish: personal pronouns.",
            level=cls.level, is_published=True,
        )
        LessonGrammar.objects.create(lesson=cls.rich, grammar=cls.grammar, order=1)
        cls.draft_grammar = Grammar.objects.create(
            title="Grammatik-Entwurf", explanation="…", level=cls.level, is_published=False
        )
        LessonGrammar.objects.create(lesson=cls.rich, grammar=cls.draft_grammar, order=2)

        for order, (role, speaker) in enumerate(
            [("EXAMPLE", ""), ("EXAMPLE", ""), ("DIALOGUE", "Anna"), ("DIALOGUE", "Ben"), ("READING", "")],
            start=1,
        ):
            sentence = Sentence.objects.create(
                text=f"Guten Tag {order}", translation_fa=f"روز بخیر {order}", level=cls.level, is_published=True
            )
            LessonSentence.objects.create(
                lesson=cls.rich, sentence=sentence, role=role, speaker=speaker, order=order
            )

        cls.exercise = Exercise.objects.create(
            lesson=cls.rich, title="واژگان — انتخاب معنی", instruction="معنی درست را انتخاب کن.",
            type="MULTIPLE_CHOICE", difficulty="EASY", order=1, is_published=True,
        )
        for order in (1, 2):
            question = Question.objects.create(exercise=cls.exercise, prompt=f"پرسش {order}", order=order)
            Answer.objects.create(question=question, text="درست", is_correct=True, order=1)
            Answer.objects.create(question=question, text="نادرست", is_correct=False, order=2)
        cls.draft_exercise = Exercise.objects.create(
            lesson=cls.rich, title="تمرین پیش‌نویس", type="TRUE_FALSE", order=2, is_published=False
        )

        # Prose and vocabulary only: no grammar, no sentences, no exercises.
        LessonContent.objects.create(lesson=cls.follow_up, type="EXPLANATION", title="Nur Text", body="فقط توضیح", order=1)
        LessonWord.objects.create(lesson=cls.follow_up, word=cls.other, role="NEW", order=1)

    @property
    def url(self):
        return reverse("lessons:lesson-detail", args=[self.rich.pk])

    @property
    def follow_up_url(self):
        return reverse("lessons:lesson-detail", args=[self.follow_up.pk])

    @property
    def bare_url(self):
        return reverse("lessons:lesson-detail", args=[self.bare.pk])

    def steps_of(self, url):
        return self.client.get(url).context["steps"]

    def test_renders_the_journey_for_anonymous_visitors(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "lessons/lesson_detail.html")
        self.assertContains(response, "js/lesson_steps.js")
        self.assertContains(response, f'data-lesson-id="{self.rich.pk}"')

    def test_steps_follow_the_lesson_content_in_order(self):
        keys = [step["key"] for step in self.steps_of(self.url)]
        self.assertEqual(
            keys,
            ["intro", "explanation", "vocabulary", "grammar", "examples", "dialogue", "reading", "practice", "finish"],
        )

    def test_every_step_is_rendered_server_side(self):
        """The stepper only hides steps; no content may depend on JavaScript."""
        response = self.client.get(self.url)
        for key in ("intro", "explanation", "vocabulary", "grammar", "examples", "dialogue", "reading", "practice", "finish"):
            self.assertContains(response, f'data-journey-step="{key}"')
        self.assertContains(response, 'class="journey-chip"')

    def test_step_counts_come_from_published_rows_only(self):
        steps = {step["key"]: step for step in self.steps_of(self.url)}
        self.assertEqual(steps["explanation"]["count"], 2)  # EXPLANATION + NOTE
        self.assertEqual(steps["vocabulary"]["count"], 3)
        self.assertEqual(steps["grammar"]["count"], 1)  # the unpublished topic is excluded
        self.assertEqual(steps["examples"]["count"], 2)
        self.assertEqual(steps["dialogue"]["count"], 2)
        self.assertEqual(steps["reading"]["count"], 1)
        self.assertEqual(steps["practice"]["count"], 1)  # the unpublished exercise is excluded

    def test_a_lesson_without_grammar_or_sentences_has_no_such_steps(self):
        keys = [step["key"] for step in self.steps_of(self.follow_up_url)]
        self.assertEqual(keys, ["intro", "explanation", "vocabulary", "finish"])

    def test_a_lesson_with_no_content_offers_no_fake_steps(self):
        response = self.client.get(self.bare_url)
        self.assertEqual([step["key"] for step in response.context["steps"]], ["intro", "finish"])
        self.assertEqual(response.context["material_step_count"], 0)
        self.assertContains(response, "هنوز محتوایی برای این درس ثبت نشده است")
        self.assertNotContains(response, 'data-journey-step="practice"')
        self.assertNotContains(response, 'data-journey-step="grammar"')

    def test_intro_agenda_lists_only_the_material_steps(self):
        response = self.client.get(self.url)
        agenda = re.search(r'<ul class="agenda">(.*?)</ul>', response.content.decode(), flags=re.S).group(1)
        self.assertEqual(agenda.count('class="agenda__link"'), 7)  # 9 steps minus intro and finish
        self.assertNotIn("آغاز", agenda)
        self.assertNotIn("پایان", agenda)

    def test_german_is_ltr_and_the_translation_follows_in_rtl(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<p class="sentence__de" lang="de" dir="ltr"')
        self.assertContains(response, "Guten Tag 3")
        self.assertContains(response, "روز بخیر 3")
        self.assertContains(response, 'lang="de" dir="ltr"')

    def test_speaker_is_shown_only_where_the_data_has_one(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'class="sentence__speaker"')
        self.assertContains(response, "Anna")
        self.assertEqual(response.content.decode().count('class="sentence__speaker"'), 2)

    def step_html(self, key, url=None, query=""):
        """One step's own markup.

        Not the whole page: every step is rendered at once, so a sentence or a word also
        appears in the examples, dialogue and practice steps. Slicing out the step under
        test is what makes "this content is here and not there" mean anything.
        """
        if url is None:
            url = self.url
        html = self.client.get(url + query).content.decode()
        begin = html.index(f'data-journey-step="{key}"')
        return html[begin:html.index("</section>", begin)]

    def vocabulary_rows(self, url=None, query=""):
        """The vocabulary step's rows, keyed by word type."""
        html = self.step_html("vocabulary", url, query)
        return dict(re.findall(r'<li class="word-row" data-word-type="(\w+)">(.*?)</li>', html, flags=re.S))

    def test_a_vocabulary_row_shows_only_the_fields_a_word_actually_has(self):
        rows = self.vocabulary_rows()
        self.assertIn("die Bücher", rows["NOUN"])
        self.assertNotIn("جداپذیر", rows["NOUN"])
        self.assertIn("جداپذیر", rows["VERB"])
        self.assertNotIn("جمع", rows["VERB"])
        self.assertIn("سلام", rows["OTHER"])
        self.assertNotIn("تلفظ", rows["OTHER"])  # this word has no pronunciation

    def test_a_vocabulary_row_shows_one_label_at_most(self):
        # Three words, three different states: the lesson introduces the noun and revisits
        # the plain word, and the verb is one of the forms the exam tests.
        rows = self.vocabulary_rows()
        self.assertIn("جدید", rows["NOUN"])
        self.assertIn("مهم برای آزمون", rows["VERB"])
        self.assertIn("مرور", rows["OTHER"])
        self.assertNotIn("جدید", rows["VERB"])

        for word_type, row in rows.items():
            with self.subTest(word_type=word_type):
                self.assertEqual(row.count('class="word-row__status '), 1)

    def test_the_vocabulary_rows_are_compact_and_not_cards(self):
        html = self.step_html("vocabulary")
        self.assertIn('<ul class="word-rows">', html)
        self.assertNotIn("word-card", html)

    def test_a_translation_in_the_vocabulary_lead_in_keeps_its_brackets(self):
        # The Phase 1 bidi fix must survive the row rewrite: `hallo (سلام)` is a German word
        # and its bracketed Persian translation, laid out left to right.
        html = self.step_html("vocabulary")
        self.assertIn('dir="ltr"><bdi class="run run--de" lang="de" dir="ltr">hallo </bdi>', html)
        self.assertIn('<bdi class="run run--fa" lang="fa" dir="rtl">(سلام)</bdi>', html)

    def test_meaning_en_is_never_rendered_even_though_it_is_stored(self):
        # The English meaning stays in the database for a future English interface; the
        # Persian page must not show it (no `book`, no `to depart`, no `hello`).
        html = self.client.get(self.url).content.decode()
        for english in ("book", "to depart", "hello"):
            self.assertNotIn(english, html)

        self.assertEqual(self.noun.meaning_en, "book")

    def test_the_english_gloss_is_not_rendered_on_the_page(self):
        # Every real block, grammar topic and lesson summary ends with an `English: …`
        # gloss for a future English interface. The Persian page renders none of it, and
        # the stored text keeps it.
        response = self.client.get(self.url)
        self.assertNotIn("English:", response.content.decode())
        self.assertIn("English:", self.rich.description)
        self.assertIn("English:", self.grammar.explanation)

    def test_the_persian_title_is_the_title_and_the_german_one_stays_beside_it(self):
        response = self.client.get(self.url)
        html = response.content.decode()
        self.assertIn("<title>سلام | درس 1 |", html)
        self.assertIn('<h1 class="lesson-head__title">', html)
        self.assertIn('<p class="lesson-head__de" lang="de" dir="ltr">Hallo</p>', html)

    def test_a_lesson_without_a_persian_title_shows_its_german_one(self):
        response = self.client.get(self.follow_up_url)
        self.assertIn("Tschüss", response.content.decode())
        self.assertNotIn('class="lesson-head__de"', response.content.decode())

    def test_the_lesson_summary_keeps_its_persian_half_only(self):
        html = self.step_html("intro")
        self.assertNotIn("greeting someone", html)

    def test_audio_is_never_invented(self):
        """None of the fixture rows has an audio file, so no player may appear."""
        response = self.client.get(self.url)
        self.assertNotContains(response, 'aria-controls="word-')
        self.assertNotContains(response, 'aria-controls="sentence-')
        self.assertNotContains(response, 'aria-controls="grammar-')

    def test_no_interactive_element_is_nested_inside_a_link(self):
        """A vocabulary row is a row, not a link wrapping a play button."""
        html = self.client.get(self.url).content.decode()
        for anchor in re.findall(r"<a\b.*?</a>", html, flags=re.S):
            self.assertNotIn("<button", anchor)
            self.assertNotIn("<audio", anchor)

    def test_practice_offers_the_lesson_exercises_and_their_size(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse("exercises:exercise-detail", args=[self.exercise.pk]))
        self.assertNotContains(response, reverse("exercises:exercise-detail", args=[self.draft_exercise.pk]))
        self.assertContains(response, "2 پرسش")

    def test_practice_numbers_exercises_by_position(self):
        # The stored `order` is a lesson-wide counter the generators keep appending to;
        # the step must number by list position, so it can never read "تمرین 61".
        lesson = Lesson.objects.create(
            course=self.course, title="Lektion mit Ordnung", order=9,
            estimated_time=10, is_published=True,
        )
        Exercise.objects.create(
            lesson=lesson, title="اول", type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            order=5, is_published=True,
        )
        Exercise.objects.create(
            lesson=lesson, title="دوم", type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            order=61, is_published=True,
        )

        response = self.client.get(reverse("lessons:lesson-detail", args=[lesson.pk]))

        self.assertContains(response, "تمرین 1")
        self.assertContains(response, "تمرین 2")
        self.assertNotContains(response, "تمرین 61")

    def test_mixed_prose_uses_explicit_direction_not_auto(self):
        # The block bodies hold Persian and German on one line; every German run must be
        # explicitly LTR and isolated, and no browser heuristic (`dir="auto"`) may decide.
        response = self.client.get(reverse("lessons:lesson-detail", args=[self.rich.pk]))
        self.assertNotContains(response, 'dir="auto"')
        self.assertContains(response, 'class="run run--de" lang="de" dir="ltr"')

    def test_a_translation_in_brackets_keeps_its_brackets(self):
        # The reported bug: `Ich bin Ali.  (من علی هستم.)` split the bracket pair across the
        # line -- `(` ended the German run, `)` began the Persian one -- so the brackets sat
        # at opposite ends and the German sentence read as the aside. A bracket belongs to
        # the text it wraps, and a German-first line is laid out left to right.
        # A NOTE block rather than an EXAMPLE one. The examples and dialogue steps render
        # the same sentences as cards and keep only the block's heading, so an EXAMPLE body
        # no longer reaches the page (see lessons/steps/_sentences.html). The direction rule
        # under test is about the body, so it is checked where a body still renders.
        LessonContent.objects.create(
            lesson=self.rich, type="NOTE", title="Achtung",
            body="Ich bin Ali.  (من علی هستم.)", order=99,
        )

        html = self.client.get(self.url).content.decode()

        self.assertIn('<bdi class="text-line" dir="ltr"><bdi class="run run--de"', html)
        self.assertIn(
            '<bdi class="run run--de" lang="de" dir="ltr">Ich bin Ali.  </bdi>'
            '<bdi class="run run--fa" lang="fa" dir="rtl">(من علی هستم.)</bdi>',
            html,
        )

    def test_the_examples_step_does_not_repeat_the_block_body(self):
        # The examples and dialogue steps hold the same sentences twice: once as a content
        # block and once as LessonSentence rows. The rows are the better rendering (audio,
        # speaker, a separated translation), so the block keeps only its heading. Without
        # that, the learner reads the whole list twice, which is most of the scroll length of
        # the two heaviest steps in the lesson.
        response = self.client.get(self.url)

        self.assertContains(response, "Beispiele")
        self.assertNotContains(response, "مثال‌ها:")
        self.assertContains(response, "Guten Tag 1")

    def test_vocabulary_step_paginates_inside_the_step(self):
        for number in range(30):
            word = Word.objects.create(
                word=f"Wort{number}", word_type="OTHER", meaning_fa=f"معنی {number}",
                level=self.level, is_published=True,
            )
            LessonWord.objects.create(lesson=self.bare, word=word, role="NEW", order=number + 1)
        response = self.client.get(self.bare_url)
        vocabulary = {step["key"]: step for step in response.context["steps"]}["vocabulary"]
        self.assertEqual(vocabulary["count"], 30)
        self.assertEqual(len(vocabulary["words"]), WORDS_PER_STEP)
        # The page link must carry the learner back to the vocabulary step.
        self.assertContains(response, "words_page=2#step-vocabulary")

    def test_a_later_vocabulary_page_shows_the_sentences_instead_of_the_lead_in(self):
        # The repetition this step had: the authored lead-in was rendered again on every
        # page. Page 1 keeps it; the pages after it show the lesson's own sentences, with
        # the words of that page marked in each one.
        lesson = Lesson.objects.create(
            course=self.course, title="Wortschatz mit Sätzen", order=10,
            estimated_time=10, is_published=True,
        )
        LessonContent.objects.create(
            lesson=lesson, type="VOCABULARY", title="Wortschatz: Alltag",
            body="واژه‌های روز:\nTag (روز) · Buch (کتاب)\n\nEnglish: everyday words.", order=1,
        )

        for number in range(28):
            word = Word.objects.create(
                word=f"Satzwort{number}", word_type="OTHER", meaning_fa=f"معنی {number}",
                level=self.level, is_published=True,
            )
            LessonWord.objects.create(lesson=lesson, word=word, role="NEW", order=number + 1)

        # The words the sentences use sit on page 2, so the context block has something to
        # show there and page 1 has something the later page does not repeat.
        tag = Word.objects.create(
            word="Tag", word_type="NOUN", article="der", gender="M", meaning_fa="روز",
            level=self.level, is_published=True,
        )
        book = Word.objects.create(
            word="Heft", word_type="NOUN", article="das", gender="N", meaning_fa="دفتر",
            level=self.level, is_published=True,
        )
        LessonWord.objects.create(lesson=lesson, word=tag, role="NEW", order=29)
        LessonWord.objects.create(lesson=lesson, word=book, role="NEW", order=30)

        lines = [
            ("Guten Tag!", "روز بخیر!", "EXAMPLE", ""),
            ("Das Heft ist neu.", "دفتر نو است.", "EXAMPLE", ""),
        ]
        for order, (text, translation, role, speaker) in enumerate(lines, start=1):
            sentence = Sentence.objects.create(
                text=text, translation_fa=translation, level=self.level, is_published=True
            )
            LessonSentence.objects.create(
                lesson=lesson, sentence=sentence, role=role, speaker=speaker, order=order
            )

        url = reverse("lessons:lesson-detail", args=[lesson.pk])
        first = self.step_html("vocabulary", url)
        second = self.step_html("vocabulary", url, "?words_page=2")

        self.assertIn("Wortschatz: Alltag", first)
        self.assertIn("واژه‌های روز", first)
        self.assertNotIn("Wortschatz: Alltag", second)
        self.assertNotIn("واژه‌های روز", second)

        self.assertNotIn("Guten Tag!", first)
        self.assertIn("Guten Tag!", second)
        self.assertIn("روز بخیر!", second)
        self.assertIn("همین واژه‌ها، این بار در جمله", second)
        # The entries are whole words of the page, shown as chips beside the sentence.
        self.assertIn('<span class="chip" lang="de" dir="ltr">Tag</span>', second)
        self.assertIn('<span class="chip" lang="de" dir="ltr">Heft</span>', second)

    def test_the_context_sentences_are_the_lessons_own_ones(self):
        lesson = Lesson.objects.create(
            course=self.course, title="Kontext", order=11, estimated_time=10, is_published=True
        )
        word = Word.objects.create(
            word="Guten", word_type="OTHER", meaning_fa="خوب", level=self.level, is_published=True
        )
        LessonWord.objects.create(lesson=lesson, word=word, role="NEW", order=1)
        sentence = Sentence.objects.create(
            text="Guten Tag, wie geht es dir?", translation_fa="روز بخیر، حالت چطور است؟",
            level=self.level, is_published=True,
        )
        LessonSentence.objects.create(lesson=lesson, sentence=sentence, role="EXAMPLE", order=1)

        steps = {step["key"]: step for step in self.steps_of(reverse("lessons:lesson-detail", args=[lesson.pk]))}
        rows = steps["vocabulary"]["context_sentences"]

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["link"].sentence, sentence)
        self.assertEqual([w.word for w in rows[0]["words"]], ["Guten"])

    def test_a_word_is_not_used_by_a_sentence_that_merely_contains_its_letters(self):
        # `es` must not match inside `dieses`, or every page would list every sentence.
        lesson = Lesson.objects.create(
            course=self.course, title="Teilwörter", order=12, estimated_time=10, is_published=True
        )
        word = Word.objects.create(
            word="es", word_type="PRONOUN", meaning_fa="آن", level=self.level, is_published=True
        )
        LessonWord.objects.create(lesson=lesson, word=word, role="NEW", order=1)
        sentence = Sentence.objects.create(
            text="Ich lese dieses Buch.", translation_fa="من این کتاب را می‌خوانم.",
            level=self.level, is_published=True,
        )
        LessonSentence.objects.create(lesson=lesson, sentence=sentence, role="EXAMPLE", order=1)

        steps = {step["key"]: step for step in self.steps_of(reverse("lessons:lesson-detail", args=[lesson.pk]))}
        self.assertEqual(steps["vocabulary"]["context_sentences"], [])

    def test_finish_step_offers_the_next_lesson_and_a_way_back(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse("lessons:lesson-detail", args=[self.follow_up.pk]))
        self.assertContains(response, reverse("lessons:lesson-list"))

    def test_the_last_lesson_closes_the_course_instead_of_only_going_back(self):
        """The last page of the course used to be one sentence and then nothing (P-30)."""
        response = self.client.get(self.bare_url)

        self.assertContains(response, "پایان دورهٔ A1")
        # The marker belongs to the next-lesson button itself, so its absence says the
        # button is gone rather than that the words happen to be missing from the page
        # («به درس بعدی بروی» is still said by a lesson with no content of its own).
        self.assertNotContains(response, "data-finish-next")

    def test_unpublished_lessons_are_not_reachable(self):
        response = self.client.get(reverse("lessons:lesson-detail", args=[self.draft.pk]))
        self.assertEqual(response.status_code, 404)

    def test_one_h1_and_one_heading_per_step(self):
        response = self.client.get(self.url)
        html = response.content.decode()
        self.assertEqual(html.count("<h1"), 1)
        self.assertEqual(html.count('class="journey-step__title"'), len(response.context["steps"]))

    def test_no_locked_or_premium_wording(self):
        response = self.client.get(self.url)
        for word in ("قفل", "پریمیوم", "اشتراک", "خرید"):
            self.assertNotContains(response, word)


class CourseFinishTests(TestCase):
    """The end of the course: the last lesson says the course is finished and what is next.

    A complete course used to stop at lesson 24 with nothing but a link back to the path,
    which is the one moment a learner decides whether to stay (P-30). The panel is built
    from the content — how many lessons the course has and whether a later course exists —
    so it cannot promise an A2 that is not there.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Deutsch A1", is_published=True
        )
        cls.first = Lesson.objects.create(
            course=cls.course, title="Hallo", order=1, estimated_time=45, is_published=True
        )
        cls.last = Lesson.objects.create(
            course=cls.course, title="Abschluss", order=2, estimated_time=45, is_published=True
        )
        cls.user = User.objects.create_user(username="sina", password="a-strong-password")

    def url(self, lesson=None):
        return reverse("lessons:lesson-detail", args=[(lesson or self.last).pk])

    def test_a_lesson_in_the_middle_of_the_course_says_nothing_about_finishing(self):
        response = self.client.get(self.url(self.first))

        self.assertNotContains(response, "پایان دورهٔ A1")
        self.assertContains(response, "data-finish-next")

    def test_the_last_lesson_names_the_finish_and_counts_the_course(self):
        response = self.client.get(self.url())

        self.assertContains(response, "پایان دورهٔ A1")
        self.assertContains(response, "2 درس از 2")

    def test_the_finish_offers_the_three_things_that_are_really_next(self):
        response = self.client.get(self.url())

        self.assertContains(response, reverse("exams:exam-index"))
        self.assertContains(response, reverse("vocabulary:word-review"))
        self.assertContains(response, reverse("lessons:practice-path"))

    def test_a_finished_learner_is_told_the_course_is_finished(self):
        self.client.force_login(self.user)
        complete_lesson(self.user, self.last, "finish")

        response = self.client.get(self.url())

        self.assertContains(response, "دورهٔ A1 را کامل کردی")

    def test_a_learner_who_has_not_finished_is_not_told_they_have(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url())

        self.assertContains(response, "پایان دورهٔ A1")
        self.assertNotContains(response, "دورهٔ A1 را کامل کردی")

    def test_without_a_later_course_the_page_says_so_instead_of_promising_one(self):
        response = self.client.get(self.url())

        self.assertContains(response, "دورهٔ بعدی (A2) هنوز اینجا نیست")

    def test_a_later_course_is_offered_when_one_exists(self):
        higher = LanguageLevel.objects.create(level="A2", title="میانی", order=2)
        next_course = Course.objects.create(
            language_level=higher, title="Deutsch A2", is_published=True
        )

        response = self.client.get(self.url())

        self.assertContains(response, reverse("lessons:course-detail", args=[next_course.pk]))
        self.assertNotContains(response, "هنوز اینجا نیست")

    def test_a_later_course_that_is_still_a_draft_is_not_offered(self):
        higher = LanguageLevel.objects.create(level="A2", title="میانی", order=2)
        Course.objects.create(language_level=higher, title="Deutsch A2", is_published=False)

        response = self.client.get(self.url())

        self.assertContains(response, "دورهٔ بعدی (A2) هنوز اینجا نیست")


class LessonProgressTests(TestCase):
    """The rules a learner's lesson history depends on (``lessons/progress.py``).

    Builds its own small course (no seeding), so it is runnable on its own:
        python manage.py test lessons.tests.LessonProgressTests
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="دورهٔ آلمانی A1", is_published=True
        )
        # Enough content for the step order intro → explanation → vocabulary →
        # grammar → finish, which the resume test below relies on.
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Hallo", order=1, estimated_time=45, is_published=True
        )
        cls.second_lesson = Lesson.objects.create(
            course=cls.course, title="Tschüss", order=2, estimated_time=30, is_published=True
        )
        LessonContent.objects.create(
            lesson=cls.lesson, type="EXPLANATION", title="Was lernst du?", body="متن", order=1
        )
        word = Word.objects.create(
            word="hallo", word_type="OTHER", meaning_fa="سلام", level=cls.level, is_published=True
        )
        LessonWord.objects.create(lesson=cls.lesson, word=word, role="NEW", order=1)
        grammar = Grammar.objects.create(
            title="Personalpronomen", explanation="توضیح", level=cls.level, is_published=True
        )
        LessonGrammar.objects.create(lesson=cls.lesson, grammar=grammar, order=1)

        cls.user = User.objects.create_user(username="sina", password="a-strong-password")

    def test_the_journey_steps_and_the_model_steps_are_the_same_ten_names(self):
        """``current_step`` stores journey keys, so the two lists must not drift apart."""
        from lessons.journey import _STEP_SPEC

        self.assertEqual(list(_STEP_SPEC), [step.value for step in LessonProgress.Step])

    def test_the_first_visit_starts_the_lesson_at_the_first_step(self):
        row = record_step(self.user, self.lesson, "intro")
        self.assertEqual(row.status, LessonProgress.Status.IN_PROGRESS)
        self.assertEqual(row.current_step, "intro")
        self.assertIsNotNone(row.started_at)
        self.assertIsNotNone(row.last_activity_at)
        self.assertIsNone(row.completed_at)

    def test_coming_back_does_not_reset_when_the_lesson_was_started(self):
        first = record_step(self.user, self.lesson, "intro")
        started_at = first.started_at

        again = record_step(self.user, self.lesson, "vocabulary")

        self.assertEqual(again.pk, first.pk, "a second visit must not create a second row")
        self.assertEqual(again.started_at, started_at)
        self.assertEqual(again.current_step, "vocabulary")

    def test_moving_a_step_moves_last_activity_and_nothing_else(self):
        first = record_step(self.user, self.lesson, "intro")
        first_activity = first.last_activity_at

        row = record_step(self.user, self.lesson, "grammar")

        self.assertGreater(row.last_activity_at, first_activity)
        self.assertIsNone(row.completed_at)
        self.assertEqual(LessonProgress.objects.filter(user=self.user).count(), 1)

    def test_completing_sets_the_status_and_both_timestamps(self):
        record_step(self.user, self.lesson, "practice")

        row = complete_lesson(self.user, self.lesson, "finish")

        self.assertEqual(row.status, LessonProgress.Status.COMPLETED)
        self.assertIsNotNone(row.completed_at)
        self.assertIsNotNone(row.started_at)
        self.assertEqual(row.current_step, "finish")
        self.assertGreaterEqual(row.completed_at, row.started_at)

    def test_completing_twice_does_not_move_the_completion_time(self):
        """Otherwise ``completed_at - started_at`` would stop being the real duration."""
        finished_at = complete_lesson(self.user, self.lesson, "finish").completed_at

        again = complete_lesson(self.user, self.lesson, "finish")

        self.assertEqual(again.completed_at, finished_at)

    def test_reading_a_finished_lesson_does_not_unfinish_it(self):
        complete_lesson(self.user, self.lesson, "finish")

        row = record_step(self.user, self.lesson, "vocabulary")

        self.assertEqual(row.status, LessonProgress.Status.COMPLETED)
        self.assertEqual(row.current_step, "vocabulary")

    def test_every_lesson_keeps_its_own_row(self):
        record_step(self.user, self.lesson, "intro")
        record_step(self.user, self.second_lesson, "intro")
        self.assertEqual(LessonProgress.objects.filter(user=self.user).count(), 2)

    def test_progress_state_speaks_the_language_the_page_scripts_read(self):
        record_step(self.user, self.lesson, "grammar")

        state = progress_state(self.user)

        self.assertEqual(state["source"], "server")
        self.assertEqual(state["lastLessonId"], self.lesson.pk)
        self.assertEqual(state["lessons"][self.lesson.pk]["status"], "started")
        self.assertIsNotNone(state["lessons"][self.lesson.pk]["updatedAt"])

    def test_progress_state_is_honest_about_an_untouched_lesson(self):
        complete_lesson(self.user, self.lesson, "finish")

        state = progress_state(self.user)

        self.assertEqual(state["lessons"][self.lesson.pk]["status"], "completed")
        self.assertNotIn(self.second_lesson.pk, state["lessons"])

    def test_the_last_lesson_is_the_one_touched_most_recently(self):
        record_step(self.user, self.lesson, "intro")
        record_step(self.user, self.second_lesson, "intro")
        self.assertEqual(progress_state(self.user)["lastLessonId"], self.second_lesson.pk)

    def test_a_learner_with_no_history_has_an_empty_state(self):
        state = progress_state(self.user)
        self.assertEqual(state["lessons"], {})
        self.assertIsNone(state["lastLessonId"])


class LessonProgressEndpointTests(TestCase):
    """The endpoint the lesson page posts each step to."""

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="دورهٔ آلمانی A1", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Hallo", order=1, estimated_time=45, is_published=True
        )
        LessonContent.objects.create(
            lesson=cls.lesson, type="EXPLANATION", title="Was lernst du?", body="متن", order=1
        )
        word = Word.objects.create(
            word="hallo", word_type="OTHER", meaning_fa="سلام", level=cls.level, is_published=True
        )
        LessonWord.objects.create(lesson=cls.lesson, word=word, role="NEW", order=1)
        grammar = Grammar.objects.create(
            title="Personalpronomen", explanation="توضیح", level=cls.level, is_published=True
        )
        LessonGrammar.objects.create(lesson=cls.lesson, grammar=grammar, order=1)

        cls.user = User.objects.create_user(username="sina", password="a-strong-password")

    def post(self, payload, lesson=None):
        return self.client.post(
            reverse("lessons:lesson-progress", args=[(lesson or self.lesson).pk]),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_an_anonymous_visitor_cannot_record_progress(self):
        response = self.post({"step": "intro"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LessonProgress.objects.exists())

    def test_a_move_is_recorded_and_the_five_facts_come_back(self):
        self.client.force_login(self.user)

        response = self.post({"step": "grammar"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body), {"status", "current_step", "started_at", "last_activity_at", "completed_at"}
        )
        self.assertEqual(body["status"], "in_progress")
        self.assertEqual(body["current_step"], "grammar")
        self.assertIsNotNone(body["started_at"])
        self.assertIsNone(body["completed_at"])

    def test_completing_reports_the_completion_time(self):
        self.client.force_login(self.user)

        body = self.post({"step": "finish", "complete": True}).json()

        self.assertEqual(body["status"], "completed")
        self.assertIsNotNone(body["completed_at"])

    def test_an_unknown_step_is_refused(self):
        self.client.force_login(self.user)
        response = self.post({"step": "spelling"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(LessonProgress.objects.exists())

    def test_a_get_is_not_a_write(self):
        """Arriving on the lesson page must not count as progress on its own."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("lessons:lesson-progress", args=[self.lesson.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertFalse(LessonProgress.objects.exists())

    def test_an_unpublished_lesson_cannot_be_recorded(self):
        draft = Lesson.objects.create(
            course=self.course, title="Entwurf", order=9, estimated_time=5, is_published=False
        )
        self.client.force_login(self.user)
        self.assertEqual(self.post({"step": "intro"}, lesson=draft).status_code, 404)

    def test_the_lesson_page_opens_on_the_step_the_learner_stopped_at(self):
        record_step(self.user, self.lesson, "grammar")
        self.client.force_login(self.user)

        response = self.client.get(reverse("lessons:lesson-detail", args=[self.lesson.pk]))

        keys = [step["key"] for step in response.context["steps"]]
        self.assertEqual(response.context["resume_step"], keys.index("grammar"))
        self.assertContains(response, f'data-resume-step="{keys.index("grammar")}"')

    def test_a_step_that_is_no_longer_in_the_journey_is_ignored(self):
        """Lesson content changes, so a stored step can outlive its step. It must not
        break the page — the learner simply opens at the beginning."""
        record_step(self.user, self.lesson, "listening")
        self.client.force_login(self.user)

        response = self.client.get(reverse("lessons:lesson-detail", args=[self.lesson.pk]))

        self.assertIsNone(response.context["resume_step"])
        self.assertNotContains(response, "data-resume-step")

    def test_a_lesson_never_opened_has_no_resume_step(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("lessons:lesson-detail", args=[self.lesson.pk]))
        self.assertIsNone(response.context["resume_step"])
        self.assertNotContains(response, "data-resume-step")

    def test_the_lesson_page_offers_the_endpoint_only_to_a_signed_in_learner(self):
        url = reverse("lessons:lesson-detail", args=[self.lesson.pk])
        endpoint = reverse("lessons:lesson-progress", args=[self.lesson.pk])

        self.client.force_login(self.user)
        self.assertContains(self.client.get(url), f'data-progress-url="{endpoint}"')

        self.client.logout()
        self.assertNotContains(self.client.get(url), "data-progress-url")

    def test_the_lesson_page_ships_the_learners_progress_to_the_browser(self):
        record_step(self.user, self.lesson, "intro")
        self.client.force_login(self.user)

        response = self.client.get(reverse("lessons:lesson-detail", args=[self.lesson.pk]))

        self.assertEqual(
            response.context["progress_state"]["lessons"][self.lesson.pk]["status"], "started"
        )
        self.assertContains(response, 'id="progress-state"')

    def test_anonymous_visitors_are_given_no_server_progress_at_all(self):
        """Without it, progress.js stays on localStorage — the pre-existing behaviour."""
        response = self.client.get(reverse("lessons:lesson-detail", args=[self.lesson.pk]))
        self.assertIsNone(response.context["progress_state"])
        self.assertNotContains(response, 'id="progress-state"')

    def test_the_signed_in_dashboard_ships_the_same_progress(self):
        record_step(self.user, self.lesson, "intro")
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"))

        self.assertContains(response, 'id="progress-state"')
        self.assertIn(self.lesson.pk, response.context["progress_state"]["lessons"])

    def test_the_learning_path_ships_the_same_progress(self):
        record_step(self.user, self.lesson, "intro")
        self.client.force_login(self.user)

        response = self.client.get(reverse("lessons:lesson-list"))

        self.assertContains(response, 'id="progress-state"')
        self.assertIn(self.lesson.pk, response.context["progress_state"]["lessons"])


class GuestProgressImportTests(TestCase):
    """Moving a browser's guest progress onto the account that just signed in.

    A visitor learns without an account and their lessons live in localStorage. Signing up
    switches the dashboard to the server's answer, which knows nothing about them — so the
    dashboard asks, and posts what the browser claims. These tests are about what that
    claim is allowed to do: create a lesson the account never opened, move a started lesson
    to completed, and nothing else. It can never un-finish a lesson or reach another
    learner's rows.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="دورهٔ آلمانی A1", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Hallo", order=1, estimated_time=45, is_published=True
        )
        cls.other = Lesson.objects.create(
            course=cls.course, title="Tschüss", order=2, estimated_time=30, is_published=True
        )
        cls.draft = Lesson.objects.create(
            course=cls.course, title="Entwurf", order=3, estimated_time=5, is_published=False
        )
        cls.user = User.objects.create_user(username="sina", password="a-strong-password")

    def post(self, payload, raw=None):
        return self.client.post(
            reverse("lessons:lesson-import"),
            data=raw if raw is not None else json.dumps(payload),
            content_type="application/json",
        )

    def rows(self):
        return LessonProgress.objects.filter(user=self.user)

    def test_an_anonymous_visitor_cannot_import(self):
        response = self.post({"lessons": {str(self.lesson.pk): "completed"}})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LessonProgress.objects.exists())

    def test_a_get_is_not_a_write(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("lessons:lesson-import"))
        self.assertEqual(response.status_code, 405)
        self.assertFalse(LessonProgress.objects.exists())

    def test_a_finished_lesson_becomes_a_real_completion(self):
        self.client.force_login(self.user)

        response = self.post({"lessons": {str(self.lesson.pk): "completed"}})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["imported"], 1)
        row = self.rows().get()
        self.assertEqual(row.status, LessonProgress.Status.COMPLETED)
        self.assertIsNotNone(row.completed_at)

    def test_a_started_lesson_becomes_an_unfinished_one(self):
        """The browser said the lesson was opened, so nothing may claim it was finished."""
        self.client.force_login(self.user)

        self.post({"lessons": {str(self.lesson.pk): "started"}})

        row = self.rows().get()
        self.assertEqual(row.status, LessonProgress.Status.IN_PROGRESS)
        self.assertIsNone(row.completed_at)

    def test_importing_never_un_finishes_a_lesson(self):
        self.client.force_login(self.user)
        done = complete_lesson(self.user, self.other, "finish")
        finished_at = done.completed_at

        response = self.post({"lessons": {str(self.other.pk): "started"}})

        self.assertEqual(response.json()["imported"], 0)
        done.refresh_from_db()
        self.assertEqual(done.status, LessonProgress.Status.COMPLETED)
        self.assertEqual(done.completed_at, finished_at)

    def test_a_second_import_of_the_same_lesson_writes_nothing_new(self):
        self.client.force_login(self.user)

        first = self.post({"lessons": {str(self.lesson.pk): "completed"}}).json()
        second = self.post({"lessons": {str(self.lesson.pk): "completed"}}).json()

        self.assertEqual(first["imported"], 1)
        self.assertEqual(second["imported"], 0)
        self.assertEqual(self.rows().count(), 1)

    def test_a_lesson_that_is_not_published_is_ignored(self):
        self.client.force_login(self.user)

        response = self.post({"lessons": {str(self.draft.pk): "completed"}})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["imported"], 0)
        self.assertFalse(self.rows().exists())

    def test_a_lesson_that_does_not_exist_is_ignored(self):
        self.client.force_login(self.user)

        response = self.post({"lessons": {"999999": "completed"}})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["imported"], 0)

    def test_broken_input_is_refused_rather_than_guessed_at(self):
        self.client.force_login(self.user)

        self.assertEqual(self.post(None, raw="{").status_code, 400)
        self.assertEqual(self.post({"lessons": []}).status_code, 400)
        self.assertEqual(self.post({"lessons": {"7": "almost"}}).status_code, 400)
        self.assertEqual(self.post({"lessons": {"sieben": "completed"}}).status_code, 400)
        self.assertFalse(self.rows().exists())

    def test_the_import_only_writes_for_the_learner_who_asks(self):
        self.client.force_login(self.user)
        someone_else = User.objects.create_user(username="ali", password="a-strong-password")

        self.post({"lessons": {str(self.lesson.pk): "completed"}})

        self.assertTrue(self.rows().exists())
        self.assertFalse(LessonProgress.objects.filter(user=someone_else).exists())

    def test_the_dashboard_offers_the_import_only_to_a_signed_in_learner(self):
        """The panel ships hidden, so a visitor is never shown an offer that cannot work."""
        visitor = self.client.get(reverse("home"))
        self.assertNotContains(visitor, "data-progress-import")

        self.client.force_login(self.user)
        member = self.client.get(reverse("home"))
        self.assertContains(member, "data-progress-import")
        self.assertContains(member, reverse("lessons:lesson-import"))


class TodayFactsTests(ReadinessFixture):
    """``lessons.today``: where the learner is, and what they have already done.

    This module used to own the whole «امروز» list; the day is now built once in
    ``lessons/skill_path.py::today_board`` and is covered by ``GuidedDayTests`` and
    ``DashboardTodayTests``. What is pinned here are the facts that day is made of: which
    lesson is the one to work on, that it is the lesson touched last, that a draft is never
    offered, and that another learner's rows are never read.
    """

    def setUp(self):
        self.today = timezone.localdate()

    def test_a_new_learner_is_sent_to_the_first_lesson(self):
        work = lesson_to_work_on(self.user)
        self.assertEqual(work["lesson"], self.lessons[0])
        self.assertFalse(work["started"])

    def test_a_started_lesson_wins_over_the_next_one(self):
        LessonProgress.objects.create(
            user=self.user, lesson=self.lessons[2], status=LessonProgress.Status.IN_PROGRESS
        )

        work = lesson_to_work_on(self.user)

        self.assertEqual(work["lesson"], self.lessons[2])
        self.assertTrue(work["started"])

    def test_the_lesson_touched_last_is_the_one_to_continue(self):
        LessonProgress.objects.create(
            user=self.user, lesson=self.lessons[0], status=LessonProgress.Status.IN_PROGRESS,
            last_activity_at=timezone.now() - timedelta(days=2),
        )
        LessonProgress.objects.create(
            user=self.user, lesson=self.lessons[1], status=LessonProgress.Status.IN_PROGRESS,
            last_activity_at=timezone.now(),
        )

        self.assertEqual(started_lesson(self.user), self.lessons[1])

    def test_a_completed_lesson_is_not_one_you_are_inside(self):
        self.complete_lesson(self.user, self.lessons[0])

        self.assertIsNone(started_lesson(self.user))
        self.assertEqual(next_lesson(self.user), self.lessons[1])

    def test_a_draft_lesson_is_never_offered_as_next(self):
        """The draft lesson sits at order 9, after the three published ones, so a query that
        forgot the draft rule would reach it."""
        for lesson in self.lessons:
            self.complete_lesson(self.user, lesson)

        self.assertEqual(self.draft_lesson.order, 9)
        self.assertIsNone(next_lesson(self.user))
        self.assertIsNone(lesson_to_work_on(self.user))

    def test_another_learners_rows_are_never_read(self):
        self.complete_lesson(self.other, self.lessons[0])
        self.answer(self.other, self.questions[0], True)
        self.word_score(self.other, self.words[0], correct=0, wrong=2)

        work = lesson_to_work_on(self.user)

        self.assertEqual(work["lesson"], self.lessons[0])
        self.assertEqual(exercises_done_today(self.user, self.today), set())
        self.assertEqual(day_summary(self.user, self.today)["answered"], 0)

    def test_todays_count_is_only_todays_answers(self):
        self.answer(self.user, self.questions[0], True)
        self.answer(self.user, self.questions[1], False)

        summary = day_summary(self.user, self.today)

        self.assertEqual(summary["answered"], 2)
        self.assertEqual(summary["correct"], 1)

    def test_yesterdays_answers_do_not_count_as_today(self):
        attempt = self.answer(self.user, self.questions[0], True)
        ExerciseAttempt.objects.filter(pk=attempt.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        self.assertEqual(day_summary(self.user, self.today)["answered"], 0)
        # …but they are real history, so the page still knows when the learner was last here.
        self.assertIsNotNone(last_activity(self.user))

    def test_last_activity_reads_both_stored_tables(self):
        nine_days_ago = timezone.now() - timedelta(days=9)
        LessonProgress.objects.create(
            user=self.user, lesson=self.lessons[0], status=LessonProgress.Status.IN_PROGRESS,
            last_activity_at=nine_days_ago,
        )

        self.assertEqual(last_activity(self.user), nine_days_ago)

        self.answer(self.user, self.questions[0], True)

        self.assertGreater(last_activity(self.user), nine_days_ago)


class DashboardTodayTests(ReadinessFixture):
    """The «امروز» panel: the same guided day «مسیر امروز» shows, plus what is already done.

    The panel used to be a list of its own — a lesson item and a practice item — and now
    renders ``lessons/skill_path.py::day_steps`` through the same include the path page uses,
    so the two pages cannot disagree about what today is. What is pinned here is that the
    panel is built for a learner we can identify and not for a visitor, that the review step
    appears for a due word and for a missed word alike, and that the week chart and the
    "answered today" line come from the learner's own stored rows.
    """

    def setUp(self):
        self.url = reverse("home")

    def test_a_visitor_gets_no_week_chart(self):
        response = self.client.get(self.url)
        self.assertIsNone(response.context["weekly"])
        self.assertNotContains(response, "dash-week")

    def test_the_week_chart_counts_the_learners_own_attempts(self):
        question = self.exercise.questions.first()
        ExerciseAttempt.objects.create(
            user=self.user, exercise=self.exercise, question=question, is_correct=True
        )
        ExerciseAttempt.objects.create(
            user=self.user, exercise=self.exercise, question=question, is_correct=False
        )

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        weekly = response.context["weekly"]
        self.assertEqual(len(weekly["days"]), 7)
        today = weekly["days"][-1]
        self.assertTrue(today["is_today"])
        self.assertEqual(today["answered"], 2)
        self.assertEqual(today["correct"], 1)
        self.assertEqual(weekly["peak"], 2)
        self.assertContains(response, "هفت روز اخیر")

    def test_a_week_with_nothing_in_it_draws_no_chart(self):
        """A learner who has answered nothing gets no empty chart — the peak is zero, so
        the page has no scale to draw and says nothing rather than nothing-shaped bars."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.context["weekly"]["peak"], 0)
        self.assertNotContains(response, "dash-week")

    def test_a_visitor_gets_the_single_next_step_instead_of_a_day(self):
        response = self.client.get(self.url)
        self.assertIsNone(response.context["board"])
        self.assertContains(response, "dash-next")
        self.assertNotContains(response, "برنامهٔ امروز تو")

    def test_a_signed_in_learner_gets_the_day_instead_of_the_card(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.context["board"]["path"]["lesson"], self.lessons[0])
        self.assertContains(response, "برنامهٔ امروز تو")
        self.assertNotContains(response, "dash-next")
        self.assertContains(
            response, reverse("lessons:lesson-detail", args=[self.lessons[0].pk])
        )

    def test_the_dashboard_and_the_path_show_the_same_day(self):
        """The whole point of the union: one «امروز», built by one function, not two."""
        self.client.force_login(self.user)

        dashboard = self.client.get(self.url)
        path = self.client.get(reverse("lessons:practice-path"))

        dashboard_steps = []
        for step in dashboard.context["board"]["day"]["steps"]:
            dashboard_steps.append((step["key"], step["title"]))

        path_steps = []
        for step in path.context["day"]["steps"]:
            path_steps.append((step["key"], step["title"]))

        self.assertEqual(dashboard_steps, path_steps)

    def test_a_started_lesson_is_todays_lesson(self):
        LessonProgress.objects.create(
            user=self.user, lesson=self.lessons[1], status=LessonProgress.Status.IN_PROGRESS
        )

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.context["board"]["path"]["lesson"], self.lessons[1])
        self.assertContains(
            response, reverse("lessons:lesson-detail", args=[self.lessons[1].pk])
        )

    def test_a_due_word_puts_review_first_in_the_day(self):
        WordProgress.objects.create(
            user=self.user, word=self.words[0], attempt_count=1, correct_count=1, wrong_count=0,
            due_at=timezone.now() - timedelta(hours=1),
        )

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        steps = response.context["board"]["day"]["steps"]
        self.assertEqual(steps[0]["key"], "review")
        self.assertEqual(steps[0]["size"], "1 واژه")
        self.assertContains(response, "وقت مرور این واژه‌ها رسیده")
        self.assertContains(response, reverse("vocabulary:word-review"))

    def test_a_word_answered_wrong_still_gets_a_review_step(self):
        """The other reason to review: nothing is due on the schedule yet, but the learner
        has words they got wrong, and both live on the same review page."""
        self.word_score(self.user, self.words[0], correct=0, wrong=2)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        steps = response.context["board"]["day"]["steps"]
        self.assertEqual(steps[0]["key"], "review")
        self.assertEqual(steps[0]["size"], "1 واژه")
        self.assertContains(response, "واژه‌هایی که در تمرین‌ها اشتباه زده‌ای")
        self.assertContains(response, reverse("vocabulary:word-review"))

    def test_a_clean_record_with_nothing_due_gets_no_review_step(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        keys = []
        for step in response.context["board"]["day"]["steps"]:
            keys.append(step["key"])

        self.assertNotIn("review", keys)

    def test_todays_count_comes_from_the_stored_attempts(self):
        self.answer(self.user, self.questions[0], True)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertContains(response, "امروز 1 پاسخ داده‌ای · 1 درست")

    def test_a_finished_course_says_so_instead_of_offering_more(self):
        for lesson in self.lessons:
            self.complete_lesson(self.user, lesson)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertIsNone(response.context["board"]["day"])
        self.assertContains(response, "همهٔ درس‌های منتشرشده را تمام کرده‌ای")

    def test_the_plan_never_turns_into_a_streak(self):
        """No streaks, no points, no invented pressure — the panel is a list, not a game."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertNotContains(response, "روز پیاپی")
        self.assertNotContains(response, "امتیاز")


class LessonFinishMistakesTests(ReadinessFixture):
    """The finish step's own block: the words *this* lesson cost the learner.

    The lesson page already showed the learner's mistakes elsewhere in the product; what
    these tests pin is that the end of a lesson closes the loop instead of only counting
    the steps behind them, that the block stays silent when there is nothing honest to
    say, and that it is scoped to the lesson being read rather than to the level.
    """

    def setUp(self):
        self.url = reverse("lessons:lesson-detail", args=[self.lessons[0].pk])

    def test_a_visitor_is_shown_no_mistake_block(self):
        # No stored answers to read, so the block is absent rather than empty.
        response = self.client.get(self.url)

        self.assertEqual(response.context["lesson_mistakes"], [])
        self.assertNotContains(response, "واژه‌هایی که در این درس اشتباه زدی")

    def test_a_learner_who_missed_nothing_in_this_lesson_gets_no_block(self):
        self.word_score(self.user, self.words[0], correct=4, wrong=0)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertNotContains(response, "واژه‌هایی که در این درس اشتباه زدی")
        self.assertNotContains(response, "finish-missed__cta")

    def test_the_words_missed_in_this_lesson_are_named_and_practised(self):
        self.word_score(self.user, self.words[0], correct=0, wrong=2)

        self.client.force_login(self.user)
        response = self.client.get(self.url)
        term_url = reverse("vocabulary:word-detail", args=[self.words[0].pk])

        self.assertContains(response, "واژه‌هایی که در این درس اشتباه زدی")
        # German inside Persian UI, and the meaning the learner was asked for.
        self.assertContains(response, f'class="finish-missed__term" href="{term_url}" lang="de" dir="ltr"')
        self.assertContains(response, self.words[0].meaning_fa)
        self.assertContains(response, "غلط: 2")
        self.assertContains(response, reverse("vocabulary:word-review"))

    def test_a_word_missed_elsewhere_is_not_named_in_this_lesson(self):
        # The fixture links every word to lesson 1 and none to lesson 2, so the mistake
        # belongs to lesson 1 and lesson 2 must not borrow it.
        self.word_score(self.user, self.words[0], correct=0, wrong=2)

        self.client.force_login(self.user)
        other = self.client.get(reverse("lessons:lesson-detail", args=[self.lessons[1].pk]))

        self.assertEqual(other.context["lesson_mistakes"], [])
        self.assertNotContains(other, "واژه‌هایی که در این درس اشتباه زدی")

    def test_finish_step_contains_srs_bridge_card(self):
        response = self.client.get(self.url)
        self.assertContains(response, "اتصال به سیستم مرور فاصله‌دار (SRS)")
        self.assertContains(response, reverse("vocabulary:word-review"))
        self.assertEqual(response.context["new_words_count"], 4)


class SkillPathTests(TestCase):
    """Today's path, one node per skill (``lessons/skill_path.py``).

    The point of the module is that a lesson's exercise wall becomes a short list, so
    these tests pin down the rules that make that honest: a skill with no material gets no
    node, pressing a skill's node opens that skill's own drill, and the nodes that are not
    drills (the conversation, speaking and the test) stay outside the day's goal.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", title_fa="درس ۱",
            is_published=True, order=1, estimated_time=10,
        )

        cls.vocabulary = Exercise.objects.create(
            lesson=cls.lesson, title="واژگان", type="MULTIPLE_CHOICE", order=1, is_published=True
        )
        cls.grammar = Exercise.objects.create(
            lesson=cls.lesson, title="آرتیکل", type="MULTIPLE_CHOICE", order=2, is_published=True
        )
        cls.listening = Exercise.objects.create(
            lesson=cls.lesson, title="شنیدن", type="LISTENING", order=3, is_published=True
        )
        cls.writing = Exercise.objects.create(
            lesson=cls.lesson, title="ترجمه", type="TRANSLATION", order=4, is_published=True
        )
        # No READING exercise on purpose: that skill must simply be absent.

        word = Word.objects.create(
            word="bestellen", word_type="VERB", meaning_fa="سفارش دادن",
            level=cls.level, is_published=True,
        )
        grammar_question = Question.objects.create(
            exercise=cls.grammar, prompt="کدام آرتیکل درست است؟", order=1
        )
        QuestionTarget.objects.create(
            question=grammar_question, word=word, role=QuestionTarget.Role.GRAMMAR
        )

        cls.user = User.objects.create_user(
            username="path-learner", password="a-strong-password"
        )

    def nodes_by_key(self, nodes):
        result = {}
        for node in nodes:
            result[node["key"]] = node
        return result

    def test_the_shape_of_an_exercise_decides_its_skill(self):
        self.assertEqual(skill_of(self.listening, set()), "listening")
        self.assertEqual(skill_of(self.writing, set()), "writing")
        self.assertEqual(skill_of(self.vocabulary, set()), "vocabulary")

    def test_a_grammar_target_outranks_the_shape(self):
        """An article drill is an ordinary multiple choice; only its target says so."""
        self.assertEqual(skill_of(self.grammar, set()), "vocabulary")
        self.assertEqual(skill_of(self.grammar, {self.grammar.pk}), "grammar")

    def test_a_visitor_gets_no_path_at_all(self):
        self.assertIsNone(build_path(AnonymousUser(), timezone.localdate()))

    def test_there_is_one_node_per_skill_that_has_material(self):
        path = build_path(self.user, timezone.localdate())
        keys = []
        for node in path["nodes"]:
            keys.append(node["key"])

        self.assertEqual(keys, ["vocabulary", "grammar", "listening", "writing", "speaking"])
        # READING has no exercise in this lesson, so it is absent rather than empty.
        self.assertNotIn("reading", keys)

    def test_the_step_test_waits_until_a_lesson_is_finished(self):
        """A test measures what has been studied. On the first day that is nothing, so the
        map does not offer one — and once a lesson is behind the learner it does."""
        path = build_path(self.user, timezone.localdate())

        self.assertFalse(path["test_ready"])
        self.assertNotIn("test", [node["key"] for node in path["nodes"]])

        Lesson.objects.create(
            course=self.course, title="Lektion 2", title_fa="درس ۲",
            is_published=True, order=2, estimated_time=10,
        )
        LessonProgress.objects.create(
            user=self.user, lesson=self.lesson, status=LessonProgress.Status.COMPLETED
        )
        started = build_path(self.user, timezone.localdate())

        self.assertTrue(started["test_ready"])
        self.assertIn("test", [node["key"] for node in started["nodes"]])

    def test_the_goal_counts_only_the_practice_nodes_that_exist(self):
        path = build_path(self.user, timezone.localdate())
        self.assertEqual(path["goal"], 4)
        self.assertEqual(path["done"], 0)

    def test_speaking_and_the_test_sit_outside_the_goal(self):
        """Speaking cannot be measured and the test is a whole sitting, not a drill. The test
        only joins the map once there is something to measure, so one lesson is finished and
        a second one is waiting here."""
        Lesson.objects.create(
            course=self.course, title="Lektion 2", title_fa="درس ۲",
            is_published=True, order=2, estimated_time=10,
        )
        LessonProgress.objects.create(
            user=self.user, lesson=self.lesson, status=LessonProgress.Status.COMPLETED
        )
        path = build_path(self.user, timezone.localdate())
        nodes = self.nodes_by_key(path["nodes"])

        self.assertTrue(nodes["speaking"]["optional"])
        self.assertTrue(nodes["test"]["milestone"])
        self.assertEqual(nodes["speaking"]["state"], "side")
        self.assertEqual(nodes["test"]["state"], "side")

    def test_every_practice_node_points_at_a_real_exercise(self):
        path = build_path(self.user, timezone.localdate())
        nodes = self.nodes_by_key(path["nodes"])

        # The node opens the graded drill itself, so the label and the content agree.
        self.assertIn("/exercises/%d/" % self.vocabulary.pk, nodes["vocabulary"]["url"])
        self.assertIn("/exam/sprechen/", nodes["speaking"]["url"])
        self.assertEqual(nodes["vocabulary"]["xp"], XP_PER_NODE)

    def test_every_skill_label_opens_its_own_drill(self):
        """The reported bug: five skill labels all opened the same conversation page, so
        «واژگان» did not lead to a vocabulary drill. Each node now opens its own exercise.
        """
        path = build_path(self.user, timezone.localdate())
        nodes = self.nodes_by_key(path["nodes"])

        self.assertEqual(nodes["vocabulary"]["mode"], "drill")
        self.assertEqual(nodes["listening"]["mode"], "drill")
        self.assertIn("/exercises/%d/" % self.listening.pk, nodes["listening"]["url"])
        self.assertIn("/exercises/%d/" % self.writing.pk, nodes["writing"]["url"])

    def test_the_lesson_practice_is_the_same_map_the_path_shows(self):
        """The journey's practice step and «مسیر امروز» must not disagree.

        Both read ``skill_nodes``, so the lesson's own map is exactly the path's drill
        nodes with the conversation, speaking and test left off — and the same tally.
        """
        today = timezone.localdate()
        path = build_path(self.user, today)
        practice = lesson_practice(self.lesson, self.user, today)

        path_skills = []
        for node in path["nodes"]:
            if node["mode"] == "drill":
                path_skills.append(node["key"])

        practice_skills = []
        for node in practice["nodes"]:
            practice_skills.append(node["key"])

        self.assertEqual(practice_skills, path_skills)
        self.assertEqual(practice["goal"], path["goal"])
        self.assertEqual(practice["done"], path["done"])

    def test_the_lesson_practice_marks_where_the_learner_is(self):
        practice = lesson_practice(self.lesson, self.user, timezone.localdate())
        self.assertEqual(practice["nodes"][0]["state"], "now")

    def test_the_journey_practice_step_shows_skill_nodes_not_the_wall(self):
        """The journey's «تمرین» step used to render the lesson's whole exercise list.
        It now shows one node per skill, with the full list kept behind a disclosure.
        """
        self.client.force_login(self.user)
        response = self.client.get(reverse("lessons:lesson-detail", args=[self.lesson.pk]))

        self.assertContains(response, "practice-node")
        self.assertContains(response, "همهٔ تمرین‌های این درس")
        # The vocabulary node opens the vocabulary drill itself, not something else.
        self.assertContains(response, "/exercises/%d/" % self.vocabulary.pk)

    def test_the_finish_step_recaps_what_the_lesson_held(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("lessons:lesson-detail", args=[self.lesson.pk]))

        self.assertContains(response, "finish-summary")
        self.assertContains(response, "این درس چه چیزی داشت")

    def test_a_lesson_with_a_dialogue_gets_one_conversation_node_of_its_own(self):
        sentence = Sentence.objects.create(
            text="Guten Morgen!", translation_fa="صبح بخیر!",
            level=self.level, is_published=True,
        )
        LessonSentence.objects.create(
            lesson=self.lesson, sentence=sentence,
            role=LessonSentence.Role.DIALOGUE, speaker="Anna", order=1,
        )

        path = build_path(self.user, timezone.localdate())
        nodes = self.nodes_by_key(path["nodes"])

        self.assertIn("conversation", nodes)
        # The teacher chat, and optional: nothing about a spoken turn can be graded here.
        self.assertIn("/exercises/chat/", nodes["conversation"]["url"])
        self.assertTrue(nodes["conversation"]["optional"])
        self.assertEqual(nodes["conversation"]["state"], "side")
        # It is one activity about the whole lesson, so it stays out of the day's goal.
        self.assertEqual(path["goal"], 4)

    def test_a_lesson_without_a_dialogue_gets_no_conversation_node(self):
        path = build_path(self.user, timezone.localdate())
        keys = []
        for node in path["nodes"]:
            keys.append(node["key"])

        self.assertNotIn("conversation", keys)

    def test_the_order_is_the_lessons_order_below_the_threshold(self):
        """Concept 15 is a selection function, and under the threshold it selects nothing."""
        question = Question.objects.create(exercise=self.writing, prompt="پرسش", order=1)
        ExerciseAttempt.objects.create(
            user=self.user, exercise=self.writing, question=question, is_correct=False
        )

        path = build_path(self.user, timezone.localdate())
        keys = []
        for node in path["nodes"]:
            keys.append(node["key"])

        self.assertEqual(keys[:4], ["vocabulary", "grammar", "listening", "writing"])

    def test_a_skill_the_learner_keeps_missing_moves_to_the_front(self):
        for number in range(MIN_ANSWERS):
            question = Question.objects.create(
                exercise=self.writing, prompt="پرسش %d" % number, order=number + 1
            )
            ExerciseAttempt.objects.create(
                user=self.user, exercise=self.writing, question=question, is_correct=False
            )

        path = build_path(self.user, timezone.localdate())
        keys = []
        for node in path["nodes"]:
            keys.append(node["key"])

        # WRITING is last in the lesson's own order; enough misses and it leads.
        self.assertEqual(keys[0], "writing")

    def test_the_first_unfinished_node_is_now_and_the_rest_are_next(self):
        path = build_path(self.user, timezone.localdate())
        states = []
        for node in path["nodes"]:
            states.append(node["state"])

        # The step test is not on the map until a lesson is finished, so the only "side"
        # node here is the speaking rehearsal.
        self.assertEqual(states, ["now", "next", "next", "next", "side"])

    def test_a_node_answered_today_is_done(self):
        ExerciseAttempt.objects.create(
            user=self.user, exercise=self.vocabulary,
            question=Question.objects.create(
                exercise=self.vocabulary, prompt="واژهٔ «hallo»؟", order=1
            ),
            is_correct=True,
        )

        path = build_path(self.user, timezone.localdate())
        nodes = self.nodes_by_key(path["nodes"])

        self.assertTrue(nodes["vocabulary"]["done"])
        self.assertEqual(path["done"], 1)
        # The unfinished one takes over as "now".
        self.assertEqual(nodes["grammar"]["state"], "now")

    def test_a_skill_stays_done_after_its_link_moves_on(self):
        """Answering one exercise must not un-finish the node.

        The node's link moves to the next exercise of that skill once one is answered, so
        "done" has to be read from the skill rather than from whatever the link points at
        now — otherwise the day's goal could never fill up.
        """
        second = Exercise.objects.create(
            lesson=self.lesson, title="واژگان ۲",
            type="MULTIPLE_CHOICE", order=5, is_published=True,
        )
        ExerciseAttempt.objects.create(
            user=self.user,
            exercise=self.vocabulary,
            question=Question.objects.create(
                exercise=self.vocabulary, prompt="واژهٔ «hallo»؟", order=1
            ),
            is_correct=True,
        )

        path = build_path(self.user, timezone.localdate())
        nodes = self.nodes_by_key(path["nodes"])

        self.assertTrue(nodes["vocabulary"]["done"])
        self.assertIn("/exercises/%d/" % second.pk, nodes["vocabulary"]["url"])
        self.assertEqual(path["done"], 1)


class LessonCheckTests(TestCase):
    """The «این درس را می‌دانم» sample check (``lessons/check.py``).

    The point of the check is that it is a *real* sample of the lesson's own questions, not
    a free pass, so these tests pin the rules that make it honest: it is short, it spans the
    lesson's kinds of drill, it never asks a question that cannot be graded, and the pass
    line is a ratio the caller can read.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", title_fa="درس ۱",
            is_published=True, order=1, estimated_time=10,
        )

        cls.choice = Exercise.objects.create(
            lesson=cls.lesson, title="واژگان", type="MULTIPLE_CHOICE", order=1, is_published=True
        )
        cls.listening = Exercise.objects.create(
            lesson=cls.lesson, title="شنیدن", type="LISTENING", order=2, is_published=True
        )

        for position in range(6):
            question = Question.objects.create(
                exercise=cls.choice, prompt="پرسش %d" % position, order=position
            )
            Answer.objects.create(question=question, text="درست", is_correct=True, order=1)
            Answer.objects.create(question=question, text="غلط", is_correct=False, order=2)

        for position in range(3):
            question = Question.objects.create(
                exercise=cls.listening, prompt="شنیداری %d" % position, order=position
            )
            Answer.objects.create(question=question, text="a", is_correct=True, order=1)
            Answer.objects.create(question=question, text="b", is_correct=False, order=2)

        # A scramble has no word bank on the check page, so it must never be sampled — the
        # same rule the daily session follows.
        cls.scramble = Exercise.objects.create(
            lesson=cls.lesson, title="مرتب کردن", type="SCRAMBLE", order=3, is_published=True
        )
        scramble_question = Question.objects.create(
            exercise=cls.scramble, prompt="مرتب کن", order=0
        )
        Answer.objects.create(
            question=scramble_question, text="Ich bin Sina", is_correct=True, order=1
        )

        cls.user = User.objects.create_user(
            username="check-learner", password="a-strong-password"
        )

    def test_the_sample_is_short_and_spans_the_drills(self):
        questions = check_questions(self.lesson)
        self.assertEqual(len(questions), CHECK_SIZE)

        types = []
        for question in questions:
            types.append(question.exercise.type)

        self.assertIn("MULTIPLE_CHOICE", types)
        self.assertIn("LISTENING", types)

    def test_a_scramble_is_never_sampled(self):
        for question in check_questions(self.lesson):
            self.assertNotEqual(question.exercise.type, "SCRAMBLE")

    def test_the_pass_line_is_a_ratio_rounded_up(self):
        self.assertEqual(pass_needed(5), 4)
        self.assertEqual(pass_needed(3), 3)
        self.assertEqual(pass_needed(0), 1)

    def test_the_intro_offers_the_check_only_to_a_signed_in_learner(self):
        url = reverse("lessons:lesson-detail", args=[self.lesson.pk])

        self.assertNotContains(self.client.get(url), "کاملش ثبت کنی")

        self.client.force_login(self.user)
        self.assertContains(self.client.get(url), "کاملش ثبت کنی")

    def test_the_check_page_asks_the_lessons_own_questions(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("lessons:lesson-check", args=[self.lesson.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "بررسی سریع این درس")
        self.assertEqual(response.context["total_questions"], CHECK_SIZE)

    def test_the_check_needs_an_account(self):
        url = reverse("lessons:lesson-check", args=[self.lesson.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])


class GuidedDayTests(SkillPathTests):
    """The guided day (``lessons/skill_path.py::day_steps``): read, practise, be measured.

    It reuses the path fixture because the day is built *from* the path — the same lesson
    and the same done-count decide both. What is pinned here is the order of the steps, that
    an unfinished step is never claimed as finished, that the day's goal can actually be
    reached, and that the single start button resumes rather than restarts.

    The step test is deliberately outside the goal — nothing about it is stored, so it can
    never be marked as taken — and it is left off the day entirely until a lesson is
    finished, because a test measures what has been studied.

    The lesson step is finished two ways on purpose: the row written by the journey's own
    button, and the plain fact of having reached the last step. The second one is what
    learners actually produce — every stored row was still ``in_progress``, so the day
    reported zero for people who had read the whole lesson.
    """

    def test_a_visitor_gets_no_guided_day(self):
        self.assertIsNone(day_steps(None, self.user, 12))

    def test_the_first_day_is_read_then_practise(self):
        """A learner who has finished nothing gets the two steps that first day is for; the
        step test is not one of them."""
        self.give_practice(self.lesson)
        path = build_path(self.user, timezone.localdate())
        day = day_steps(path, self.user, 12)

        self.assertEqual([step["key"] for step in day["steps"]], ["lesson", "practice"])
        # Sizes are the real ones, not a target invented for the page.
        self.assertEqual(day["steps"][0]["size"], "10 دقیقه")
        self.assertEqual(day["steps"][1]["size"], "1 پرسش")
        self.assertEqual(day["goal"], 2)
        self.assertEqual(day["finished"], 0)

    def second_lesson(self):
        """A second published lesson, so finishing the first leaves one to work on."""
        return Lesson.objects.create(
            course=self.course, title="Lektion 2", title_fa="درس ۲",
            is_published=True, order=2, estimated_time=10,
        )

    def give_practice(self, lesson):
        """One question of ``lesson`` that a session can really ask.

        The path fixture's exercises carry no answers, so its lesson has nothing to practise
        and therefore gets no practice step. The tests about that step give it something to
        ask; one question is one topic, so one question is a whole sitting.
        """
        exercise = Exercise.objects.create(
            lesson=lesson, title="تمرین", type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            order=9, is_published=True,
        )
        question = Question.objects.create(exercise=exercise, prompt="معنی؟", order=1)
        Answer.objects.create(question=question, text="درست", is_correct=True, order=1)
        Answer.objects.create(question=question, text="غلط", is_correct=False, order=2)
        return question

    def test_a_lesson_with_nothing_to_practise_gets_no_practice_step(self):
        """A step with nothing behind it would be a dead link, which is the same reason the
        skill map leaves a skill out rather than showing it empty."""
        path = build_path(self.user, timezone.localdate())
        day = day_steps(path, self.user, 12)

        self.assertEqual([step["key"] for step in day["steps"]], ["lesson"])
        self.assertEqual(day["goal"], 1)
        self.assertEqual(day["start"]["key"], "lesson")

    def test_the_step_test_joins_the_day_once_a_lesson_is_finished(self):
        """It is shown, and it is *not* counted: nothing about the test is stored, so it can
        never be ticked off, and a goal that included it could never be reached."""
        self.give_practice(self.second_lesson())
        LessonProgress.objects.create(
            user=self.user, lesson=self.lesson, status=LessonProgress.Status.COMPLETED
        )

        path = build_path(self.user, timezone.localdate())
        day = day_steps(path, self.user, 12)

        self.assertEqual(
            [step["key"] for step in day["steps"]], ["lesson", "practice", "test"]
        )
        self.assertEqual(day["steps"][2]["size"], "12 پرسش")
        self.assertFalse(day["steps"][2]["counted"])
        self.assertFalse(day["steps"][2]["done"])
        self.assertEqual(
            [step["key"] for step in day["steps"] if step["counted"]],
            ["lesson", "practice"],
        )

    def test_a_new_learner_starts_at_the_lesson(self):
        path = build_path(self.user, timezone.localdate())
        day = day_steps(path, self.user, 12)

        self.assertEqual(day["start"]["key"], "lesson")
        self.assertEqual(day["finished"], 0)

    def test_the_lesson_step_offers_the_short_read_beside_the_journey(self):
        """The journey is eight screens built from the lesson's own material; the revision
        page shows the same rows as one list. Both count, so both are offered."""
        path = build_path(self.user, timezone.localdate())
        day = day_steps(path, self.user, 12)
        lesson_step = day["steps"][0]

        self.assertEqual(
            lesson_step["url"], reverse("lessons:lesson-detail", args=[self.lesson.pk])
        )
        self.assertEqual(
            lesson_step["alt_url"], reverse("lessons:lesson-review", args=[self.lesson.pk])
        )

    def test_only_the_lesson_step_has_a_second_way_in(self):
        path = build_path(self.user, timezone.localdate())
        day = day_steps(path, self.user, 12)

        for step in day["steps"]:
            if step["key"] == "lesson":
                continue
            self.assertNotIn("alt_url", step)

    def test_a_finished_lesson_moves_the_start_to_practice(self):
        # The path is read first: this fixture has one lesson, so once it is completed there
        # is no lesson to work on and the day is empty (which the last test asserts). Here
        # the lesson is the one already chosen, and finishing it must move the start on.
        self.give_practice(self.lesson)
        path = build_path(self.user, timezone.localdate())
        LessonProgress.objects.create(
            user=self.user, lesson=self.lesson, status=LessonProgress.Status.COMPLETED
        )

        day = day_steps(path, self.user, 12)

        self.assertTrue(day["steps"][0]["done"])
        self.assertEqual(day["start"]["key"], "practice")
        self.assertEqual(day["finished"], 1)

    def test_reaching_the_last_step_counts_as_reading_the_lesson(self):
        """The row records where the learner is; pressing the button is a separate, and
        optional, act. Reaching the finish step means every step was walked."""
        self.give_practice(self.lesson)
        path = build_path(self.user, timezone.localdate())
        LessonProgress.objects.create(
            user=self.user,
            lesson=self.lesson,
            status=LessonProgress.Status.IN_PROGRESS,
            current_step=LessonProgress.Step.FINISH,
        )

        day = day_steps(path, self.user, 12)

        self.assertTrue(day["steps"][0]["done"])
        self.assertEqual(day["start"]["key"], "practice")
        self.assertEqual(day["finished"], 1)

    def test_a_lesson_left_in_the_middle_is_not_finished(self):
        path = build_path(self.user, timezone.localdate())
        LessonProgress.objects.create(
            user=self.user,
            lesson=self.lesson,
            status=LessonProgress.Status.IN_PROGRESS,
            current_step=LessonProgress.Step.GRAMMAR,
        )

        day = day_steps(path, self.user, 12)

        self.assertFalse(day["steps"][0]["done"])
        self.assertEqual(day["start"]["key"], "lesson")

    def test_the_day_can_reach_the_goal_it_prints(self):
        """The reported flaw: the step test was counted but can never be finished, so the day
        sat at «۲ از ۳» for ever and the button pointed back at the test. The goal counts only
        the steps that can honestly be finished, so reading the lesson and doing its sitting
        ends the day — and then there is nothing left to resume."""
        question = self.give_practice(self.second_lesson())
        LessonProgress.objects.create(
            user=self.user, lesson=self.lesson, status=LessonProgress.Status.COMPLETED
        )
        path = build_path(self.user, timezone.localdate())
        today_lesson = path["lesson"]

        day = day_steps(path, self.user, 12)

        self.assertEqual(day["goal"], 2)
        self.assertEqual(day["finished"], 0)
        self.assertEqual(day["start"]["key"], "lesson")

        # Read the lesson (the stored row is what finishes that step), then answer its
        # sitting — one question is one topic, so that one answer is the whole session.
        LessonProgress.objects.create(
            user=self.user, lesson=today_lesson,
            status=LessonProgress.Status.IN_PROGRESS,
            current_step=LessonProgress.Step.FINISH,
        )
        ExerciseAttempt.objects.create(
            user=self.user, exercise=question.exercise, question=question,
            answer=question.answers.get(is_correct=True), is_correct=True,
        )

        # Both the day and its practice step are built once per page load, so the next load
        # is what sees the work — exactly what ``today_board`` does on every request.
        day = day_steps(build_path(self.user, timezone.localdate()), self.user, 12)

        self.assertEqual(day["finished"], day["goal"])
        self.assertIsNone(day["start"])
        # The test is still on the page — it is simply not part of the goal.
        self.assertEqual(day["steps"][-1]["key"], "test")
        self.assertFalse(day["steps"][-1]["counted"])

    def due_word(self):
        """A published word this learner is due to review (the scheduler's own input)."""
        word = Word.objects.create(
            word="Tisch", word_type="NOUN", meaning_fa="میز",
            level=self.level, is_published=True,
        )
        WordProgress.objects.create(
            user=self.user, word=word,
            state=WordProgress.State.REVIEW,
            due_at=timezone.now() - timedelta(days=1),
        )
        return word

    def test_a_due_word_comes_first_in_the_day(self):
        """The schedule was the strongest retention tool in the product and the day never
        used it; the words whose review time has arrived now lead the day."""
        self.due_word()
        path = build_path(self.user, timezone.localdate())
        day = day_steps(path, self.user, 12)

        self.assertEqual(path["due_count"], 1)
        self.assertEqual(day["steps"][0]["key"], "review")
        self.assertEqual(day["steps"][0]["label"], "مرور")
        self.assertEqual(day["steps"][0]["url"], reverse("vocabulary:word-review"))
        self.assertEqual(day["steps"][0]["size"], "1 واژه")
        self.assertIn("وقت مرور", day["steps"][0]["hint"])
        # The lesson and the rest still follow it.
        self.assertEqual(day["start"]["key"], "review")

    def test_a_mistake_without_a_due_word_still_offers_review(self):
        """The two reasons to review are the schedule's due words and the learner's own
        mistakes. The step appears for either one, keeps the same identity («مرور»), and
        leads to the one review page both kinds of word live on."""
        word = Word.objects.create(
            word="rechnen", word_type="VERB", meaning_fa="حساب کردن",
            level=self.level, is_published=True,
        )
        WordProgress.objects.create(
            user=self.user, word=word, attempt_count=2, correct_count=0, wrong_count=2,
        )

        path = build_path(self.user, timezone.localdate())
        day = day_steps(path, self.user, 12)

        self.assertEqual(path["due_count"], 0)
        self.assertEqual(path["wrong_count"], 1)
        self.assertEqual(day["steps"][0]["key"], "review")
        self.assertEqual(day["steps"][0]["label"], "مرور")
        self.assertEqual(day["steps"][0]["size"], "1 واژه")
        self.assertEqual(day["steps"][0]["url"], reverse("vocabulary:word-review"))
        self.assertIn("اشتباه", day["steps"][0]["hint"])

    def test_nothing_due_leaves_the_day_as_it_was(self):
        self.give_practice(self.lesson)
        path = build_path(self.user, timezone.localdate())
        day = day_steps(path, self.user, 12)

        self.assertEqual(path["due_count"], 0)
        self.assertEqual([step["key"] for step in day["steps"]], ["lesson", "practice"])

    def test_a_finished_course_with_due_words_still_has_a_day(self):
        """A learner who finished the course used to get an empty day; the reviews that are
        due are now the whole day, so the loop keeps going."""
        self.due_word()
        LessonProgress.objects.create(
            user=self.user, lesson=self.lesson, status=LessonProgress.Status.COMPLETED
        )
        path = build_path(self.user, timezone.localdate())

        self.assertIsNone(path["lesson"])

        day = day_steps(path, self.user, 12)

        self.assertIsNotNone(day)
        self.assertEqual([step["key"] for step in day["steps"]], ["review"])

    def test_a_learner_with_no_lesson_left_gets_no_guided_day(self):
        """Every published lesson finished: there is nothing to read, so nothing to guide."""
        LessonProgress.objects.create(
            user=self.user, lesson=self.lesson, status=LessonProgress.Status.COMPLETED
        )
        path = build_path(self.user, timezone.localdate())

        self.assertIsNone(path["lesson"])
        self.assertIsNone(day_steps(path, self.user, 12))


class PracticePathPageTests(TestCase):
    """The page that shows the path: public, and honest about needing an account."""

    url = reverse("lessons:practice-path")

    @classmethod
    def setUpTestData(cls):
        level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        course = Course.objects.create(language_level=level, title="Kurs", is_published=True)
        lesson = Lesson.objects.create(
            course=course, title="Lektion 1", title_fa="درس ۱",
            is_published=True, order=1, estimated_time=10,
        )
        Exercise.objects.create(
            lesson=lesson, title="واژگان", type="MULTIPLE_CHOICE", order=1, is_published=True
        )
        cls.user = User.objects.create_user(username="page-learner", password="a-strong-password")

    def test_a_visitor_is_asked_for_an_account_rather_than_redirected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "به حساب تو نیاز دارد")

    def test_a_learner_sees_the_path_and_their_level(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "گرهٔ امروز")
        self.assertContains(response, "path-node--now")
        # The speaking rehearsal is reachable from the path.
        self.assertContains(response, reverse("exams:sprechen"))


class LessonReviewTests(TestCase):
    """The lesson review page: the lesson's own material, condensed, published only.

    Builds its own lesson (no seeding) so it is runnable on its own:
        python manage.py test lessons.tests.LessonReviewTests
    """

    @classmethod
    def setUpTestData(cls):
        level = LanguageLevel.objects.create(level="A1", title="مقدماتی", order=1)
        course = Course.objects.create(language_level=level, title="دورهٔ A1", is_published=True)
        cls.lesson = Lesson.objects.create(
            course=course, title="Hallo", title_fa="سلام",
            is_published=True, order=1, estimated_time=10,
        )

        # The key ideas are the prose blocks; a vocabulary block is not one.
        LessonContent.objects.create(lesson=cls.lesson, type="EXPLANATION", title="Was lernst du?", body="متن", order=1)
        LessonContent.objects.create(lesson=cls.lesson, type="NOTE", title="Achtung", body="نکته", order=2)
        LessonContent.objects.create(lesson=cls.lesson, type="VOCABULARY", title="Wortschatz", body="واژه‌ها", order=3)

        cls.word = Word.objects.create(
            word="Buch", word_type="NOUN", article="das", gender="N", plural="die Bücher",
            meaning_fa="کتاب", level=level, is_published=True,
        )
        cls.draft_word = Word.objects.create(
            word="Entwurf", word_type="OTHER", meaning_fa="پیش‌نویس", level=level, is_published=False,
        )
        LessonWord.objects.create(lesson=cls.lesson, word=cls.word, role="NEW", order=1)
        LessonWord.objects.create(lesson=cls.lesson, word=cls.draft_word, role="NEW", order=2)

        cls.grammar = Grammar.objects.create(
            title="Artikel",
            explanation="پاراگراف اول قاعده.\n\nپاراگراف دوم.",
            level=level, is_published=True,
        )
        LessonGrammar.objects.create(lesson=cls.lesson, grammar=cls.grammar, order=1)

        sentence = Sentence.objects.create(
            text="Das ist ein Buch.", translation_fa="این یک کتاب است.", level=level, is_published=True,
        )
        LessonSentence.objects.create(lesson=cls.lesson, sentence=sentence, role="EXAMPLE", order=1)

        cls.draft_lesson = Lesson.objects.create(
            course=course, title="Entwurf", is_published=False, order=2, estimated_time=10,
        )
        # A course is one per level, so the hidden lesson needs its own level too.
        other_level = LanguageLevel.objects.create(level="A2", title="پیشرفته", order=2)
        hidden_course = Course.objects.create(language_level=other_level, title="Entwurf-Kurs", is_published=False)
        cls.hidden_lesson = Lesson.objects.create(
            course=hidden_course, title="Versteckt", is_published=True, order=1, estimated_time=10,
        )

        cls.user = User.objects.create_user(username="review-learner", password="a-strong-password")

    @property
    def url(self):
        return reverse("lessons:lesson-review", args=[self.lesson.pk])

    def test_renders_for_anonymous_visitors(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "lessons/lesson_review.html")
        self.assertContains(response, "واژه‌های این درس")

    def test_only_published_words_are_shown(self):
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["word_rows"]), 1)
        self.assertContains(response, "Buch")
        self.assertNotContains(response, "Entwurf")

    def test_grammar_is_condensed_to_its_first_paragraph(self):
        response = self.client.get(self.url)
        self.assertContains(response, "پاراگراف اول قاعده.")
        self.assertNotContains(response, "پاراگراف دوم.")

    def test_key_ideas_are_the_explanation_and_note_blocks_only(self):
        response = self.client.get(self.url)
        titles = [block.title for block in response.context["review"]["ideas"]]
        self.assertEqual(titles, ["Was lernst du?", "Achtung"])
        self.assertNotContains(response, "Wortschatz")

    def test_words_and_sentences_are_both_rendered(self):
        response = self.client.get(self.url)
        self.assertContains(response, "کتاب")
        self.assertContains(response, "Das ist ein Buch.")

    def test_a_signed_in_learner_sees_a_status_label(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "word-row__status")

    def test_the_completion_action_is_offered_to_a_signed_in_learner(self):
        """Reading the lesson the short way has to count as reading it, or the day's first
        step could only ever be finished by walking all eight screens of the journey."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertContains(response, "data-review-complete")
        self.assertContains(
            response, reverse("lessons:lesson-progress", args=[self.lesson.pk])
        )

    def test_the_page_ships_this_learners_progress_so_the_button_knows(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'id="progress-state"')

    def test_an_anonymous_visitor_is_not_offered_the_completion_action(self):
        # A visitor has no LessonProgress row to write, so the button is not rendered and
        # the endpoint is not named — nothing to press, and nothing that lies about saving.
        response = self.client.get(self.url)

        self.assertNotContains(response, "data-review-complete")
        self.assertNotContains(
            response, reverse("lessons:lesson-progress", args=[self.lesson.pk])
        )
        self.assertNotContains(response, 'id="progress-state"')

    def test_an_unpublished_lesson_is_not_reachable(self):
        response = self.client.get(reverse("lessons:lesson-review", args=[self.draft_lesson.pk]))
        self.assertEqual(response.status_code, 404)

    def test_a_lesson_of_an_unpublished_course_is_not_reachable(self):
        response = self.client.get(reverse("lessons:lesson-review", args=[self.hidden_lesson.pk]))
        self.assertEqual(response.status_code, 404)

    def test_the_lesson_page_links_to_the_review(self):
        response = self.client.get(reverse("lessons:lesson-detail", args=[self.lesson.pk]))
        self.assertContains(response, self.url)


class ContrastiveCalloutsCommandTests(TestCase):
    """Verifies that seed_a1_contrastive_callouts seeds 10 callout blocks across L01–L05."""

    @classmethod
    def setUpTestData(cls):
        level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        course = Course.objects.create(language_level=level, title="German A1", is_published=True)
        for i in range(1, 6):
            Lesson.objects.create(course=course, order=i, title=f"Lesson {i}", estimated_time=15, is_published=True)

    def test_dry_run_does_not_mutate_database(self):
        out = io.StringIO()
        call_command("seed_a1_contrastive_callouts", "--dry-run", stdout=out)
        self.assertIn("[DRY RUN]", out.getvalue())
        self.assertEqual(LessonContent.objects.count(), 0)

    def test_command_seeds_callouts_and_is_idempotent(self):
        out = io.StringIO()
        call_command("seed_a1_contrastive_callouts", stdout=out)
        self.assertIn("10 created", out.getvalue())
        self.assertEqual(LessonContent.objects.count(), 10)

        # Verify each lesson has 2 callouts with types and badges
        for order in range(1, 6):
            blocks = LessonContent.objects.filter(lesson__order=order)
            self.assertEqual(blocks.count(), 2)
            titles = [b.title for b in blocks]
            self.assertTrue(any("تلهٔ فارسی‌زبانان" in t for t in titles))
            self.assertTrue(any("کارآموزی و زندگی" in t for t in titles))

        # Idempotency run
        out2 = io.StringIO()
        call_command("seed_a1_contrastive_callouts", stdout=out2)
        self.assertIn("10 reused", out2.getvalue())
        self.assertEqual(LessonContent.objects.count(), 10)

    def test_callouts_render_with_custom_classes_and_tags(self):
        call_command("seed_a1_contrastive_callouts", stdout=io.StringIO())
        lesson = Lesson.objects.get(order=1)
        response = self.client.get(reverse("lessons:lesson-detail", args=[lesson.pk]) + "?step=explanation")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "callout-falle")
        self.assertContains(response, "callout-ausbildung")
        self.assertContains(response, "tag--falle")
        self.assertContains(response, "tag--ausbildung")

