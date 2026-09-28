"""Presentation facts for the exercise runner.

The exercise page asks the learner one question at a time, so it needs to know — per
question — how the learner answers it. That decision is made here, from real rows only,
instead of being spread across the template and the JavaScript.

How the kind is decided (`Answer` rows are the only signal):

- **choice** — more than one answer row: pick one of the rendered options. This is
  every `MULTIPLE_CHOICE` / `TRUE_FALSE` / `READING` question, and the `FILL_BLANK`
  questions that were authored with distractors.
- **text** — exactly one answer row: type the answer. Every `TRANSLATION` question,
  and the five `FILL_BLANK` questions that have no distractors.
- **none** — no answer row at all, so there is nothing to grade. The question is
  still shown, labelled as unchecked, and left out of the score. No live question
  is in this state today (checked against the live database), but the runner must
  not invent a verdict for one.

Nothing here writes to the database and nothing here grades: this module is the *shape*
of the page. What counts as correct is decided when the learner submits, in
``exercises/grading.py``, and the questions render without their answers.
"""

CHOICE = "choice"
TEXT = "text"
UNCHECKED = "none"


def _passage(question):
    """The German sentence a question is built on, or an empty string.

    Only READING questions carry one: their `CONTEXT` target points at a real
    `Sentence`, which is the passage the learner is asked about.
    """
    for target in question.targets.all():
        if target.sentence_id and target.sentence:
            return target.sentence.text
    return ""


def build_runner(exercise):
    """One exercise's real rows → the ordered question list the runner renders.

    `exercises/views.py::ExerciseDetailView` is the only caller.
    """
    questions = []
    for position, question in enumerate(exercise.questions.all(), start=1):
        answers = list(question.answers.all())  # Answer.order
        correct = [answer for answer in answers if answer.is_correct]

        if not answers or not correct:
            kind = UNCHECKED
        elif len(answers) > 1:
            kind = CHOICE
        else:
            kind = TEXT

        questions.append(
            {
                "id": question.pk,
                # Display position, not Question.order: `order` counts across every
                # question of the lesson (a lesson's TRUE_FALSE exercise really does
                # start at question 12), so it cannot be used as "question 1 of 2".
                "number": position,
                "kind": kind,
                "prompt": question.prompt,
                "passage": _passage(question),
                # Options only exist for the questions that render a choice; a typed
                # answer renders an input instead.
                "options": answers if kind == CHOICE else [],
                "audio": question.audio,
                "image": question.image,
            }
        )
    return questions


def scoreable_count(questions):
    """How many of these questions can actually be graded."""
    total = 0
    for question in questions:
        if question["kind"] != UNCHECKED:
            total += 1
    return total
