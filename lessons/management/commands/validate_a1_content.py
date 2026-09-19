"""Validate the seeded A1 course content against the live database.

    python manage.py validate_a1_content

Read-only: nothing is written. It runs the same checks as ``lessons/tests.py`` but
against the real database, so it works even when the database user is not allowed to
create a test database. Exit code is 1 when a check fails.
"""

from __future__ import annotations

import sys

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from lessons.models import (
    Course,
    LanguageLevel,
    LessonContent,
    LessonGrammar,
    LessonSentence,
    LessonWord,
)
from vocabulary.models import Grammar, Sentence, Word


class Command(BaseCommand):
    help = "Check the A1 course structure, links, German word data and translations."

    def add_arguments(self, parser):
        parser.add_argument("--level", default="A1", help="Language level code (default A1).")
        parser.add_argument("--show", type=int, default=12, help="How many examples to print per problem.")

    def handle(self, *args, **options):
        code = options["level"]
        show = options["show"]
        level = LanguageLevel.objects.filter(level=code).first()
        if level is None:
            raise CommandError(f"LanguageLevel {code!r} does not exist.")
        course = Course.objects.filter(language_level=level).first()
        if course is None:
            raise CommandError(f"No course for {code!r} – run `python manage.py seed_a1_course` first.")

        problems: list[tuple[str, list[str]]] = []
        notes: list[str] = []

        def check(name: str, items: list[str]) -> None:
            problems.append((name, items))

        lessons = list(course.lessons.order_by("order"))
        orders = [lesson.order for lesson in lessons]
        check(
            "lesson order is 1…n without gaps",
            [] if orders == list(range(1, len(orders) + 1)) else [f"orders: {orders}"],
        )
        check(
            "every lesson has a title, description and duration",
            [
                f"lesson {lesson.order}: missing title/description/duration"
                for lesson in lessons
                if not lesson.title.strip() or not lesson.description.strip() or lesson.estimated_time <= 0
            ],
        )

        # ------------------------------------------------------------ content blocks
        blocks = list(LessonContent.objects.select_related("lesson").order_by("lesson__order", "order"))
        block_problems: list[str] = []
        for lesson in lessons:
            lesson_blocks = [block for block in blocks if block.lesson_id == lesson.id]
            if not lesson_blocks:
                block_problems.append(f"lesson {lesson.order}: no content blocks")
                continue
            if [block.order for block in lesson_blocks] != list(range(1, len(lesson_blocks) + 1)):
                block_problems.append(f"lesson {lesson.order}: block order is not contiguous")
        block_problems += [
            f"lesson {block.lesson.order} block {block.order}: unknown type {block.type!r}"
            for block in blocks
            if block.type not in dict(LessonContent.ContentType.choices)
        ]
        block_problems += [
            f"lesson {block.lesson.order} block {block.order}: no English gloss"
            for block in blocks
            if "English:" not in block.body
        ]
        check("content blocks are complete and ordered", block_problems[:show])

        # --------------------------------------------------------------- word links
        links = list(LessonWord.objects.select_related("lesson", "word").order_by("lesson__order", "order"))
        link_problems: list[str] = []
        for lesson in lessons:
            lesson_links = [link for link in links if link.lesson_id == lesson.id]
            if [link.order for link in lesson_links] != list(range(1, len(lesson_links) + 1)):
                link_problems.append(f"lesson {lesson.order}: word order is not contiguous")
        duplicates = (
            LessonWord.objects.values("lesson", "word").annotate(total=Count("id")).filter(total__gt=1)
        )
        link_problems += [
            f"word linked twice in the same lesson: lesson {row['lesson']} word {row['word']}"
            for row in duplicates
        ]
        check("word links are ordered and unique", link_problems[:show])

        introduced: set[int] = set()
        review_problems: list[str] = []
        for lesson in lessons:
            for link in lesson.lesson_words.all():
                if link.role == LessonWord.Role.REVIEW and link.word_id not in introduced:
                    review_problems.append(
                        f"lesson {lesson.order}: {link.word.word!r} is REVIEW but never NEW before"
                    )
            introduced |= set(
                link.word_id
                for link in lesson.lesson_words.all()
                if link.role == LessonWord.Role.NEW
            )
        check("every REVIEW word was introduced earlier as NEW", review_problems[:show])

        linked_ids = {link.word_id for link in links}
        check(
            "linked words belong to the level",
            [
                f"lesson {link.lesson.order}: {link.word.word!r} is level {link.word.level_id}"
                for link in links
                if link.word.level_id != level.id
            ][:show],
        )
        unlinked = (
            Word.objects.filter(level=level).exclude(id__in=linked_ids).order_by("word")
        )
        check(
            "every level word is linked to a lesson",
            [] if not unlinked.exists() else [f"{unlinked.count()} unlinked: " + ", ".join(
                unlinked.values_list("word", flat=True)[:show]
            )],
        )

        # ----------------------------------------------------------------- grammar
        grammar_links = list(
            LessonGrammar.objects.select_related("lesson", "grammar").order_by("lesson__order", "order")
        )
        grammar_problems: list[str] = []
        for lesson in lessons:
            lesson_grammar = [link for link in grammar_links if link.lesson_id == lesson.id]
            if [link.order for link in lesson_grammar] != list(range(1, len(lesson_grammar) + 1)):
                grammar_problems.append(f"lesson {lesson.order}: grammar order is not contiguous")
        grammar_problems += [
            f"grammar {grammar.title!r}: empty explanation or missing English gloss"
            for grammar in Grammar.objects.filter(level=level)
            if not grammar.explanation.strip() or "English:" not in grammar.explanation
        ]
        orphans = Grammar.objects.filter(level=level).exclude(
            id__in={link.grammar_id for link in grammar_links}
        )
        grammar_problems += [f"grammar topic not used in any lesson: {g.title!r}" for g in orphans]
        check("grammar topics are complete and linked", grammar_problems[:show])

        # --------------------------------------------------------------- sentences
        sentence_links = list(
            LessonSentence.objects.select_related("lesson", "sentence").order_by("lesson__order", "order")
        )
        sentence_problems: list[str] = []
        for lesson in lessons:
            lesson_sentences = [link for link in sentence_links if link.lesson_id == lesson.id]
            if [link.order for link in lesson_sentences] != list(range(1, len(lesson_sentences) + 1)):
                sentence_problems.append(f"lesson {lesson.order}: sentence order is not contiguous")
        sentence_problems += [
            f"lesson {link.lesson.order}: unknown sentence role {link.role!r}"
            for link in sentence_links
            if link.role not in dict(LessonSentence.Role.choices)
        ]
        sentence_problems += [
            f"lesson {link.lesson.order}: dialogue line without a speaker: {link.sentence.text!r}"
            for link in sentence_links
            if link.role == LessonSentence.Role.DIALOGUE and not link.speaker.strip()
        ]
        sentence_problems += [
            f"lesson {link.lesson.order}: non-dialogue line has a speaker: {link.sentence.text!r}"
            for link in sentence_links
            if link.role != LessonSentence.Role.DIALOGUE and link.speaker.strip()
        ]
        sentence_problems += [
            f"sentence without Persian translation: {sentence.text!r}"
            for sentence in Sentence.objects.filter(level=level)
            if not sentence.translation_fa.strip() or not sentence.text.strip()
        ]
        notes += [
            f"no final punctuation (check by hand): {sentence.text!r}"
            for sentence in Sentence.objects.filter(level=level)
            if not sentence.text.strip().endswith((".", "!", "?", "…", "-"))
        ]
        sentence_orphans = Sentence.objects.filter(level=level).exclude(
            id__in={link.sentence_id for link in sentence_links}
        )
        sentence_problems += [f"unused sentence: {s.text!r}" for s in sentence_orphans]
        check("sentences are complete, ordered and translated", sentence_problems[:show])

        # ------------------------------------------------------------ word data
        word_problems: list[str] = []
        for word in Word.objects.filter(level=level):
            if word.word_type == Word.WordType.NOUN:
                expected = {"der": "M", "die": "F", "das": "N"}.get(word.article)
                if expected is None:
                    word_problems.append(f"noun without a valid article: {word.word!r} ({word.article!r})")
                elif word.gender != expected:
                    word_problems.append(
                        f"article/gender mismatch: {word.article} {word.word} (gender {word.gender})"
                    )
                if not word.word[:1].isupper():
                    word_problems.append(f"noun not capitalised: {word.word!r}")
                if word.plural and not word.plural.startswith("die "):
                    word_problems.append(f"plural without die: {word.word!r} → {word.plural!r}")
            else:
                if word.article:
                    word_problems.append(f"non-noun carries an article: {word.word!r}")
                if word.gender:
                    word_problems.append(f"non-noun carries a gender: {word.word!r}")
            if word.word_type == Word.WordType.VERB and not word.perfect_auxiliary:
                word_problems.append(f"verb without haben/sein: {word.word!r}")
            if not word.meaning_fa.strip():
                word_problems.append(f"word without a Persian meaning: {word.word!r}")
        check("German word data is consistent", word_problems[:show])

        # ------------------------------------------------------------------ report
        counts = (
            f"{len(lessons)} lessons · {len(blocks)} content blocks · {len(links)} word links · "
            f"{Grammar.objects.filter(level=level).count()} grammar topics · "
            f"{Sentence.objects.filter(level=level).count()} sentences · "
            f"{Word.objects.filter(level=level).count()} words"
        )
        self.stdout.write(f"Content: {counts}")

        failed = 0
        for name, items in problems:
            if items:
                failed += 1
                self.stderr.write(self.style.ERROR(f"  FAIL  {name} ({len(items)} problem(s))"))
                for item in items[:show]:
                    self.stderr.write(f"          {item}")
            else:
                self.stdout.write(self.style.SUCCESS(f"  ok    {name}"))

        for note in notes:
            self.stdout.write(f"  note  {note}")

        if failed:
            self.stderr.write(self.style.ERROR(f"{failed} check(s) failed."))
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS("All checks passed."))
