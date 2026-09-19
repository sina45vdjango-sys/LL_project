from django.test import TestCase
from django.urls import reverse
from lessons.models import LanguageLevel
from .models import Word


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

    def test_detail_has_accessible_theme_control_and_styles(self):
        response = self.client.get(reverse("vocabulary:word-detail", args=[self.word.pk]))
        self.assertContains(response, 'id="theme-toggle"')
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'vocabulary/css/word_detail.css')
        self.assertContains(response, 'id="word-details"')

