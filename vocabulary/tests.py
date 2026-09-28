import re

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from exercises.models import Answer, Exercise, Question, QuestionTarget
from lessons.models import Course, LanguageLevel, Lesson, LessonWord

from .german_text import PERSIAN, spoken_text
from .models import Word, WordProgress


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

    def test_detail_has_dark_theme_and_styles(self):
        # The UI is dark-only as of the frontend redesign, so the light/dark
        # toggle that used to sit in the navbar is intentionally gone.
        response = self.client.get(reverse("vocabulary:word-detail", args=[self.word.pk]))
        self.assertNotContains(response, 'id="theme-toggle"')
        self.assertContains(response, 'content="dark"')
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
        self.assertContains(response, 'class="audio-control audio-control--icon"')
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
        response = self.client.get(self.url)
        self.assertContains(response, "5 واژه")
        self.assertNotContains(response, "صفحهٔ 1 از 1")  # a single page needs no page state
        for number in range(25):  # 30 words in total → two pages of 24
            Word.objects.create(word=f"Wort{number}", word_type="OTHER", meaning_fa="م",
                                level=self.level, is_published=True)
        first = self.client.get(self.url)
        self.assertContains(first, "صفحهٔ 1 از 2")
        self.assertContains(first, "قبلی")
        self.assertContains(first, "بعدی")
        self.assertContains(first, "?page=2")
        second = self.client.get(self.url, {"page": 2})
        self.assertContains(second, "صفحهٔ 2 از 2")
        self.assertContains(second, "?page=1")

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
        response = self.client.get(reverse("vocabulary:word-review"))
        self.assertContains(response, "هنوز واژه‌ای اشتباه نشده.")

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
        response = self.client.get(reverse("vocabulary:word-list"), {"q": "   "})
        self.assertEqual(response.context["words"].paginator.count, 5)

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

