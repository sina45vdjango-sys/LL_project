"""Import the A1 German vocabulary list and generate audio for every word.

The word data lives in JSON files under ``vocabulary/data/`` and is loaded with::

    python manage.py import_a1_words

Audio is produced once per distinct spoken text with Microsoft Edge TTS and then
written to ``MEDIA_ROOT/words/audio/``. After that the files are served locally
by Django -- no internet connection is needed to use them.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from lessons.models import LanguageLevel
from vocabulary.models import Word

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

DEFAULT_VOICE = "de-DE-KatjaNeural"

#: level -> (title, order)
LEVELS = {
    "A1": ("A1 - Beginner", 1),
    "A2": ("A2 - Elementary", 2),
    "B1": ("B1 - Intermediate", 3),
    "B2": ("B2 - Upper intermediate", 4),
    "C1": ("C1 - Advanced", 5),
    "C2": ("C2 - Proficiency", 6),
}

#: JSON-friendly word type -> Word.WordType value.
#: Short and long spellings are both accepted so the data files stay readable.
TYPE_MAP = {
    "NOUN": Word.WordType.NOUN,
    "VERB": Word.WordType.VERB,
    "ADJ": Word.WordType.ADJECTIVE,
    "ADJECTIVE": Word.WordType.ADJECTIVE,
    "ADV": Word.WordType.ADVERB,
    "ADVERB": Word.WordType.ADVERB,
    "PREP": Word.WordType.PREPOSITION,
    "PREPOSITION": Word.WordType.PREPOSITION,
    "PRON": Word.WordType.PRONOUN,
    "PRONOUN": Word.WordType.PRONOUN,
    "OTHER": Word.WordType.OTHER,
}

GENDER_MAP = {
    "M": Word.Gender.MASCULINE,
    "F": Word.Gender.FEMININE,
    "N": Word.Gender.NEUTER,
}

AUX_MAP = {
    "haben": Word.PerfectAuxiliary.HABEN,
    "sein": Word.PerfectAuxiliary.SEIN,
}

UMLAUTS = {
    "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
}


def audio_filename(text: str) -> str:
    """A stable, filesystem-safe filename for the spoken text."""
    ascii_text = "".join(UMLAUTS.get(ch, ch) for ch in text)
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in ascii_text).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{slug[:60]}-{digest}.mp3"


def spoken_text(entry: dict, word_type: str) -> str:
    """What the audio should say. Nouns are spoken with their article."""
    article = (entry.get("article") or "").strip()
    word = entry["word"].strip()
    if word_type == "NOUN" and article:
        return f"{article} {word}"
    return word


class Command(BaseCommand):
    help = "Import A1 words from vocabulary/data/*.json and generate their audio."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data",
            action="append",
            default=None,
            help="JSON file(s) or directory to load. Defaults to vocabulary/data/*.json",
        )
        parser.add_argument("--level", default="A1", help="Language level code (default A1).")
        parser.add_argument(
            "--no-audio",
            action="store_true",
            help="Import words only, do not generate audio.",
        )
        parser.add_argument(
            "--force-audio",
            action="store_true",
            help="Regenerate audio even if the file already exists.",
        )
        parser.add_argument(
            "--voice",
            default=DEFAULT_VOICE,
            help=f"Edge TTS voice name (default {DEFAULT_VOICE}).",
        )
        parser.add_argument(
            "--concurrency",
            type=int,
            default=6,
            help="How many audio files to generate in parallel (default 6).",
        )
        parser.add_argument(
            "--unpublished",
            action="store_true",
            help="Leave the imported words unpublished.",
        )

    # ------------------------------------------------------------------ helpers

    def get_level(self, code: str) -> LanguageLevel:
        if code not in LEVELS:
            raise CommandError(f"Unknown level {code!r}. Known: {', '.join(LEVELS)}")
        title, order = LEVELS[code]
        level, _ = LanguageLevel.objects.get_or_create(
            level=code,
            defaults={"title": title, "order": order},
        )
        return level

    def resolve_files(self, raw: list[str] | None) -> list[Path]:
        if not raw:
            return sorted(DATA_DIR.glob("*.json"))
        files: list[Path] = []
        for item in raw:
            path = Path(item)
            if path.is_dir():
                files.extend(sorted(path.glob("*.json")))
            elif path.exists():
                files.append(path)
            else:
                raise CommandError(f"No such data file or directory: {path}")
        return files

    def load_entries(self, files: list[Path]) -> list[dict]:
        entries: list[dict] = []
        for path in files:
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
            items = payload["words"] if isinstance(payload, dict) else payload
            for item in items:
                item.setdefault("source", path.name)
                entries.append(item)
        return entries

    # ------------------------------------------------------------------- import

    def import_words(self, entries, level, publish: bool):
        created = updated = skipped = 0
        seen: set[tuple] = set()
        for entry in entries:
            raw_type = (entry.get("type") or "OTHER").upper()
            if raw_type not in TYPE_MAP:
                self.stderr.write(f"  ! unknown type {raw_type!r} for {entry['word']!r}")
                raw_type = "OTHER"

            gender = entry.get("gender") or None
            if gender:
                gender = GENDER_MAP.get(gender.upper())
            if raw_type != "NOUN":
                gender = None

            defaults = {
                "article": entry.get("article", "") or "",
                "plural": entry.get("plural") or None,
                "meaning_fa": entry.get("fa", "").strip(),
                "meaning_en": entry.get("en", "") or "",
                "pronunciation": entry.get("ipa", "") or "",
                "is_separable": bool(entry.get("separable", False)),
                "perfect_auxiliary": AUX_MAP.get((entry.get("aux") or "").lower()),
                "is_published": publish,
            }

            key = (entry["word"], TYPE_MAP[raw_type], gender)
            if key in seen:
                skipped += 1
                continue
            seen.add(key)

            word, was_created = Word.objects.update_or_create(
                word=entry["word"],
                word_type=TYPE_MAP[raw_type],
                gender=gender,
                level=level,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1
        return created, updated, skipped

    # -------------------------------------------------------------------- audio

    def generate_audio(self, entries, level, voice, concurrency, force):
        target_dir = Path(settings.MEDIA_ROOT) / "words" / "audio"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Map spoken text -> filename, one job per distinct text.
        jobs: dict[str, str] = {}
        for entry in entries:
            raw_type = (entry.get("type") or "OTHER").upper()
            text = spoken_text(entry, raw_type)
            jobs.setdefault(text, audio_filename(text))

        pending = {
            text: name
            for text, name in jobs.items()
            if force or not (target_dir / name).exists()
        }
        self.stdout.write(
            f"Audio: {len(jobs)} distinct clips, {len(jobs) - len(pending)} already on disk, "
            f"{len(pending)} to generate."
        )

        if pending:
            failures = asyncio.run(self._render_all(pending, target_dir, voice, concurrency))
            for text, error in failures:
                self.stderr.write(f"  ! audio failed for {text!r}: {error}")
            if failures:
                self.stdout.write(f"Audio: {len(pending) - len(failures)} generated, {len(failures)} failed.")

        linked = 0
        with transaction.atomic():
            for entry in entries:
                raw_type = (entry.get("type") or "OTHER").upper()
                text = spoken_text(entry, raw_type)
                name = jobs[text]
                if not (target_dir / name).exists():
                    continue
                gender = entry.get("gender") or None
                if gender:
                    gender = GENDER_MAP.get(gender.upper())
                if raw_type != "NOUN":
                    gender = None
                Word.objects.filter(
                    word=entry["word"],
                    word_type=TYPE_MAP.get(raw_type, Word.WordType.OTHER),
                    gender=gender,
                    level=level,
                ).update(audio=f"words/audio/{name}")
                linked += 1
        return linked

    async def _render_all(self, pending, target_dir, voice, concurrency):
        import edge_tts

        semaphore = asyncio.Semaphore(max(1, concurrency))
        failures: list[tuple[str, str]] = []
        done = 0

        async def render(text: str, name: str):
            nonlocal done
            async with semaphore:
                path = target_dir / name
                last_error = "unknown error"
                for attempt in range(3):
                    try:
                        communicate = edge_tts.Communicate(text, voice)
                        await communicate.save(str(path))
                        if path.stat().st_size > 0:
                            break
                        last_error = "empty file"
                    except Exception as exc:  # noqa: BLE001 - surfaced to the caller
                        last_error = f"{type(exc).__name__}: {exc}"
                    await asyncio.sleep(1 + attempt)
                else:
                    failures.append((text, last_error))
                    if path.exists():
                        path.unlink()
                    return
                done += 1
                if done % 25 == 0:
                    self.stdout.write(f"  ... {done}/{len(pending)} clips generated")

        await asyncio.gather(*(render(text, name) for text, name in pending.items()))
        return failures

    # ------------------------------------------------------------------- handle

    def handle(self, *args, **options):
        files = self.resolve_files(options["data"])
        if not files:
            raise CommandError(f"No JSON data files found in {DATA_DIR}")

        entries = self.load_entries(files)
        if not entries:
            raise CommandError("The data files contain no words.")

        level = self.get_level(options["level"])
        publish = not options["unpublished"]

        self.stdout.write(f"Loading {len(entries)} defined entries from {len(files)} file(s).")
        created, updated, skipped = self.import_words(entries, level, publish)
        self.stdout.write(
            self.style.SUCCESS(
                f"Words: {created} created, {updated} updated, {skipped} duplicate entries skipped."
            )
        )

        if options["no_audio"]:
            total = Word.objects.filter(level=level).count()
            self.stdout.write(f"Total words for {level.level}: {total} (audio generation skipped)")
            return

        linked = self.generate_audio(
            entries,
            level,
            voice=options["voice"],
            concurrency=options["concurrency"],
            force=options["force_audio"],
        )
        total = Word.objects.filter(level=level).count()
        with_audio = Word.objects.filter(level=level, audio__isnull=False).exclude(audio="").count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {linked} rows linked to audio. "
                f"Level {level.level}: {total} words, {with_audio} with audio."
            )
        )
