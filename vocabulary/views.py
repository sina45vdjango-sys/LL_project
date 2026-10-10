from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from accounts.models import UserProfile
from exercises.models import Exercise, QuestionTarget
from lessons.models import LanguageLevel, LessonWord
from lessons.readiness import grammar_review

from .lookup import lookup_candidates
from .models import Word
from .review import review_plan
from .schedule import review_queue
from .text_direction import PERSIAN_LETTER

#: One page of the word list. The list is a dense row layout, so this is about how far a
#: learner scans before turning the page, not how much fits on screen.
WORDS_PER_PAGE = 24


def _published_words():
    """Every learner-facing word list is published-only, like the rest of the product."""
    return Word.objects.filter(is_published=True).select_related("level")


def _course_words():
    """The words the published lessons actually teach — this course's vocabulary.

    The word book is a reference for the course, so it opens on these rather than on the
    whole published bank: a learner who has been taught about a thousand words should not
    land on `Abbildung` and two thousand B1 entries the lessons never mention. Nothing is
    hidden — a search, a level tab, or ``scope=all`` still reaches every published word —
    and only where the list *starts* changes.
    """
    return (
        Word.objects.filter(
            is_published=True,
            lesson_links__lesson__is_published=True,
            lesson_links__lesson__course__is_published=True,
        )
        .distinct()
        .select_related("level")
    )


