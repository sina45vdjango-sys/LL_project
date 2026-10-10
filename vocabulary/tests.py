import asyncio
import json
import re
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import AnonymousUser, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.paginator import Paginator
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from config.templatetags.lesson_text import list_lines, without_english
from exercises.models import Answer, Exercise, ExerciseAttempt, Question, QuestionTarget
from lessons.management.commands import generate_lesson_content_audio as content_audio
from lessons.models import (
    Course,
    LanguageLevel,
    Lesson,
    LessonContent,
    LessonProgress,
    LessonWord,
)

from . import audio
from .german_text import PERSIAN, spoken_text
from .lookup import lookup_candidates
from .management.commands import generate_grammar_audio as grammar_audio
from .management.commands import generate_sentence_audio as sentence_audio
from .management.commands import import_a1_words as word_import
from .models import Grammar, Sentence, Word, WordProgress
from .status import MISTAKE_LIMIT, STATUS_LABELS, status_of, word_rows
from .text_direction import line_runs, rendered
from .review import exercises_for_words, last_used_type, lesson_mistakes, review_plan
from .schedule import (
    DEFAULT_EASE,
    FAST_SECONDS,
    MAX_EASE,
    MAX_INTERVAL_DAYS,
    MIN_EASE,
    SLOW_SECONDS,
    due_words,
    ease_after_correct,
    ease_after_wrong,
    new_words,
    next_review,
    review_queue,
    speed_bucket,
)


class WordPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="Beginner", order=1)
        cls.word = Word.objects.create(word="Buch", word_type="NOUN", article="das",
                                       gender="N", plural="Bücher", meaning_fa="کتاب",
                                       meaning_en="book", level=cls.level, is_published=True)

    def test_word_list_renders_words_and_detail_links(self):
        response = self.client.get(reverse("vocabulary:word-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("vocabulary:word-detail", args=[self.word.pk]))
        self.assertContains(response, "کتاب")

    def test_word_list_is_paginated(self):
        for i in range(30):
            self.level.words.create(word=f"Wort{i}", word_type="OTHER", meaning_fa=f"معنی {i}",
                                    level=self.level, is_published=True)
        first = self.client.get(reverse("vocabulary:word-list"))
        self.assertEqual(len(first.context["words"]), 24)
        self.assertEqual(first.context["words"].paginator.count, 31)
        second = self.client.get(reverse("vocabulary:word-list") + "?page=2")
        self.assertEqual(len(second.context["words"]), 7)
        self.assertContains(first, "?page=2")

    def test_word_detail_omits_generic_study_advice(self):
        for word_type in ["NOUN", "VERB"]:
            self.word.word_type = word_type
            self.word.save(update_fields=["word_type"])
            response = self.client.get(reverse("vocabulary:word-detail", args=[self.word.pk]))
            self.assertNotContains(response, 'class="study-note"')
            self.assertNotContains(response, "کوچک، اما ماندگار")
            self.assertContains(response, "کتاب")
            self.assertContains(response, 'id="word-details"')

    def test_word_detail_renders_real_word(self):
        response = self.client.get(reverse("vocabulary:word-detail", args=[self.word.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "vocabulary/word_detail.html")
        self.assertContains(response, "Buch")
        self.assertContains(response, "کتاب")
        self.assertContains(response, "Bücher")

    def test_detail_has_themes_and_styles(self):
        # The theme is chosen on the profile page and resolved before the first paint,
        # so there is no navbar toggle; a signed-out visitor follows the system.
        response = self.client.get(reverse("vocabulary:word-detail", args=[self.word.pk]))
        self.assertNotContains(response, 'id="theme-toggle"')
        self.assertContains(response, 'content="light dark"')
        self.assertContains(response, 'data-theme-mode="system"')
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'vocabulary/css/word_detail.css')
        self.assertContains(response, 'id="word-details"')


class VocabularyFixture(TestCase):
    """Shared fixture: a level, a course, a lesson and words of every shape.

    Covers the fields the pages must show when they exist and hide when they do not:
    a full noun, a noun with no plural on record, a verb, a plain word, an unpublished
    word, and a word from a second level.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="Beginner", order=1)
        cls.other_level = LanguageLevel.objects.create(level="A2", title="Elementary", order=2)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", is_published=True, order=1, estimated_time=10
        )

        cls.noun = Word.objects.create(
            word="Buch", word_type="NOUN", article="das", gender="N", plural="Bücher",
            meaning_fa="کتاب", meaning_en="book", pronunciation="buːx", level=cls.level,
            is_published=True, audio="words/audio/buch.mp3",
        )
        cls.noun_without_plural = Word.objects.create(
            word="Name", word_type="NOUN", article="der", gender="M",
            meaning_fa="نام", level=cls.level, is_published=True,
        )
        cls.verb = Word.objects.create(
            word="lernen", word_type="VERB", meaning_fa="یاد گرفتن", level=cls.level,
            is_published=True, perfect_auxiliary="HABEN",
        )
        cls.plain = Word.objects.create(
            word="hallo", word_type="OTHER", meaning_fa="سلام", level=cls.level, is_published=True
        )
        cls.draft = Word.objects.create(
            word="Zzz", word_type="OTHER", meaning_fa="پیش‌نویس", level=cls.level, is_published=False
        )
        cls.other_level_word = Word.objects.create(
            word="Arbeit", word_type="NOUN", article="die", gender="F", meaning_fa="کار",
            level=cls.other_level, is_published=True,
        )

        LessonWord.objects.create(lesson=cls.lesson, word=cls.noun, role="NEW", order=1)

        cls.exercise = Exercise.objects.create(
            lesson=cls.lesson, title="واژگان — انتخاب معنی", instruction="یک گزینه را انتخاب کن.",
            type=Exercise.ExerciseType.MULTIPLE_CHOICE, order=1, is_published=True,
        )
        question = Question.objects.create(exercise=cls.exercise, prompt="معنی Buch؟", order=1)
        Answer.objects.create(question=question, text="کتاب", is_correct=True, order=1)
        Answer.objects.create(question=question, text="میز", is_correct=False, order=2)
        QuestionTarget.objects.create(question=question, word=cls.noun, role="TESTED_ITEM")


class WordListPageTests(VocabularyFixture):
    """The list is a dense row list: term + audio, meaning, grammar."""

    def setUp(self):
        self.url = reverse("vocabulary:word-list")

    def test_list_is_a_row_list_not_a_card_grid(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'class="vrow"')
        self.assertNotContains(response, "word-tile")
        self.assertNotContains(response, "word-grid")

    def test_each_row_carries_the_three_zones(self):
        response = self.client.get(self.url)
        detail_url = reverse("vocabulary:word-detail", args=[self.noun.pk])
        self.assertContains(response, f'class="vrow__term" href="{detail_url}" lang="de" dir="ltr"')
        self.assertContains(response, "کتاب")                 # the meaning
        self.assertContains(response, self.noun.type_label)    # اسم
        self.assertContains(response, self.noun.gender_label)  # خنثی
        self.assertContains(response, "Bücher")               # the plural

    def test_rows_use_the_shared_chip_and_audio_components(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'class="chip"')
        self.assertContains(response, 'class="chip chip--accent"')
        self.assertContains(response, 'class="audio-control audio-control--inline"')
        self.assertContains(response, f'aria-controls="word-{self.noun.pk}"')
        # The word without an audio file simply has no player.
        self.assertNotContains(response, f'aria-controls="word-{self.plain.pk}"')
        # The control is beside the term, never inside the link to the word page.
        for anchor in re.findall(r"<a\b.*?</a>", response.content.decode(), flags=re.S):
            self.assertNotIn("<button", anchor)

    def test_unpublished_words_are_not_listed(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, self.draft.meaning_fa)

    def test_level_tabs_carry_real_counts(self):
        response = self.client.get(self.url)
        counts = {level.level: level.word_count for level in response.context["levels"]}
        self.assertEqual(counts, {"A1": 4, "A2": 1})
        self.assertEqual(response.context["word_total"], 5)
        self.assertContains(response, str(reverse("vocabulary:word-level-list", args=["A2"])))

    def test_level_tabs_keep_their_order(self):
        """Annotating drops Meta ordering, so the tabs must be ordered explicitly."""
        response = self.client.get(self.url)
        html = response.content.decode()
        self.assertLess(html.index(">A1<"), html.index(">A2<"))
        self.assertLess(html.index("همهٔ سطح‌ها"), html.index(">A1<"))

    def test_page_state_is_stated_once(self):
        # `scope=all` on purpose: this test is about the pagination state, so it asks for
        # the whole published bank (5 words here) rather than the course's own words, which
        # the default list now shows.
        response = self.client.get(self.url, {"scope": "all"})
        self.assertContains(response, "5 واژه")
        self.assertNotContains(response, "صفحهٔ 1 از 1")  # a single page needs no page state
        for number in range(25):  # 30 words in total → two pages of 24
            Word.objects.create(word=f"Wort{number}", word_type="OTHER", meaning_fa="م",
                                level=self.level, is_published=True)
        first = self.client.get(self.url, {"scope": "all"})
        self.assertContains(first, "صفحهٔ 1 از 2")
        self.assertContains(first, "قبلی")
        self.assertContains(first, "بعدی")
        # The scope is carried through the pagination links, so page 2 keeps the full bank.
        self.assertContains(first, "?scope=all&amp;page=2")
        second = self.client.get(self.url, {"page": 2, "scope": "all"})
        self.assertContains(second, "صفحهٔ 2 از 2")
        self.assertContains(second, "?scope=all&amp;page=1")

    def test_level_list_shows_only_that_level(self):
        response = self.client.get(reverse("vocabulary:word-level-list", args=["a2"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "کار")
        self.assertNotContains(response, "کتاب")
        self.assertEqual(response.context["selected_level"], self.other_level)

    def test_level_with_no_words_has_an_empty_state(self):
        empty_level = LanguageLevel.objects.create(level="B1", title="Intermediate", order=3)
        response = self.client.get(reverse("vocabulary:word-level-list", args=[empty_level.level]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "vlist__empty")
        self.assertNotContains(response, 'class="vrow"')

    def test_list_loads_only_its_own_stylesheet(self):
        response = self.client.get(self.url)
        self.assertContains(response, "vocabulary/css/word_list.css")
        self.assertNotContains(response, "reader_modern.css")


class WordDetailPageTests(VocabularyFixture):
    """The word page is a study screen built from the shared components."""

    def get(self, word):
        response = self.client.get(reverse("vocabulary:word-detail", args=[word.pk]))
        self.assertEqual(response.status_code, 200)
        return response

    def test_the_german_word_is_the_heading(self):
        response = self.get(self.noun)
        self.assertEqual(response.content.decode().count("<h1"), 1)
        self.assertContains(response, 'id="german-word" lang="de" dir="ltr"')
        self.assertContains(response, "das")
        self.assertContains(response, self.noun.pronunciation)

    def test_it_uses_the_shared_audio_control(self):
        response = self.get(self.noun)
        self.assertContains(response, 'class="audio-toggle"')
        self.assertContains(response, f'aria-controls="word-{self.noun.pk}"')
        # The page's own second player is gone with its script.
        self.assertNotContains(response, 'id="word-audio"')
        self.assertNotContains(response, "word_audio.js")
        self.assertNotContains(response, 'class="audio-icon"')

    def test_missing_audio_is_stated_rather_than_hidden(self):
        response = self.get(self.plain)
        self.assertContains(response, "فایل تلفظ برای این واژه ثبت نشده است.")
        self.assertNotContains(response, 'class="audio-toggle"')

    def test_grammatical_rows_only_appear_when_the_word_has_them(self):
        noun = self.get(self.noun)
        self.assertContains(noun, "شکل جمع")
        self.assertContains(noun, "Bücher")
        self.assertContains(noun, "جنسیت")
        self.assertContains(noun, "خنثی")

        no_plural = self.get(self.noun_without_plural)
        self.assertContains(no_plural, "ثبت نشده")

        verb = self.get(self.verb)
        self.assertContains(verb, "جداشدنی")
        self.assertContains(verb, self.verb.get_perfect_auxiliary_display())
        self.assertNotContains(verb, "شکل جمع")

        other = self.get(self.plain)
        self.assertNotContains(other, "جداشدنی")
        self.assertNotContains(other, "جنسیت")

    def test_it_links_the_lessons_that_teach_the_word(self):
        response = self.get(self.noun)
        self.assertContains(response, reverse("lessons:lesson-detail", args=[self.lesson.pk]))
        self.assertContains(response, "درس 1")
        self.assertContains(response, "جدید")

    def test_it_links_the_exercises_that_test_the_word(self):
        response = self.get(self.noun)
        self.assertContains(response, reverse("exercises:exercise-detail", args=[self.exercise.pk]))
        self.assertContains(response, self.exercise.type_label)

    def test_context_panels_stay_out_of_the_way_when_there_is_nothing_to_show(self):
        response = self.get(self.other_level_word)
        self.assertNotContains(response, "این واژه در این درس‌ها")
        self.assertNotContains(response, "تمرین‌های این واژه")

    def test_the_decorative_flag_and_tagline_are_gone(self):
        response = self.get(self.noun)
        self.assertNotContains(response, "german-flag")
        self.assertNotContains(response, "word-card__bottom")
        self.assertNotContains(response, "یک واژه، یک دنیای تازه")
        self.assertNotContains(response, "WORT FÜR WORT")

    def test_a_draft_word_is_not_reachable_by_url(self):
        """The list hides it, so the detail page must hide it too."""
        response = self.client.get(reverse("vocabulary:word-detail", args=[self.draft.pk]))
        self.assertEqual(response.status_code, 404)


class WordLabelTests(VocabularyFixture):
    """Persian labels live on the model, so no template can drift."""

    def test_type_labels(self):
        self.assertEqual(self.noun.type_label, "اسم")
        self.assertEqual(self.verb.type_label, "فعل")
        self.assertEqual(self.plain.type_label, "سایر")

    def test_gender_label_is_empty_without_a_gender(self):
        self.assertEqual(self.noun.gender_label, "خنثی")
        self.assertEqual(self.other_level_word.gender_label, "مؤنث")
        self.assertEqual(self.verb.gender_label, "")

    def test_lookup_returns_the_persian_type_label(self):
        response = self.client.get(reverse("vocabulary:word-lookup"), {"q": "Buch"})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(results[0]["word_type"], "اسم")
        self.assertEqual(results[0]["meaning_fa"], "کتاب")
        self.assertTrue(results[0]["audio"].endswith("words/audio/buch.mp3"))


class WordLookupCandidateTests(SimpleTestCase):
    """vocabulary/lookup.py -- the pure guessing, with no database involved."""

    def test_infinitive_is_guessed_from_a_conjugated_form(self):
        self.assertIn("heißen", lookup_candidates("heiße"))
        self.assertIn("heißen", lookup_candidates("heißt"))

    def test_umlaut_and_plural_ending_are_both_undone(self):
        self.assertIn("Haus", lookup_candidates("Häuser"))
        self.assertIn("Buch", lookup_candidates("Bücher"))

    def test_adjective_ending_is_stripped(self):
        self.assertIn("schön", lookup_candidates("schöne"))
        self.assertIn("schön", lookup_candidates("schönen"))

    def test_reflexive_verb_is_guessed_with_its_pronoun(self):
        # Reflexive verbs are stored as "sich ärgern", but the sentence says "ärgert".
        self.assertIn("sich ärgern", lookup_candidates("ärgert"))
        self.assertIn("sich freuen", lookup_candidates("freut"))

    def test_the_word_itself_is_never_a_candidate(self):
        self.assertNotIn("Buch", lookup_candidates("Buch"))


class WordLookupInflectionTests(VocabularyFixture):
    """The lookup answers for an inflected form, not only the dictionary form."""

    def lookup(self, query):
        response = self.client.get(reverse("vocabulary:word-lookup"), {"q": query})
        self.assertEqual(response.status_code, 200)
        return response.json()["results"]

    def test_conjugated_verb_finds_its_infinitive(self):
        results = self.lookup("lernt")
        self.assertEqual(results[0]["word"], "lernen")

    def test_plural_finds_its_noun(self):
        results = self.lookup("Bücher")
        self.assertEqual(results[0]["word"], "Buch")

    def test_article_prefix_is_ignored(self):
        results = self.lookup("die Bücher")
        self.assertEqual(results[0]["word"], "Buch")

    def test_conjugated_reflexive_verb_finds_the_stored_entry(self):
        Word.objects.create(
            word="sich ärgern", word_type="VERB", meaning_fa="دلخور شدن",
            level=self.level, is_published=True,
        )
        results = self.lookup("ärgert")
        self.assertEqual(results[0]["word"], "sich ärgern")

    def test_nothing_is_invented_for_an_unknown_word(self):
        self.assertEqual(self.lookup("xyzzy"), [])

    def test_unpublished_word_stays_hidden(self):
        self.assertEqual(self.lookup("Zzz"), [])

    def test_exact_match_still_wins(self):
        results = self.lookup("Buch")
        self.assertEqual(results[0]["word"], "Buch")


class WordReviewPageTests(VocabularyFixture):
    """The review page: the first thing in the product to read WordProgress back."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = User.objects.create_user(username="learner", password="test-pass-12345")
        cls.other_user = User.objects.create_user(username="other", password="test-pass-12345")

    def setUp(self):
        self.client.force_login(self.user)

    def make_progress(self, word, wrong, correct):
        return WordProgress.objects.create(
            user=self.user,
            word=word,
            attempt_count=wrong + correct,
            wrong_count=wrong,
            correct_count=correct,
        )

    def test_anonymous_visitor_is_asked_for_an_account(self):
        self.client.logout()
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "این صفحه به حساب تو نیاز دارد.")
        # Nothing is listed, and no word row is rendered at all.
        self.assertNotContains(response, 'class="vrow"')
        self.assertEqual(list(response.context["words"]), [])

    def test_a_visitor_gets_no_new_words_block(self):
        """A visitor has no stored rows, so the scheduler has no queue to build."""
        self.client.logout()
        response = self.client.get(reverse("vocabulary:word-review"))

        self.assertIsNone(response.context["queue"])
        self.assertNotContains(response, "واژه‌های تازه‌ای که رسیده‌ای")

    def test_the_reached_new_words_are_shown_even_with_no_mistakes_yet(self):
        # The *new* tier belongs to a learner `review_plan` returns None for — words they
        # reached and never practised — so it must not sit behind the mistakes list.
        response = self.client.get(reverse("vocabulary:word-review"))

        self.assertEqual(list(response.context["words"]), [])
        self.assertEqual(response.context["queue"]["new"], [self.noun])
        self.assertContains(response, "واژه‌های تازه‌ای که رسیده‌ای")
        self.assertContains(response, reverse("vocabulary:word-detail", args=[self.noun.pk]))
        # The empty state says there are no mistakes; that is still true, but it is no
        # longer the whole page.
        self.assertNotContains(response, "هنوز اشتباهی ثبت نشده.")

    def test_a_practised_word_is_no_longer_new(self):
        self.make_progress(self.noun, wrong=0, correct=2)
        response = self.client.get(reverse("vocabulary:word-review"))

        self.assertEqual(response.context["queue"]["new"], [])
        self.assertNotContains(response, "واژه‌های تازه‌ای که رسیده‌ای")
        self.assertContains(response, "هنوز اشتباهی ثبت نشده.")

    def test_only_words_that_were_missed_are_listed(self):
        self.make_progress(self.noun, wrong=2, correct=1)
        # A word answered correctly every time is not a word to review.
        self.make_progress(self.verb, wrong=0, correct=4)
        response = self.client.get(reverse("vocabulary:word-review"))
        words = [row.word for row in response.context["words"]]
        self.assertIn(self.noun, words)
        self.assertNotIn(self.verb, words)

    def test_the_worst_word_comes_first(self):
        self.make_progress(self.noun, wrong=1, correct=5)
        self.make_progress(self.verb, wrong=3, correct=0)
        self.make_progress(self.plain, wrong=2, correct=2)
        response = self.client.get(reverse("vocabulary:word-review"))
        words = [row.word for row in response.context["words"]]
        self.assertEqual(words, [self.verb, self.plain, self.noun])

    def test_a_word_answered_right_more_often_sorts_later(self):
        # Same number of misses, so the tie is broken by how often it was answered right.
        self.make_progress(self.noun, wrong=2, correct=0)
        self.make_progress(self.verb, wrong=2, correct=6)
        response = self.client.get(reverse("vocabulary:word-review"))
        words = [row.word for row in response.context["words"]]
        self.assertEqual(words, [self.noun, self.verb])

    def test_the_row_shows_the_real_counters(self):
        self.make_progress(self.noun, wrong=7, correct=3)
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertContains(response, "غلط: 7")
        self.assertContains(response, "درست: 3")
        self.assertContains(response, "کتاب")

    def test_the_row_links_to_the_word_page(self):
        self.make_progress(self.noun, wrong=1, correct=0)
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertContains(response, reverse("vocabulary:word-detail", args=[self.noun.pk]))

    def test_an_unpublished_word_is_not_listed(self):
        self.make_progress(self.draft, wrong=5, correct=0)
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertEqual(list(response.context["words"]), [])

    def test_another_learners_mistakes_are_not_shown(self):
        WordProgress.objects.create(
            user=self.other_user, word=self.noun, attempt_count=3, wrong_count=3, correct_count=0
        )
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertEqual(list(response.context["words"]), [])

    def test_the_empty_state_says_the_list_fills_from_practice(self):
        # The empty state is for a learner with nothing at all to see: no mistakes *and*
        # no reached-but-unpractised words. The fixture's one linked word is marked as
        # practised first, or the page would (correctly) show it as a new word instead of
        # showing this empty state.
        self.make_progress(self.noun, wrong=0, correct=1)
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertContains(response, "هنوز اشتباهی ثبت نشده.")

    def test_the_page_says_nothing_about_rules_without_a_rule_mistake(self):
        # This fixture has no grammar question at all, so the rule half must be absent
        # rather than empty-looking (lessons/tests.py covers the half that has data).
        self.make_progress(self.noun, wrong=1, correct=0)
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertIsNone(response.context["grammar"])
        self.assertNotContains(response, "قاعده‌هایی که اشتباه زده‌ای")

    def test_the_list_is_paginated(self):
        for i in range(30):
            word = self.level.words.create(
                word=f"Wort{i}", word_type="OTHER", meaning_fa=f"معنی {i}",
                level=self.level, is_published=True,
            )
            self.make_progress(word, wrong=1, correct=0)
        first = self.client.get(reverse("vocabulary:word-review"))
        self.assertEqual(len(first.context["words"]), 24)
        second = self.client.get(reverse("vocabulary:word-review") + "?page=2")
        self.assertEqual(len(second.context["words"]), 6)
        self.assertContains(first, "?page=2")

    def test_the_vocabulary_list_offers_the_review_page(self):
        response = self.client.get(reverse("vocabulary:word-list"))
        self.assertContains(response, reverse("vocabulary:word-review"))

    def test_the_page_offers_where_to_practise(self):
        """A list of missed words is a report; the exercises are the review."""
        self.make_progress(self.noun, wrong=2, correct=0)
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertContains(response, "از کجا تمرین کنی")
        self.assertContains(response, self.exercise.title)
        self.assertContains(response, reverse("exercises:exercise-detail", args=[self.exercise.pk]))

    def test_a_row_carries_the_exercise_that_tests_its_own_word(self):
        self.make_progress(self.noun, wrong=2, correct=0)
        response = self.client.get(reverse("vocabulary:word-review"))
        row = response.context["words"][0]
        self.assertEqual(row.practice, [self.exercise])
        self.assertContains(response, "vrow__practice")

    def test_a_word_no_exercise_tests_gets_no_practice_link(self):
        # Nothing tests `hallo`, so the page must not pretend something does.
        self.make_progress(self.plain, wrong=3, correct=0)
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertEqual(response.context["words"][0].practice, [])
        self.assertNotContains(response, "vrow__practice")
        self.assertNotContains(response, "از کجا تمرین کنی")

    def test_a_draft_exercise_is_never_offered(self):
        # `update()` rather than `save()`: setUpTestData's objects are shared between the
        # tests of this class, so the in-memory row must keep saying what the DB says.
        Exercise.objects.filter(pk=self.exercise.pk).update(is_published=False)
        self.make_progress(self.noun, wrong=2, correct=0)
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertEqual(response.context["words"][0].practice, [])
        self.assertNotContains(response, "از کجا تمرین کنی")

    def test_the_page_counts_what_it_is_showing(self):
        self.make_progress(self.noun, wrong=2, correct=0)
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertEqual(response.context["wrong_word_count"], 1)
        self.assertEqual(response.context["exercise_count"], 1)


class WordReviewPlanTests(VocabularyFixture):
    """``vocabulary.review``: the one rule the review page and the dashboard share.

    Pure database work, no templates: what counts as a word to review, and which real
    exercises practise it.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = User.objects.create_user(username="plan", password="test-pass-12345")

    def make_progress(self, word, wrong, correct):
        return WordProgress.objects.create(
            user=self.user,
            word=word,
            attempt_count=wrong + correct,
            wrong_count=wrong,
            correct_count=correct,
        )

    def test_a_visitor_we_cannot_identify_has_no_plan(self):
        self.assertIsNone(review_plan(AnonymousUser()))

    def test_a_learner_with_no_mistakes_has_no_plan(self):
        self.make_progress(self.noun, wrong=0, correct=3)
        self.assertIsNone(review_plan(self.user))

    def test_the_plan_lists_the_missed_words_worst_first(self):
        self.make_progress(self.noun, wrong=1, correct=4)
        self.make_progress(self.verb, wrong=3, correct=0)
        plan = review_plan(self.user)
        self.assertEqual([row.word for row in plan["words"]], [self.verb, self.noun])
        self.assertEqual(plan["wrong_word_count"], 2)

    def test_the_word_limit_shortens_the_list_but_not_the_count(self):
        self.make_progress(self.noun, wrong=3, correct=0)
        self.make_progress(self.verb, wrong=2, correct=0)
        self.make_progress(self.plain, wrong=1, correct=0)
        plan = review_plan(self.user, word_limit=2)
        self.assertEqual(len(plan["words"]), 2)
        self.assertEqual(plan["wrong_word_count"], 3)

    def test_the_practice_is_the_real_exercise_that_tests_the_word(self):
        self.make_progress(self.noun, wrong=2, correct=0)
        plan = review_plan(self.user)
        self.assertEqual(len(plan["exercises"]), 1)
        self.assertEqual(plan["exercises"][0]["exercise"], self.exercise)
        self.assertEqual(plan["exercises"][0]["words"], [self.noun])
        self.assertEqual(plan["exercises"][0]["question_count"], 1)
        self.assertEqual(plan["exercises_by_word"][self.noun.pk], [self.exercise])

    def test_a_word_that_is_only_context_is_not_practised(self):
        # A word that merely appears in a question is not a word the learner was tested
        # on, so no exercise may be offered for it.
        question = self.exercise.questions.first()
        QuestionTarget.objects.create(question=question, word=self.plain, role="CONTEXT")
        self.make_progress(self.plain, wrong=2, correct=0)
        plan = review_plan(self.user)
        self.assertEqual(plan["words"][0].word, self.plain)
        self.assertEqual(plan["exercises"], [])
        self.assertNotIn(self.plain.pk, plan["exercises_by_word"])

    def test_the_exercise_covering_more_mistakes_comes_first(self):
        self.make_progress(self.noun, wrong=2, correct=0)
        self.make_progress(self.verb, wrong=2, correct=0)

        # The fixture's exercise tests one of the two; this one tests both.
        both = Exercise.objects.create(
            lesson=self.lesson, title="هر دو واژه", type="MULTIPLE_CHOICE",
            order=2, is_published=True,
        )
        number = 0
        for word in [self.noun, self.verb]:
            number += 1
            question = Question.objects.create(exercise=both, prompt=f"پرسش {number}", order=number)
            Answer.objects.create(question=question, text="پاسخ", is_correct=True, order=1)
            QuestionTarget.objects.create(question=question, word=word, role="TESTED_ITEM")

        plan = review_plan(self.user, exercise_limit=5)
        titles = [row["exercise"].title for row in plan["exercises"]]
        self.assertEqual(titles, ["هر دو واژه", self.exercise.title])

    def test_a_short_list_still_knows_where_every_word_is_practised(self):
        # The dashboard limits the list, but a word it does show must keep its practice
        # link even when that word is not one of the recommended exercises.
        self.make_progress(self.noun, wrong=3, correct=0)
        self.make_progress(self.verb, wrong=2, correct=0)

        only_verb = Exercise.objects.create(
            lesson=self.lesson, title="تمرین فعل", type="MULTIPLE_CHOICE", order=2, is_published=True
        )
        question = Question.objects.create(exercise=only_verb, prompt="فعل", order=1)
        Answer.objects.create(question=question, text="یاد گرفتن", is_correct=True, order=1)
        QuestionTarget.objects.create(question=question, word=self.verb, role="TESTED_ITEM")

        plan = review_plan(self.user, word_limit=1)
        # Only the worst word is shown...
        self.assertEqual(len(plan["words"]), 1)
        self.assertEqual(plan["words"][0].word, self.noun)
        # ...but the hidden one still knows where it is practised.
        self.assertIn(self.noun.pk, plan["exercises_by_word"])
        self.assertIn(self.verb.pk, plan["exercises_by_word"])


class LessonMistakesTests(VocabularyFixture):
    """``vocabulary.review.lesson_mistakes``: the review list, narrowed to one lesson.

    The finish step of a lesson is the one page that has to answer "what did *this*
    lesson cost me", so this pins the narrowing and the two empty cases, and leaves the
    definition of a missed word to ``WordReviewPlanTests``.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = User.objects.create_user(username="lektion", password="test-pass-12345")

    def make_progress(self, word, wrong, correct):
        return WordProgress.objects.create(
            user=self.user,
            word=word,
            attempt_count=wrong + correct,
            wrong_count=wrong,
            correct_count=correct,
        )

    def test_a_visitor_we_cannot_identify_has_nothing(self):
        self.assertEqual(lesson_mistakes(AnonymousUser(), self.lesson), [])

    def test_only_the_words_this_lesson_links_are_reported(self):
        # The noun is the lesson's own word; the verb was missed just as badly but no
        # lesson link attaches it to this lesson, so this lesson cannot ask for it.
        self.make_progress(self.noun, wrong=1, correct=0)
        self.make_progress(self.verb, wrong=3, correct=0)
        rows = lesson_mistakes(self.user, self.lesson)
        self.assertEqual([row.word for row in rows], [self.noun])

    def test_a_word_the_learner_never_missed_is_not_reported(self):
        self.make_progress(self.noun, wrong=0, correct=4)
        self.assertEqual(lesson_mistakes(self.user, self.lesson), [])

    def test_the_worst_word_of_the_lesson_comes_first(self):
        LessonWord.objects.create(lesson=self.lesson, word=self.verb, role="REVIEW", order=2)
        self.make_progress(self.noun, wrong=1, correct=4)
        self.make_progress(self.verb, wrong=3, correct=0)
        rows = lesson_mistakes(self.user, self.lesson)
        self.assertEqual([row.word for row in rows], [self.verb, self.noun])

    def test_a_word_another_learner_missed_is_not_reported(self):
        other = User.objects.create_user(username="fremd", password="test-pass-12345")
        WordProgress.objects.create(
            user=other, word=self.noun, attempt_count=1, wrong_count=1, correct_count=0
        )
        self.assertEqual(lesson_mistakes(self.user, self.lesson), [])


class TextDirectionTests(SimpleTestCase):
    """``vocabulary.text_direction``: explicit, isolated direction for mixed text.

    The direction comes out of the text itself, never out of a browser heuristic
    (``dir="auto"``). The samples are the shapes the real lesson material uses, plus the
    cases the reporter named: a German sentence inside Persian, a German sentence with
    digits in it, German and Persian sharing one line, and a translation in brackets.
    """

    def test_pure_persian_is_one_rtl_run(self):
        html = rendered("سلام، امروز درس می‌خوانیم.")
        self.assertEqual(
            html,
            '<bdi class="text-line" dir="rtl">'
            '<bdi class="run run--fa" lang="fa" dir="rtl">سلام، امروز درس می‌خوانیم.</bdi>'
            '</bdi>',
        )

    def test_pure_german_is_one_ltr_run(self):
        html = rendered("Ich bin Sina.")
        self.assertEqual(
            html,
            '<bdi class="text-line" dir="ltr">'
            '<bdi class="run run--de" lang="de" dir="ltr">Ich bin Sina.</bdi>'
            '</bdi>',
        )

    def test_a_line_is_laid_out_in_the_language_it_starts_in(self):
        # `Ich bin Sina. یعنی من سینا هستم.` is written German first, so it is laid out
        # left to right: German on the left, its translation on the right.
        html = rendered("Ich bin Sina. یعنی من سینا هستم.")
        self.assertTrue(html.startswith('<bdi class="text-line" dir="ltr">'))
        self.assertLess(
            html.index('class="run run--de"'), html.index('class="run run--fa"')
        )

    def test_a_line_that_starts_in_persian_is_laid_out_right_to_left(self):
        html = rendered("جمله زیر را بخوانید: Ich bin Sina.")
        self.assertTrue(html.startswith('<bdi class="text-line" dir="rtl">'))
        self.assertLess(
            html.index('class="run run--fa"'), html.index('class="run run--de"')
        )

    def test_a_translation_keeps_its_own_brackets(self):
        # The reporter's case: `(` used to end the German run and `)` the Persian one, so
        # the pair sat at opposite ends of the line and the German sentence read as the
        # aside instead of the translation. The bracket belongs to the translation.
        html = rendered("Ich bin Ali.  (من علی هستم.)")
        self.assertIn(
            '<bdi class="run run--de" lang="de" dir="ltr">Ich bin Ali.  </bdi>'
            '<bdi class="run run--fa" lang="fa" dir="rtl">(من علی هستم.)</bdi>',
            html,
        )

    def test_a_german_sentence_inside_persian_is_its_own_ltr_run(self):
        html = rendered("جمله زیر را بخوانید: Ich bin Sina.")
        # The space after the colon is neutral, so it is not swallowed by either run.
        self.assertIn(
            '<bdi class="run run--fa" lang="fa" dir="rtl">جمله زیر را بخوانید:</bdi>', html
        )
        self.assertIn('<bdi class="run run--de" lang="de" dir="ltr">Ich bin Sina.</bdi>', html)

    def test_a_german_sentence_before_persian_keeps_its_word_order(self):
        html = rendered("Ich bin Sina. یعنی من سینا هستم.")
        # The space between the two runs is neutral, not part of either one, so the line's
        # own direction places it. It is written here between the two tags.
        self.assertIn('<bdi class="run run--de" lang="de" dir="ltr">Ich bin Sina.</bdi>', html)
        self.assertIn(
            '<bdi class="run run--fa" lang="fa" dir="rtl">یعنی من سینا هستم.</bdi>', html
        )

    def test_digits_inside_a_german_sentence_do_not_split_the_run(self):
        # Digits are neutral in both scripts, so they never cut the sentence around them.
        for line in ("Ich (1) bin (2) Sina.", "Ich (۱) bin (۲) Sina."):
            html = rendered(line)
            self.assertIn(
                f'<bdi class="run run--de" lang="de" dir="ltr">{line}</bdi>', html
            )
            self.assertEqual(html.count("run--"), 1)

    def test_a_german_word_inside_a_persian_question_is_isolated(self):
        html = rendered("واژهٔ «hallo» به چه معنی است؟")
        # The opening guillemet belongs to the German word it quotes, so it travels with
        # it instead of being stranded at the end of the Persian run.
        self.assertIn('<bdi class="run run--de" lang="de" dir="ltr">«hallo»</bdi>', html)
        self.assertTrue(
            html.endswith(
                '<bdi class="run run--fa" lang="fa" dir="rtl">به چه معنی است؟</bdi></bdi>'
            )
        )

    def test_the_space_after_a_quoted_german_word_stays_between_the_runs(self):
        # Regression: the space used to end up inside the LTR run, whose trailing space
        # sits on its right -- beside «واژهٔ» -- so the line read «hallo»به with the gap on
        # the wrong side of the word. The space is neutral now and the line places it.
        html = rendered("واژهٔ «hallo» به چه معنی است؟")
        self.assertIn(
            '<bdi class="run run--de" lang="de" dir="ltr">«hallo»</bdi>'
            ' '
            '<bdi class="run run--fa" lang="fa" dir="rtl">به چه معنی است؟</bdi>',
            html,
        )
        self.assertNotIn('«hallo» </bdi>', html)

    def test_html_in_the_text_is_escaped(self):
        html = rendered("Ich <b>bin</b> Sina.")
        self.assertNotIn("<b>", html)
        self.assertIn("&lt;b&gt;", html)

    def test_a_paragraph_break_never_falls_inside_a_run(self):
        html = rendered("Hallo\n\nIch bin Sina.")
        self.assertIn("</bdi>\n\n<bdi", html)

    def test_every_line_is_covered_with_nothing_lost(self):
        lines = (
            "واژهٔ «hallo» به چه معنی است؟",
            "Ich bin Ali.  (من علی هستم.)",
            "Ich (۱) bin (۲) Sina. · Ich (۱) heiße (۲) Sara.",
            "• machen: انجام دادن یک کار مشخص: Was machst du? (چه کار می‌کنی؟)",
            "• «Was sind Sie von Beruf?» یعنی: شغل شما چیست؟",
        )
        for line in lines:
            joined = "".join(run["text"] for run in line_runs(line))
            self.assertEqual(joined, line)

    def test_it_composes_with_linebreaks_without_escaping_the_runs(self):
        from django.template import Context, Template

        output = Template("{{ value|direction|linebreaks }}").render(
            Context({"value": "Ich bin Sina.\n\nسلام"})
        )
        self.assertIn("<p>", output)
        self.assertEqual(output.count('class="text-line"'), 2)
        self.assertEqual(output.count("run--"), 2)
        self.assertNotIn("&lt;bdi", output)


class SpokenTextTests(SimpleTestCase):
    """``vocabulary.german_text``: what the German audio actually reads out.

    Pure string work, so no database is needed. The samples are the real shapes the
    lesson and grammar data uses (see ``lessons/data`` and ``vocabulary/data``).
    """

    def test_keeps_the_german_and_drops_the_translation_beside_it(self):
        text = spoken_text("Beispiele", "Ich bin Ali.  (من علی هستم.)")
        self.assertEqual(text, "Beispiele\nIch bin Ali.")

    def test_drops_the_english_note_at_the_end(self):
        body = "Der Mann.  (مرد.)\n\nEnglish: The man, and how to say it."
        text = spoken_text("Artikel", body)
        self.assertIn("Der Mann.", text)
        self.assertNotIn("English", text)
        self.assertNotIn("The man", text)

    def test_narrates_the_title_when_the_body_is_persian_only(self):
        body = "در این درس یاد می‌گیرید به کسی سلام کنید.\nEnglish: You greet people."
        text = spoken_text("Was lernst du in dieser Lektion?", body)
        self.assertEqual(text, "Was lernst du in dieser Lektion?")

    def test_a_list_separator_becomes_a_comma(self):
        text = spoken_text("", "das Konto · der Schalter · die Auskunft")
        self.assertEqual(text, "das Konto, der Schalter, die Auskunft")

    def test_quote_marks_go_but_the_german_inside_them_stays(self):
        text = spoken_text("", "نکته: «ein» برای مذکر")
        self.assertEqual(text, "ein")

    def test_a_persian_only_line_is_dropped_without_taking_its_neighbours(self):
        body = "Ich bin Ali.\nسلام کردن:\nDas ist Frau Schmidt."
        text = spoken_text("", body)
        self.assertEqual(text, "Ich bin Ali.\nDas ist Frau Schmidt.")

    def test_nothing_at_all_returns_an_empty_string(self):
        body = "در این درس یاد می‌گیرید.\nEnglish: You learn a lot."
        self.assertEqual(spoken_text("", body), "")

    def test_nothing_at_all_with_an_empty_body(self):
        self.assertEqual(spoken_text("", ""), "")

    def test_a_german_aside_in_brackets_is_kept(self):
        text = spoken_text("", "Guten Tag (formell) sagt man bis 18 Uhr.")
        self.assertIn("(formell)", text)

    def test_a_stranded_full_stop_is_cleaned_up(self):
        # The real line ends with a Persian note whose full stop survives the removal.
        body = "Ben: B-E-N.  (ب-ن.)   ← در درس ۳ هجی کردن را کامل یاد می‌گیرید."
        text = spoken_text("Dialog", body)
        self.assertIn("Ben: B-E-N.", text)
        self.assertNotIn("..", text)

    def test_the_result_never_contains_persian_characters(self):
        body = "معرفه: der Mann، die Frau، das Kind\nEnglish: The articles."
        text = spoken_text("Artikel: der, die, das", body)
        self.assertIsNone(PERSIAN.search(text))
        self.assertIn("der Mann", text)


class WordListScopeTests(VocabularyFixture):
    """The book opens on the course's own words; the whole bank stays one click away."""

    def test_default_list_is_the_courses_own_words(self):
        response = self.client.get(reverse("vocabulary:word-list"))
        self.assertTrue(response.context["scoped_to_course"])
        self.assertEqual(response.context["words"].paginator.count, 1)  # Buch, the taught word
        self.assertContains(response, "Buch")
        # `Arbeit` is published but no lesson teaches it, so it is not in the opening list.
        self.assertNotContains(response, "Arbeit")

    def test_scope_all_shows_the_whole_published_bank(self):
        response = self.client.get(reverse("vocabulary:word-list"), {"scope": "all"})
        self.assertFalse(response.context["scoped_to_course"])
        self.assertEqual(response.context["words"].paginator.count, 5)
        self.assertContains(response, "Arbeit")


class WordSearchTests(VocabularyFixture):
    """``?q=`` on the word list: the term and both meanings are searched."""

    def test_search_matches_the_german_term(self):
        response = self.client.get(reverse("vocabulary:word-list"), {"q": "Buch"})
        words = [word.word for word in response.context["words"]]
        self.assertEqual(words, ["Buch"])

    def test_search_matches_the_persian_meaning(self):
        response = self.client.get(reverse("vocabulary:word-list"), {"q": "کار"})
        words = [word.word for word in response.context["words"]]
        self.assertEqual(words, ["Arbeit"])

    def test_search_matches_the_english_meaning(self):
        response = self.client.get(reverse("vocabulary:word-list"), {"q": "book"})
        words = [word.word for word in response.context["words"]]
        self.assertEqual(words, ["Buch"])

    def test_search_ignores_case(self):
        response = self.client.get(reverse("vocabulary:word-list"), {"q": "bUcH"})
        words = [word.word for word in response.context["words"]]
        self.assertEqual(words, ["Buch"])

    def test_search_never_returns_an_unpublished_word(self):
        response = self.client.get(reverse("vocabulary:word-list"), {"q": "Zzz"})
        self.assertEqual(list(response.context["words"]), [])

    def test_a_search_with_no_match_says_so(self):
        response = self.client.get(reverse("vocabulary:word-list"), {"q": "xyzzy"})
        self.assertContains(response, "پیدا نشد")
        # A failed search is not an empty catalogue, so it must not borrow its wording.
        self.assertNotContains(response, "هنوز واژه‌ای اینجا نیست.")

    def test_the_search_box_keeps_what_was_typed(self):
        response = self.client.get(reverse("vocabulary:word-list"), {"q": "Buch"})
        self.assertContains(response, 'value="Buch"')

    def test_an_empty_search_is_not_a_search(self):
        # A blank box is not a search, so the page must show exactly what it shows with no
        # query at all — the course's own words, not the whole published bank.
        blank = self.client.get(reverse("vocabulary:word-list"), {"q": "   "})
        unfiltered = self.client.get(reverse("vocabulary:word-list"))
        self.assertEqual(
            blank.context["words"].paginator.count,
            unfiltered.context["words"].paginator.count,
        )

    def test_pagination_keeps_the_search(self):
        for i in range(30):
            self.level.words.create(
                word=f"Suchwort{i}", word_type="OTHER", meaning_fa=f"معنی {i}",
                level=self.level, is_published=True,
            )
        first = self.client.get(reverse("vocabulary:word-list"), {"q": "Suchwort"})
        self.assertEqual(first.context["words"].paginator.count, 30)
        self.assertContains(first, "?q=Suchwort&amp;page=2")

    def test_search_works_inside_a_level(self):
        in_level = self.client.get(
            reverse("vocabulary:word-level-list", args=[self.level.level]), {"q": "Buch"}
        )
        words = [word.word for word in in_level.context["words"]]
        self.assertEqual(words, ["Buch"])

        # Another level's word is out of scope, even when it matches the search.
        other_level = self.client.get(
            reverse("vocabulary:word-level-list", args=[self.level.level]), {"q": "Arbeit"}
        )
        self.assertEqual(list(other_level.context["words"]), [])


class ReportA1WortlisteTests(TestCase):
    """``report_a1_wortliste``: how much of the official list the course teaches.

    The fixture is a miniature official list, one entry per notation the real one uses, so
    every matching rule is pinned without shipping third-party content in a test: the
    article and plural marker, an optional bracket, a slash alternative, a reflexive entry
    and a stem. The numbers are exact — the list has nine main entries, seven of them
    taught — and a draft word and another level's word must stay out of both sides.
    """

    ENTRIES = [
        {"word": "die Adresse, -n", "tier": "main"},
        {"word": "gern(e)", "tier": "main"},
        {"word": "Grad (Celsius)", "tier": "main"},
        {"word": "(sich) anmelden", "tier": "main"},
        {"word": "(sich) freuen", "tier": "main"},
        {"word": "circa/ca.", "tier": "main"},
        {"word": "all-", "tier": "main"},
        {"word": "der Entwurf", "tier": "main"},
        {"word": "das Büro", "tier": "main"},
        {"word": "die Abfahrt", "tier": "sub"},
    ]

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.other_level = LanguageLevel.objects.create(level="A2", title="A2", order=2)

        cls.word("Adresse", cls.level)
        cls.word("gern", cls.level)
        cls.word("Grad", cls.level)
        cls.word("anmelden", cls.level)
        cls.word("sich freuen", cls.level)
        cls.word("ca", cls.level)
        cls.word("alle", cls.level)
        cls.word("Auto", cls.level)
        # A draft: never counted on either side of the comparison.
        cls.word("Entwurf", cls.level, is_published=False)
        # Another level: the report is asked about one level at a time.
        cls.word("Büro", cls.other_level)

    @classmethod
    def word(cls, text, level, is_published=True):
        return Word.objects.create(
            word=text, word_type=Word.WordType.OTHER, meaning_fa="…",
            level=level, is_published=is_published,
        )

    def run_report(self, *args, entries=None, path=None):
        """Run the command against a temporary list file and return its output."""
        if path is None:
            if entries is None:
                entries = self.ENTRIES
            directory = tempfile.mkdtemp()
            path = Path(directory) / "a1.json"
            payload = {"level": "A1", "source": "test list", "entries": entries}
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        out = StringIO()
        err = StringIO()
        call_command("report_a1_wortliste", "--list", str(path), *args, stdout=out, stderr=err)
        return out.getvalue()

    # --------------------------------------------------------------------- numbers

    def test_it_reports_the_covered_share_the_missing_words_and_the_extras(self):
        output = self.run_report()

        self.assertIn("Covered: 7 of 9 main entries (77.8%)", output)
        self.assertIn("Missing: 2", output)
        # Auto and alle are taught and are not on this miniature list.
        self.assertIn("Taught beyond the list: 2 (informational)", output)

    def test_sub_entries_are_counted_but_not_compared(self):
        """The official list marks derivable entries by indenting them; they are not the 650."""
        output = self.run_report()

        self.assertIn("+1 derivable sub-entries", output)
        self.assertNotIn("die Abfahrt", output)

    # ---------------------------------------------------------------- the notation

    def test_a_leading_article_and_plural_marker_are_folded_away(self):
        output = self.run_report()

        self.assertNotIn("die Adresse, -n", output)

    def test_an_optional_bracket_is_tried_both_ways(self):
        output = self.run_report()

        self.assertNotIn("gern(e)", output)
        self.assertNotIn("Grad (Celsius)", output)

    def test_a_reflexive_entry_matches_with_and_without_sich(self):
        output = self.run_report()

        self.assertNotIn("(sich) anmelden", output)
        self.assertNotIn("(sich) freuen", output)

    def test_a_slash_means_either_form(self):
        output = self.run_report()

        self.assertNotIn("circa/ca.", output)

    def test_a_stem_matches_by_prefix_and_is_reported_separately(self):
        """``all-`` stands for the whole paradigm, so it is the one inexact match there is."""
        output = self.run_report()

        self.assertIn("Matched as a stem (1): all- → alle", output)

        missing_section = output.split("Missing official entries:")[1]
        self.assertNotIn("all-", missing_section)

    # --------------------------------------------------------------- what is excluded

    def test_a_draft_word_never_counts_as_covered(self):
        output = self.run_report()

        self.assertIn("der Entwurf", output)

    def test_another_levels_word_never_counts_as_covered(self):
        output = self.run_report()

        self.assertIn("das Büro", output)

    # --------------------------------------------------------------------- the output

    def test_show_limits_the_missing_list_and_all_prints_every_word(self):
        entries = []
        for index in range(5):
            entries.append({"word": f"fehlt{index}", "tier": "main"})

        limited = self.run_report("--show", "2", entries=entries)
        self.assertIn("… and 3 more (use --all)", limited)

        full = self.run_report("--all", entries=entries)
        for index in range(5):
            self.assertIn(f"fehlt{index}", full)

    def test_a_missing_list_file_is_refused_rather_than_reported_as_zero(self):
        with self.assertRaises(CommandError) as caught:
            self.run_report(path=Path("does/not/exist.json"))

        self.assertIn("--list", str(caught.exception))

    def test_a_list_without_entries_is_refused(self):
        with self.assertRaises(CommandError):
            self.run_report(entries=[])

    def test_it_writes_nothing(self):
        """The report reads a file and the database; no row and no file is created by it."""
        before = Word.objects.count()

        output = self.run_report()

        self.assertIn("Covered:", output)
        self.assertEqual(Word.objects.count(), before)


class SchedulerTests(SimpleTestCase):
    """``vocabulary/schedule.py``: states, adaptive intervals, ease and response time.

    The scheduler is a pure function, so every rule can be checked here with no database
    and no wall clock: the caller passes ``now`` in and reads the result out.
    """

    def setUp(self):
        self.now = timezone.now()

    def schedule(self, state, interval, ease, is_correct, speed=None):
        # The scheduler reads a number of seconds; the tests name the bucket for clarity.
        if speed == "fast":
            response_time = 1.0
        elif speed == "normal":
            response_time = 6.0
        elif speed == "slow":
            response_time = 20.0
        else:
            response_time = None
        return next_review(state, interval, ease, is_correct, response_time, self.now)

    def test_a_new_word_answered_right_comes_back_tomorrow(self):
        result = self.schedule("NEW", 0, DEFAULT_EASE, True)
        self.assertEqual(result["interval_days"], 1)
        self.assertEqual(result["state"], "LEARNING")
        self.assertEqual(result["due_at"], self.now + timedelta(days=1))

    def test_a_new_word_answered_wrong_also_comes_back_tomorrow(self):
        result = self.schedule("NEW", 0, DEFAULT_EASE, False)
        self.assertEqual(result["interval_days"], 1)
        self.assertEqual(result["state"], "LEARNING")

    def test_the_interval_grows_by_the_ease(self):
        result = self.schedule("LEARNING", 10, DEFAULT_EASE, True)
        self.assertEqual(result["interval_days"], 25)  # 10 × 2.5

    def test_a_correct_answer_always_moves_the_word_forward(self):
        for interval in (1, 2, 5, 30, 100):
            result = self.schedule("LEARNING", interval, DEFAULT_EASE, True, "slow")
            self.assertGreater(result["interval_days"], interval)

    def test_the_interval_never_passes_the_cap(self):
        result = self.schedule("REVIEW", 180, MAX_EASE, True, "fast")
        self.assertEqual(result["interval_days"], MAX_INTERVAL_DAYS)

    def test_a_word_graduates_to_review_once_its_interval_is_long_enough(self):
        result = self.schedule("LEARNING", 10, DEFAULT_EASE, True)
        self.assertEqual(result["interval_days"], 25)
        self.assertEqual(result["state"], "REVIEW")

    def test_a_wrong_review_word_becomes_relearning(self):
        result = self.schedule("REVIEW", 40, DEFAULT_EASE, False)
        self.assertEqual(result["interval_days"], 1)
        self.assertEqual(result["state"], "RELEARNING")

    def test_a_wrong_learning_word_stays_learning(self):
        self.assertEqual(self.schedule("LEARNING", 3, DEFAULT_EASE, False)["state"], "LEARNING")

    def test_a_relearning_word_that_passes_again_returns_to_review(self):
        result = self.schedule("RELEARNING", 10, DEFAULT_EASE, True)
        self.assertEqual(result["state"], "REVIEW")

    def test_a_fast_correct_answer_grows_the_interval_more_than_a_slow_one(self):
        fast = self.schedule("REVIEW", 20, DEFAULT_EASE, True, "fast")
        normal = self.schedule("REVIEW", 20, DEFAULT_EASE, True, None)
        slow = self.schedule("REVIEW", 20, DEFAULT_EASE, True, "slow")
        self.assertGreater(fast["interval_days"], normal["interval_days"])
        self.assertLess(slow["interval_days"], normal["interval_days"])

    def test_a_correct_answer_is_correct_whatever_the_response_time(self):
        for speed in ("fast", "slow", None):
            result = self.schedule("REVIEW", 20, DEFAULT_EASE, True, speed)
            self.assertGreater(result["interval_days"], 0)
            self.assertEqual(result["due_at"], self.now + timedelta(days=result["interval_days"]))

    def test_a_wrong_answer_is_always_due_tomorrow_whatever_the_time(self):
        for speed in ("fast", "slow", None):
            result = self.schedule("REVIEW", 40, DEFAULT_EASE, False, speed)
            self.assertEqual(result["interval_days"], 1)

    def test_speed_bucket_reads_the_boundaries(self):
        self.assertIsNone(speed_bucket(None))
        self.assertEqual(speed_bucket(0.5), "fast")
        self.assertEqual(speed_bucket(FAST_SECONDS), "fast")
        self.assertEqual(speed_bucket(FAST_SECONDS + 0.1), "normal")
        self.assertEqual(speed_bucket(SLOW_SECONDS - 0.1), "normal")
        self.assertEqual(speed_bucket(SLOW_SECONDS), "slow")
        self.assertEqual(speed_bucket(60.0), "slow")

    def test_ease_rises_on_a_fast_correct_answer_and_falls_on_a_wrong_one(self):
        self.assertGreater(ease_after_correct(DEFAULT_EASE, "fast"), DEFAULT_EASE)
        self.assertLess(ease_after_wrong(DEFAULT_EASE, "normal"), DEFAULT_EASE)

    def test_ease_stays_inside_its_bounds(self):
        self.assertEqual(ease_after_correct(MAX_EASE, "fast"), MAX_EASE)
        self.assertEqual(ease_after_wrong(MIN_EASE, "fast"), MIN_EASE)

    def test_a_confident_fast_mistake_lowers_ease_more_than_a_slow_one(self):
        self.assertLess(
            ease_after_wrong(DEFAULT_EASE, "fast"), ease_after_wrong(DEFAULT_EASE, "slow")
        )

    def test_one_slow_answer_does_not_collapse_the_interval(self):
        """A careful answer adjusts the next interval a little, not a lot."""
        normal = self.schedule("REVIEW", 30, DEFAULT_EASE, True, None)
        slow = self.schedule("REVIEW", 30, DEFAULT_EASE, True, "slow")
        self.assertGreaterEqual(slow["interval_days"], normal["interval_days"] - 6)

    def test_repeated_success_grows_the_interval(self):
        interval = 1
        state = "LEARNING"
        ease = DEFAULT_EASE
        for _ in range(6):
            result = self.schedule(state, interval, ease, True, "normal")
            self.assertGreater(result["interval_days"], interval)
            interval = result["interval_days"]
            state = result["state"]
            ease = result["ease"]
        self.assertGreater(interval, 10)

    def test_repeated_failures_keep_the_word_at_one_day(self):
        for _ in range(5):
            result = self.schedule("RELEARNING", 1, DEFAULT_EASE, False)
            self.assertEqual(result["interval_days"], 1)

    def test_a_successful_review_is_never_due_later_than_after_a_failure(self):
        success = self.schedule("REVIEW", 30, DEFAULT_EASE, True)
        failure = self.schedule("REVIEW", 30, DEFAULT_EASE, False)
        self.assertGreater(success["interval_days"], failure["interval_days"])

    def test_the_interval_never_becomes_zero_or_negative(self):
        for interval in (0, 1, 5, 180):
            for correct in (True, False):
                result = self.schedule("LEARNING", interval, DEFAULT_EASE, correct)
                self.assertGreaterEqual(result["interval_days"], 1)


class DueWordsTests(VocabularyFixture):
    """``due_words``: which of the learner's words are waiting, and which are not."""

    def setUp(self):
        self.user = User.objects.create_user(username="learner", password="test-pass-12345")
        self.other = User.objects.create_user(username="other", password="test-pass-12345")

    def progress(self, word, due_at, user=None):
        if user is None:
            user = self.user
        return WordProgress.objects.create(
            user=user, word=word, attempt_count=1, correct_count=1, wrong_count=0, due_at=due_at,
        )

    def test_a_word_past_its_due_time_is_waiting(self):
        row = self.progress(self.noun, timezone.now() - timedelta(hours=1))
        self.assertEqual(due_words(self.user), [row])

    def test_a_word_still_inside_its_gap_is_not_waiting(self):
        self.progress(self.noun, timezone.now() + timedelta(days=1))
        self.assertEqual(due_words(self.user), [])

    def test_a_word_with_no_recorded_due_time_is_left_to_the_mistakes_list(self):
        WordProgress.objects.create(
            user=self.user, word=self.noun, attempt_count=2, wrong_count=2, correct_count=0
        )
        self.assertEqual(due_words(self.user), [])

    def test_the_most_overdue_word_comes_first(self):
        later = self.progress(self.verb, timezone.now() - timedelta(hours=1))
        earlier = self.progress(self.plain, timezone.now() - timedelta(days=3))
        self.assertEqual(due_words(self.user), [earlier, later])

    def test_a_draft_word_is_never_due(self):
        self.progress(self.draft, timezone.now() - timedelta(days=1))
        self.assertEqual(due_words(self.user), [])

    def test_another_learners_words_are_never_read(self):
        self.progress(self.noun, timezone.now() - timedelta(days=1), user=self.other)
        self.assertEqual(due_words(self.user), [])


class ReviewQueueTests(VocabularyFixture):
    """``review_queue``: the tiers a session is built from, and the limits on them."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = User.objects.create_user(username="queuelearner", password="test-pass-12345")

    def progress(self, word, due_at, state="LEARNING"):
        return WordProgress.objects.create(
            user=self.user, word=word, attempt_count=1, correct_count=1,
            state=state, due_at=due_at,
        )

    def test_an_overdue_word_comes_before_a_word_due_later_today(self):
        today = timezone.localtime(timezone.now()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        due_today = self.progress(self.verb, today + timedelta(hours=1))
        overdue = self.progress(self.plain, today - timedelta(days=2))

        queue = review_queue(self.user)

        self.assertEqual(queue["due"][0], overdue)
        self.assertEqual(queue["due"][1], due_today)
        self.assertEqual(queue["overdue_count"], 1)

    def test_a_relearning_word_is_its_own_tier(self):
        self.progress(self.noun, timezone.now() - timedelta(hours=1), state="RELEARNING")
        queue = review_queue(self.user)
        self.assertEqual(len(queue["relearning"]), 1)
        self.assertEqual(len(queue["due"]), 1)

    def test_a_future_word_is_not_in_the_queue(self):
        self.progress(self.noun, timezone.now() + timedelta(days=3))
        self.assertEqual(review_queue(self.user)["due"], [])

    def test_the_review_limit_caps_the_queue(self):
        for index in range(5):
            word = Word.objects.create(
                word=f"W{index}", word_type="OTHER", meaning_fa="…",
                level=self.level, is_published=True,
            )
            self.progress(word, timezone.now() - timedelta(days=1))

        self.assertEqual(len(review_queue(self.user, review_limit=2)["due"]), 2)

    def test_new_words_are_eligible_words_never_practised(self):
        # ``noun`` is the only word linked to the learner's reached lesson, and it has no
        # progress row, so it is the one new word.
        self.assertEqual(new_words(self.user), [self.noun])
        self.assertEqual(review_queue(self.user)["new_count"], 1)

    def test_a_practised_word_is_not_new(self):
        self.progress(self.noun, timezone.now() + timedelta(days=3))
        self.assertNotIn(self.noun, new_words(self.user))

    def test_a_visitor_has_no_new_words(self):
        self.assertEqual(new_words(AnonymousUser()), [])

    def second_lesson_word(self):
        lesson = Lesson.objects.create(
            course=self.course, title="Lektion 2", is_published=True, order=2, estimated_time=10
        )
        word = Word.objects.create(
            word="Zukunft", word_type="OTHER", meaning_fa="آینده", level=self.level,
            is_published=True,
        )
        LessonWord.objects.create(lesson=lesson, word=word, role="NEW", order=1)
        return lesson, word

    def test_a_word_in_an_unreached_lesson_is_not_new(self):
        """A future lesson's vocabulary stays out of the queue until the learner reaches it."""
        _, future_word = self.second_lesson_word()
        self.assertNotIn(future_word, new_words(self.user))

    def test_reaching_a_lesson_makes_its_new_words_available(self):
        lesson, future_word = self.second_lesson_word()
        LessonProgress.objects.create(
            user=self.user, lesson=lesson, status=LessonProgress.Status.IN_PROGRESS
        )
        self.assertIn(future_word, new_words(self.user))


class ExerciseVarietyTests(TestCase):
    """``last_used_type`` and ``avoid_type``: keep a word's format from repeating."""

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="A1", order=1)
        cls.course = Course.objects.create(
            language_level=cls.level, title="Kurs", is_published=True
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion", is_published=True, order=1, estimated_time=10
        )
        cls.word = Word.objects.create(
            word="Buch", word_type="NOUN", article="das", gender="N", meaning_fa="کتاب",
            level=cls.level, is_published=True,
        )
        cls.choice = Exercise.objects.create(
            lesson=cls.lesson, title="معنی", type=Exercise.ExerciseType.MULTIPLE_CHOICE,
            order=1, is_published=True,
        )
        cls.writing = Exercise.objects.create(
            lesson=cls.lesson, title="نوشتن", type=Exercise.ExerciseType.TRANSLATION,
            order=2, is_published=True,
        )
        for exercise in (cls.choice, cls.writing):
            question = Question.objects.create(exercise=exercise, prompt="؟", order=1)
            Answer.objects.create(question=question, text="Buch", is_correct=True, order=1)
            QuestionTarget.objects.create(question=question, word=cls.word, role="TESTED_ITEM")

        cls.user = User.objects.create_user(username="variety", password="test-pass-12345")

    def test_the_last_used_type_is_the_newest_attempt(self):
        self.assertIsNone(last_used_type(self.user))
        ExerciseAttempt.objects.create(
            user=self.user, exercise=self.choice, question=self.choice.questions.first(),
            is_correct=True, response_text="",
        )
        self.assertEqual(last_used_type(self.user), Exercise.ExerciseType.MULTIPLE_CHOICE)

    def test_the_avoided_type_is_pushed_to_the_end(self):
        words = [self.word]
        # By default the lesson order wins.
        self.assertEqual(exercises_for_words(words)[0]["exercise"], self.choice)

        preferred = exercises_for_words(
            words, avoid_type=Exercise.ExerciseType.MULTIPLE_CHOICE
        )[0]["exercise"]
        self.assertEqual(preferred, self.writing)


class LessonTextFilterTests(SimpleTestCase):
    """The two filters that decide what the Persian pages show of the authored text.

    Every prose block, every grammar explanation and every lesson description ends with an
    ``English: …`` gloss that documents the German for a future English interface. The
    Persian page has no use for it, so it is cut at render time; the stored text is never
    touched. ``Englisch`` (the German word for English) belongs to the material and is not
    a gloss.
    """

    def test_the_english_gloss_is_cut_from_a_paragraph_body(self):
        body = "توضیح این درس.\n\nEnglish: what this lesson teaches."
        self.assertEqual(without_english(body), "توضیح این درس.")

    def test_the_gloss_is_cut_when_it_shares_the_line_with_the_persian_text(self):
        text = "سلام و خداحافظی، معرفی خود. English: greetings and introductions."
        self.assertEqual(without_english(text), "سلام و خداحافظی، معرفی خود.")

    def test_text_without_a_gloss_is_returned_unchanged(self):
        self.assertEqual(without_english("فقط متن فارسی.\nخط دوم."), "فقط متن فارسی.\nخط دوم.")

    def test_the_german_word_for_english_is_not_a_gloss(self):
        text = "زبان‌ها: Deutsch · Englisch · Persisch"
        self.assertEqual(without_english(text), text)

    def test_nothing_is_invented_for_an_empty_value(self):
        self.assertEqual(without_english(None), "")
        self.assertEqual(list_lines(None), "")

    def test_a_separated_list_becomes_one_item_per_line(self):
        line = "danke (متشکرم) · bitte (لطفاً) · Entschuldigung (ببخشید)"
        self.assertEqual(
            list_lines(line),
            "danke (متشکرم)\nbitte (لطفاً)\nEntschuldigung (ببخشید)",
        )

    def test_lines_that_are_already_one_per_line_are_left_alone(self):
        body = "سلام کردن بر اساس ساعت روز:\nguten Morgen (صبح بخیر)\n\nخداحافظی:\ntschüss (خداحافظ)"
        self.assertEqual(list_lines(body), body)

    def test_both_filters_are_available_in_every_template(self):
        """Registered as builtins, so no template needs a {% load %}."""
        output = Template("{{ body|without_english|list_lines }}").render(
            Context({"body": "یک · دو\nEnglish: one, two"})
        )
        self.assertEqual(output, "یک\nدو")


class WordStatusTests(TestCase):
    """Which label a vocabulary row shows, and the order the states are checked in.

    ``vocabulary/status.py`` owns the rule, so it is tested on its own: a row shows at most
    one label, and the most useful true one wins.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="Beginner", order=1)
        cls.course = Course.objects.create(language_level=cls.level, title="Kurs", is_published=True)
        cls.lesson = Lesson.objects.create(
            course=cls.course, title="Lektion 1", is_published=True, order=1, estimated_time=10
        )
        cls.user = User.objects.create_user(username="lerner", password="pw")

        cls.intro_word = Word.objects.create(
            word="hallo", word_type="OTHER", meaning_fa="سلام", level=cls.level, is_published=True
        )
        cls.reviewed_word = Word.objects.create(
            word="danke", word_type="OTHER", meaning_fa="متشکرم", level=cls.level, is_published=True
        )
        cls.exam_word = Word.objects.create(
            word="fahren", word_type="VERB", meaning_fa="رفتن", level=cls.level,
            is_published=True, is_exam_important=True,
        )

        cls.intro_link = LessonWord.objects.create(
            lesson=cls.lesson, word=cls.intro_word, role="NEW", order=1
        )
        cls.review_link = LessonWord.objects.create(
            lesson=cls.lesson, word=cls.reviewed_word, role="REVIEW", order=2
        )
        cls.exam_link = LessonWord.objects.create(
            lesson=cls.lesson, word=cls.exam_word, role="NEW", order=3
        )

    def progress(self, word, **fields):
        row = WordProgress.objects.create(user=self.user, word=word)
        for name, value in fields.items():
            setattr(row, name, value)
        row.save()
        return row

    def test_a_word_this_lesson_introduces_says_new(self):
        self.assertEqual(status_of(self.intro_link, None, timezone.now()), "new")

    def test_a_word_this_lesson_revisits_says_review(self):
        self.assertEqual(status_of(self.review_link, None, timezone.now()), "review")

    def test_a_word_the_exam_tests_says_exam_even_when_it_is_new(self):
        self.assertEqual(status_of(self.exam_link, None, timezone.now()), "exam")

    def test_a_due_word_beats_the_exam_label(self):
        progress = self.progress(self.exam_word, due_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(status_of(self.exam_link, progress, timezone.now()), "due")

    def test_a_word_that_keeps_going_wrong_beats_a_due_date(self):
        progress = self.progress(
            self.exam_word, due_at=timezone.now() - timedelta(hours=1), wrong_count=MISTAKE_LIMIT
        )
        self.assertEqual(status_of(self.exam_link, progress, timezone.now()), "wrong")

    def test_one_mistake_is_not_a_repeated_mistake(self):
        progress = self.progress(self.intro_word, wrong_count=MISTAKE_LIMIT - 1)
        self.assertEqual(status_of(self.intro_link, progress, timezone.now()), "new")

    def test_a_word_checked_before_today_is_not_due_yet(self):
        # The schedule only ever writes a future date (vocabulary/schedule.py), so a row
        # with one is a word that is not due, not one that is overdue.
        progress = self.progress(self.intro_word, due_at=timezone.now() + timedelta(days=3))
        self.assertEqual(status_of(self.intro_link, progress, timezone.now()), "new")

    def test_a_visitor_we_cannot_identify_gets_no_personal_label(self):
        self.progress(self.exam_word, wrong_count=MISTAKE_LIMIT)

        rows = self.rows(AnonymousUser())

        labels = []
        for row in rows:
            labels.append(row["label"])
        self.assertEqual(labels, ["جدید", "مرور", "مهم برای آزمون"])

    def test_a_signed_in_learner_sees_their_own_state(self):
        self.progress(self.exam_word, wrong_count=MISTAKE_LIMIT)

        rows = self.rows(self.user)

        by_status = {}
        for row in rows:
            by_status[row["status"]] = row["label"]
        self.assertEqual(by_status["wrong"], "اشتباه پرتکرار")

    def test_every_row_carries_the_label_its_status_names(self):
        for row in self.rows(self.user):
            self.assertEqual(row["label"], STATUS_LABELS[row["status"]])

    def rows(self, user):
        links = self.lesson.lesson_words.order_by("order")
        page = Paginator(links, 24).get_page(1)
        return word_rows(page, user, timezone.now())


class AudioSettingsTests(SimpleTestCase):
    """The voice and the speaking rate live in one module: ``vocabulary/audio.py``.

    Every generator reads them from there, so the whole course is one speaker at one
    speed and a change of pace is a one-line edit rather than four.
    """

    def test_the_speaking_rate_is_a_small_slow_down(self):
        # edge-tts takes a percentage, and "slightly slower" is the whole point: the
        # default pace is too fast to catch a new word in, while a big slow-down makes
        # the speaker sound artificial.
        self.assertTrue(audio.RATE.startswith("-"))
        self.assertTrue(audio.RATE.endswith("%"))
        percent = int(audio.RATE.strip("-").rstrip("%"))
        self.assertGreaterEqual(percent, 5)
        self.assertLessEqual(percent, 25)

    def test_the_voice_is_a_german_one(self):
        self.assertTrue(audio.VOICE.startswith("de-DE-"))

    def test_the_word_importer_defaults_to_the_shared_voice(self):
        self.assertEqual(word_import.DEFAULT_VOICE, audio.VOICE)

    def test_the_generators_name_no_voice_or_rate_of_their_own(self):
        """The bug being guarded against: a second copy of the settings per command."""
        for module in (grammar_audio, sentence_audio, content_audio):
            source = Path(module.__file__).read_text()
            self.assertNotIn("de-DE-KatjaNeural", source)
            self.assertIn("audio.RATE", source)
            self.assertIn("audio.VOICE", source)


class FakeTts:
    """Stands in for ``edge_tts.Communicate`` and remembers what it was asked to say."""

    calls = []

    def __init__(self, text, voice=None, rate=None):
        self.text = text
        FakeTts.calls.append({"text": text, "voice": voice, "rate": rate})

    async def save(self, path):
        Path(path).write_bytes(b"not really an mp3")

    @classmethod
    def reset(cls):
        cls.calls = []


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class AudioGeneratorTests(TestCase):
    """What each generator asks the synthesiser to say, and at which voice and rate.

    ``edge_tts`` and the ffmpeg validity check are replaced with fakes, so this covers the
    part the field confusion lived in: a content block's text is in ``body`` and a
    grammar's in ``explanation``, and neither model has a ``text`` field at all.
    """

    @classmethod
    def setUpTestData(cls):
        cls.level = LanguageLevel.objects.create(level="A1", title="Beginner", order=1)
        cls.course = Course.objects.create(language_level=cls.level, title="A1", is_published=True)
        cls.lesson = Lesson.objects.create(course=cls.course, title="Hallo", order=1,
                                           estimated_time=10, is_published=True)

    def setUp(self):
        FakeTts.reset()

    def narrate(self, name, module):
        with mock.patch(module + ".edge_tts.Communicate", FakeTts):
            with mock.patch(module + ".subprocess.run"):
                call_command(name)
        self.assertTrue(FakeTts.calls, f"{name} narrated nothing")
        return FakeTts.calls[0]

    def test_the_content_block_is_narrated_from_its_body(self):
        LessonContent.objects.create(
            lesson=self.lesson, title="Beispiele", order=1,
            body="Ich bin Ali. (من على هستم.)\nEnglish: I am Ali.",
        )
        said = self.narrate("generate_lesson_content_audio", content_audio.__name__)
        self.assertIn("Beispiele", said["text"])
        self.assertIn("Ich bin Ali.", said["text"])
        self.assertNotIn("على", said["text"])          # the Persian aside is dropped
        self.assertNotIn("English:", said["text"])     # the English note is dropped

    def test_the_grammar_is_narrated_from_its_explanation(self):
        Grammar.objects.create(
            title="sein", level=self.level, is_published=True,
            explanation="ich bin (من هستم)\nEnglish: I am.",
        )
        said = self.narrate("generate_grammar_audio", grammar_audio.__name__)
        self.assertIn("sein", said["text"])
        self.assertNotIn("هستم", said["text"])
        self.assertNotIn("English:", said["text"])

    def test_the_sentence_is_narrated_as_it_stands(self):
        Sentence.objects.create(text="Wie geht's?", translation_fa="چطوری؟",
                                level=self.level, is_published=True)
        said = self.narrate("generate_sentence_audio", sentence_audio.__name__)
        self.assertEqual(said["text"], "Wie geht's?")

    def test_every_generator_speaks_at_the_shared_voice_and_rate(self):
        LessonContent.objects.create(lesson=self.lesson, title="Dialog", order=1, body="Guten Tag.")
        Grammar.objects.create(title="Artikel", level=self.level, is_published=True, explanation="der, die, das")
        Sentence.objects.create(text="Guten Tag.", translation_fa="روز بخیر",
                                level=self.level, is_published=True)
        for name, module in (
            ("generate_lesson_content_audio", content_audio.__name__),
            ("generate_grammar_audio", grammar_audio.__name__),
            ("generate_sentence_audio", sentence_audio.__name__),
        ):
            with self.subTest(command=name):
                said = self.narrate(name, module)
                self.assertEqual(said["voice"], audio.VOICE)
                self.assertEqual(said["rate"], audio.RATE)

    def test_the_word_audio_uses_the_shared_rate(self):
        # The word importer renders inside one async pass, so it is called directly
        # rather than through the command; edge_tts is imported inside it, which is why
        # the patch is on the library rather than on the command module.
        target = Path(tempfile.mkdtemp())
        with mock.patch("edge_tts.Communicate", FakeTts):
            asyncio.run(word_import.Command().render_audio_all(
                {"hallo": "hallo.mp3"}, target, audio.VOICE, 1))
        self.assertEqual(FakeTts.calls[0]["text"], "hallo")
        self.assertEqual(FakeTts.calls[0]["rate"], audio.RATE)

    def test_the_content_and_grammar_models_have_no_text_field(self):
        """The name that caused the confusion: neither model has a ``text`` field."""
        self.assertNotIn("text", [field.name for field in LessonContent._meta.fields])
        self.assertNotIn("text", [field.name for field in Grammar._meta.fields])


class AudioControlMarkupTests(SimpleTestCase):
    """The shared control: one compact icon button, and no player until the script says.

    Whether the native player is worth showing is decided in the browser from the clip's
    real length (static/js/audio.js), so what the template must get right is that the
    player starts hidden and that the button belongs to exactly one <audio> element.

    The playback behaviour itself is exercised in a real browser, not here.
    """

    def render(self, **overrides):
        values = {"audio": {"url": "/media/words/audio/hallo.mp3"}, "prefix": "word",
                  "pk": 7, "label": "hallo"}
        values.update(overrides)
        template = Template('{% include "includes/audio_control.html" %}')
        return template.render(Context(values))

    def test_the_button_is_the_compact_icon_control(self):
        html = self.render()
        self.assertIn('class="audio-control"', html)
        self.assertIn('class="audio-toggle" hidden', html)
        self.assertIn('aria-expanded="false"', html)
        self.assertIn('audio-toggle__play', html)
        self.assertIn('audio-toggle__stop', html)

    def test_the_button_points_at_its_own_audio_element(self):
        html = self.render()
        self.assertIn('aria-controls="word-7"', html)
        self.assertIn('id="word-7"', html)

    def test_the_fallback_link_works_without_javascript(self):
        html = self.render()
        self.assertIn("<noscript>", html)
        self.assertIn('href="/media/words/audio/hallo.mp3"', html)

    def test_the_accessible_label_is_persian_and_names_the_clip(self):
        html = self.render()
        self.assertIn('aria-label="پخش hallo"', html)
        # The bare name travels separately, so the script can build "پخش …" / "توقف …"
        # without having to take its own label apart -- and without doubling the verb.
        self.assertIn('data-label="hallo"', html)

    def test_no_player_is_rendered_by_default(self):
        html = self.render()
        self.assertNotIn("<audio", html)
        self.assertIn('data-audio-src="/media/words/audio/hallo.mp3"', html)

    def test_an_inline_control_asks_for_no_space_above_it(self):
        self.assertIn('class="audio-control audio-control--inline"', self.render(inline=True))
        self.assertNotIn("audio-control--inline", self.render())

    def test_a_missing_audio_file_renders_nothing_at_all(self):
        self.assertEqual(self.render(audio="").strip(), "")
        self.assertEqual(self.render(audio=None).strip(), "")
