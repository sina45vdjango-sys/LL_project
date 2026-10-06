"""One mock exam paper: what it asks, and what it is worth.

``exams/spec.py`` says what the official exam is. This module turns that into an actual
paper out of this product's own published questions, and marks it.

Four rules carry the module:

* **A paper is written down.** Selection is varied enough to be a fresh exam each sitting,
  but every question chosen is stored in ``ExamRunQuestion``, so opening a run again shows
  the same paper. Nothing is re-derived from the content later, which is also why the
  section is stored on the row instead of being read back out of the question.
* **A paper comes from the curated set, not from the practice table.** A question is only
  exam content if it carries an ``exam_section`` (see ``exercises/models.py``). Adding a
  drill to a lesson can therefore never silently change the exam, which is what the audit
  found happening, and the index can count a section without classifying all 4 600
  published questions on every request. What gets marked, and why, is
  ``management/commands/export_a1_exam_items.py``; the marks themselves are stored in
  ``exams/data/a1_exam_items.json`` and applied by ``import_a1_exam_items``.
* **A question is only asked if it can be marked.** A question with no authored correct
  answer would be a hole in the score, so a marked question is checked for one here as
  well as when it was selected.
* **Marking is the official arithmetic and nothing else.** A section's right answers are
  its raw points, 15 of them are worth 25 after the ×1.66 factor, the three written
  sections add up to 75, and the pass line is 60 — with the written subtotal's
  ``WRITTEN_MINIMUM`` deciding whether the oral section can still bring a candidate there.

The section→content mapping is honest rather than exact, and the exam page says so: this
product does not author Goethe task types, so each section is marked up from the course's
own questions — see the curation command for the exact rule per section.
"""

import math
import random

from django.utils import timezone

from exercises.models import Exercise, Question, QuestionTarget
from vocabulary.models import Sentence, Word

from .models import ExamRun, ExamRunQuestion
from .sections import Section
from .spec import (
    DURATION_MINUTES,
    INSTRUCTIONS,
    ITEMS_PER_SECTION,
    PASS_POINTS,
    SCORE_FACTOR,
    SECTION_FACTS,
    SECTION_ORDER,
    SPOKEN_MAX_POINTS,
    WRITTEN_MAX_POINTS,
    WRITTEN_MINIMUM,
)


def section_of(question):
    """The one official section this question can stand in for, or ``None``.

    A question belongs to **exactly one** section, and the order of the checks is the
    rule: a recording is the Hören skill, a passage is the Lesen skill, and a typed
    answer is the Schreiben skill. The rule exists because the two pools used to
    overlap: a dictation has both a recording and a single typed answer, so it
    qualified for HÖREN *and* SCHREIBEN, and a paper that drew the same question in
    both broke the ``unique_question_per_exam_run`` constraint. One question, one
    section.

    A ``SCRAMBLE`` question stands in for nothing: it is answered by typing, but the exam
    renders a paper's questions from many exercises at once and has no word bank to show,
    so a scramble without its words is just a translation.
    """
    if question.exercise.type == Exercise.ExerciseType.SCRAMBLE:
        return None

    if not markable(question):
        return None

    if question.audio:
        return Section.HOEREN

    if has_passage(question):
        return Section.LESEN

    if is_typed(question):
        return Section.SCHREIBEN

    return None


def section_pools():
    """Every section's pool: the questions marked for that section, and nothing else.

    The mark is a stored field, so the three pools are disjoint by construction (one
    column holds one value) and a paper can never ask the same question twice. It also
    means this reads only the 45-odd marked rows instead of classifying every published
    question in Python — the audit measured the old version at ~600 ms of CPU for the
    public exam index, paid again for every visit.

    Visibility is still the product's usual rule: a draft exercise, lesson or course
    contributes nothing even if a question was marked. The order is the course's own, so a
    paper reads in teaching order before anything is sampled.

    ``answers__is_correct=True`` is the markable check (``markable``, below) written as a
    join instead of a Python loop, and it is cheap here because it only ever runs over the
    marked rows: a mark on a question with no authored answer cannot put a hole in a score.
    The join can repeat a row when several answers are correct, hence ``distinct()``.
    """
    pools = {}

    for section in SECTION_ORDER:
        pools[section] = list(
            Question.objects.filter(
                exam_section=section,
                exercise__is_published=True,
                exercise__lesson__is_published=True,
                exercise__lesson__course__is_published=True,
                answers__is_correct=True,
            )
            .distinct()
            .select_related("exercise", "exercise__lesson")
            .prefetch_related("answers", "targets")
            .order_by("exercise__lesson__order", "exercise__order", "order", "pk")
        )

    return pools


def markable(question):
    """Whether this question has an authored correct answer at all.

    The exam mode may not ask a question whose answer was never written down: it would be
    a hole in the score that looks like a mistake the learner made. Since the exam set was
    curated this is a second check rather than the selection rule — the curation command
    refuses to mark an unanswerable question, and this keeps a hand-edited mark from
    reaching a paper.
    """
    for answer in question.answers.all():
        if answer.is_correct:
            return True
    return False


