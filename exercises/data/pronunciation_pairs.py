"""The sound contrasts the pronunciation drill trains.

A minimal pair is two words that differ in exactly one sound: ``dann`` / ``denn``,
``schon`` / ``schön``, ``Uhr`` / ``Ohr``. Hearing that difference is the skill the
``seed_a1_pronunciation_drills`` questions ask for, and it is the one part of listening the
rest of the product never touched — every existing question plays a whole sentence and asks
what it *means*, which a learner can often answer from the one word they did catch.

What is written here is the **contrast**, never a list of pairs. A hand-written pair list
would be a second copy of the course's vocabulary, able to drift from the words the lessons
actually teach; the words are already the source of truth (``vocabulary/data/*.json``). Each
entry is therefore two spellings that stand for two different sounds plus the Persian name
of the difference, and the command substitutes one for the other inside every word of the
level, keeping the result only when it happens to spell another published word. A pair
exists exactly when the course really contains both words, so the drill cannot invent
vocabulary and it grows and shrinks with the content.

Every entry was checked against the live course (1,008 published words): these fifteen
contrasts yield **38 real pairs**, each of them two words that differ by a single sound and
each already recorded. Rules that looked obvious and produced nothing were **left out**
rather than kept "for later": ``s``/``ß``, ``ss``/``ß``, ``d``/``t``, ``b``/``p``,
``g``/``k``, ``f``/``v``, ``w``/``v``, ``ch``/``sch``, ``s``/``sch``, ``t``/``z`` and the
vowel-length spellings (``a``/``aa``, ``e``/``ee``, ``o``/``oo``, ``u``/``uh``) have no
honest pair in this vocabulary.

Consonant doubling is the instructive exclusion. ``man`` / ``Mann`` is the only pair it
produces, and it is a *spelling* contrast rather than a sound one — German pronounces both
with a short a — so a question built on it would ask the learner to hear a difference that
is not there.

**The order of the list matters, and it is ordered by how much of the word the spelling
covers.** The first contrast that finds a partner names the question, so the two-letter
spellings come before the single letters: ``auch`` / ``euch`` is a vowel contrast
(``au`` against ``eu``) and must not be described as ``a`` against ``e`` by a rule that
happens to be able to spell it that way. Persian labels say what the difference sounds
like, because "ö is the rounded one" is the thing a learner cannot look up in a dictionary.
"""

#: (spelling, other spelling, how the two sounds differ).
#:
#: Longest spellings first — see the module docstring; a two-letter contrast must be able to
#: claim a pair before a one-letter rule renames it. Both directions are tried, so one entry
#: covers ``leben`` → ``lieben`` and ``lieben`` → ``leben`` without being written twice.
CONTRASTS = [
    ("ie", "e", "e کوتاه در برابر ie کشیده"),
    ("ih", "i", "i کوتاه در برابر ih کشیده"),
    ("ei", "i", "ei در برابر i"),
    ("ei", "eu", "ei در برابر eu"),
    ("au", "eu", "au در برابر eu"),
    ("e", "ei", "e در برابر ei"),
    ("u", "ü", "ü گرد در برابر u"),
    ("o", "ö", "ö گرد در برابر o"),
    ("e", "ö", "e در برابر ö"),
    ("e", "i", "e در برابر i"),
    ("a", "e", "a در برابر e"),
    ("o", "u", "o در برابر u"),
    ("m", "n", "m در برابر n"),
    ("l", "r", "l در برابر r"),
    ("n", "r", "پایانهٔ -n در برابر -r"),
]
