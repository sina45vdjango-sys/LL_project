"""Give the generated questions a reason, so a miss teaches something.

The runner already shows the right answer and, for a word, a card with the word's article,
plural, pronunciation and meaning. What it cannot show is *why*, and that is the piece a
learner actually needs on a miss. ``Question.explanation`` carries it, but the field is
almost empty: 5,339 of 5,428 questions had nothing in it, because the generators write
questions and nobody ever wrote prose for them.

The generated questions do not need prose, though — they need the fact they were built
from, and every one of them was built from a ``Word`` or a ``Sentence`` row. A meaning
drill was written from ``Word.meaning_fa``; an article drill from ``Word.article`` and its
gender; a plural drill from ``Word.plural``; a Perfekt drill from
``Word.perfect_auxiliary``; a dictation drill from the word it plays; a sentence drill from
the sentence's own two fields. So the explanation is not written here, it is **derived**
from the same row the question is about, and it therefore cannot disagree with the answer
it is explaining.

Why a separate command rather than teaching the ``seed_*`` generators:

* the generators **delete and rebuild**, and rebuilding is refused while learner attempts
  exist (``--yes-replace-history`` overrides that on purpose). Adding a sentence to a
  question that already exists is not worth deleting anybody's history for;
* this command is **additive**. It touches one field, writes nothing else, deletes nothing,
  and needs no migration — ``explanation`` has been on the model all along. Running it twice
  changes nothing, because a question that already has an explanation is left alone.

Two honest limits, both deliberate:

* it explains **only what the question's own rows say**. Where a fact cannot be derived —
  an authored question whose reasoning lives in a person's head, or a question whose word
  target is missing — the explanation is left empty and counted in the report. An invented
  reason is worse than no reason: the learner cannot tell which one they are reading;
* the two sentence directions that store no target are matched to their sentence by the
  text of the answer, against a map built once from the published ``Sentence`` rows. A text
  that more than one published sentence uses is treated as ambiguous and skipped rather than
  guessed at, so ``Sentence`` having no unique constraint on ``text`` cannot produce a wrong
  explanation.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from exercises.generated import (
    DICTATION_DRILL_PREFIX,
    LISTENING_DRILL_PREFIX,
    PRONUNCIATION_DRILL_PREFIX,
    SENTENCE_DRILL_PREFIX,
    generated_exercises,
)
from exercises.models import Question, QuestionTarget
from vocabulary.models import Sentence

#: The three prefixes of ``seed_a1_word_drills``. Which of its drills a question belongs to
#: is read from the rest of the title, because that command writes five different questions
#: under these three names and only the title says which is which.
WORD_PREFIXES = ["تمرین واژگان", "تمرین گرامر", "تمرین نوشتن"]

WRITING_PREFIX = "تمرین نوشتن"


class Command(BaseCommand):
    help = (
        "Fill Question.explanation on the generated drills, derived from the word or "
        "sentence each question was built from. Additive and idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report without writing.")

    def sentence_maps(self):
        """Two lookups into the published sentences, each built in one query.

        ``translation_by_text`` answers "what does this German sentence mean?" for the two
        sentence directions that store no target — their only handle on the sentence is the
        answer text. A text that more than one published sentence uses maps to ``None``, so
        the caller skips it instead of picking one of them at random.

        ``sentence_by_audio`` is the same join the seeds use to recognise a listening
        question: the file it plays is the sentence's own file, so the row is found by
        ``Sentence.audio`` rather than by guessing from the prompt.
        """
        translation_by_text = {}
        sentence_by_audio = {}

        for sentence in Sentence.objects.filter(is_published=True).order_by("pk"):
            if sentence.text not in translation_by_text:
                translation_by_text[sentence.text] = sentence.translation_fa
            else:
                translation_by_text[sentence.text] = None

            if sentence.audio:
                if sentence.audio.name not in sentence_by_audio:
                    sentence_by_audio[sentence.audio.name] = sentence

        return translation_by_text, sentence_by_audio

    def drill_kind(self, title):
        """Which question a generated title names.

        Read from the title because ``seed_a1_word_drills`` writes meaning, article, plural,
        Perfekt and writing drills under three prefixes, and the exercise *type* cannot tell
        them apart — an article drill and a meaning drill are both ``MULTIPLE_CHOICE``. The
        titles are the generators' own constants, so this reads the same strings the
        commands that write them use.
        """
        if title.startswith(DICTATION_DRILL_PREFIX):
            return "dictation"

        if title.startswith(PRONUNCIATION_DRILL_PREFIX):
            return "sound"

        if title.startswith(LISTENING_DRILL_PREFIX):
            return "listening"

        if title.startswith(SENTENCE_DRILL_PREFIX):
            if "مرتب کردن" in title:
                return "sentence_order"
            if "کدام جمله" in title:
                return "sentence_german"
            return "sentence_meaning"

        word_drill = False
        for prefix in WORD_PREFIXES:
            if title.startswith(prefix):
                word_drill = True

        if not word_drill:
            return ""

        if title.startswith(WRITING_PREFIX):
            return "writing"

        # The review lesson asks the same facts turned around, so each direction has a
        # reversed twin. Checked first, because a reversed title contains the forward word.
        if "وارون" in title:
            if "معنی" in title:
                return "meaning_reverse"
            if "آرتیکل" in title:
                return "article_reverse"
            if "جمع" in title:
                return "plural_reverse"
            if "Perfekt" in title:
                return "perfect_reverse"
            return ""

        if "معنی" in title:
            return "meaning"
        if "آرتیکل" in title:
            return "article"
        if "جمع" in title:
            return "plural"
        if "Perfekt" in title:
            return "perfect"

        return ""

    def explanation_for(self, question, kind, translation_by_text, sentence_by_audio):
        """The reason behind one question, or ``""`` when it cannot be derived.

        Empty is a real answer here and the caller counts it: a question whose rows have
        nothing to say is left alone rather than given a sentence that restates the answer.
        """
        word = None
        sentence = None

        for target in question.targets.all():
            if target.word_id is not None and target.role == QuestionTarget.Role.TESTED_ITEM:
                word = target.word
            if target.sentence_id is not None:
                sentence = target.sentence

        correct = ""
        wrong = []

        for answer in question.answers.all():
            if answer.is_correct:
                correct = answer.text
            else:
                wrong.append(answer.text)

        if word is not None:
            if kind == "meaning":
                return f"«{word.word}» یعنی «{word.meaning_fa}»."

            if kind == "meaning_reverse":
                return f"«{word.meaning_fa}» یعنی «{word.word}»."

            if kind == "article" and word.gender_label:
                return f"«{word.word}» {word.gender_label} است، پس «{word.article} {word.word}»."

            if kind == "article_reverse" and word.gender_label:
                return f"«{word.word}» {word.gender_label} است و با «{word.article}» می‌آید."

            if kind == "plural" and word.plural:
                return f"جمعِ «{word.article} {word.word}» می‌شود «{word.plural}»."

            if kind == "plural_reverse" and word.plural:
                return f"«{word.word}» مفردِ «{word.plural}» است."

            if kind == "perfect":
                return f"فعل «{word.word}» در Perfekt با «{correct}» می‌آید."

            if kind == "perfect_reverse":
                return f"فعل «{word.word}» در Perfekt با «{correct}» می‌آید."

            if kind == "writing":
                return f"ترجمهٔ «{word.meaning_fa}» به آلمانی «{word.word}» است."

            if kind == "dictation":
                return f"واژه‌ای که شنیدی «{word.word}» بود؛ یعنی «{word.meaning_fa}»."

        if kind == "sound" and wrong:
            return f"«{correct}» را شنیدی، نه «{wrong[0]}»؛ این دو فقط در یک صدا فرق دارند."

        if kind == "sentence_meaning" and sentence is not None:
            return f"«{sentence.text}» یعنی «{sentence.translation_fa}»."

        if kind == "sentence_german" or kind == "sentence_order":
            if correct in translation_by_text:
                meaning = translation_by_text[correct]
            else:
                meaning = None

            if meaning is not None:
                if kind == "sentence_order":
                    return f"ترتیب درست «{correct}» است؛ یعنی «{meaning}»."
                return f"«{correct}» یعنی «{meaning}»."

        if kind == "listening":
            if question.audio.name in sentence_by_audio:
                heard = sentence_by_audio[question.audio.name]
            else:
                heard = None

            if heard is not None:
                return f"جمله‌ای که شنیدی «{heard.text}» بود؛ یعنی «{heard.translation_fa}»."

        return ""

    def handle(self, *args, **options):
        translation_by_text, sentence_by_audio = self.sentence_maps()

        questions = (
            Question.objects.filter(exercise__in=generated_exercises())
            .select_related("exercise")
            .prefetch_related("answers", "targets__word", "targets__sentence")
            .order_by("pk")
        )

        already = 0
        written = 0
        per_kind = {}
        skipped = {}

        for question in questions:
            # A question that already carries an explanation is left exactly as it is, which
            # is what makes a second run change nothing.
            if question.explanation:
                already += 1
                continue

            kind = self.drill_kind(question.exercise.title)
            text = self.explanation_for(question, kind, translation_by_text, sentence_by_audio)

            if not text:
                if kind in skipped:
                    skipped[kind] = skipped[kind] + 1
                else:
                    skipped[kind] = 1
                continue

            if kind in per_kind:
                per_kind[kind] = per_kind[kind] + 1
            else:
                per_kind[kind] = 1

            if not options["dry_run"]:
                question.explanation = text
                question.save(update_fields=["explanation"])

            written += 1

        for kind in sorted(per_kind):
            self.stdout.write(f"  {kind}: {per_kind[kind]}")

        if skipped:
            self.stdout.write("Left without an explanation, by kind:")
            for kind in sorted(skipped):
                self.stdout.write(f"  {kind or '(unrecognised title)'}: {skipped[kind]}")

        self.stdout.write(f"Already had an explanation: {already}.")

        if options["dry_run"]:
            self.stdout.write(f"Dry run: would write {written} explanation(s).")
            return

        self.stdout.write(f"Wrote {written} explanation(s).")