def has_passage(question):
    """Whether a real sentence sits behind this question — the reading section's shape.

    Only the target row is read. A ``sentence_id`` that is set means the sentence exists —
    the foreign key guarantees it — so loading the sentence itself would add a join for a
    check that never looks at its text. That matters because ``section_pools`` classifies
    every published question, and fetching each target's sentence was the largest part of
    the index's cost.
    """
    for target in question.targets.all():
        if target.sentence_id is not None:
            return True
    return False


def is_typed(question):
    """Whether this question is answered by typing: no wrong option is written for it.

    This is the same rule ``exercises/runner.py`` uses to decide a question renders an
    input instead of options, restated here because the exam picks its paper before any
    page is rendered. It is "there is nothing wrong to choose", not "there is one row":
    a typed question may carry several accepted spellings of the same answer (``Oma`` and
    ``Großmutter`` for ``مادربزرگ``), and all of them are correct rows.
    """
    total = 0

    for answer in question.answers.all():
        if not answer.is_correct:
            return False
        total += 1

    return total > 0


def paper_problems():
    """The sections the curated set cannot supply a full paper for, if any.

    A section with fewer than 15 marked questions would be a shorter paper than the exam,
    and its score would be out of fewer raw points than the official 15 — so the exam
    refuses to start rather than quietly asking a smaller exam. On the live content all
    three sections are above the line; this exists so an unseeded or thinned exam set says
    so instead of producing a paper that cannot be scored like the real thing.

    It counts the same pools the paper is built from, which is what makes it cheap enough
    for the public index: those query only the marked rows.
    """
    pools = section_pools()
    problems = []

    for section in SECTION_ORDER:
        available = len(pools[section])
        if available < ITEMS_PER_SECTION:
            problems.append({
                "section": section,
                "facts": SECTION_FACTS[section],
                "available": available,
            })

    return problems


def build_paper(run):
    """Write one run's paper: 15 questions per section, chosen once and stored.

    The random seed is the run's own id, so a paper is reproducible from the run row alone
    and two sittings of the same learner are two different papers. ``random.Random`` with
    an explicit seed is used rather than the module-level functions so building a paper
    can never depend on, or disturb, any other randomness in the process.
    """
    chooser = random.Random(run.pk)
    pools = section_pools()

    order = 0
    rows = []

    for section in SECTION_ORDER:
        pool = pools[section]

        # `paper_problems()` is what stops a run from starting on thin content; taking the
        # smaller of the two here means this can never be the place a run breaks.
        wanted = ITEMS_PER_SECTION
        if len(pool) < wanted:
            wanted = len(pool)

        chosen = chooser.sample(pool, wanted)

        for question in chosen:
            order += 1
            rows.append(
                ExamRunQuestion(
                    run=run,
                    question=question,
                    section=section,
                    order=order,
                )
            )

    ExamRunQuestion.objects.bulk_create(rows)
    return rows


def section_results(run):
    """One row per section: how many questions it asked and how many were right.

    Unanswered questions count as nothing rather than as wrong, and the two numbers say
    which happened: ``answered`` is how many of the section the learner actually reached.
    """
    rows = list(run.questions.order_by("order"))

    results = []
    raw_total = 0
    answered_total = 0

    for section in SECTION_ORDER:
        asked = 0
        answered = 0
        correct = 0

        for row in rows:
            if row.section != section:
                continue

            asked += 1
            if row.is_correct is None:
                continue

            answered += 1
            if row.is_correct:
                correct += 1

        raw_total += correct
        answered_total += answered

        results.append({
            "section": section,
            "facts": SECTION_FACTS[section],
            "asked": asked,
            "answered": answered,
            "correct": correct,
            "points": round(correct * SCORE_FACTOR),
        })

    return results, raw_total, answered_total


def score(run):
    """What the sitting was worth, in the official numbers.

    The sections are multiplied by the official factor and then added up, and the total is
    rounded once — exactly the rule the exam states — which is why a perfect written paper
    is 75 and not 3 × 25 rounded somewhere along the way.

    ``needed_from_spoken`` is the honest answer to "did I pass?": the written part is 75 of
    the 100 points, so the learner's own score decides how much the (ungraded, here)
    spoken section would have to supply. ``spoken_can_reach`` says whether it still can —
    which is the exam's own rule about a written subtotal below ``WRITTEN_MINIMUM``.
    """
    sections, raw_total, answered_total = section_results(run)

    points = round(raw_total * SCORE_FACTOR)

    needed = PASS_POINTS - points
    if needed < 0:
        needed = 0

    return {
        "sections": sections,
        "asked_total": len(sections) * ITEMS_PER_SECTION,
        "answered_total": answered_total,
        "raw_total": raw_total,
        "raw_max": len(sections) * ITEMS_PER_SECTION,
        "points": points,
        "max_points": WRITTEN_MAX_POINTS,
        "pass_points": PASS_POINTS,
        "needed_from_spoken": needed,
        "spoken_max_points": SPOKEN_MAX_POINTS,
        "spoken_can_reach": points + SPOKEN_MAX_POINTS >= PASS_POINTS,
        "written_minimum": WRITTEN_MINIMUM,
        "written_above_minimum": points >= WRITTEN_MINIMUM,
    }


