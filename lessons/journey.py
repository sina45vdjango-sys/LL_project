"""The lesson as a guided journey.

A lesson's shape comes from its own data, so nothing here invents content. A step
is added only when the thing it teaches exists, and a lesson whose author never
attached grammar never renders an empty grammar step:

    intro        always — orientation: what this lesson contains
    explanation  LessonContent of type EXPLANATION / NOTE
    vocabulary   LessonWord links (VOCABULARY content blocks as the lead-in on page 1,
                 the lesson's own sentences on the pages after it)
    grammar      LessonGrammar links (GRAMMAR content blocks as the lead-in)
    examples     LessonSentence role EXAMPLE (EXAMPLE content blocks)
    dialogue     LessonSentence role DIALOGUE (DIALOGUE content blocks)
    reading      LessonSentence role READING
    listening    LessonSentence role LISTENING
    practice     published Exercise rows attached to the lesson
    finish       always — the summary and the completion action

Each step is a plain dict in display order that names the partial rendering its
body, so ``templates/lessons/lesson_detail.html`` stays a composition instead of
ten inline sections. Step order, labels and counts therefore have exactly one
definition: this module.

Nothing here writes to the database, and nothing here knows about the browser —
status and completion are the client's business (see ``static/js/lesson_status.js``).
"""

import re
from collections import defaultdict

from .models import LessonContent, LessonSentence

#: How many sentences the vocabulary step shows beside a page of words. A page of twenty-
#: four ordinary words can mention a dozen sentences, and the reading material belongs in
#: the examples and dialogue steps; a handful is enough to see the words in use.
CONTEXT_SENTENCES = 6

#: Where each content-block type is read. NOTE sits with EXPLANATION because both
#: are prose the learner reads straight through.
_BLOCK_STEP = {
    LessonContent.ContentType.EXPLANATION: "explanation",
    LessonContent.ContentType.NOTE: "explanation",
    LessonContent.ContentType.GRAMMAR: "grammar",
    LessonContent.ContentType.VOCABULARY: "vocabulary",
    LessonContent.ContentType.EXAMPLE: "examples",
    LessonContent.ContentType.DIALOGUE: "dialogue",
}

#: The vocabulary step from page 2 on. Page 1 introduces the words; the pages after it
#: show them in the lesson's own sentences, so the step names what it is actually showing.
_VOCABULARY_AFTER_INTRO = {
    "title": "همین واژه‌ها، این بار در جمله",
    "hint": "صفحهٔ اول واژه‌ها را معرفی کرد؛ این صفحه همان واژه‌ها را در جمله‌های خودِ درس نشان می‌دهد.",
}

#: Sentence roles that earn their own step, in display order.
_SENTENCE_STEPS = (
    ("examples", LessonSentence.Role.EXAMPLE),
    ("dialogue", LessonSentence.Role.DIALOGUE),
    ("reading", LessonSentence.Role.READING),
    ("listening", LessonSentence.Role.LISTENING),
)

