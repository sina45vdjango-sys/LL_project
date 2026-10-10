"""A lesson's own material, gathered for a quick review pass.

The problem: the lesson journey teaches a lesson step by step, and the only way the
product offered to *revise* one was to walk the stepper again — the same narrative
paragraphs, in the same order, at the same length. That is re-reading, not reviewing.

This module gathers the same rows the journey teaches from, but as lists: the words the
lesson links, its grammar topics, its sentences, and its key-idea blocks. Lists can be
scanned in a minute; the journey is what you read when you are learning.

Nothing is authored here and nothing is written: every item is a ``LessonWord``,
``LessonGrammar``, ``LessonSentence`` or ``LessonContent`` row that already exists. The
published-only rule is the product's usual one — a draft word, rule or sentence
contributes nothing, so the review cannot show material the lesson itself hides.

Grammar is the one entry that is *condensed* rather than repeated: a rule's stored
explanation is several paragraphs long, and the review shows only its first paragraph —
enough to bring the rule back to mind, with a link into the lesson for the full text.
"""


def quote_first_paragraph(text):
    """The first paragraph of a stored explanation, or an empty string.

    Explanations are written as paragraphs separated by blank lines (see
    ``lessons/data/a1_grammar.py``), so the first one is the rule stated in one breath —
    exactly the reminder a review wants, while the rest of the text stays in the lesson.
    """
    if not text:
        return ""

    for block in text.split("\n\n"):
        stripped = block.strip()
        if stripped:
            return stripped

    return ""


def word_rows(lesson):
    """The lesson's linked words, in the lesson's own order.

    Ordered by the link's ``order`` rather than by the word itself, because the lesson
    introduces its vocabulary in a deliberate sequence and the review should follow it.
    """
    return list(
        lesson.lesson_words.filter(word__is_published=True)
        .select_related("word")
        .order_by("order", "pk")
    )


def grammar_rows(lesson):
    """The lesson's grammar topics, each with its first paragraph as a summary.

    New words first is deliberate in the lesson's own data: ``role`` is not read here
    because both roles are worth reviewing, and the link order already puts the lesson's
    introduction before the recycled material.
    """
    rows = []

    for link in (
        lesson.lesson_grammars.filter(grammar__is_published=True)
        .select_related("grammar")
        .order_by("order", "pk")
    ):
        rows.append(
            {
                "grammar": link.grammar,
                "summary": quote_first_paragraph(link.grammar.explanation),
            }
        )

    return rows


def sentence_rows(lesson):
    """The lesson's sentences, in the lesson's own order, published ones only."""
    return list(
        lesson.lesson_sentences.filter(sentence__is_published=True)
        .select_related("sentence")
        .order_by("order", "pk")
    )


def idea_rows(lesson):
    """The lesson's non-vocabulary prose blocks: what the lesson explains and notes.

    The journey renders these in full while teaching. Here they are reduced to their
    titles, which is what a quick review of "what was this lesson about" needs; the
    vocabulary, grammar and example blocks have their own sections above and are left
    out so the same material is not shown twice.
    """
    return list(
        lesson.contents.filter(
            type__in=(
                "EXPLANATION",
                "NOTE",
            )
        ).order_by("order", "pk")
    )


def build_review(lesson):
    """Everything the review page shows, gathered in one pass over the lesson's rows."""
    return {
        "words": word_rows(lesson),
        "grammar": grammar_rows(lesson),
        "sentences": sentence_rows(lesson),
        "ideas": idea_rows(lesson),
    }
