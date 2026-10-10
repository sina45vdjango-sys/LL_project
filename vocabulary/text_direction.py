"""Give mixed Persian and German text an explicit direction, run by run.

The lesson material is written for Persian speakers, so one line often holds German and
its Persian translation side by side::

    Ich bin Ali.  (من علی هستم.)

A browser lays that out with the Unicode bidirectional algorithm, and the only hint it
has is the characters themselves. ``dir="auto"`` and ``unicode-bidi: plaintext`` make it
guess from the first strong character, which is a heuristic: a line that starts with a
German sentence but continues in Persian can end up reordering the German words, which is
exactly the bug this module removes. Nothing here lets the browser guess.

Instead the text is cut into **runs** of one language each, and every run is wrapped in a
``<bdi>`` carrying the language and its direction. ``<bdi>`` isolates a run from its
neighbours in every browser (its own direction is what we set, not ``auto``), so a German
sentence stays ``Ich bin Sina.`` and never becomes ``bin ich Sina`` however much Persian
surrounds it.

Two rules keep this small and predictable, because the content is structured rather than
free prose:

* Consecutive words of the same language are **one** run. The spaces between them are
  neutral, so a whole German sentence is a single isolated run rather than a word-by-word
  sequence that would be split apart. Only Persian *letters* and German letters count as
  strong: spaces, punctuation and digits are neutral, which is why ``Ich (1) bin (2)
  Sina.`` stays one German run.
* A run keeps the neutral characters **around** it up to the next opening bracket or
  quote. That is what keeps a translation in brackets attached to the translation:
  ``Ich bin Ali.  (من علی هستم.)`` is a German sentence, then a Persian sentence in
  brackets -- the full stop stays with the German, the ``(`` goes with the Persian. Get
  this wrong and the two brackets end up on opposite ends of the line, which reads as
  though the German sentence is the parenthetical one.
* The **spaces** at the end of a run do not travel inside it. A space follows the
  direction of the run it sits in, and that is not always the side the next run is on:
  ``واژهٔ «hallo» به چه معنی است؟`` once ended the German run with the space, and an LTR
  run's trailing space sits on its *right* -- next to ``واژهٔ`` -- so the line read
  ``«hallo»به`` while the gap moved to the wrong side. Trailing spaces are handed back as
  a neutral piece between the two runs, and the line's own direction puts them in the
  gap they were written in.

The whole line is then wrapped in one more ``<bdi>`` whose direction is the direction of
the language the line *starts* in. So a line that begins in German is laid out left to
right (German on the left, its translation on the right) and a line that begins in
Persian is laid out right to left. The order of the runs therefore always matches the
order they are written in; only their own internal direction is language-specific.

The Persian letters are spelled out here instead of reusing ``german_text.PERSIAN``:
that pattern also covers Persian digits and punctuation on purpose, because the audio has
to strip them. Direction is the opposite question -- the ``۱`` in ``Ich (۱) bin (۲)
Sina.`` belongs to the German sentence around it, and calling it Persian would cut that
sentence into pieces.

``rendered`` is the one entry point; ``config/templatetags/direction.py`` exposes it to
templates as the ``direction`` filter. Nothing here touches the database.
"""

import re

from django.utils.html import escape

from .german_text import GERMAN_LETTER

#: Persian letters, as ``german_text.PERSIAN`` has them minus the digits and the
#: punctuation (which are neutral -- see the module docstring).
PERSIAN_LETTER = re.compile(
    "["
    "\u0621-\u063a"  # hamza to ghain
    "\u0641-\u064a"  # feh to yeh
    "\u066e-\u066f"  # dotless beh and qaf
    "\u0671-\u06d3"  # the rest of the Persian block, stopping before its full stop
    "\u06d5\u06ee-\u06ef\u06fa-\u06fc\u06ff"
    "\u0750-\u077f"  # Arabic supplement
    "\ufb50-\ufdff\ufe70-\ufefc"  # presentation forms
    "]"
)

#: A maximal run of one script. Built from the two patterns above, so "Persian" and "a
#: German letter" mean here exactly what they mean to the audio code.
SCRIPT_RUN = re.compile(
    "(?P<fa>(?:" + PERSIAN_LETTER.pattern + ")+)|(?P<de>(?:" + GERMAN_LETTER.pattern + ")+)"
)

#: Characters that open a bracket or a quotation. One of these at the start of the text
#: between two runs belongs to the run on its right: ``(من علی هستم.)`` is the Persian
#: translation with its own brackets, not something the German sentence opened. Closing
#: characters need no list -- they simply stay where they are, with the run on their left.
OPENING = "([{«„“‘‹"

