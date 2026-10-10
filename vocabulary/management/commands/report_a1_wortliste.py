"""Report how much of the official Goethe A1 Wortliste this course teaches.

    python manage.py report_a1_wortliste

Read-only: it loads a data file and runs SELECT queries. Nothing is written.

Why this exists
---------------
The course teaches 1,008 words, chosen while the official Wortliste was open — four of the
data files under ``vocabulary/data/`` are even named after the gaps they were written to
fill. But nothing in the project ever said *which* official entries were still missing, so
"A1 coverage" was a claim rather than a number, and the next vocabulary decision had to be
made from memory. This command answers it from two files instead: the official list and the
database.

Where the official list comes from
----------------------------------
``vocabulary/data/wortliste/a1.json`` holds the entries exactly as the PDF prints them
(``die Adresse, -n``, ``all-``, ``(sich) anmelden``), so every line stays traceable to its
source. It sits in a **subdirectory** on purpose: ``import_a1_words`` loads every ``*.json``
directly under ``vocabulary/data/``, and the official list must never be imported as course
words. The extraction is documented in the README; the file is data, not code, and the
command refuses to guess when it is absent.

How an entry is matched
-----------------------
The list is written the way a dictionary writes it, so the comparison folds away the
notation rather than the words:

* a leading article is dropped — ``die Adresse, -n`` is the word ``Adresse``;
* everything after the first comma is dropped (the plural marker: ``-n``, ``-Ä``, ``-s``);
* ``/`` means either form (``circa/ca.``), so both are tried;
* brackets are optional parts (``gern(e)``, ``Grad (Celsius)``), so both forms are tried;
* ``(sich) anmelden`` is tried as ``anmelden`` **and** as ``sich anmelden``;
* a trailing ``-`` marks a stem whose paradigm counts (``all-`` for *alle, alles, allen*),
  so it matches any taught word that starts with it — and what a stem matched is reported
  separately, because it is the one place a match is not exact;
* case is folded, because the list capitalises what German orthography capitalises.

Anything left over is reported as missing. A taught word the list does not contain is
reported too, as information rather than a problem: this course is deliberately wider than
the exam vocabulary (the official list expects passive understanding of the rest).
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from lessons.models import LanguageLevel
from vocabulary.models import Word

#: The official list, one entry per line as the PDF prints it. A subdirectory of
#: ``vocabulary/data/`` so the word importer's ``*.json`` glob never sees it.
DEFAULT_LIST = Path(__file__).resolve().parents[2] / "data" / "wortliste" / "a1.json"

#: The articles the list prints in front of a noun. Dropped before comparing.
ARTICLES = ["der ", "die ", "das "]


class Command(BaseCommand):
    help = "Report how many official Goethe A1 Wortliste entries the course teaches."

    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            default=str(DEFAULT_LIST),
            help=f"Official word list to compare against (default {DEFAULT_LIST}).",
        )
        parser.add_argument("--level", default="A1", help="Language level code (default A1).")
        parser.add_argument(
            "--show", type=int, default=15, help="How many words to print per section."
        )
        parser.add_argument(
            "--all", action="store_true", help="Print every missing word, not just --show of them."
        )

    def load_entries(self, path):
        """The entries of the official list file, or a clear error.

        A missing file is not an empty list: it means the comparison cannot be made at all,
        and reporting "0 covered" for it would be a wrong number rather than a missing one.
        """
        file = Path(path)
        if not file.exists():
            raise CommandError(
                f"Official word list not found at {file}. See the README section on the "
                f"Wortliste report for where it comes from; --list points at a different file."
            )

        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise CommandError(f"{file} is not valid JSON: {error}")

        entries = data.get("entries")
        if not entries:
            raise CommandError(f"{file} has no 'entries' — it is not an official word list.")

        return data, entries

    def spellings(self, entry):
        """Every spelling ``entry`` stands for, and whether it is a stem.

        Returns ``(spellings, is_stem)``. The notation the list uses is folded here and
        nowhere else, so the data file keeps the words exactly as they were published.
        """
        text = entry["word"].strip()
        is_stem = text.endswith("-")

        parts = []
        if text.startswith("(sich) "):
            # The list's way of saying "with or without the reflexive pronoun".
            rest = text[len("(sich) ") :]
            parts.append(rest)
            parts.append("sich " + rest)
        elif "(" in text:
            # A bracketed part is optional: `gern(e)` is gern or gerne, and
            # `Grad (Celsius)` is Grad.
            without = text
            while "(" in without:
                open_at = without.index("(")
                close_at = without.index(")", open_at)
                without = without[:open_at] + without[close_at + 1 :]
            parts.append(text)
            parts.append(" ".join(without.split()))
        else:
            parts.append(text)

        spellings = []
        for part in parts:
            for alternative in part.split("/"):
                word = alternative.split(",")[0].strip()
                for article in ARTICLES:
                    if word.lower().startswith(article):
                        word = word[len(article) :]
                word = word.rstrip(". ").strip()
                if is_stem:
                    word = word.rstrip("-").strip()
                if word and word.lower() not in spellings:
                    spellings.append(word.lower())

        return spellings, is_stem

    def taught_spellings(self, level):
        """Every published word of the level, lower-cased, plus the same list sorted, plus
        how many rows that came from.

        The set folds the spellings that differ only in case (``sie``/``Sie``,
        ``essen``/``Essen``), which is what the comparison is about; the row count is kept
        beside it so the report can say both numbers instead of implying the course teaches
        fewer words than it does. The sorted list is what a stem is matched against.
        """
        taught = set()
        rows = 0
        for word in Word.objects.filter(level=level, is_published=True):
            taught.add(word.word.lower())
            rows += 1
        return taught, sorted(taught), rows

    def matching_stem(self, spellings, taught_sorted):
        """The first taught word a stem stands for, or ``None``.

        ``all-`` stands for *alle*, *alles*, *allen* — the list marks it with a hyphen
        precisely because the paradigm counts. Exact matching cannot see that, so a stem
        is the one entry kind matched by prefix instead.
        """
        for spelling in spellings:
            for taught in taught_sorted:
                if taught.startswith(spelling):
                    return taught
        return None

    def handle(self, *args, **options):
        code = options["level"]
        level = LanguageLevel.objects.filter(level=code).first()
        if level is None:
            raise CommandError(f"LanguageLevel {code!r} does not exist.")

        data, entries = self.load_entries(options["list"])

        main_entries = []
        sub_total = 0
        for entry in entries:
            if entry.get("tier") == "sub":
                sub_total += 1
            else:
                main_entries.append(entry)

        taught, taught_sorted, taught_rows = self.taught_spellings(level)

        covered = 0
        stem_matched = []
        missing = []
        official_spellings = set()

        for entry in main_entries:
            spellings, is_stem = self.spellings(entry)
            for spelling in spellings:
                official_spellings.add(spelling)

            found = False
            for spelling in spellings:
                if spelling in taught:
                    found = True

            if found:
                covered += 1
                continue

            if is_stem:
                match = self.matching_stem(spellings, taught_sorted)
                if match is not None:
                    covered += 1
                    stem_matched.append((entry["word"], match))
                    continue

            missing.append(entry["word"])

        extra = []
        for spelling in sorted(taught):
            if spelling not in official_spellings:
                extra.append(spelling)

        self.stdout.write(
            f"Official Wortliste: {len(main_entries)} main entries "
            f"(+{sub_total} derivable sub-entries) — {data.get('source', 'source not recorded')}"
        )
        self.stdout.write(f"List file: {options['list']}")
        self.stdout.write(
            f"Course words ({code}, published): {taught_rows} rows, "
            f"{len(taught)} distinct spellings"
        )
        self.stdout.write("")

        share = 0
        if main_entries:
            share = round(100 * covered / len(main_entries), 1)
        self.stdout.write(
            self.style.SUCCESS(f"Covered: {covered} of {len(main_entries)} main entries ({share}%)")
        )
        self.stdout.write(f"Missing: {len(missing)}")
        self.stdout.write(f"Taught beyond the list: {len(extra)} (informational)")

        if stem_matched:
            words = []
            for entry_word, taught_word in stem_matched:
                words.append(f"{entry_word} → {taught_word}")
            self.stdout.write("")
            self.stdout.write(f"Matched as a stem ({len(stem_matched)}): {', '.join(words)}")

        if missing:
            self.stdout.write("")
            self.stdout.write("Missing official entries:")
            shown = missing
            if not options["all"]:
                shown = missing[: options["show"]]
            for word in shown:
                self.stdout.write(f"  {word}")
            if len(shown) < len(missing):
                self.stdout.write(f"  … and {len(missing) - len(shown)} more (use --all)")

        if extra:
            self.stdout.write("")
            self.stdout.write("Taught beyond the list:")
            shown_extra = extra
            if not options["all"]:
                shown_extra = extra[: options["show"]]
            for spelling in shown_extra:
                self.stdout.write(f"  {spelling}")
            if len(shown_extra) < len(extra):
                self.stdout.write(f"  … and {len(extra) - len(shown_extra)} more (use --all)")
