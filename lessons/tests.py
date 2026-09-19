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

from __future__ import annotations

import io

from django.core.management import call_command
from django.db.models import Count
from django.test import TestCase

from lessons.models import (
    Course,
    LanguageLevel,
    LessonContent,
    LessonGrammar,
    LessonSentence,
    LessonWord,
)
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
        introduced: set[int] = set()
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
                self.assertIn(word.article, expected, f"{word.word} needs der/die/das")
                self.assertEqual(word.gender, expected[word.article], "article must match gender")
                self.assertTrue(word.word[:1].isupper(), "German nouns are capitalised")

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

    def counts(self) -> tuple[int, ...]:
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
