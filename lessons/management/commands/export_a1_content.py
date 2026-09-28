"""Export the A1 course content to CSV files for review.

    python manage.py export_a1_content
    python manage.py export_a1_content --output-dir exports/a1 --level A1

The files are written as UTF-8 **with BOM** so Excel shows the Persian text
correctly on Windows, and they are comma separated with quoted fields. This is a
read-only command: it never writes to the database.

Files produced:

* ``01_lessons.csv``        -- one row per lesson
* ``02_lesson_content.csv`` -- every content block of every lesson
* ``03_lesson_words.csv``   -- the word links of a lesson, in teaching order
* ``04_vocabulary.csv``     -- every A1 word with the lessons it appears in
* ``05_grammar.csv``        -- grammar topics and where they are taught
* ``06_sentences.csv``      -- every sentence with lesson, role, speaker, translation
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from lessons.models import Course, LanguageLevel, LessonWord
from lessons.models import LessonSentence
from vocabulary.models import Grammar, Sentence, Word

DEFAULT_DIR = "exports/a1"


class Command(BaseCommand):
    help = "Write the A1 course content to CSV files for spelling / translation review."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=DEFAULT_DIR,
            help=f"Directory for the CSV files (default {DEFAULT_DIR}).",
        )
        parser.add_argument("--level", default="A1", help="Language level code (default A1).")

    def write_csv(self, path, header, rows):
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
            writer.writerow(header)
            writer.writerows(rows)
        return len(rows)

    def handle(self, *args, **options):
        code = options["level"]
        level = LanguageLevel.objects.filter(level=code).first()
        if level is None:
            raise CommandError(f"LanguageLevel {code!r} does not exist.")
        course = Course.objects.filter(language_level=level).first()
        if course is None:
            raise CommandError(f"No course for {code!r}. Run `python manage.py seed_a1_course` first.")

        out_dir = Path(options["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        written = []

        lessons = list(course.lessons.order_by("order"))

        # ------------------------------------------------------------------ 01 lessons
        rows = [
            [
                lesson.order,
                lesson.title,
                lesson.description,
                lesson.estimated_time,
                "yes" if lesson.is_published else "no",
                lesson.contents.count(),
                lesson.lesson_words.filter(role=LessonWord.Role.NEW).count(),
                lesson.lesson_words.filter(role=LessonWord.Role.REVIEW).count(),
                lesson.lesson_grammars.count(),
                lesson.lesson_sentences.count(),
            ]
            for lesson in lessons
        ]
        written.append(
            (
                "01_lessons.csv",
                self.write_csv(
                    out_dir / "01_lessons.csv",
                    [
                        "lesson_order",
                        "title",
                        "description",
                        "estimated_time_min",
                        "is_published",
                        "content_blocks",
                        "words_new",
                        "words_review",
                        "grammar_topics",
                        "sentences",
                    ],
                    rows,
                ),
            )
        )

        # ----------------------------------------------------------- 02 content blocks
        rows = [
            [lesson.order, lesson.title, block.order, block.type, block.title, block.body]
            for lesson in lessons
            for block in lesson.contents.order_by("order")
        ]
        written.append(
            (
                "02_lesson_content.csv",
                self.write_csv(
                    out_dir / "02_lesson_content.csv",
                    ["lesson_order", "lesson_title", "block_order", "type", "block_title", "body"],
                    rows,
                ),
            )
        )

        # ------------------------------------------------------------ 03 lesson words
        rows = [
            [
                lesson.order,
                lesson.title,
                link.order,
                "NEW" if link.role == LessonWord.Role.NEW else "REVIEW",
                link.word.word,
                link.word.article,
                link.word.plural or "",
                link.word.meaning_fa,
                link.word.meaning_en,
            ]
            for lesson in lessons
            for link in lesson.lesson_words.select_related("word").order_by("order")
        ]
        written.append(
            (
                "03_lesson_words.csv",
                self.write_csv(
                    out_dir / "03_lesson_words.csv",
                    [
                        "lesson_order",
                        "lesson_title",
                        "position",
                        "role",
                        "word",
                        "article",
                        "plural",
                        "meaning_fa",
                        "meaning_en",
                    ],
                    rows,
                ),
            )
        )

        # -------------------------------------------------------------- 04 vocabulary
        lesson_map = {}
        for link in LessonWord.objects.select_related("lesson").order_by("lesson__order", "order"):
            role = "NEW" if link.role == LessonWord.Role.NEW else "REV"
            lesson_map.setdefault(link.word_id, []).append(f"{link.lesson.order}({role})")

        rows = [
            [
                word.level.level,
                word.word,
                word.word_type,
                word.article,
                word.gender or "",
                word.plural or "",
                word.meaning_fa,
                word.meaning_en,
                word.pronunciation,
                "yes" if word.is_separable else "",
                word.perfect_auxiliary or "",
                word.is_published,
                ", ".join(lesson_map.get(word.id, [])),
            ]
            for word in Word.objects.filter(level=level).order_by("word")
        ]
        written.append(
            (
                "04_vocabulary.csv",
                self.write_csv(
                    out_dir / "04_vocabulary.csv",
                    [
                        "level",
                        "word",
                        "word_type",
                        "article",
                        "gender",
                        "plural",
                        "meaning_fa",
                        "meaning_en",
                        "pronunciation_ipa",
                        "is_separable",
                        "perfect_auxiliary",
                        "is_published",
                        "lessons",
                    ],
                    rows,
                ),
            )
        )

        # ----------------------------------------------------------------- 05 grammar
        grammar_lessons = {}
        for link in Grammar.objects.filter(level=level).all():
            for lesson in link.lesson_links.select_related("lesson").order_by("lesson__order"):
                grammar_lessons.setdefault(link.id, []).append(f"{lesson.lesson.order}. {lesson.lesson.title}")
        rows = [
            [
                grammar.level.level,
                grammar.title,
                grammar.explanation,
                grammar.is_published,
                " | ".join(grammar_lessons.get(grammar.id, [])),
            ]
            for grammar in Grammar.objects.filter(level=level).order_by("title")
        ]
        written.append(
            (
                "05_grammar.csv",
                self.write_csv(
                    out_dir / "05_grammar.csv",
                    ["level", "title", "explanation", "is_published", "taught_in_lessons"],
                    rows,
                ),
            )
        )

        # --------------------------------------------------------------- 06 sentences
        rows = [
            [
                link.lesson.order,
                link.lesson.title,
                link.order,
                link.role,
                link.speaker,
                link.sentence.text,
                link.sentence.translation_fa,
            ]
            for link in LessonSentence.objects.select_related("lesson", "sentence").order_by(
                "lesson__order", "order"
            )
        ]
        written.append(
            (
                "06_sentences.csv",
                self.write_csv(
                    out_dir / "06_sentences.csv",
                    [
                        "lesson_order",
                        "lesson_title",
                        "position",
                        "role",
                        "speaker",
                        "german",
                        "persian",
                    ],
                    rows,
                ),
            )
        )

        self.stdout.write(self.style.SUCCESS(f"Wrote {len(written)} files to {out_dir.resolve()}"))
        for name, count in written:
            self.stdout.write(f"  {name:24} {count:5} rows")
