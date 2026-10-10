"""Turn an inflected German word into the dictionary forms it might come from.

The lesson reader makes every German word clickable, and a learner who taps
``heiße`` expects the entry for ``heißen``. German marks its grammar at the end of
the word (``spielen → spielt``), in the stem vowel (``Haus → Häuser``), or in both
at once (``Buch → Bücher``) -- and the database only ever stores the dictionary
form, so the exact string is often not a row. The lookup therefore has to guess a
little. This module owns that guessing and nothing else: the view asks it for
candidate forms and does the querying itself. Keeping the guess a pure function
means it can be tested on its own, without a database.

A verb is stored with its pronoun when it is reflexive ("sich ärgern", "sich
freuen"), but the sentence the learner taps says "ärgert" -- so every verb guess is
offered twice, once plain and once with "sich" in front.
"""

#: Umlaut -> its base vowel, so ``Häuser`` can be walked back to ``Haus``.
UMLAUTS = {"ä": "a", "ö": "o", "ü": "u"}

#: The personal endings a conjugated verb adds, longest first so ``spieltest``
#: loses ``test`` before ``t`` and the stem keeps the letters it needs.
VERB_ENDINGS = ("test", "ten", "tet", "te", "st", "t", "e")

#: The endings an inflected adjective adds (``schön -> schöne, schöner, schönsten``).
ADJECTIVE_ENDINGS = ("sten", "ste", "er", "es", "em", "en", "e")

#: The endings a noun plural adds (``Auto -> Autos``, ``Frau -> Frauen``).
NOUN_ENDINGS = ("nen", "en", "er", "e", "n", "s")


def without_umlaut(text):
    """``text`` with every umlaut folded back to its base vowel."""
    result = ""
    for char in text:
        if char in UMLAUTS:
            result += UMLAUTS[char]
        else:
            result += char
    return result


def lookup_candidates(word):
    """The dictionary forms ``word`` could be an inflection of, best guess first.

    The word itself is never in the list: the caller tries the exact string first
    and only reaches for these guesses when nothing matched, so repeating it here
    would just be noise. The order matters -- the view stops at the first candidate
    that is a real entry -- so the most likely reading is built first.
    """
    guesses = []

    def add(guess):
        if not guess:
            return
        if guess.lower() == word.lower():
            return
        if guess in guesses:
            return
        guesses.append(guess)

    # A past participle carries a "ge" the infinitive does not have, so the verb
    # rules are tried on the word with and without that prefix ("gespielt").
    stems = [word]
    if word.startswith("ge") and len(word) > 4:
        stems.append(word[2:])

    for base in stems:
        for ending in VERB_ENDINGS:
            if not base.endswith(ending):
                continue
            stem = base[: -len(ending)]
            if len(stem) < 2:
                continue
            add(stem + "en")
            add(stem + "n")
            add("sich " + stem + "en")
            add("sich " + stem + "n")
            add(without_umlaut(stem) + "en")
            add(without_umlaut(stem) + "n")

    # A plural adds an ending and often an umlaut too ("das Buch, die Bücher"), so
    # the stem is tried plain and with the umlaut folded away.
    for ending in NOUN_ENDINGS:
        if not word.endswith(ending):
            continue
        stem = word[: -len(ending)]
        if len(stem) < 3:
            continue
        add(stem)
        add(without_umlaut(stem))

    for ending in ADJECTIVE_ENDINGS:
        if not word.endswith(ending):
            continue
        stem = word[: -len(ending)]
        if len(stem) < 3:
            continue
        add(stem)
        add(without_umlaut(stem))

    return guesses
