"""Pull the German out of a lesson's mixed-language text, for text-to-speech.

The material is written for Persian speakers, so a single line holds German and its
Persian translation side by side::

    Ich bin Ali.  (من علی هستم.)

Every content block and grammar topic also ends with an ``English:`` sentence that
explains the point of the text. None of that Persian or English is what the learner
needs to hear -- the audio is for the German -- so :func:`spoken_text` keeps the
German words and throws the rest away.

The rules, in the order they are applied:

1. Everything from the ``English:`` line onwards is dropped. It is a note about the
   text, not part of it, and it sits last, so the rest of the text is unaffected.
2. A ``(...)`` group holding Persian is the translation of the German beside it, so
   the whole group goes -- brackets included, which is why the line does not end up
   with an empty ``()``.
3. Whatever Persian characters are left are removed.
4. The middle dot that separates list items becomes a comma, because a comma is the
   pause a reader makes there. Quote marks and arrows are dropped; they are not said
   out loud.
5. A line with no German letters left in it (a Persian-only heading, for instance) is
   dropped instead of being sent to the synthesiser as silence.

The title is narrated as well. Every title in the course is German and names the
material (``Beispiele: Personen vorstellen``), so it makes a natural heading for the
audio. When nothing German survives the whole text, ``spoken_text`` returns an empty
string, which is the caller's signal to skip the row rather than synthesise nothing.
"""

import re

# Persian and Arabic letters, their punctuation and digits, and the invisible marks
# that join Persian letters together. German audio must contain none of these.
PERSIAN_RANGE = "\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF\u200c\u200d\u200e\u200f"

PERSIAN = re.compile("[" + PERSIAN_RANGE + "]")

# A translated aside, for example "(من علی هستم.)". Only the ones holding Persian are
# removed, so a German aside in brackets is left alone.
PARENTHETICAL_PERSIAN = re.compile(r"\([^)]*[" + PERSIAN_RANGE + r"][^)]*\)")

# "das Konto · der Schalter" -- the dot becomes a comma, with no space left in front
# of it, so the spoken list reads naturally.
LIST_SEPARATOR = re.compile(r"\s*·\s*")

# Quote marks and arrows: punctuation the reader does not say.
DECORATION = re.compile(r"[«»‹›„“”‘’←→…–—]")

# A line needs at least one of these to be worth reading aloud.
GERMAN_LETTER = re.compile(r"[A-Za-zÄÖÜäöüß]")

# Left at the end of a line when the Persian or a bracket beside it is removed, for
# example "Ben: B-E-N.   (ب-ن.)   ← ..." leaves a stranded full stop behind.
ORPHAN_TAIL = re.compile(r"(?:\s+[.,;:!?])+$")

# The marker that starts the closing English note.
ENGLISH_NOTE = "English:"


def spoken_text(title, body):
    """The German in ``title`` and ``body``, ready to be read aloud.

    Returns an empty string when the two hold no German at all.
    """
    body_lines = []

    for line in body.splitlines():
        if line.lstrip().startswith(ENGLISH_NOTE):
            break
        body_lines.append(line)

    text = "\n".join(body_lines)
    text = PARENTHETICAL_PERSIAN.sub("", text)
    text = PERSIAN.sub("", text)
    text = LIST_SEPARATOR.sub(", ", text)
    text = DECORATION.sub("", text)

    spoken_lines = []

    for line in (title + "\n" + text).splitlines():
        # Collapse the runs of spaces the removals left behind.
        line = " ".join(line.split())
        line = ORPHAN_TAIL.sub("", line)
        line = line.strip(" \t:;,")
        if GERMAN_LETTER.search(line):
            spoken_lines.append(line)

    return "\n".join(spoken_lines)
