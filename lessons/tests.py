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

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.models import Count
from django.test import TestCase
from django.urls import reverse

from exercises.models import Answer, Exercise, Question
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
from lessons.views import WORDS_PER_STEP
from vocabulary.models import Grammar, Sentence, Word

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
        cls.rich = Lesson.objects.create(
            course=cls.course, title="Hallo", description="سلام و احوال‌پرسی.", order=1, estimated_time=45, is_published=True
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
            LessonContent.objects.create(
                lesson=cls.rich, type=kind, title=title, body="متن توضیح.\nhallo", order=order
            )

        cls.noun = Word.objects.create(
            word="Buch", word_type="NOUN", article="das", gender="N", plural="die Bücher",
            meaning_fa="کتاب", meaning_en="book", pronunciation="buːx", level=cls.level, is_published=True,
        )
        cls.verb = Word.objects.create(
            word="abfliegen", word_type="VERB", meaning_fa="پرواز کردن", meaning_en="to depart",
            pronunciation="ˈapfliːɡn̩", is_separable=True, perfect_auxiliary="SEIN",
            level=cls.level, is_published=True,
        )
        cls.other = Word.objects.create(
            word="hallo", word_type="OTHER", meaning_fa="سلام", meaning_en="hello",
            level=cls.level, is_published=True,
        )
        for order, word in enumerate([cls.noun, cls.verb, cls.other], start=1):
            LessonWord.objects.create(lesson=cls.rich, word=word, role="NEW" if order < 3 else "REVIEW", order=order)

        cls.grammar = Grammar.objects.create(
            title="Personalpronomen", explanation="توضیح گرامر.\nich bin", level=cls.level, is_published=True
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

    def test_word_cards_show_only_the_fields_a_word_actually_has(self):
        html = self.client.get(self.url).content.decode()
        cards = dict(re.findall(r'<article class="word-card" data-word-type="(\w+)">(.*?)</article>', html, flags=re.S))
        self.assertIn("die Bücher", cards["NOUN"])
        self.assertNotIn("جداپذیر", cards["NOUN"])
        self.assertIn("جداپذیر", cards["VERB"])
        self.assertNotIn("جمع", cards["VERB"])
        self.assertIn("سلام", cards["OTHER"])
        self.assertNotIn("تلفظ", cards["OTHER"])  # this word has no pronunciation

    def test_audio_is_never_invented(self):
        """None of the fixture rows has an audio file, so no player may appear."""
        response = self.client.get(self.url)
        self.assertNotContains(response, 'aria-controls="word-')
        self.assertNotContains(response, 'aria-controls="sentence-')
        self.assertNotContains(response, 'aria-controls="grammar-')

    def test_no_interactive_element_is_nested_inside_a_link(self):
        """Every word card is a card, not a link wrapping a play button."""
        html = self.client.get(self.url).content.decode()
        for anchor in re.findall(r"<a\b.*?</a>", html, flags=re.S):
            self.assertNotIn("<button", anchor)
            self.assertNotIn("<audio", anchor)

    def test_practice_offers_the_lesson_exercises_and_their_size(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse("exercises:exercise-detail", args=[self.exercise.pk]))
        self.assertNotContains(response, reverse("exercises:exercise-detail", args=[self.draft_exercise.pk]))
        self.assertContains(response, "2 پرسش")

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

    def test_finish_step_offers_the_next_lesson_and_a_way_back(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse("lessons:lesson-detail", args=[self.follow_up.pk]))
        self.assertContains(response, reverse("lessons:lesson-list"))
        self.assertContains(self.client.get(self.bare_url), "این آخرین درس این دوره است")

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
