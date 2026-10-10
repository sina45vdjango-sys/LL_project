"""Presentation facts for the exercise runner.

The exercise page asks the learner one question at a time, so it needs to know — per
question — how the learner answers it. That decision is made here, from real rows only,
instead of being spread across the template and the JavaScript.

How the kind is decided (`Answer` rows are the only signal, with one exception):

- **choice** — at least one wrong option is written: pick one of the rendered options.
  This is every `MULTIPLE_CHOICE` / `TRUE_FALSE` / `READING` question, and the
  `FILL_BLANK` questions that were authored with distractors.
- **text** — every answer row is a correct one: type the answer. Every `TRANSLATION`
  question, and the five `FILL_BLANK` questions that have no distractors.

  The rule is "there are no wrong options", not "there is exactly one row", because one
  Persian gloss often has more than one correct German word (``مادربزرگ`` is both ``Oma``
  and ``Großmutter``). A typed question carries one answer row **per accepted spelling**,
  so the second correct word is graded right instead of being marked wrong — and the page
  still renders an input instead of options, because there is still nothing to pick.
- **order** — a scramble: the sentence's own words are shown shuffled — without their
  punctuation, which is not what the question asks — and the learner writes them back in the
  right order. This is the exception to the rule above — it is decided by the
  exercise's own type, because a scramble has a single correct `Answer` row (the sentence) and
  would otherwise be indistinguishable from a typed question. The words come from that answer;
  their order, which is the whole task, is what the page never holds.
- **none** — no answer row at all, so there is nothing to grade. The question is
  still shown, labelled as unchecked, and left out of the score. No live question
  is in this state today (checked against the live database), but the runner must
  not invent a verdict for one.

Nothing here writes to the database and nothing here grades: this module is the *shape*
of the page. What counts as correct is decided when the learner submits, in
``exercises/grading.py``, and the questions render without their answers.

A choice question's options are **shuffled** before they are rendered. Every authored
multiple-choice question stored its correct option first, so the answer was always option
1 and the learner could pass by always picking it. The shuffle is seeded from the
question's id, the same way a scramble is, so one question always shows the same order —
a refresh does not rearrange the options under the learner. Nothing about *which*
option is correct leaves the server: the shuffle only changes their positions, and
grading still compares the submitted ``Answer`` id with the rows themselves.
"""

import random
import re

from exercises.models import Exercise

CHOICE = "choice"
TEXT = "text"
ORDER = "order"
UNCHECKED = "none"

#: The punctuation a scramble's words are shown without. ``exercises/grading.py`` ignores
#: the same marks when it compares a scramble answer, so what the tray shows and what the
#: server accepts cannot drift apart.
PUNCTUATION = re.compile(r"[.!?,;:،؛«»\"']+")


def _passage(question):
    """The German text a question is built on, or an empty string.

    Only READING questions carry one: their `CONTEXT` targets point at real `Sentence`
    rows. A reading question may carry **several** — that is the passage it is about — so
    they are joined in target order. Returning only the first line was why the reading
    exercise had a one-line "text"; a question built from a real passage now shows one.
    """
    lines = []

    for target in question.targets.all():
        if target.sentence_id and target.sentence:
            lines.append(target.sentence.text)

    if not lines:
        return ""

    return "\n".join(lines)


def extract_sentence_words(question):
    """The words of a scramble's own sentence, bare and shuffled so their order is the answer.

    The sentence is the question's single correct `Answer` row. The words are shown **without
    their punctuation**: the tray is a set of words to put in order, not the sentence in
    disguise, and a chip reading «danke.» or «gut,» reads as one unit to copy instead of a
    word to place. Grading ignores punctuation for a scramble for the same reason, so the
    learner is never asked to reproduce a mark the tray did not show.

    The shuffle is seeded from the question's id, the same way ``exams/paper.py`` seeds a
    paper from the run, so two page loads show the same order rather than re-scrambling under
    the learner. A shuffle that lands back on the sentence's own order would hand over the
    answer, so it is rotated by one word instead.
    """
    sentence = ""
    for answer in question.answers.all():
        if answer.is_correct:
            sentence = answer.text
            break

    words = sentence.split()
    if len(words) < 2:
        return words

    bare = []
    for word in words:
        without_punctuation = PUNCTUATION.sub("", word)
        # A word that is only punctuation (an ellipsis, say) has no bare form; dropping it
        # would remove a word the learner has to place, so it is shown as it is.
        if without_punctuation:
            bare.append(without_punctuation)
        else:
            bare.append(word)

    shuffled = list(bare)
    random.Random(question.pk).shuffle(shuffled)

    if shuffled == bare:
        shuffled = bare[1:] + bare[:1]

    return shuffled


def build_runner(exercise):
    """One exercise's real rows → the ordered question list the runner renders.

    `exercises/views.py::ExerciseDetailView` is the only caller. A scramble is the one kind
    decided by the exercise's own type, so the exercise is what tells `question_rows` to read
    it as one.
    """
    scramble = exercise.type == Exercise.ExerciseType.SCRAMBLE
    return question_rows(list(exercise.questions.all()), scramble=scramble)


def question_rows(questions, scramble=False):
    """Real questions → the ordered list the runner renders, numbered from 1.

    Shared by an exercise page and by the exam mode, which asks a set of questions drawn
    from many exercises at once: "how a question is answered" (its kind, its options, its
    passage) has to have exactly one definition, or an exam question could render one way
    and grade another. ``scramble`` is set only by an exercise page whose whole exercise is a
    scramble; the exam never draws one (``exams/paper.py`` leaves them out), so it takes the
    default.
    """
    rows = []
    for position, question in enumerate(questions, start=1):
        answers = list(question.answers.all())  # Answer.order
        correct = []
        for answer in answers:
            if answer.is_correct:
                correct.append(answer)

        if scramble:
            kind = ORDER
        elif not answers or not correct:
            kind = UNCHECKED
        elif len(correct) == len(answers):
            # Only correct rows: a typed question, possibly with several accepted
            # spellings of the same answer. Options are rendered only when there is
            # something wrong to choose from.
            kind = TEXT
        else:
            kind = CHOICE

        if kind == CHOICE:
            # The stored order put the correct option first in every authored question, so
            # the options are shuffled here. The seed is the question's id, so a reload
            # shows the same order and grading (which uses the option's id, not its
            # position) is unaffected.
            options = list(answers)
            random.Random(question.pk).shuffle(options)
        else:
            options = []

        # The shuffled words of a scramble, in display order. Empty for every other kind;
        # the answer is their order, which is not here.
        tokens = []
        if kind == ORDER:
            tokens = extract_sentence_words(question)

        rows.append(
            {
                "id": question.pk,
                # Which exercise this question belongs to. A page that shows one exercise
                # does not need it, but a session draws questions from many exercises at
                # once and has to submit each one to the exercise it really came from.
                "exercise_id": question.exercise_id,
                # Display position, not Question.order: `order` counts across every
                # question of the lesson (a lesson's TRUE_FALSE exercise really does
                # start at question 12), so it cannot be used as "question 1 of 2".
                "number": position,
                "kind": kind,
                "prompt": question.prompt,
                "passage": _passage(question),
                # Options only exist for the questions that render a choice; a typed
                # answer renders an input instead.
                "options": options,
                "tokens": tokens,
                "audio": question.audio,
                "image": question.image,
            }
        )
    return rows


def scoreable_count(questions):
    """How many of these questions can actually be graded."""
    total = 0
    for question in questions:
        if question["kind"] != UNCHECKED:
            total += 1
    return total
