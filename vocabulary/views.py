from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View

from exercises.models import Exercise, QuestionTarget
from lessons.models import LanguageLevel, LessonWord

from .models import Word, WordProgress

#: One page of the word list. The list is a dense row layout, so this is about how far a
#: learner scans before turning the page, not how much fits on screen.
WORDS_PER_PAGE = 24


def _published_words():
    """Every learner-facing word list is published-only, like the rest of the product."""
    return Word.objects.filter(is_published=True).select_related("level")


def _levels_with_counts():
    """The level tabs, with the real number of published words behind each one.

    `order_by` is explicit on purpose: adding an aggregate makes Django drop the model's
    Meta ordering from the SQL, which silently shuffled the tabs (A2 before A1).
    """
    return LanguageLevel.objects.annotate(
        word_count=Count("words", filter=Q(words__is_published=True))
    ).order_by("order")


def _level_context(levels, **extra):
    """Level tabs plus the total behind the "all levels" tab."""
    levels = list(levels)
    word_total = 0
    for level in levels:
        word_total += level.word_count

    context = {"levels": levels, "word_total": word_total}
    context.update(extra)
    return context


def _search_filter(words, query):
    """Narrow a word queryset to the learner's search, or hand it back untouched.

    All three text fields are searched, because a learner may remember the German term,
    the Persian meaning or the English one without remembering which. An empty query is
    not a search, so in that case the queryset comes back exactly as it arrived.
    """
    if not query:
        return words

    return words.filter(
        Q(word__icontains=query)
        | Q(meaning_fa__icontains=query)
        | Q(meaning_en__icontains=query)
    )


def _page_params(request):
    """The current query string without ``page``, ready to prefix a pagination link.

    Without this, moving to page 2 of a search would throw the search away. The result is
    an empty string when there is nothing worth carrying, so a plain word list keeps its
    plain links and the shared pagination partial needs no special case.
    """
    params = request.GET.copy()
    params.pop("page", None)
    encoded = params.urlencode()

    if not encoded:
        return ""
    return encoded + "&"


class WordListView(View):
    template_name = "vocabulary/word_list.html"

    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "").strip()
        words = _search_filter(_published_words(), query).order_by("word", "pk")
        words = Paginator(words, WORDS_PER_PAGE).get_page(request.GET.get("page"))
        return render(
            request,
            self.template_name,
            _level_context(
                _levels_with_counts(),
                words=words,
                query=query,
                page_params=_page_params(request),
            ),
        )


class WordLevelListView(WordListView):
    template_name = "vocabulary/word_level_list.html"

    def get(self, request, level_code, *args, **kwargs):
        # Fetched through the annotated queryset so the tab the learner is on already
        # carries its own word count.
        level = get_object_or_404(_levels_with_counts(), level__iexact=level_code)
        query = request.GET.get("q", "").strip()
        words = _search_filter(_published_words(), query).filter(level=level).order_by("word", "pk")
        words = Paginator(words, WORDS_PER_PAGE).get_page(request.GET.get("page"))
        return render(
            request,
            self.template_name,
            _level_context(
                _levels_with_counts(),
                words=words,
                selected_level=level,
                query=query,
                page_params=_page_params(request),
            ),
        )


class WordReviewView(View):
    """The words a signed-in learner has answered wrong, worst first.

    This is the page that reads ``WordProgress`` back. Those counters were already
    being written by every exercise submission (see ``vocabulary/progress.py``) but
    nothing had ever shown them to the learner, so this is where they finally earn
    their keep.

    Nothing here is invented. A word is listed because the learner really did miss
    it, and the row repeats the two counters it was listed for. ``correct_count`` is
    the second sort key on purpose: between two words missed the same number of
    times, the one that has been answered right least often is the harder one.

    Ordering happens in SQL rather than in Python because the list is paginated. A
    visitor we cannot identify has no history to read, so the page explains that
    instead of showing an empty list that would look like a bug.
    """

    template_name = "vocabulary/word_review.html"

    def get(self, request, *args, **kwargs):
        words = []

        if request.user.is_authenticated:
            missed = (
                WordProgress.objects.filter(
                    user=request.user,
                    wrong_count__gt=0,
                    word__is_published=True,
                )
                .select_related("word", "word__level")
                .order_by("-wrong_count", "correct_count", "-last_wrong_at")
            )
            words = Paginator(missed, WORDS_PER_PAGE).get_page(request.GET.get("page"))

        return render(request, self.template_name, {"words": words})


class WordDetailView(View):
    """One word as a focused study screen.

    Nothing is invented: the grammatical block only shows the fields the word actually
    has, and the lesson/exercise context is real rows that reference this word.
    """

    template_name = "vocabulary/word_detail.html"

    def get(self, request, pk, *args, **kwargs):
        word = get_object_or_404(Word.objects.select_related("level"), pk=pk)

        # Where this word is taught (every live word is attached to at least one lesson).
        lesson_links = (
            LessonWord.objects.filter(word=word, lesson__is_published=True)
            .select_related("lesson", "lesson__course__language_level")
            .order_by("lesson__course__language_level__order", "lesson__order")
        )

        # The exercises that actually test this word. Two queries on purpose: filtering
        # Exercise by `questions__targets__word` fans out the rows and would make both the
        # row count and any annotation wrong.
        exercise_ids = (
            QuestionTarget.objects.filter(
                word=word, role=QuestionTarget.Role.TESTED_ITEM
            )
            .values_list("question__exercise_id", flat=True)
            .distinct()
        )
        exercises = (
            Exercise.objects.filter(pk__in=list(exercise_ids), is_published=True)
            .select_related("lesson")
            .annotate(question_count=Count("questions"))
            .order_by("lesson__course__language_level__order", "lesson__order", "order")
        )

        return render(request, self.template_name, {
            "word": word,
            "lesson_links": lesson_links,
            "exercises": exercises,
        })


class WordLookupView(View):
    """AJAX endpoint: look up a word by its German text and return minimal JSON."""

    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "").strip()
        if not query:
            return JsonResponse({"error": "missing query parameter"}, status=400)

        # Match exact word, optionally stripping an article prefix (e.g. "der Haus").
        parts = query.split()
        word_value = parts[-1]

        words = list(
            Word.objects.select_related("level").filter(
                Q(word__iexact=word_value) & Q(is_published=True)
            )[:5]
        )

        if not words:
            return JsonResponse({"results": []})

        results = []
        for word in words:
            results.append(
                {
                    "word": word.word,
                    "article": word.article,
                    "meaning_fa": word.meaning_fa,
                    # Persian label, because the popover is Persian UI (it used to say "Noun").
                    "word_type": word.type_label,
                    "plural": word.plural,
                    "pronunciation": word.pronunciation,
                    "meaning_en": word.meaning_en,
                    "audio": word.audio.url if word.audio else "",
                    "url": reverse("vocabulary:word-detail", kwargs={"pk": word.pk}),
                }
            )

        return JsonResponse({"results": results})
