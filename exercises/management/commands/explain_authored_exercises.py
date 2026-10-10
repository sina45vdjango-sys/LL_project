"""Enrich authored vocabulary and reading exercises with structured Persian explanations.

Complements `explain_a1_drills` by covering the core authored exercises (exercises 21..111)
and reading text drills that were not handled by the generated drill command.

Additive, idempotent, and non-destructive:
- Touches only `Question.explanation` where it is currently empty.
- Never alters exercises that already carry an explanation.
- Supports `--dry-run` to preview changes without committing.
"""

from django.core.management.base import BaseCommand
from exercises.models import Question, QuestionTarget


class Command(BaseCommand):
    help = (
        "Fill Question.explanation on authored vocabulary and reading questions. "
        "Additive and idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report without saving changes to the database.",
        )

    def derive_explanation(self, question):
        ex_title = question.exercise.title
        word = None
        sentence = None

        for target in question.targets.all():
            if target.word_id is not None:
                word = target.word
            if target.sentence_id is not None:
                sentence = target.sentence

        correct_ans = ""
        for answer in question.answers.all():
            if answer.is_correct:
                correct_ans = answer.text
                break

        # 1. Authored Vocabulary: Meaning Selection
        if "واژگان — انتخاب معنی" in ex_title and word:
            if word.word_type == "NOUN" and word.article:
                plural_part = f" و جمع آن «{word.plural}» است" if word.plural else ""
                gender_part = f" ({word.gender_label})" if word.gender_label else ""
                return f"«{word.word}» اسم{gender_part} با آرتیکل «{word.article}» است{plural_part}؛ یعنی «{word.meaning_fa}»."
            if word.word_type == "VERB":
                aux_part = f" (در گذشته با {word.get_perfect_auxiliary_display()})" if word.perfect_auxiliary else ""
                sep_part = " (جداشدنی)" if word.is_separable else ""
                return f"«{word.word}» فعل{sep_part}{aux_part} است؛ یعنی «{word.meaning_fa}»."
            return f"«{word.word}» یعنی «{word.meaning_fa}»."

        # 2. Authored Vocabulary: Translation to German
        if "واژگان — ترجمه به آلمانی" in ex_title and word:
            if word.word_type == "NOUN" and word.article:
                return f"معادل «{word.meaning_fa}» در آلمانی «{word.article} {word.word}» است."
            return f"معادل «{word.meaning_fa}» در آلمانی «{word.word}» است."

        # 3. Authored Reading Comprehension
        if "خواندن و درک مطلب" in ex_title:
            lines = [line.strip().strip('"') for line in question.prompt.splitlines() if line.strip().startswith('"')]
            german_quote = lines[0] if lines else ""
            if sentence:
                return f"معادل «{sentence.text}» به فارسی «{sentence.translation_fa}» است."
            if german_quote:
                return f"معادل «{german_quote}» به فارسی «{correct_ans}» است."
            return f"پاسخ درست «{correct_ans}» است."

        # 4. Reading Comprehension Text Drills
        if "تمرین خواندن — متن کوتاه" in ex_title:
            if "کدام خطِ متن آمده است" in question.prompt:
                p_part = question.prompt.split("معنیِ «")[1].split("»")[0] if "معنیِ «" in question.prompt else ""
                return f"در متن، جملهٔ «{correct_ans}» یعنی «{p_part}»."
            if "کدام جمله در این متن نیست" in question.prompt:
                return f"جملهٔ «{correct_ans}» در متن بالا به کار نرفته است."
            return f"پاسخ درست «{correct_ans}» است."

        # 5. Plural-only nouns in article drills (Eltern, Geschwister, etc.)
        if "آرتیکل" in ex_title and word:
            return f"«{word.word}» اسمی است که فقط در حالت جمع به کار می‌رود و آرتیکل جمع آن «die» است؛ یعنی «{word.meaning_fa}»."

        return ""

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        questions = (
            Question.objects.filter(explanation="")
            .select_related("exercise__lesson")
            .prefetch_related("targets__word", "targets__sentence", "answers")
            .order_by("pk")
        )

        written = 0
        skipped = 0

        for question in questions:
            text = self.derive_explanation(question)
            if not text:
                skipped += 1
                continue

            if not dry_run:
                question.explanation = text
                question.save(update_fields=["explanation"])
            written += 1

        action = "Would write" if dry_run else "Wrote"
        self.stdout.write(f"{action} {written} explanation(s). Skipped: {skipped}.")