#: Copy and the partial for each step. `unit` is the noun used when the step's
#: size is shown ("۵۰ واژه"), so counts read naturally in the agenda.
_STEP_SPEC = {
    "intro": {
        "label": "آغاز",
        "title": "نقشهٔ این درس",
        "hint": "ببین این درس چه چیزی برایت دارد و از کجا شروع می‌کنی.",
        "unit": "",
        "template": "lessons/steps/_intro.html",
    },
    "explanation": {
        "label": "توضیح",
        "title": "توضیح و نکته‌ها",
        "hint": "هر بخش یک ایده دارد؛ کوتاه بخوان و جلو برو.",
        "unit": "بخش",
        # The step is nothing but its prose blocks, so it reuses the shared lead-in.
        "template": "lessons/steps/_lead.html",
    },
    "vocabulary": {
        "label": "واژگان",
        "title": "واژه‌های این درس",
        "hint": "معنی را ببین، تلفظ را بشنو و واژه را در جمله‌های بعدی پیدا کن.",
        "unit": "واژه",
        "template": "lessons/steps/_vocabulary.html",
    },
    "grammar": {
        "label": "گرامر",
        "title": "گرامر این درس",
        "hint": "قاعده‌ای که این درس روی آن بنا شده است.",
        "unit": "موضوع",
        "template": "lessons/steps/_grammar.html",
    },
    "examples": {
        "label": "مثال‌ها",
        "title": "مثال‌های کاربردی",
        "hint": "اول جملهٔ آلمانی را بخوان، بعد ترجمه را بررسی کن.",
        "unit": "جمله",
        "template": "lessons/steps/_sentences.html",
    },
    "dialogue": {
        "label": "گفت‌وگو",
        "title": "گفت‌وگوی این درس",
        "hint": "نقش هر گوینده را ببین و جمله‌ها را بشنو.",
        "unit": "جمله",
        "template": "lessons/steps/_sentences.html",
    },
    "reading": {
        "label": "خواندن",
        "title": "متن خواندنی",
        "hint": "متن را بخوان و با ترجمه تطبیق بده.",
        "unit": "جمله",
        "template": "lessons/steps/_sentences.html",
    },
    "listening": {
        "label": "شنیدن",
        "title": "تمرین شنیدن",
        "hint": "اول فقط گوش کن، بعد ترجمه را ببین.",
        "unit": "جمله",
        "template": "lessons/steps/_sentences.html",
    },
    "practice": {
        "label": "تمرین",
        "title": "تمرین‌های این درس",
        "hint": "همین مطالب را در عمل به کار ببر.",
        "unit": "تمرین",
        "template": "lessons/steps/_practice.html",
    },
    "finish": {
        "label": "پایان",
        "title": "درس را تمام کن",
        "hint": "خلاصهٔ این درس و قدم بعدی.",
        "unit": "",
        "template": "lessons/steps/_finish.html",
    },
}


def _step(key, count, **extra):
    step = {"key": key, "count": count}
    step.update(_STEP_SPEC[key])
    step.update(extra)
    return step


def sentences_using(words, sentence_links):
    """The lesson's own sentences that put any of ``words`` to use, in lesson order.

    Each row is ``{"link", "words"}``: the sentence, and the given words it uses, so the
    page can mark which of its own words appear in it.

    The vocabulary step shows these from page 2 on. Page 1 carries the authored lead-in
    that introduces the words; repeating that paragraph on every further page would be the
    same text over and over, so the pages after it show the words doing something instead
    — in sentences the lesson already teaches, which is why nothing here is invented.

    A sentence counts when one of the words appears in it as a **whole word**, so ``es``
    does not match inside ``dieses`` and a word is not "used" by a word that merely
    contains it. Inflected forms are not matched, so the list shows what is certain rather
    than guessing at a stem. At most ``CONTEXT_SENTENCES`` sentences are returned, because
    the reading material belongs in the examples and dialogue steps.
    """
    patterns = []
    for word in words:
        patterns.append((word, re.compile(r"(?<!\w)" + re.escape(word.word) + r"(?!\w)", re.IGNORECASE)))

    found = []
    for link in sentence_links:
        used = []
        for word, pattern in patterns:
            if pattern.search(link.sentence.text):
                used.append(word)

        if used:
            found.append({"link": link, "words": used})

        if len(found) == CONTEXT_SENTENCES:
            break

    return found


#: The 15-minute path: the same lesson, trimmed to what fits one short sitting. Two whole
#: steps are left out — «خواندن» and «شنیدن» are extra material built on the same sentences
#: the examples and dialogue steps already show — and each remaining step keeps only its
#: first few items.
#:
#: This is deliberately not a second lesson system. It is the same content, the same
#: templates, the same exercise pages and the same completion rule; only the amount shown
#: differs. Nothing is authored twice, nothing is invented, and the full lesson is one link
#: away — the finish step names what this path did not cover.
SHORT_DROPPED_STEPS = ("reading", "listening")

#: How much of each step the short path keeps: two prose blocks, a dozen words, one grammar
#: topic, four example sentences, four dialogue lines, one exercise. The caps are here rather
#: than scattered through the template so that "what does the short version cover" has one
#: answer, in one place, that the page can also print.
SHORT_BLOCK_LIMIT = 2
SHORT_WORD_LIMIT = 12
SHORT_GRAMMAR_LIMIT = 1
SHORT_SENTENCE_LIMIT = 4
SHORT_EXERCISE_LIMIT = 1


