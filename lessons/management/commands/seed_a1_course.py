"""Seed the structured A1 German course (course, lessons, content, links).

The lesson material lives in reviewable Python data modules under ``lessons/data/``:

* ``a1_grammar``  -- grammar topics, keyed by their (unique) title
* ``a1_lessons_a`` -- lessons 1-12  (A1.1)
* ``a1_lessons_b`` -- lessons 13-24 (A1.2)

Load it with::

    python manage.py seed_a1_course                 # create what is missing
    python manage.py seed_a1_course --check         # validate only, write nothing
    python manage.py seed_a1_course --dry-run       # no database writes
    python manage.py seed_a1_course --update        # refresh text of existing rows
    python manage.py seed_a1_course --lesson 1 --lesson 2

Safety: existing ``LanguageLevel``, ``Word`` rows and any lesson material that is
already in the database are never deleted. ``Word`` rows are only *linked*
(``LessonWord``); their own fields are never rewritten by this command. Text on an
already existing ``Lesson`` / ``LessonContent`` / ``Grammar`` / ``Sentence`` is left
untouched unless ``--update`` is passed.
"""

import sys
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from lessons.data import a1_grammar, a1_lessons_a, a1_lessons_b
from lessons.models import Course, LanguageLevel, Lesson, LessonContent, LessonGrammar, LessonSentence, LessonWord
from vocabulary.models import Grammar, Sentence, Word

#: level -> (title, order). Mirrors the map used by ``import_a1_words``.
LEVELS = {
    "A1": ("A1 - Beginner", 1),
    "A2": ("A2 - Elementary", 2),
    "B1": ("B1 - Intermediate", 3),
    "B2": ("B2 - Upper intermediate", 4),
    "C1": ("C1 - Advanced", 5),
    "C2": ("C2 - Proficiency", 6),
}

COURSES = {
    "A1": (
        "Deutsch A1 – Von null bis A1",
        "A complete beginner course in 24 lessons: A1.1 (lessons 1–12) takes you from "
        "greeting someone to describing your home, A1.2 (lessons 13–24) covers free time, "
        "travelling, health, the past tense and everyday situations. Original material, "
        "aligned with the CEFR A1 level.",
        # The Persian summary, which is the one the learner pages show. It says the same
        # three things as the paragraph above — where the course starts, how far it goes
        # and that the material is this project's own — because those are the three facts
        # a visitor is trying to establish. No claim about the official exam is made here:
        # the exam page is where that is handled, and it handles it honestly.
        "دورهٔ آلمانی از صفر تا سطح A1، در ۲۴ درس پشت سر هم. از سلام‌و‌احوال و معرفی خودت "
        "شروع می‌شود و به خرید، سفر، سلامت و گذشتهٔ ساده می‌رسد. همهٔ متن‌ها، جمله‌ها و "
        "تمرین‌های این دوره محتوای خودِ همین پروژه است، نه برگهٔ رسمی گوته.",
    ),
}


