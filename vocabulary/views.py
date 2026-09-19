from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views import View
from lessons.models import LanguageLevel
from .models import Word


class WordListView(View):
    template_name = "vocabulary/word_list.html"

    def get(self, request, *args, **kwargs):
        words = Word.objects.select_related("level").order_by("word", "pk")
        words = Paginator(words, 24).get_page(request.GET.get("page"))
        return render(request, self.template_name, {
            "words": words, "levels": LanguageLevel.objects.all(),
        })


class WordLevelListView(WordListView):
    template_name = "vocabulary/word_level_list.html"

    def get(self, request, level_code, *args, **kwargs):
        level = get_object_or_404(LanguageLevel, level__iexact=level_code)
        words = Word.objects.select_related("level").filter(level=level).order_by("word", "pk")
        words = Paginator(words, 24).get_page(request.GET.get("page"))
        return render(request, self.template_name, {
            "words": words, "levels": LanguageLevel.objects.all(), "selected_level": level,
        })


class WordDetailView(View):
    def get(self, request, pk, *args, **kwargs):
        # Fetch the language level in the same query as the word.
        word = get_object_or_404(Word.objects.select_related("level"), pk=pk)
        return render(request, "vocabulary/word_detail.html", {"word": word})


class WordLookupView(View):
    """AJAX endpoint: look up a word by its German text and return minimal JSON."""

    def get(self, request, *args, **kwargs):
        from django.http import JsonResponse
        from django.urls import reverse
        from django.db.models import Q

        query = request.GET.get("q", "").strip()
        if not query:
            return JsonResponse({"error": "missing query parameter"}, status=400)

        # Match exact word, optionally stripping an article prefix (e.g. "der Haus").
        parts = query.split()
        word_value = parts[-1]

        words = list(Word.objects.select_related("level").filter(
            Q(word__iexact=word_value) & Q(is_published=True)
        )[:5])

        if not words:
            return JsonResponse({"results": []})

        results = [
            {
                "word": w.word,
                "article": w.article,
                "meaning_fa": w.meaning_fa,
                "word_type": w.get_word_type_display(),
                "plural": w.plural,
                "pronunciation": w.pronunciation,
                "meaning_en": w.meaning_en,
                "audio": w.audio.url if w.audio else "",
                "url": reverse("vocabulary:word-detail", kwargs={"pk": w.pk}),
            }
            for w in words
        ]
        return JsonResponse({"results": results})