def build_journey(*, blocks, grammar_links, sentence_links, word_page, word_rows, exercises, short=False):
    """Turn one lesson's real content into an ordered list of steps.

    ``word_page`` is a ``Paginator`` page (the vocabulary step is paginated; a
    lesson can carry well over a hundred words), ``word_rows`` is that page of words as
    the vocabulary rows to render (``vocabulary/status.py``), and ``exercises`` are
    published ``Exercise`` rows.

    ``short`` builds the 15-minute path instead of the full one: the same steps, with the
    two extra reading steps dropped and every step trimmed to its first few items. Each
    step's ``count`` is recomputed so the agenda and the finish summary keep telling the
    truth about what this path actually contains.
    """
    blocks_by_step = defaultdict(list)
    for block in blocks:
        blocks_by_step[_BLOCK_STEP.get(block.type, "explanation")].append(block)

    sentences_by_role = defaultdict(list)
    for link in sentence_links:
        sentences_by_role[link.role].append(link)

    word_total = word_page.paginator.count

    steps = [_step("intro", 0)]

    if blocks_by_step["explanation"]:
        steps.append(_step("explanation", len(blocks_by_step["explanation"]), blocks=blocks_by_step["explanation"]))

    if word_total:
        page_words = []
        for row in word_rows:
            page_words.append(row["word"])

        context_sentences = sentences_using(page_words, sentence_links)

        step = _step(
            "vocabulary",
            word_total,
            blocks=blocks_by_step["vocabulary"],
            words=word_rows,
            word_page=word_page,
            context_sentences=context_sentences,
        )

        # Page 1 is where the words are introduced, so that is where the lead-in belongs.
        # From page 2 on the step is about something else, and it says so.
        if word_page.number > 1 and context_sentences:
            step.update(_VOCABULARY_AFTER_INTRO)

        steps.append(step)

    if grammar_links:
        steps.append(
            _step("grammar", len(grammar_links), blocks=blocks_by_step["grammar"], grammar=grammar_links)
        )

    for key, role in _SENTENCE_STEPS:
        sentences = sentences_by_role.get(role, [])
        # A step exists if the lesson has sentences in that role *or* a prose
        # block about it — otherwise it would be an empty screen.
        if sentences or blocks_by_step[key]:
            steps.append(_step(key, len(sentences), blocks=blocks_by_step[key], sentences=sentences))

    if exercises:
        steps.append(_step("practice", len(exercises), exercises=exercises))

    steps.append(_step("finish", 0))

    if short:
        kept = []
        for step in steps:
            if step["key"] in SHORT_DROPPED_STEPS:
                continue

            if step["key"] == "explanation":
                step["blocks"] = step["blocks"][:SHORT_BLOCK_LIMIT]
                step["count"] = len(step["blocks"])

            if step["key"] == "vocabulary":
                # `word_page` still carries the lesson's real total, which is what the step
                # shows beside the trimmed list — "۱۲ واژه در این نسخه، از ۵۰ واژهٔ درس".
                step["words"] = step["words"][:SHORT_WORD_LIMIT]
                step["count"] = len(step["words"])
                step["short"] = True

            if step["key"] == "grammar":
                step["grammar"] = step["grammar"][:SHORT_GRAMMAR_LIMIT]
                step["count"] = len(step["grammar"])

            if step["key"] in ("examples", "dialogue"):
                step["sentences"] = step["sentences"][:SHORT_SENTENCE_LIMIT]
                step["count"] = len(step["sentences"])

            if step["key"] == "practice":
                step["exercises"] = step["exercises"][:SHORT_EXERCISE_LIMIT]
                step["count"] = len(step["exercises"])

            kept.append(step)

        steps = kept

    return steps


def content_step_count(steps):
    """How many steps carry material (everything except intro and finish)."""
    total = 0
    for step in steps:
        if step["key"] not in ("intro", "finish"):
            total += 1
    return total