def instruction_rows():
    """The official instruction words, each marked with the course word that teaches it.

    A learner who cannot read «ankreuzen» on the task sheet is stopped by vocabulary rather
    than by German, so the exam page lists these. The mark is looked up among the real
    published ``Word`` rows rather than written down here, so adding one of these words to
    the course makes the list notice by itself — and a word the course does not teach is
    shown as a gap instead of being quietly assumed.
    """
    taught_by_word = {}
    for word in Word.objects.filter(is_published=True):
        taught_by_word[word.word.lower()] = word

    rows = []

    for entry in INSTRUCTIONS:
        taught = None

        for part in entry["german"].split("/"):
            for piece in part.split():
                if piece == "der" or piece == "die" or piece == "das":
                    continue
                if piece.lower() in taught_by_word:
                    taught = taught_by_word[piece.lower()]
                    break
            if taught is not None:
                break

        rows.append({
            "german": entry["german"],
            "fa": entry["fa"],
            "taught": taught,
        })

    return rows


def open_run(user):
    """The learner's unfinished run, if they left one, so an exam is resumed not restacked."""
    return ExamRun.objects.filter(user=user, finished_at__isnull=True).first()


def elapsed_minutes(run, now=None):
    """How long ago the paper was started, in minutes.

    The clock is the run's own ``started_at``, not the browser's, so closing the tab does
    not pause the exam and refreshing does not extend it.
    """
    if now is None:
        now = timezone.now()

    return (now - run.started_at).total_seconds() / 60


def remaining_minutes(run, now=None):
    """How much of the paper's clock is left, for the page to show.

    Rounded **up**, so an exam just started reads `65` rather than `64` because a fraction
    of a second has already gone by — the same reason the pace arithmetic in
    ``lessons/readiness.py`` rounds its suggestions up.
    """
    left = DURATION_MINUTES - elapsed_minutes(run, now)

    if left < 0:
        return 0
    return math.ceil(left)


def time_is_up(run, now=None):
    """Whether the paper's clock has run out.

    Asked separately from ``remaining_minutes`` because the two are not the same question:
    answering is refused the moment the time is over, while the page shows whole minutes
    left and would otherwise start refusing answers up to a minute early.
    """
    return elapsed_minutes(run, now) >= DURATION_MINUTES


def phrase_prefix(german):
    """The first few words of a phrase, for matching it against a real sentence.

    An exam phrase is a pattern (``Ich heiße … / Mein Name ist …``) and a course sentence
    is a fact, so a phrase can only be linked to practice when the course really has a
    sentence that begins with it. Three words are enough to be specific and short enough
    to survive a variant the phrase data does not spell out.
    """
    first = german.split("/")[0]
    first = first.replace("…", " ")

    words = []
    for piece in first.split():
        words.append(piece)
        if len(words) == 3:
            break

    return " ".join(words).lower()


def spoken_practice(parts):
    """Each spoken phrase, with the practice that already asks about it when there is any.

    SPRECHEN is the one section this product cannot grade, so the rehearsal can at least
    make sure the phrases are *practised* — and the way to do that honestly is to point at
    existing questions about the product's own sentences, not at a new quiz invented for
    the exam page. A phrase the course has no sentence for is returned without practice
    and the page shows it as a phrase to learn rather than pretending there is a drill.
    """
    sentences = list(Sentence.objects.filter(is_published=True))

    exercises_by_sentence = {}

    targets = (
        QuestionTarget.objects.filter(
            sentence__isnull=False,
            question__exercise__is_published=True,
            question__exercise__lesson__is_published=True,
            question__exercise__lesson__course__is_published=True,
        )
        .select_related("question__exercise__lesson")
        .order_by("question__exercise__lesson__order", "question__exercise__order", "question__order")
    )

    for target in targets:
        exercise = target.question.exercise

        if target.sentence_id not in exercises_by_sentence:
            exercises_by_sentence[target.sentence_id] = []

        if exercise not in exercises_by_sentence[target.sentence_id]:
            exercises_by_sentence[target.sentence_id].append(exercise)

    rows = []

    for part in parts:
        phrases = []

        for phrase in part["phrases"]:
            prefix = phrase_prefix(phrase["de"])

            sentence = None
            for candidate in sentences:
                if candidate.text.lower().startswith(prefix):
                    sentence = candidate
                    break

            practice = []
            if sentence is not None and sentence.pk in exercises_by_sentence:
                practice = exercises_by_sentence[sentence.pk]

            phrases.append({
                "de": phrase["de"],
                "fa": phrase["fa"],
                "sentence": sentence,
                "practice": practice,
            })

        part_row = {
            "number": part["number"],
            "title": part["title"],
            "german": part["german"],
            "minutes": part["minutes"],
            "points": part["points"],
            "what": part["what"],
            "phrases": phrases,
        }
        rows.append(part_row)

    return rows