def _stamp_review_rows(rows, exercises_by_word, now):
    """Give each review row the two facts a template cannot work out for itself.

    ``row.practice`` is the exercises that test that row's own word — a template cannot
    index a dict with a variable key, so the pairing happens here and the page only reads
    the attribute. ``row.is_due`` is whether the row's due time has passed, which is what
    the «وقت مرور» chip shows. Both the sitting and the longer list of the learner's
    mistakes are stamped here, so one word cannot appear two different ways on one page.
    """
    for row in rows:
        if row.word_id in exercises_by_word:
            row.practice = exercises_by_word[row.word_id]
        else:
            row.practice = []
        row.is_due = row.due_at is not None and row.due_at <= now


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
        scope = request.GET.get("scope", "")

        words = _published_words()
        scoped_to_course = False

        # With nothing asked of it, the book opens on the course's own words. A search
        # reaches the whole bank, and so does `scope=all` or a level tab. On a database
        # where no lesson is published yet the scope falls back to everything, so the page
        # is never emptier than the content.
        if not query and scope != "all":
            course_words = _course_words()
            if course_words.exists():
                words = course_words
                scoped_to_course = True

        words = _search_filter(words, query).order_by("word", "pk")
        words = Paginator(words, WORDS_PER_PAGE).get_page(request.GET.get("page"))

        # The search box is typed in both directions — a German term (the main use) or a
        # Persian meaning — so its direction is decided here from the search itself and set
        # explicitly in the template. This project does not hand direction to the browser's
        # `dir="auto"` heuristic. An empty box is LTR, which is what typing German wants.
        search_dir = "ltr"
        if PERSIAN_LETTER.search(query):
            search_dir = "rtl"

        # The learner already said which level they are on when they set a goal, so this
        # page should not open on the whole word bank. When there is no search, that level
        # is moved to the front of the tabs and one short line points at it. Nothing is
        # hidden: every tab and every word stays one click away, and the hint goes away by
        # itself as soon as the learner searches or picks a tab.
        levels = list(_levels_with_counts())
        suggested_level = None

        if not query:
            profile = None

            if request.user.is_authenticated:
                profile = UserProfile.objects.filter(user=request.user).first()

            if profile is not None:
                if profile.target_level is not None:
                    suggested_level = profile.target_level
                else:
                    suggested_level = profile.current_level

        if suggested_level is not None:
            ordered = []

            for level in levels:
                if level.pk == suggested_level.pk:
                    ordered.append(level)

            for level in levels:
                if level.pk != suggested_level.pk:
                    ordered.append(level)

            levels = ordered

        return render(
            request,
            self.template_name,
            _level_context(
                levels,
                words=words,
                query=query,
                search_dir=search_dir,
                page_params=_page_params(request),
                suggested_level=suggested_level,
                scoped_to_course=scoped_to_course,
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

        # Same rule as the all-levels view above: the direction comes from the search, set
        # explicitly, never from the browser's `dir="auto"` heuristic.
        search_dir = "ltr"
        if PERSIAN_LETTER.search(query):
            search_dir = "rtl"

        return render(
            request,
            self.template_name,
            _level_context(
                _levels_with_counts(),
                words=words,
                selected_level=level,
                query=query,
                search_dir=search_dir,
                page_params=_page_params(request),
            ),
        )


class WordReviewView(View):
    """The words a signed-in learner has answered wrong — and where to practise them.

    This is the page that reads ``WordProgress`` back. Those counters were already
    being written by every exercise submission (see ``vocabulary/progress.py``) but
    nothing had ever shown them to the learner, so this is where they finally earn
    their keep.

    The list alone would only be a report. ``vocabulary/review.py`` also finds the
    real exercises that test these words, so the page can offer practice instead of
    sympathy: the plan's exercises at the top, and a link on every row.

    Nothing here is invented. A word is listed because the learner really did miss
    it, and the row repeats the two counters it was listed for. A visitor we cannot
    identify has no history to read, so the page explains that instead of showing an
    empty list that would look like a bug.

    The page answers the same question about **rules** as well: a question can carry a
    ``GRAMMAR`` target, so a wrong answer can be remembered against a rule, and those
    rules were the one mistake the product stored and never showed. ``grammar_review``
    supplies them and the exercises that ask about them, so this page is where a learner
    sees both kinds of mistake in one place.
    """

    template_name = "vocabulary/word_review.html"

    def get(self, request, *args, **kwargs):
        plan = review_plan(request.user, exercise_limit=5)
        # The rules the learner's own answers got wrong, and the exercises that ask about
        # them — the same idea as the words above, one level up. None for a visitor we
        # cannot identify and for a learner who has got every tagged question right
        # (lessons/readiness.py owns the rule).
        grammar = grammar_review(request.user, exercise_limit=5)

        # The scheduler's own answer to "what is waiting", built for **every** signed-in
        # learner rather than only for one who has made mistakes (vocabulary/schedule.py).
        # Its *new* tier — words the learner has reached and never practised — belongs to
        # precisely the learner `review_plan` returns None for, so computing the queue
        # inside the plan branch below would hide the tier from the only person it is for.
        # A visitor has no stored rows to build a queue from.
        queue = None
        sitting = []
        if request.user.is_authenticated:
            queue = review_queue(request.user)
            # Today's review is one sitting, bounded by the scheduler, not every word that
            # is due: a learner with fifty words waiting is handed fifteen and told the
            # rest stays in the queue (vocabulary/schedule.py::SITTING_SIZE).
            sitting = queue["due"]

        words = []
        exercises = []
        wrong_word_count = 0
        exercise_count = 0
        exercises_by_word = {}

        if plan is not None:
            # Paged after the fact rather than in SQL: the plan already holds the
            # learner's own rows in their sort order, and it is their own mistakes —
            # not a catalogue — that this page shows.
            words = Paginator(plan["words"], WORDS_PER_PAGE).get_page(request.GET.get("page"))
            exercises = plan["exercises"]
            wrong_word_count = plan["wrong_word_count"]
            exercise_count = plan["exercise_count"]
            exercises_by_word = plan["exercises_by_word"]

        # Both word lists carry the same two facts, stamped the same way.
        now = timezone.now()
        _stamp_review_rows(sitting, exercises_by_word, now)
        _stamp_review_rows(words, exercises_by_word, now)

        return render(
            request,
            self.template_name,
            {
                "sitting": sitting,
                "words": words,
                "exercises": exercises,
                "wrong_word_count": wrong_word_count,
                "exercise_count": exercise_count,
                "grammar": grammar,
                "queue": queue,
            },
        )


class WordDetailView(View):
    """One word as a focused study screen.

    Nothing is invented: the grammatical block only shows the fields the word actually
    has, and the lesson/exercise context is real rows that reference this word.

    The page is published-only, like every other learner-facing word list, so a draft
    word is not reachable by typing its URL either.
    """

    template_name = "vocabulary/word_detail.html"

    def get(self, request, pk, *args, **kwargs):
        word = get_object_or_404(
            Word.objects.filter(is_published=True).select_related("level"), pk=pk
        )

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
    """AJAX endpoint: look up a word by its German text and return minimal JSON.

    The word can arrive inflected (``heiße``, ``Häuser``), because the lesson reader
    makes every German word clickable and the learner taps whichever form stands in
    the sentence. An exact entry is tried first; when there is none, the dictionary
    forms ``vocabulary/lookup.py`` suggests for the word are tried in turn, so the
    popover answers with the entry the learner was really asking about instead of
    nothing.
    """

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

        # Nothing matched, so the learner probably tapped an inflected form. Try the
        # dictionary forms it could belong to, best guess first, and stop at the first
        # one that is a real entry -- showing every guess would bury the right answer.
        if not words:
            for candidate in lookup_candidates(word_value):
                words = list(
                    Word.objects.select_related("level").filter(
                        Q(word__iexact=candidate) & Q(is_published=True)
                    )[:5]
                )
                if words:
                    break

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
