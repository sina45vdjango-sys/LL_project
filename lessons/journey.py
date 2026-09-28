"""The lesson as a guided journey.

A lesson's shape comes from its own data, so nothing here invents content. A step
is added only when the thing it teaches exists, and a lesson whose author never
attached grammar never renders an empty grammar step:

    intro        always — orientation: what this lesson contains
    explanation  LessonContent of type EXPLANATION / NOTE
    vocabulary   LessonWord links (VOCABULARY content blocks as the lead-in)
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

from collections import defaultdict

from .models import LessonContent, LessonSentence

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


def build_journey(*, blocks, grammar_links, sentence_links, word_page, exercises):
    """Turn one lesson's real content into an ordered list of steps.

    ``word_page`` is a ``Paginator`` page (the vocabulary step is paginated; a
    lesson can carry well over a hundred words) and ``exercises`` are published
    ``Exercise`` rows.
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
        steps.append(
            _step(
                "vocabulary",
                word_total,
                blocks=blocks_by_step["vocabulary"],
                words=list(word_page),
                word_page=word_page,
            )
        )

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
    return steps


def content_step_count(steps):
    """How many steps carry material (everything except intro and finish)."""
    total = 0
    for step in steps:
        if step["key"] not in ("intro", "finish"):
            total += 1
    return total