class Command(BaseCommand):
    help = "Create the A1 course structure: course, lessons, content blocks and their links."

    # ---------------------------------------------------------------- arguments

    def add_arguments(self, parser):
        parser.add_argument("--level", default="A1", help="Language level code (default A1).")
        parser.add_argument(
            "--lesson",
            action="append",
            type=int,
            default=None,
            metavar="N",
            help="Only seed this lesson order number. May be repeated.",
        )
        parser.add_argument("--update", action="store_true", help="Refresh text of rows that already exist.")
        parser.add_argument("--dry-run", action="store_true", help="Report what would change, write nothing.")
        parser.add_argument("--check", action="store_true", help="Validate the data modules only, write nothing.")
        parser.add_argument("--unpublished", action="store_true", help="Leave everything unpublished.")
        parser.add_argument(
            "--list-orphans",
            action="store_true",
            help="List every word that no lesson links to yet (default: only count them).",
        )

    # ------------------------------------------------------------------ helpers

    def lesson_data(self):
        lessons = list(a1_lessons_a.LESSONS) + list(a1_lessons_b.LESSONS)
        lessons.sort(key=lambda item: item["order"])
        return lessons

    def get_level(self, code, create=True):
        if code not in LEVELS:
            raise CommandError(f"Unknown level {code!r}. Known: {', '.join(LEVELS)}")
        title, order = LEVELS[code]
        if not create:
            level = LanguageLevel.objects.filter(level=code).first()
            if level is None:
                raise CommandError(
                    f"LanguageLevel {code!r} does not exist yet – run "
                    f"`python manage.py import_a1_words --level {code} --no-audio` first."
                )
            return level
        level, _ = LanguageLevel.objects.get_or_create(level=code, defaults={"title": title, "order": order})
        return level

    def word_index(self, level):
        """Map German word -> Word row. Returns (index, ambiguous refs)."""
        index = {}
        ambiguous = []
        for word in Word.objects.filter(level=level):
            if word.word in index:
                ambiguous.append(word.word)
            index[word.word] = word
        return index, ambiguous

    def resolve_word(self, ref, index, level):
        """``ref`` is either ``Wort`` or ``Wort::NOUN`` when the text is ambiguous."""
        if "::" in ref:
            text, _, type_name = ref.partition("::")
            return Word.objects.filter(level=level, word=text, word_type=type_name.upper()).first()
        return index.get(ref)

    # --------------------------------------------------------------- validation

    def validate(self, lessons, index, ambiguous, level):
        """Return (errors, warnings, stats) describing problems in the data modules."""
        errors = []
        warnings = []

        for text in ambiguous:
            errors.append(
                f"word {text!r} exists more than once – reference it as '{text}::NOUN', '{text}::VERB', …"
            )

        orders = Counter(item["order"] for item in lessons)
        for order, count in sorted(orders.items()):
            if count > 1:
                errors.append(f"lesson order {order} is used {count} times")
        expected = list(range(1, len(lessons) + 1))
        if sorted(orders) != expected:
            warnings.append(f"lesson orders are {sorted(orders)} – expected 1…{len(lessons)}")

        introduced = {}
        total_links = 0
        for item in lessons:
            lesson_no = item["order"]
            label = f"lesson {lesson_no} ({item['title']})"

            for ref in item.get("words_new", []):
                word = self.resolve_word(ref, index, level)
                if word is None:
                    errors.append(f"{label}: unknown word {ref!r} at A1")
                elif word.word in introduced:
                    warnings.append(
                        f"{label}: {word.word!r} is NEW but was already introduced in lesson {introduced[word.word]}"
                    )
                else:
                    introduced[word.word] = lesson_no

            for field in ("words_new", "words_review"):
                refs = item.get(field, [])
                texts = [self.resolve_word(r, index, level) for r in refs]
                texts = [w.word for w in texts if w is not None]
                for text, count in Counter(texts).items():
                    if count > 1:
                        errors.append(f"{label}: word {text!r} is listed twice in {field}")

            new_words = {
                w.word for w in (self.resolve_word(r, index, level) for r in item.get("words_new", [])) if w
            }
            review_words = {
                w.word
                for w in (self.resolve_word(r, index, level) for r in item.get("words_review", []))
                if w
            }
            for text in sorted(new_words & review_words):
                errors.append(
                    f"{label}: word {text!r} is listed as NEW and as REVIEW "
                    f"(unique_word_per_lesson)"
                )

            for ref in item.get("words_review", []):
                word = self.resolve_word(ref, index, level)
                if word is None:
                    errors.append(f"{label}: unknown review word {ref!r} at A1")
                elif word.word not in introduced:
                    warnings.append(
                        f"{label}: {word.word!r} is REVIEW but is not introduced as NEW in this or an earlier lesson"
                    )

            # The Persian pages show the Persian title, so a lesson without one would
            # fall back to its German name on every learner screen. That is a gap in the
            # data rather than a broken reference, so it is a warning, not an error.
            for field in ("title_fa", "description_fa"):
                if not item.get(field, ""):
                    warnings.append(f"{label}: has no {field} – the German text will be shown instead")

            for title in item.get("grammar", []):
                if title not in a1_grammar.GRAMMAR:
                    errors.append(f"{label}: unknown grammar topic {title!r}")

            seen_sentences = set()
            for sentence in item.get("sentences", []):
                text = sentence[0]
                if text in seen_sentences:
                    errors.append(f"{label}: sentence {text!r} is linked twice (unique_sentence_per_lesson)")
                seen_sentences.add(text)
                if sentence[2] not in dict(LessonSentence.Role.choices):
                    errors.append(f"{label}: unknown sentence role {sentence[2]!r} for {text!r}")

            blocks = item.get("contents", [])
            if not blocks:
                errors.append(f"{label}: has no content blocks")
            known_types = dict(LessonContent.ContentType.choices)
            for block_type, title, _body in blocks:
                if block_type not in known_types:
                    errors.append(f"{label}: unknown content type {block_type!r} ({title!r})")
            if len(blocks) != len({b[1] for b in blocks}):
                warnings.append(f"{label}: two content blocks share the same title")

            total_links += len(item.get("words_new", [])) + len(item.get("words_review", []))

        if not lessons:
            errors.append("the lesson data modules are empty")

        stats = {"lessons": len(lessons), "links": total_links, "grammar_topics": len(a1_grammar.GRAMMAR)}
        return errors, warnings, stats

    # ------------------------------------------------------------------- writing

    def seed_lesson(self, item, level, course, index, update, publish, dry, counters):
        lesson, created = Lesson.objects.get_or_create(
            course=course,
            order=item["order"],
            defaults={
                "title": item["title"],
                "title_fa": item.get("title_fa", ""),
                "description": item.get("description", ""),
                "description_fa": item.get("description_fa", ""),
                "estimated_time": item.get("estimated_time", 60),
                "is_published": publish,
            },
        )
        if created:
            counters["lessons_created"] += 1
        else:
            counters["lessons_reused"] += 1

        if not created:
            fields = []
            if lesson.title != item["title"]:
                fields.append(f"title: {lesson.title!r} vs {item['title']!r}")
            if lesson.title_fa != item.get("title_fa", ""):
                fields.append(f"title_fa: {lesson.title_fa!r} vs {item.get('title_fa', '')!r}")
            if lesson.estimated_time != item.get("estimated_time", 60):
                fields.append(f"estimated_time: {lesson.estimated_time} vs {item.get('estimated_time', 60)}")
            if fields and not update:
                counters["lesson_differences"].append(f"lesson {item['order']}: " + "; ".join(fields))
            if update and not dry:
                lesson.title = item["title"]
                lesson.title_fa = item.get("title_fa", "")
                lesson.description = item.get("description", "")
                lesson.description_fa = item.get("description_fa", "")
                lesson.estimated_time = item.get("estimated_time", 60)
                lesson.is_published = publish
                lesson.save(
                    update_fields=[
                        "title", "title_fa", "description", "description_fa",
                        "estimated_time", "is_published",
                    ]
                )
                counters["lessons_updated"] += 1

        # ---- content blocks
        for order, (block_type, title, body) in enumerate(item.get("contents", []), start=1):
            block, block_created = LessonContent.objects.get_or_create(
                lesson=lesson,
                order=order,
                defaults={"type": block_type, "title": title, "body": body},
            )
            if block_created:
                counters["contents_created"] += 1
            else:
                counters["contents_reused"] += 1
                if update and (block.type != block_type or block.title != title or block.body != body):
                    if not dry:
                        block.type, block.title, block.body = block_type, title, body
                        block.save(update_fields=["type", "title", "body"])
                    counters["contents_updated"] += 1

        # ---- words (one continuous order: NEW first, then REVIEW)
        order = 0
        for field, role in (("words_new", LessonWord.Role.NEW), ("words_review", LessonWord.Role.REVIEW)):
            for ref in item.get(field, []):
                word = self.resolve_word(ref, index, level)
                if word is None:
                    counters["problems"].append(f"lesson {item['order']}: skipped unknown word {ref!r}")
                    continue
                order += 1
                _, link_created = LessonWord.objects.get_or_create(
                    lesson=lesson, word=word, defaults={"role": role, "order": order}
                )
                if link_created:
                    counters["word_links_created"] += 1
                else:
                    counters["word_links_reused"] += 1
                    LessonWord.objects.filter(lesson=lesson, word=word).update(role=role, order=order)
                counters[f"words_{role.lower()}"] += 1

        # ---- grammar
        for order, title in enumerate(item.get("grammar", []), start=1):
            spec = a1_grammar.GRAMMAR.get(title)
            if spec is None:
                counters["problems"].append(f"lesson {item['order']}: skipped unknown grammar {title!r}")
                continue
            grammar, grammar_created = Grammar.objects.get_or_create(
                level=level,
                title=title,
                defaults={"explanation": spec, "is_published": publish},
            )
            if grammar_created:
                counters["grammar_created"] += 1
            else:
                counters["grammar_reused"] += 1
                if update and grammar.explanation != spec:
                    if not dry:
                        grammar.explanation = spec
                        grammar.save(update_fields=["explanation"])
                    counters["grammar_updated"] += 1
            _, link_created = LessonGrammar.objects.get_or_create(
                lesson=lesson, grammar=grammar, defaults={"order": order}
            )
            if link_created:
                counters["grammar_links_created"] += 1
            else:
                counters["grammar_links_reused"] += 1
                LessonGrammar.objects.filter(lesson=lesson, grammar=grammar).update(order=order)

        # ---- sentences
        for order, sentence in enumerate(item.get("sentences", []), start=1):
            # A sentence entry is [text, translation_fa] with optional role and speaker.
            text = sentence[0]
            translation_fa = sentence[1] if len(sentence) > 1 else ""
            role = sentence[2] if len(sentence) > 2 else "EXAMPLE"
            speaker = sentence[3] if len(sentence) > 3 else ""
            row, sentence_created = Sentence.objects.get_or_create(
                level=level,
                text=text,
                defaults={"translation_fa": translation_fa, "is_published": publish},
            )
            if sentence_created:
                counters["sentences_created"] += 1
            else:
                counters["sentences_reused"] += 1
                if update and row.translation_fa != translation_fa:
                    if not dry:
                        row.translation_fa = translation_fa
                        row.save(update_fields=["translation_fa"])
                    counters["sentences_updated"] += 1
            _, link_created = LessonSentence.objects.get_or_create(
                lesson=lesson,
                sentence=row,
                defaults={"role": role, "speaker": speaker, "order": order},
            )
            if link_created:
                counters["sentence_links_created"] += 1
            else:
                counters["sentence_links_reused"] += 1
                LessonSentence.objects.filter(lesson=lesson, sentence=row).update(
                    role=role, speaker=speaker, order=order
                )

    # -------------------------------------------------------------------- handle

    def handle(self, *args, **options):
        level_code = options["level"]
        update = options["update"]
        dry = options["dry_run"]
        check_only = options["check"]
        publish = not options["unpublished"]

        lessons = self.lesson_data()
        if options["lesson"]:
            wanted = set(options["lesson"])
            lessons = [item for item in lessons if item["order"] in wanted]
            missing = wanted - {item["order"] for item in lessons}
            if missing:
                raise CommandError(f"No lesson data for order(s): {sorted(missing)}")

        level = self.get_level(level_code, create=not check_only)
        index, ambiguous = self.word_index(level)

        errors, warnings, stats = self.validate(lessons, index, ambiguous, level)
        self.stdout.write(f"Data modules: {stats['lessons']} lessons, {stats['links']} word links, {stats['grammar_topics']} grammar topics.")

        for message in errors:
            self.stderr.write(self.style.ERROR(f"  error: {message}"))
        for message in warnings:
            self.stdout.write(self.style.WARNING(f"  warning: {message}"))

        if errors:
            self.stdout.write(self.style.ERROR(f"{len(errors)} error(s) found – nothing was written."))
            sys.exit(1)

        if check_only:
            self.stdout.write(self.style.SUCCESS("Check only: data modules are valid, nothing was written."))
            return

        counters = Counter()
        counters["lesson_differences"] = []
        counters["problems"] = []

        title, description, description_fa = COURSES.get(
            level_code, (f"Deutsch {level_code}", "", "")
        )
        course, course_created = Course.objects.get_or_create(
            language_level=level,
            defaults={
                "title": title,
                "description": description,
                "description_fa": description_fa,
                "is_published": publish,
            },
        )
        if not course_created and update and not dry:
            course.title = title
            course.description = description
            course.description_fa = description_fa
            course.save(update_fields=["title", "description", "description_fa"])

        with transaction.atomic():
            for item in lessons:
                self.seed_lesson(item, level, course, index, update, publish, dry, counters)
            if dry:
                transaction.set_rollback(True)

        for message in counters["problems"]:
            self.stderr.write(self.style.ERROR(f"  skipped: {message}"))
        for message in counters["lesson_differences"]:
            self.stdout.write(
                self.style.WARNING(f"  kept existing text (use --update to refresh): {message}")
            )

        if dry:
            prefix = "Dry run – no changes written. "
        else:
            prefix = ""

        if course_created:
            course_status = "created"
        else:
            course_status = "reused"

        # "updated" is only worth mentioning when it is not zero.
        lessons_updated = ""
        if counters["lessons_updated"]:
            lessons_updated = f", {counters['lessons_updated']} updated"
        contents_updated = ""
        if counters["contents_updated"]:
            contents_updated = f", {counters['contents_updated']} updated"

        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Course: {course_status} ({course.title})\n"
                f"  Lessons: {counters['lessons_created']} created, {counters['lessons_reused']} reused"
                f"{lessons_updated}\n"
                f"  Content blocks: {counters['contents_created']} created, {counters['contents_reused']} reused"
                f"{contents_updated}\n"
                f"  Words linked: {counters['words_new']} NEW, {counters['words_review']} REVIEW "
                f"({counters['word_links_created']} new links, {counters['word_links_reused']} already there)\n"
                f"  Grammar: {counters['grammar_created']} topics created, {counters['grammar_reused']} reused, "
                f"{counters['grammar_links_created']} new lesson links\n"
                f"  Sentences: {counters['sentences_created']} created, {counters['sentences_reused']} reused, "
                f"{counters['sentence_links_created']} new lesson links"
            )
        )

        linked = set(
            LessonWord.objects.filter(lesson__course=course).values_list("word_id", flat=True)
        )
        orphans = (
            Word.objects.filter(level=level)
            .exclude(id__in=linked)
            .order_by("word")
        )
        total = Word.objects.filter(level=level).count()
        if not orphans.exists():
            self.stdout.write(self.style.SUCCESS(f"All {total} A1 words are linked to a lesson."))
            return

        self.stdout.write(
            self.style.WARNING(
                f"{orphans.count()} of {total} A1 words are not linked to any lesson yet "
                f"(pass --list-orphans to see them)."
            )
        )
        if options["list_orphans"]:
            for word in orphans:
                self.stdout.write(f"    {word}")