#: Per-language direction. Persian is the product's reading direction; German is not.
DIRECTIONS = {"fa": "rtl", "de": "ltr"}

#: One isolated run. `<bdi>` already means "isolate"; the class is the CSS hook that
#: states it out loud so a reset cannot quietly take it away.
RUN_TEMPLATE = '<bdi class="run run--{lang}" lang="{lang}" dir="{dir}">{text}</bdi>'

#: One line. The direction is the direction of the language the line starts in, so the
#: runs are placed in writing order whatever that language is.
LINE_TEMPLATE = '<bdi class="text-line" dir="{dir}">{text}</bdi>'


def opening_offset(gap):
    """How much of ``gap`` stays with the run on its left.

    Everything up to the first opening bracket or quote: ``.  (`` puts the full stop and
    the spaces with the run before it and hands the ``(`` to the run after it.
    """
    for position, character in enumerate(gap):
        if character in OPENING:
            return position
    return len(gap)


def line_runs(line):
    """Split one line into runs, in display order, each with the language it is in.

    Every run is ``{"lang", "text"}``. ``lang`` is ``None`` for the neutral characters in
    front of the first run; those are returned untouched so the line can be put back
    together exactly as it was. The runs always cover the whole line, in order, with no
    text lost.
    """
    groups = []

    for match in SCRIPT_RUN.finditer(line):
        if match.group("fa"):
            lang = "fa"
        else:
            lang = "de"

        # Same language as the run before it? Extend that run instead of starting a new
        # one, so the neutral characters in between stay inside it.
        if groups and groups[-1]["lang"] == lang:
            groups[-1]["end"] = match.end()
            continue

        groups.append({"lang": lang, "start": match.start(), "end": match.end()})

    if not groups:
        return [{"lang": None, "text": line}]

    runs = []

    # Anything before the first run (a bullet, for instance) is neutral text.
    if groups[0]["start"] > 0:
        runs.append({"lang": None, "text": line[: groups[0]["start"]]})

    for position, group in enumerate(groups):
        # This run starts after the gap the run before it kept to itself.
        if position == 0:
            start = group["start"]
        else:
            gap = line[groups[position - 1]["end"]:group["start"]]
            start = groups[position - 1]["end"] + opening_offset(gap)

        # And it ends at its own last letter, plus the gap up to the next opening
        # character. The last run on the line keeps whatever is left.
        trailing = ""
        if position + 1 < len(groups):
            gap = line[group["end"]:groups[position + 1]["start"]]
            offset = opening_offset(gap)

            if offset < len(gap):
                end = group["end"] + offset
            else:
                # The gap holds no bracket, only punctuation and spaces. The punctuation
                # stays with the run it closes, but the spaces must not: a space inside a
                # run follows that run's direction, not the line's, so an LTR run's
                # trailing space sits on its right -- next to the run *before* it -- and
                # the gap appears on the wrong side. The spaces become a neutral piece
                # between the two runs instead, where the line's direction places them.
                end = group["end"] + len(gap.rstrip())
                trailing = line[end:groups[position + 1]["start"]]
        else:
            end = len(line)

        runs.append({"lang": group["lang"], "text": line[start:end]})

        if trailing:
            runs.append({"lang": None, "text": trailing})

    return runs


def rendered(text):
    """``text`` as HTML with one isolated run per language, line by line.

    Lines are handled separately so a run can never span a paragraph break: the body is
    later passed through Django's ``linebreaks``, and a tag straddling a blank line would
    be split into unbalanced HTML. A run may still contain a single newline, which
    ``linebreaks`` turns into ``<br>`` inside the run.
    """
    lines = []

    for line in str(text).split("\n"):
        pieces = []
        direction = None

        for run in line_runs(line):
            if run["lang"] is None:
                pieces.append(escape(run["text"]))
                continue

            if direction is None:
                direction = DIRECTIONS[run["lang"]]

            pieces.append(
                RUN_TEMPLATE.format(
                    lang=run["lang"],
                    dir=DIRECTIONS[run["lang"]],
                    text=escape(run["text"]),
                )
            )

        # A line with no letters in it has no direction of its own; it stays plain text
        # and keeps the direction of the page it is on.
        if direction is None:
            lines.append("".join(pieces))
        else:
            lines.append(LINE_TEMPLATE.format(dir=direction, text="".join(pieces)))

    return "\n".join(lines)
