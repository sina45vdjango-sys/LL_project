"""Which exercises a management command wrote, rather than a person.

Every generator marks its own exercises with a Persian title prefix and rebuilds only what
carries that prefix, so each command already knows its own content. Two questions need the
whole list, though, and they are why this module exists:

* ``seed_a1_word_drills`` asks "does this word already have a question?" before it writes a
  meaning drill, and the only questions it must not write again are the **authored** ones. A
  word that has a generated drill of another kind — spelled by ear, told apart by sound — has
  not been asked what it means, so that question must still be written. The dictation drills
  do tag the word they play (they have to, or a miss could never be reviewed), so without
  this distinction the word drills would see nearly every word as already asked and quietly
  stop writing meaning questions.
* ``seed_a1_exercises`` used to rebuild by exercise *type* — every ``LISTENING`` exercise —
  which also swept up the drills the other generators write in that type. It now scopes
  itself to its own title; the difference between the two is exactly this list.

No hand-written exercise uses any of these prefixes. The listening title is the one that also
appears in ``exercises/data/a1_exercises.json``, because that export contains the listening
generator's own output — nothing was written by hand under that name.
"""

from django.db.models import Q

from exercises.models import Exercise

#: ``seed_a1_word_drills``: what a word means, its article, its plural, its auxiliary, and
#: the word written from its Persian meaning.
WORD_DRILL_PREFIXES = ["تمرین واژگان", "تمرین گرامر", "تمرین نوشتن"]

#: ``seed_a1_sentence_drills``: a sentence's meaning, and which sentence was heard.
SENTENCE_DRILL_PREFIX = "تمرین جمله"

#: ``seed_a1_pronunciation_drills``: hear which of two words one sound apart was played.
PRONUNCIATION_DRILL_PREFIX = "تمرین تلفظ"

#: ``seed_a1_dictation_drills``: write the word that was played.
DICTATION_DRILL_PREFIX = "تمرین املا"

#: ``seed_a1_reading_drills``: which line of the text carries a meaning, and which sentence
#: is not in the text.
READING_DRILL_PREFIX = "تمرین خواندن"

#: ``seed_a1_exercises``: the listening exercise built from a lesson's own sentences.
LISTENING_DRILL_PREFIX = "شنیدن: جمله‌های این درس"

#: Every prefix above, built from the names so a new family is added in one place.
TITLE_PREFIXES = WORD_DRILL_PREFIXES + [
    SENTENCE_DRILL_PREFIX,
    PRONUNCIATION_DRILL_PREFIX,
    DICTATION_DRILL_PREFIX,
    READING_DRILL_PREFIX,
    LISTENING_DRILL_PREFIX,
]


def generated_exercises():
    """Every exercise a management command wrote, matched by its title prefix."""
    query = Q()

    for prefix in TITLE_PREFIXES:
        query = query | Q(title__startswith=prefix)

    return Exercise.objects.filter(query)
