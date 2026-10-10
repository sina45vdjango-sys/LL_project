"""What the Persian lesson pages show of the authored lesson text.

The material under ``lessons/data/`` is authored once and ends every prose block, every
grammar explanation and every lesson description with an ``English: …`` gloss. That gloss
documents the German for a future English interface: it is not something a Persian learner
reads, and on the page it is a line of English wedged under a Persian paragraph. The two
filters here are the whole answer, and neither of them touches the stored text — they
change what is *rendered*, so the data stays ready for that English product.

* ``without_english`` cuts the trailing gloss off. It is applied to every block body, every
  grammar explanation and the lesson description.
* ``list_lines`` turns the vocabulary block's ``danke (متشکرم) · bitte (لطفاً)`` line into
  one item per line. The ``·`` separates list items, so a line per item is what the text
  already means — and the words themselves are also the rows right below, where a run-on
  line would only be unreadable.

Registered as a builtin beside ``direction`` (see ``settings.TEMPLATES``), so no template
needs a ``{% load %}``.
"""

from django import template

register = template.Library()

#: How the authored material marks its English gloss. Everything from this marker to the
#: end of the text is the gloss, which is why it has to sit on its own line or at the end
#: of one; `Englisch` (the German word for English) is not it.
GLOSS = "English:"

#: The list separator used inside a vocabulary block's word lines.
SEPARATOR = "·"


@register.filter(name="without_english")
def without_english(value):
    """``value`` with its trailing ``English: …`` gloss removed.

    The gloss is always the last thing in the text, so the first line that carries the
    marker is where the text ends; what is kept before it is the Persian material. The
    newlines are left alone, so ``linebreaks`` downstream still builds the same
    paragraphs (minus the gloss) as it would have.
    """
    if value is None:
        return ""

    kept = []

    for line in str(value).split("\n"):
        marker = line.find(GLOSS)

        if marker != -1:
            line = line[:marker].rstrip()
            if line:
                kept.append(line)
            break

        kept.append(line)

    while kept and not kept[-1].strip():
        kept.pop()

    return "\n".join(kept)


@register.filter(name="list_lines")
def list_lines(value):
    """One item per line, for text that writes its items on one ``·``-separated line.

    Only the vocabulary step passes its body through this. A line without a separator is
    left exactly as it was written, so the block's headings and its already-one-per-line
    entries are untouched, and a blank line stays the blank line ``linebreaks`` needs.
    """
    if value is None:
        return ""

    lines = []

    for line in str(value).split("\n"):
        if SEPARATOR not in line:
            lines.append(line)
            continue

        for part in line.split(SEPARATOR):
            part = part.strip()
            if part:
                lines.append(part)

    return "\n".join(lines)
