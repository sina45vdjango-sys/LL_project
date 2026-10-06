"""Turn each lesson's own words into questions, so every word — and its grammar — can be practised.

The course teaches 1,008 words, but only 138 of them are the ``TESTED_ITEM`` of some
question. That number is the whole problem: ``WordProgress`` only moves when a word is
really tested (``vocabulary/progress.py``), and ``vocabulary/review.py`` can only offer
an exercise that tests the word the learner missed. For the other 870 words the product
can show the word and nothing else — no question, no progress, no review.

This command closes that gap from the content that is already there. It reads, per
lesson, the words that lesson introduces (``LessonWord`` with ``role=NEW`` — 1,008 links
covering all 1,008 words, so every word is introduced exactly once) and writes five
drills, all of them from facts the ``Word`` row already stores:

1. **معنی** — «واژهٔ X به چه معنی است؟», four Persian options; the wrong ones come from
   the same lesson's own words, so they are a plausible confusion rather than a random
   one. Tests a word and nothing else.
2. **آرتیکل** — «___ X», options ``der`` / ``die`` / ``das``, from ``Word.article``.
3. **جمع** — «جمعِ „der Abend“ کدام است؟», four options from ``Word.plural``.
4. **Perfekt** — «فعل X در Perfekt با کدام فعل کمکی می‌آید؟», options ``haben`` / ``sein``,
   from ``Word.perfect_auxiliary``.
5. **نوشتن** — «ترجمهٔ „ماشین“ به آلمانی؟», typed rather than chosen. Recognition is not
   production: a learner can pick ``Auto`` out of four options without being able to
   write it, so every word gets asked for in the other direction too. This one is a
   ``TRANSLATION`` exercise with no wrong options, which is what makes the runner ask
   for typing instead of options, and the accepted answers are the bare words — the same
   shape the authored «ترجمهٔ … به آلمانی؟» questions already use (``Land``, not
   ``das Land``), so both kinds of typed question are graded the same way.

   A Persian gloss often names more than one German word (``مادربزرگ`` is both ``Oma``
   and ``Großmutter``, ``شروع کردن`` both ``anfangen`` and ``beginnen``). The question
   therefore accepts **every taught German word that carries the same gloss** as a
   correct answer, because marking ``Oma`` wrong when the learner was asked for
   ``مادربزرگ`` punishes a learner for being right. ``grading.py`` already compares a
   typed answer against every correct row, and the runner now calls a question typed
   whenever it has no wrong option — so this needed no new field, only more honest rows.

Drills 2–4 are grammar, and they are **tagged to the grammar topic they really test** —
``Artikel: der, die, das und ein, eine, ein``, ``Der Plural der Nomen`` and one of the two
``Perfekt`` topics. That is the honest half of this command: the authored questions could
not be tagged, because a question's grammar topic is not stored anywhere and a lesson
teaches three or four topics, so any lesson-level tag would make "grammar accuracy" a
relabelled copy of vocabulary accuracy. A generated question *does* know which rule it
asks about, so the tag belongs to the question that was built for the rule.

The three grammar drills are built **only in the lessons that teach the rule**, read from
the lesson's own ``LessonGrammar`` links. Lesson 4 introduces «Artikel: der, die, das und
ein, eine, ein» and «Der Plural der Nomen», so lesson 4 asks about articles and plurals;
lesson 1 never does, so it never asks. Before this rule every lesson asked about articles,
plurals and Perfekt, which meant lesson 1 opened with a Perfekt question about a rule the
course introduces in lesson 17 — practice that did not match the teaching. A lesson may
also be drilled on a rule taught earlier in the course when the lesson's own job is asking
again (see ``revisits_earlier_material``), so the two review lessons keep their drills and
lesson 12 is asked about articles — taught in lesson 4 — but not about Perfekt, which the
course has not reached yet. A lesson with no grammar link at all is drilled on nothing
but the words themselves, which is the honest answer: nothing in the data says it teaches
a rule, and guessing one would put a claim on the readiness page that the content does not
make.

A lesson that introduces no word at all is a **review lesson**. It drills the words it
**revisits** (``LessonWord`` with ``role=REVIEW`` — 40 words in lesson 12,
«Wiederholung A1.1: Das kann ich jetzt»), because the drill is defined as "the words this
lesson introduces" and a review lesson would otherwise have nothing to practise in the one
lesson whose whole job is to ask again what came before it.

It does not ask those words the same way, though. Every one of them already has its forward
drills from the lesson that introduced it, so repeating them would be the same question
twice — the repetition the learner cannot learn from. A review lesson therefore gets the
**turned-around** version instead: a Persian meaning with German options, an article asking
which noun takes it, a plural asking for its singular, and an auxiliary asking which verb
takes it. Recognising a word from its meaning is a different skill from recognising its
meaning, so the second pass is practice rather than a rerun. The typed translation has no
such reversal — the only other direction is typing Persian, which grades badly — so it is
left out of the review.

Two rules about not repeating what exists:

* a word that already has an **authored** question gets no meaning question — the authored
  «واژگان — انتخاب معنی» exercises already cover 138 words, and writing those again would be
  duplicate content, not more practice. A question another *generator* wrote does not count:
  a word with a dictated or a sound drill has not been asked what it means;
* a word that already has a **typed** question of its own gets no writing question
  either, for the same reason: the authored «ترجمهٔ … به آلمانی؟» questions are the same
  task.

No generated drill counts as covering its own words, or a second run would read its own
output as existing content and build almost nothing. That is why every "what is already
covered" query excludes the generated exercises through ``generated_exercises()``
(``exercises/generated.py``) rather than repeating a prefix comparison in each place — and
why a drill written by *another* generator is never mistaken for an authored question.

Batching never changes *which* questions exist, only how they are split: the options of a
question come from the lesson's whole word list and their position is offset by the
word's id, so ``--batch`` can be tuned freely and the same content always produces the
same exercises. Offset also matters inside one exercise — always reading the pool from
the front would hand every question the same wrong options, which is learnable without
learning the word.

A question is dropped rather than written without honest wrong options: a lesson that
introduces fewer than four words is skipped, and a plural question is left out when the
lesson cannot supply three different plural forms to offer beside the right one. Every
live lesson introduces at least 27 words, so this only guards the rule.

**This command deletes and rebuilds.** What it wrote last time is removed first — only
its own exercises, identified by the title prefixes in ``TITLE_PREFIXES``, which no
authored exercise uses. Running it twice does not double the content. Deleting an
exercise cascades to its questions (and an ``ExerciseAttempt`` points at both), so a
learner's recorded attempts *on a generated drill* go with it; attempts on authored
exercises are untouched. Rebuilding is therefore refused while any such attempt exists,
and ``--yes-replace-history`` allows it on purpose and says how much history it deletes.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max, Q

from exercises.generated import generated_exercises
from exercises.models import Answer, Exercise, ExerciseAttempt, Question, QuestionTarget
from lessons.models import Lesson, LessonWord
from vocabulary.models import Grammar, Word

#: Options per question whose answers are text (meaning, plural). Four is what the
#: authored «واژگان — انتخاب معنی» questions use.
OPTIONS = 4

#: The three articles, in the order a German dictionary lists them.
ARTICLES = ["der", "die", "das"]

#: The two perfect auxiliaries. There are only ever two, so this drill offers two options
#: rather than padding the choice with a third that cannot be right.
AUXILIARIES = ["haben", "sein"]

#: Questions per exercise. A little more than the authored six, and small enough that one
#: exercise is a sitting rather than a chore.
BATCH = 10

#: Every exercise this command writes starts with one of these, and no authored exercise
#: does — the authored ones are called «واژگان — انتخاب معنی», «درست / غلط», «تمرین تکمیل
#: جمله» and so on. It is what marks a generated drill for the rebuild, and one list so a
#: new family cannot be added without the rebuild, the history gate and the "what is
#: already covered" checks all seeing it.
WORD_PREFIX = "تمرین واژگان"
GRAMMAR_PREFIX = "تمرین گرامر"
WRITING_PREFIX = "تمرین نوشتن"
TITLE_PREFIXES = [WORD_PREFIX, GRAMMAR_PREFIX, WRITING_PREFIX]

MEANING_TITLE = "تمرین واژگان — معنی"
ARTICLE_TITLE = "تمرین گرامر — آرتیکل"
PLURAL_TITLE = "تمرین گرامر — جمع"
PERFECT_TITLE = "تمرین گرامر — Perfekt"
WRITING_TITLE = "تمرین نوشتن — واژه"

MEANING_INSTRUCTION = "یک گزینهٔ درست برای معنی واژهٔ زیر انتخاب کنید."
ARTICLE_INSTRUCTION = "آرتیکل درست (der / die / das) را انتخاب کنید."
PLURAL_INSTRUCTION = "جمعِ درست را انتخاب کنید."
PERFECT_INSTRUCTION = "فعل کمکی درست برای Perfekt را انتخاب کنید."
WRITING_INSTRUCTION = "معنی فارسی را به آلمانی بنویسید (اسم‌ها بدون حرف تعریف)."

#: The review lesson asks its words again, turned around, so its drills are named apart
#: from the forward ones. Every title still starts with one of ``TITLE_PREFIXES``, so the
#: rebuild recognises a review drill as this command's own content like any other.
REVIEW_MEANING_TITLE = "تمرین واژگان — معنی وارون"
REVIEW_ARTICLE_TITLE = "تمرین گرامر — آرتیکل وارون"
REVIEW_PLURAL_TITLE = "تمرین گرامر — جمع وارون"
REVIEW_PERFECT_TITLE = "تمرین گرامر — Perfekt وارون"

REVIEW_MEANING_INSTRUCTION = "واژهٔ آلمانی درست را برای این معنی انتخاب کنید."
REVIEW_ARTICLE_INSTRUCTION = "واژه‌ای را انتخاب کنید که با این آرتیکل می‌آید."
REVIEW_PLURAL_INSTRUCTION = "شکل مفردِ این جمع کدام است؟"
REVIEW_PERFECT_INSTRUCTION = "فعلی را انتخاب کنید که در Perfekt با این فعل کمکی می‌آید."

#: The grammar topic each drill is tagged with, by the topic's own title in the database.
#: The command looks them up and refuses to run when one is missing, rather than writing a
#: target that points at nothing — a tag that named a rule the content no longer teaches
#: would put an invented number on the readiness page. The titles also decide *where* a
#: drill may be built: only a lesson that teaches (or is revising) the rule gets it.
ARTIKEL_TOPIC = "Artikel: der, die, das und ein, eine, ein"
PLURAL_TOPIC = "Der Plural der Nomen"
PERFEKT_HABEN_TOPIC = "Perfekt mit „haben“"
PERFEKT_SEIN_TOPIC = "Perfekt mit „sein“: Reisen in der Vergangenheit"

#: A lesson whose own grammar topics are named like this is the course's closing revision
#: («Wiederholung: Verbformen im Überblick» in lesson 24), so it may be asked about every
#: rule the course has taught by then even though it teaches no rule of its own.
REVISION_TOPIC_PREFIX = "Wiederholung"

#: The most words one lesson's batteries drill as new. A lesson may **teach** more — lesson
#: 24's closing word bank is deliberately larger, and a topic lesson lists the whole topic —
#: but no lesson asks five questions about every one of a hundred words. That was a wall, not
#: practice, and it was the last thing between a learner and the end of a lesson.
#:
#: Capping the drills costs no content: the words beyond the cap stay on the lesson page and
#: **every** linked word the learner has reached and never practised is offered by
#: ``vocabulary/schedule.py::new_words``, which is what puts them in the review queue. The cap
#: decides how much a lesson asks in one sitting, not which words exist.
MAX_DRILL_WORDS = 30


def owned_exercises():
    """Every exercise this command owns — everything under its own title prefixes."""
    query = Q()

    for prefix in TITLE_PREFIXES:
        query = query | Q(title__startswith=prefix)

    return Exercise.objects.filter(query)


class Command(BaseCommand):
    help = "Build per-lesson vocabulary, grammar and writing drills from the words each lesson teaches."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report without writing.")
        parser.add_argument(
            "--batch",
            type=int,
            default=BATCH,
            help="Questions per exercise. Only changes how the questions are split.",
        )
        parser.add_argument(
            "--lesson",
            type=int,
            default=0,
            help="Only this lesson id. Zero means every published lesson.",
        )
        parser.add_argument(
            "--yes-replace-history",
            action="store_true",
            help="Also delete the stored attempts that belong to the drills being replaced.",
        )

    def grammar_topics(self):
        """The four grammar topics the drills are tagged with.

        Refuses rather than skipping when one is missing: on a database where the grammar
        has not been seeded yet, running on would write the word drills with no grammar
        tags and quietly leave the grammar half of the page empty.
        """
        wanted = [
            ("artikel", ARTIKEL_TOPIC),
            ("plural", PLURAL_TOPIC),
            ("haben", PERFEKT_HABEN_TOPIC),
            ("sein", PERFEKT_SEIN_TOPIC),
        ]

        topics = {}

        for key, title in wanted:
            topic = Grammar.objects.filter(title=title).first()
            if topic is None:
                raise CommandError(
                    f"Grammar topic {title!r} does not exist. Run seed_a1_course first."
                )
            topics[key] = topic

        return topics

    def asked_words(self, exercise_type=None):
        """The ids of the words that already have an **authored** question.

        Generated drills do not count, and that is the whole point: a word that has a
        dictation drill or a sound drill has not been asked what it means, so it still gets
        its meaning question. Only what a person wrote — and this command's own previous
        output — is left out of the pool.

        With ``exercise_type``, only the questions of that exercise type are counted — used
        for the writing drill, where a typed question of the authored kind is the same task
        and must not be written again.
        """
        targets = QuestionTarget.objects.filter(
            role=QuestionTarget.Role.TESTED_ITEM, word__isnull=False
        ).exclude(question__exercise__in=generated_exercises())

        if exercise_type is not None:
            targets = targets.filter(question__exercise__type=exercise_type)

        word_ids = set()
        for word_id in targets.values_list("word_id", flat=True):
            word_ids.add(word_id)

        return word_ids

    def wrong_options(self, correct, candidates, start):
        """Three wrong options for ``correct``, or ``None`` when the pool is too small.

        The scan starts at ``start`` and wraps around. Always reading the pool from the
        front would hand every question of a lesson the same three wrong answers, which a
        learner can learn to pattern-match instead of learning the words; the offset is the
        word's own id, so the variation is real but still reproducible.
        """
        if not candidates:
            return None

        wrong = []
        index = start % len(candidates)
        tries = 0

        while len(wrong) < OPTIONS - 1 and tries < len(candidates):
            text = candidates[index]
            if text != correct and text not in wrong:
                wrong.append(text)

            index += 1
            if index == len(candidates):
                index = 0
            tries += 1

        if len(wrong) < OPTIONS - 1:
            return None
        return wrong

    def option_rows(self, correct, wrong, slot):
        """The options in display order, the correct one in slot ``slot`` (1-based).

        The slot comes from the word's id, so the right answer is not always in the same
        place — while still being decided by the data, so two runs on the same content
        agree.
        """
        options = []
        wrong_index = 0

        for position in range(1, len(wrong) + 2):
            if position == slot:
                options.append((correct, True))
            else:
                options.append((wrong[wrong_index], False))
                wrong_index += 1

        return options

    def lesson_topics(self, lesson):
        """The titles of the grammar topics this lesson itself teaches.

        Read from ``LessonGrammar``, which is where the course says which rule a lesson
        teaches — the same link the lesson page renders its grammar block from. Nothing
        here is guessed from the lesson title.
        """
        titles = set()

        for link in lesson.lesson_grammars.select_related("grammar"):
            titles.add(link.grammar.title)

        return titles

    def revisits_earlier_material(self, lesson, own_topics):
        """Whether this lesson's job is asking again what the course taught before it.

        Two shapes do that. A lesson that introduces no new word is a review lesson
        (lesson 12, «Wiederholung A1.1») — ``is_review_lesson`` already names it. And a
        lesson whose own topics are called «Wiederholung: …» is the closing revision
        (lesson 24), which does introduce the words of its closing word bank and so is not
        a review lesson, but still asks about rules from the whole course.
        """
        if self.is_review_lesson(lesson):
            return True

        for title in own_topics:
            if title.startswith(REVISION_TOPIC_PREFIX):
                return True

        return False

    def allowed_topics(self, lesson, own_topics, taught_before):
        """The grammar topics this lesson may be drilled on, by title.

        A lesson is drilled on the rules it teaches and on nothing else. Asking about the
        plural of a noun in a lesson that never introduced the plural, or about Perfekt in
        lesson 1, is practice that does not match the teaching — the audit's P-19, where
        "article/plural in every lesson" was the noise that hid the missing grammar
        practice. A lesson that is revising may also be drilled on every rule the course has
        taught by the time it arrives, which is what keeps lesson 12 and lesson 24 useful.

        ``taught_before`` is the set of topic titles the earlier lessons in the course
        teach; the caller accumulates it in course order.
        """
        allowed = set(own_topics)

        if not self.revisits_earlier_material(lesson, own_topics):
            return allowed

        for title in taught_before:
            allowed.add(title)

        return allowed

    def is_review_lesson(self, lesson):
        """Whether this lesson introduces no new word and reviews the ones before it.

        ``published_words`` makes the same distinction for where it reads the words from;
        this names it, because ``lesson_plan`` has to change *what it builds* for a review
        lesson, not only where it reads the words from.
        """
        return not lesson.lesson_words.filter(role=LessonWord.Role.NEW).exists()

    def published_words(self, lesson):
        """The words this lesson should drill, in the order the lesson lists them.

        Normally that is the words it *introduces* (``role=NEW``). A lesson that introduces no
        word is a **review lesson** — lesson 12, «Wiederholung A1.1» — and for it the words
        are the ones it *revisits* (``role=REVIEW``), which is what the lesson is for. Without
        this fallback the learner reaches the middle of the course and finds nothing to
        practise, because a drill built from "the words this lesson introduces" has nothing
        to read there.

        The list is cut at ``MAX_DRILL_WORDS``. The lesson's own order is the order it teaches
        in, so the words the lesson leans on come first and the tail — the part a learner is
        least likely to hold on to anyway — is what waits for the review queue.
        """
        links = lesson.lesson_words.filter(
            role=LessonWord.Role.NEW, word__is_published=True
        )

        if not links.exists():
            links = lesson.lesson_words.filter(
                role=LessonWord.Role.REVIEW, word__is_published=True
            )

        words = []
        for link in links.select_related("word").order_by("order", "pk"):
            words.append(link.word)

        return words[:MAX_DRILL_WORDS]

    def meaning_questions(self, words, pool, asked):
        """One meaning question per word the lesson introduces that nothing asks about yet.

        ``asked`` is the set of word ids that already have a question this command did not
        write, read once before anything is written.
        """
        questions = []

        for word in words:
            if word.pk in asked:
                continue

            wrong = self.wrong_options(word.meaning_fa, pool, word.pk)
            if wrong is None:
                continue

            questions.append(
                {
                    "word": word,
                    "prompt": f"واژهٔ «{word.word}» به چه معنی است؟",
                    "correct": word.meaning_fa,
                    "wrong": wrong,
                    "slot": (word.pk % OPTIONS) + 1,
                    "grammar": None,
                }
            )

        return questions

    def synonyms_by_meaning(self):
        """``{Persian gloss: [German word, ...]}`` for the words that share a gloss.

        One gloss, several German words is normal — ``مادربزرگ`` is ``Oma`` and
        ``Großmutter`` — and asking a learner to type *one* of them while grading the
        other wrong is the unfairness this map exists to prevent. Every **published**
        word counts, not only the words of one level: a correct German translation is
        correct whatever level the bank files it under, so a synonym the learner happens
        to know must not turn a right answer into a wrong one.
        """
        by_meaning = {}

        for word in Word.objects.filter(is_published=True).order_by("pk"):
            if word.meaning_fa not in by_meaning:
                by_meaning[word.meaning_fa] = []
            if word.word not in by_meaning[word.meaning_fa]:
                by_meaning[word.meaning_fa].append(word.word)

        return by_meaning

    def writing_questions(self, words, asked, synonyms):
        """One typed question per word the lesson introduces that has no typed question.

        The accepted answers are the bare words, without the article, which is exactly
        what the authored «ترجمهٔ … به آلمانی؟» questions accept. Every German word of the
        same level that carries the same Persian gloss is accepted too, so a correct
        answer is never marked wrong because the course also teaches a synonym.
        """
        questions = []

        for word in words:
            if word.pk in asked:
                continue

            # Compared lower-cased, because ``Deutsch`` and ``deutsch`` are one accepted
            # answer and writing both would put a duplicate option on the question.
            accepted = [word.word]
            lowered = [word.word.lower()]

            if word.meaning_fa in synonyms:
                for other in synonyms[word.meaning_fa]:
                    if other.lower() in lowered:
                        continue
                    lowered.append(other.lower())
                    accepted.append(other)

            questions.append(
                {
                    "word": word,
                    "prompt": f"ترجمهٔ «{word.meaning_fa}» به آلمانی؟",
                    "correct": word.word,
                    # Every accepted spelling, the word's own first so the order is stable.
                    "accepted": accepted,
                    "wrong": [],
                    "slot": 1,
                    "grammar": None,
                }
            )

        return questions

    def article_questions(self, words, topic):
        """One article question per noun the lesson introduces that has an article.

        A noun with no article is skipped instead of guessed at: ``der`` / ``die`` /
        ``das`` is the whole question, so there is nothing honest to ask about a word that
        has none.
        """
        questions = []

        for word in words:
            if word.word_type != Word.WordType.NOUN:
                continue
            if not word.article:
                continue

            wrong = []
            for article in ARTICLES:
                if article != word.article:
                    wrong.append(article)

            questions.append(
                {
                    "word": word,
                    "prompt": f"آرتیکل درست کدام است؟ «___ {word.word}» ({word.meaning_fa})",
                    "correct": word.article,
                    "wrong": wrong,
                    "slot": (word.pk % len(ARTICLES)) + 1,
                    "grammar": topic,
                }
            )

        return questions

    def plural_questions(self, words, pool, topic):
        """One plural question per noun the lesson introduces that has a plural form.

        ``pool`` is every plural the lesson teaches, so the wrong options are other nouns
        of the same lesson and the learner is choosing between real plural shapes (``die
        Abende`` against ``die Namen``, not against a word that is not a plural at all).
        """
        questions = []

        for word in words:
            if word.word_type != Word.WordType.NOUN:
                continue
            if not word.plural:
                continue

            # A plural-only noun keeps the same written form (``die Eltern``), so the
            # prompt «جمعِ „die Eltern“ کدام است؟» would already contain its own answer.
            # There is nothing to test, so the question is left out.
            if word.plural == f"{word.article} {word.word}":
                continue

            wrong = self.wrong_options(word.plural, pool, word.pk)
            if wrong is None:
                continue

            questions.append(
                {
                    "word": word,
                    "prompt": f"جمعِ «{word.article} {word.word}» کدام است؟",
                    "correct": word.plural,
                    "wrong": wrong,
                    "slot": (word.pk % OPTIONS) + 1,
                    "grammar": topic,
                }
            )

        return questions

    def perfect_questions(self, words, haben, sein, allowed):
        """One Perfekt question per verb the lesson introduces that has an auxiliary.

        The topic tagged is the one the right answer belongs to: a verb that takes ``sein``
        is exercising the ``sein`` rule, so that is the rule the learner is being asked
        about — tagging it with both would count one submission against two topics.

        A verb whose rule the lesson does not teach (nor revise) is skipped rather than
        asked: lesson 17 introduces «Perfekt mit „sein“: Reisen in der Vergangenheit» and
        lesson 19 «Perfekt mit „haben“», so neither asks about the other's auxiliary.
        """
        questions = []

        for word in words:
            if word.word_type != Word.WordType.VERB:
                continue
            if not word.perfect_auxiliary:
                continue

            # The verb names itself in the prompt, so a verb whose own name is the
            # auxiliary (``sein``, ``haben``) or ends in it (``an sein``, ``zu sein``)
            # hands the answer over. There is nothing to test, so it is skipped.
            if word.perfect_auxiliary == Word.PerfectAuxiliary.SEIN:
                correct = "sein"
                topic = sein
            else:
                correct = "haben"
                topic = haben

            if correct in word.word.split():
                continue

            if topic.title not in allowed:
                continue

            wrong = []
            for auxiliary in AUXILIARIES:
                if auxiliary != correct:
                    wrong.append(auxiliary)

            questions.append(
                {
                    "word": word,
                    "prompt": f"فعل «{word.word}» در Perfekt با کدام فعل کمکی می‌آید؟",
                    "correct": correct,
                    "wrong": wrong,
                    "slot": (word.pk % len(AUXILIARIES)) + 1,
                    "grammar": topic,
                }
            )

        return questions

    def review_meaning_questions(self, words):
        """The forward meaning drill turned around: a Persian meaning, German options.

        The forward drill shows a German word and asks for its meaning. A review lesson
        cannot ask that again — the word was already asked that way when it was introduced
        — so it asks the other direction instead. Recognising a word from its meaning is a
        different task from recognising its meaning, which is why the review is not simply
        the old question twice.
        """
        pool = []
        for word in words:
            pool.append(word.word)

        questions = []

        for word in words:
            wrong = self.wrong_options(word.word, pool, word.pk)
            if wrong is None:
                continue

            questions.append(
                {
                    "word": word,
                    "prompt": f"کدام واژهٔ آلمانی معنی «{word.meaning_fa}» را می‌رساند؟",
                    "correct": word.word,
                    "wrong": wrong,
                    "slot": (word.pk % OPTIONS) + 1,
                    "grammar": None,
                }
            )

        return questions

    def review_article_questions(self, words, topic):
        """The article drill turned around: an article, and the noun that takes it.

        The wrong options are nouns of the *other* articles, so exactly one option takes
        the article asked about. Reading the article off a noun and naming a noun from its
        article are different ways of knowing the same fact, which is what makes this a
        review rather than a repeat.
        """
        questions = []

        for word in words:
            if word.word_type != Word.WordType.NOUN:
                continue
            if not word.article:
                continue

            candidates = []
            for candidate in words:
                if candidate.word_type != Word.WordType.NOUN:
                    continue
                if candidate.article == word.article:
                    continue
                candidates.append(candidate.word)

            wrong = self.wrong_options(word.word, candidates, word.pk)
            if wrong is None:
                continue

            questions.append(
                {
                    "word": word,
                    "prompt": f"کدام واژه با آرتیکل «{word.article}» می‌آید؟",
                    "correct": word.word,
                    "wrong": wrong,
                    "slot": (word.pk % OPTIONS) + 1,
                    "grammar": topic,
                }
            )

        return questions

    def review_plural_questions(self, words, topic):
        """The plural drill turned around: a plural, and the noun it belongs to.

        Knowing the plural of a noun and recognising the noun from its plural are the two
        directions of the same fact, and the forward direction was already asked.
        """
        questions = []

        for word in words:
            if word.word_type != Word.WordType.NOUN:
                continue
            if not word.plural:
                continue

            # A noun whose plural is its own singular written again (``der Morgen`` →
            # ``die Morgen``) would show the answer inside its own prompt — «مفردِ „die
            # Morgen“» — so there is nothing to ask.
            if word.word in word.plural.split():
                continue

            candidates = []
            for candidate in words:
                if candidate.word_type != Word.WordType.NOUN:
                    continue
                if candidate.word == word.word:
                    continue
                candidates.append(candidate.word)

            wrong = self.wrong_options(word.word, candidates, word.pk)
            if wrong is None:
                continue

            questions.append(
                {
                    "word": word,
                    "prompt": f"مفردِ «{word.plural}» کدام است؟",
                    "correct": word.word,
                    "wrong": wrong,
                    "slot": (word.pk % OPTIONS) + 1,
                    "grammar": topic,
                }
            )

        return questions

    def review_perfect_questions(self, words, haben, sein, allowed):
        """The Perfekt drill turned around: an auxiliary, and a verb that takes it.

        The wrong options are verbs of the *other* auxiliary, so exactly one option takes
        the auxiliary asked about. Like the forward drill, it is only built for an
        auxiliary whose rule the lesson teaches or is revising.
        """
        questions = []

        for word in words:
            if word.word_type != Word.WordType.VERB:
                continue
            if not word.perfect_auxiliary:
                continue

            if word.perfect_auxiliary == Word.PerfectAuxiliary.SEIN:
                auxiliary = "sein"
                topic = sein
                opposite = Word.PerfectAuxiliary.HABEN
            else:
                auxiliary = "haben"
                topic = haben
                opposite = Word.PerfectAuxiliary.SEIN

            # The auxiliary is named in the prompt, so a verb whose own name is that
            # auxiliary would hand the answer over. The forward drill skips these too.
            if auxiliary in word.word.split():
                continue

            if topic.title not in allowed:
                continue

            candidates = []
            for candidate in words:
                if candidate.word_type != Word.WordType.VERB:
                    continue
                if candidate.perfect_auxiliary != opposite:
                    continue
                candidates.append(candidate.word)

            wrong = self.wrong_options(word.word, candidates, word.pk)
            if wrong is None:
                continue

            questions.append(
                {
                    "word": word,
                    "prompt": f"کدام فعل در Perfekt با «{auxiliary}» می‌آید؟",
                    "correct": word.word,
                    "wrong": wrong,
                    "slot": (word.pk % OPTIONS) + 1,
                    "grammar": topic,
                }
            )

        return questions

    def distinct_meanings(self, words):
        """Every different Persian meaning among ``words``, in lesson order.

        Duplicates are dropped rather than repeated: two options with the same text would
        make one of them a second correct answer.
        """
        meanings = []

        for word in words:
            if word.meaning_fa not in meanings:
                meanings.append(word.meaning_fa)

        return meanings

    def distinct_plurals(self, words):
        """Every different plural form among ``words``, in lesson order, blanks dropped."""
        plurals = []

        for word in words:
            if not word.plural:
                continue
            if word.plural not in plurals:
                plurals.append(word.plural)

        return plurals

    def batches(self, questions, batch):
        """The questions split into exercises of ``batch`` questions each."""
        parts = []

        for start in range(0, len(questions), batch):
            parts.append(questions[start : start + batch])

        return parts

    def lesson_plan(self, lesson, batch, topics, asked_anywhere, asked_typed, synonyms, allowed):
        """The exercises this lesson should get, already split into batches.

        ``allowed`` holds the titles of the grammar rules this lesson may be drilled on
        (``allowed_topics``); the meaning and writing drills are built for every word the
        lesson teaches and are not gated, because a word's meaning is always its own
        lesson's teaching.

        A lesson that neither introduces nor revisits a word returns an empty list rather
        than an empty exercise.
        """
        words = self.published_words(lesson)

        if not words:
            return []

        if self.is_review_lesson(lesson):
            # A review lesson revisits words that already have their forward drills, so the
            # same questions would be the same question twice. Each review drill is turned
            # around instead (a meaning with German options, an article asking for the noun)
            # and the typed translation is left out, because it cannot be reversed without
            # asking the learner to type Persian, which grades badly.
            # The reversed meaning question is built for every review lesson: it tests the
            # words the lesson revisits, not a rule.
            drills = [
                (
                    REVIEW_MEANING_TITLE,
                    Exercise.ExerciseType.MULTIPLE_CHOICE,
                    REVIEW_MEANING_INSTRUCTION,
                    self.review_meaning_questions(words),
                ),
            ]

            # The reversed grammar drills follow the same rule as the forward ones: only a
            # rule the course has taught by the time this lesson arrives.
            if ARTIKEL_TOPIC in allowed:
                drills.append(
                    (
                        REVIEW_ARTICLE_TITLE,
                        Exercise.ExerciseType.MULTIPLE_CHOICE,
                        REVIEW_ARTICLE_INSTRUCTION,
                        self.review_article_questions(words, topics["artikel"]),
                    )
                )

            if PLURAL_TOPIC in allowed:
                drills.append(
                    (
                        REVIEW_PLURAL_TITLE,
                        Exercise.ExerciseType.MULTIPLE_CHOICE,
                        REVIEW_PLURAL_INSTRUCTION,
                        self.review_plural_questions(words, topics["plural"]),
                    )
                )

            if PERFEKT_HABEN_TOPIC in allowed or PERFEKT_SEIN_TOPIC in allowed:
                drills.append(
                    (
                        REVIEW_PERFECT_TITLE,
                        Exercise.ExerciseType.MULTIPLE_CHOICE,
                        REVIEW_PERFECT_INSTRUCTION,
                        self.review_perfect_questions(
                            words, topics["haben"], topics["sein"], allowed
                        ),
                    )
                )
        else:
            # Every meaning and every plural the lesson teaches, in lesson order. The wrong
            # options are drawn from here, so they are words of the same lesson.
            meanings = self.distinct_meanings(words)
            plurals = self.distinct_plurals(words)

            drills = [
                (
                    MEANING_TITLE,
                    Exercise.ExerciseType.MULTIPLE_CHOICE,
                    MEANING_INSTRUCTION,
                    self.meaning_questions(words, meanings, asked_anywhere),
                ),
            ]

            # The three grammar drills, each only in a lesson that teaches its rule.
            if ARTIKEL_TOPIC in allowed:
                drills.append(
                    (
                        ARTICLE_TITLE,
                        Exercise.ExerciseType.MULTIPLE_CHOICE,
                        ARTICLE_INSTRUCTION,
                        self.article_questions(words, topics["artikel"]),
                    )
                )

            if PLURAL_TOPIC in allowed:
                drills.append(
                    (
                        PLURAL_TITLE,
                        Exercise.ExerciseType.MULTIPLE_CHOICE,
                        PLURAL_INSTRUCTION,
                        self.plural_questions(words, plurals, topics["plural"]),
                    )
                )

            if PERFEKT_HABEN_TOPIC in allowed or PERFEKT_SEIN_TOPIC in allowed:
                drills.append(
                    (
                        PERFECT_TITLE,
                        Exercise.ExerciseType.MULTIPLE_CHOICE,
                        PERFECT_INSTRUCTION,
                        self.perfect_questions(
                            words, topics["haben"], topics["sein"], allowed
                        ),
                    )
                )

            # The typed drill is the words' own teaching in the other direction, so it is
            # never gated.
            drills.append(
                (
                    WRITING_TITLE,
                    Exercise.ExerciseType.TRANSLATION,
                    WRITING_INSTRUCTION,
                    self.writing_questions(words, asked_typed, synonyms),
                )
            )

        plan = []

        for title, exercise_type, instruction, questions in drills:
            for number, part in enumerate(self.batches(questions, batch), start=1):
                plan.append(
                    {
                        "title": f"{title} ({number})",
                        "type": exercise_type,
                        "instruction": instruction,
                        "questions": part,
                    }
                )

        return plan

    def write_exercise(self, lesson, drill):
        """Write one exercise with its questions, their options and their targets.

        ``Question.order`` is numbered across the whole lesson in the existing data, so
        these continue from where the lesson's questions stop, and each exercise of the
        lesson carries on from the one before it.
        """
        last_order = Exercise.objects.filter(lesson=lesson).aggregate(Max("order"))["order__max"]
        if last_order is None:
            last_order = 0

        exercise = Exercise.objects.create(
            lesson=lesson,
            title=drill["title"],
            instruction=drill["instruction"],
            type=drill["type"],
            difficulty=Exercise.Difficulty.EASY,
            order=last_order + 1,
            is_published=True,
        )

        last_question = Question.objects.filter(exercise__lesson=lesson).aggregate(Max("order"))
        order = last_question["order__max"]
        if order is None:
            order = 0

        for row in drill["questions"]:
            order += 1
            question = Question.objects.create(
                exercise=exercise,
                prompt=row["prompt"],
                order=order,
            )

            if drill["type"] == Exercise.ExerciseType.TRANSLATION:
                # Only correct rows, which is what makes the runner ask for typing instead
                # of options: a typed question never gets a distractor. Several are
                # written when the Persian gloss has more than one German word, so every
                # taught spelling is accepted.
                for position, accepted in enumerate(row["accepted"], start=1):
                    Answer.objects.create(
                        question=question, text=accepted, is_correct=True, order=position
                    )
            else:
                options = self.option_rows(row["correct"], row["wrong"], row["slot"])
                for position, option in enumerate(options, start=1):
                    text = option[0]
                    is_correct = option[1]
                    Answer.objects.create(
                        question=question,
                        text=text,
                        is_correct=is_correct,
                        order=position,
                    )

            # The word this question is about. `vocabulary/progress.py` moves that word's
            # counters from this row and nothing else.
            QuestionTarget.objects.create(
                question=question,
                word=row["word"],
                role=QuestionTarget.Role.TESTED_ITEM,
            )

            # …and the rule it asks about, for the questions that ask about one. The
            # meaning and writing questions test a word and no rule, so they carry no
            # grammar target rather than a guessed one.
            if row["grammar"] is not None:
                QuestionTarget.objects.create(
                    question=question,
                    grammar=row["grammar"],
                    role=QuestionTarget.Role.GRAMMAR,
                )

        return exercise

    def handle(self, *args, **options):
        if options["batch"] < 1:
            raise CommandError("batch must be at least 1")

        topics = self.grammar_topics()

        wanted = options["lesson"]

        # Every published lesson, in course order, even when only one of them is to be
        # planned: which rules a lesson may be drilled on depends on what the lessons before
        # it taught, so the ones before it have to be read either way.
        lessons = Lesson.objects.filter(
            is_published=True, course__is_published=True
        ).select_related("course__language_level").order_by(
            "course__language_level__order", "order", "pk"
        )

        asked_anywhere = self.asked_words()
        asked_typed = self.asked_words(Exercise.ExerciseType.TRANSLATION)

        # Built once: the map reads the whole published word table and every lesson shares it.
        synonyms = self.synonyms_by_meaning()

        planned = []

        # The rules the course has taught by the time each lesson arrives, accumulated in
        # course order. A lesson's own topics are added after it has been planned, because
        # "taught before" means before this lesson, not including it. The running set is
        # cleared when the course changes: what another course taught is not this course's
        # teaching, and a review lesson must not be asked about it.
        taught_before = set()
        current_course = None

        for lesson in lessons:
            if lesson.course_id != current_course:
                current_course = lesson.course_id
                taught_before = set()

            own_topics = self.lesson_topics(lesson)
            allowed = self.allowed_topics(lesson, own_topics, taught_before)

            for title in own_topics:
                taught_before.add(title)

            if wanted and lesson.pk != wanted:
                continue

            plan = self.lesson_plan(
                lesson,
                options["batch"],
                topics,
                asked_anywhere,
                asked_typed,
                synonyms,
                allowed,
            )
            if plan:
                planned.append((lesson, plan))

        for lesson, plan in planned:
            question_total = 0
            for drill in plan:
                question_total += len(drill["questions"])
            self.stdout.write(
                f"lesson {lesson.pk}: {len(plan)} exercise(s) / {question_total} "
                f"questions ({lesson.title})"
            )

        if not planned:
            self.stdout.write("Nothing to build: no published lesson introduces a word.")
            return

        exercise_total = 0
        question_total = 0
        for lesson, plan in planned:
            exercise_total += len(plan)
            for drill in plan:
                question_total += len(drill["questions"])

        existing = owned_exercises().count()

        # An attempt points at both the exercise and the question, and the rebuild deletes
        # both, so these rows disappear with the drills. Count them while they still exist.
        attempt_rows = ExerciseAttempt.objects.filter(
            exercise__in=owned_exercises()
        )
        attempt_total = attempt_rows.count()
        learner_total = attempt_rows.values("user").distinct().count()

        if options["dry_run"]:
            self.stdout.write(
                f"Dry run: would replace {existing} generated drill(s) with {exercise_total} "
                f"exercises / {question_total} questions."
            )
            if attempt_total:
                self.stdout.write(
                    f"Dry run: {attempt_total} stored attempt(s) from {learner_total} "
                    f"learner(s) belong to those exercises and would be deleted as well."
                )
            return

        # Rebuilding is safe while nobody has answered these questions. Once somebody has,
        # replacing them would quietly destroy learning history, so it needs the flag.
        if attempt_total and not options["yes_replace_history"]:
            self.stderr.write(
                self.style.WARNING(
                    f"{attempt_total} stored attempt(s) from {learner_total} learner(s) belong "
                    f"to the {existing} generated drill(s) this command would replace."
                )
            )
            self.stderr.write(
                "Deleting those exercises also deletes those attempts, which are the history "
                "the review and progress features read."
            )
            raise CommandError(
                "Refusing to replace generated drills that have learner attempts. "
                "Re-run with --yes-replace-history to delete that history too."
            )

        if attempt_total:
            self.stderr.write(
                self.style.WARNING(
                    f"--yes-replace-history: deleting {attempt_total} stored attempt(s) from "
                    f"{learner_total} learner(s) together with the generated drills."
                )
            )

        # One transaction, so a failure half-way cannot leave the content deleted.
        with transaction.atomic():
            owned_exercises().delete()

            for lesson, plan in planned:
                for drill in plan:
                    self.write_exercise(lesson, drill)

        after = set(
            QuestionTarget.objects.filter(
                role=QuestionTarget.Role.TESTED_ITEM, word__isnull=False
            ).values_list("word_id", flat=True)
        )
        grammar_total = QuestionTarget.objects.filter(
            role=QuestionTarget.Role.GRAMMAR
        ).count()
        typed_total = Question.objects.filter(
            exercise__type=Exercise.ExerciseType.TRANSLATION,
            exercise__in=owned_exercises(),
        ).count()

        self.stdout.write(
            f"Built {exercise_total} generated drill(s) with {question_total} questions, "
            f"replacing {existing}."
        )
        self.stdout.write(f"Words with a question: {len(asked_anywhere)} → {len(after)}.")
        self.stdout.write(
            f"Words asked to be typed: {len(asked_typed)} → {len(asked_typed) + typed_total}."
        )
        self.stdout.write(f"Grammar targets: {grammar_total}.")
