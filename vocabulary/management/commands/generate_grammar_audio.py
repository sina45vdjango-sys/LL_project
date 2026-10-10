"""Generate German speech for published grammars which have no audio.

Grammar explanations are written for Persian speakers, so the German material
(paradigms and examples) sits on the same lines as the Persian rule text. Only the
German remainder is narrated -- ``vocabulary.german_text`` does that extraction.

A grammar row's own text lives in its ``explanation`` field; there is no ``text``
field. The synthesiser is fed the *spoken* text -- what ``spoken_text`` returned after
stripping the Persian and the closing English note -- which is why each job carries it
under ``spoken`` and not under a field name. The voice and the speaking rate come from
``vocabulary.audio``, the one place they are set.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import os
import subprocess
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import edge_tts

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from vocabulary import audio
from vocabulary.german_text import spoken_text
from vocabulary.models import Grammar


class Command(BaseCommand):
    help = "Generate German MP3 audio for published grammars missing audio."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List pending count without changes.")
        parser.add_argument("--retries", type=int, default=2, help="Additional attempts per grammar.")
        parser.add_argument("--limit", type=int, default=0, help="Maximum rows; zero means all.")
        parser.add_argument("--workers", type=int, default=1, help="Concurrent synthesis workers (1-8).")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-narrate rows that already have audio, replacing each file in place.",
        )

    def generate(self, grammar, retries):
        directory = Path(settings.MEDIA_ROOT) / "grammars/audio"
        directory.mkdir(parents=True, exist_ok=True)
        last_error = None
        for attempt in range(retries + 1):
            fd, name = tempfile.mkstemp(prefix=f"grammar-{grammar.pk}-", suffix=".mp3", dir=directory)
            os.close(fd)
            staging = Path(name)
            try:
                asyncio.run(
                    edge_tts.Communicate(grammar.spoken, voice=audio.VOICE, rate=audio.RATE).save(str(staging))
                )

                # The file must be a real MP3, so ffmpeg reads it once as a check.
                command = [
                    "ffmpeg", "-v", "error", "-xerror",
                    "-i", str(staging), "-f", "null", "-",
                ]
                subprocess.run(command, check=True, capture_output=True, timeout=60)
                if grammar.existing:
                    # Re-narrating: replace the file the row already points at, so the old
                    # recording is gone rather than left behind as an orphan. The replace
                    # happens only after the check above passed, so a failure leaves the
                    # existing audio untouched.
                    target = Path(settings.MEDIA_ROOT) / grammar.existing
                    os.replace(staging, target)
                    return target
                return staging
            except Exception as exc:
                staging.unlink(missing_ok=True)
                last_error = exc
                if attempt < retries:
                    time.sleep(min(2 ** attempt, 8))
        raise RuntimeError(str(last_error)) from last_error

    def handle(self, *args, **options):
        if not 1 <= options["workers"] <= 8 or not 0 <= options["retries"] <= 5 or options["limit"] < 0:
            raise CommandError("workers must be 1-8, retries 0-5, limit nonnegative")
        pending = Grammar.objects.filter(is_published=True)
        if not options["force"]:
            pending = pending.filter(Q(audio="") | Q(audio__isnull=True))
        pending = pending.order_by("pk")
        rows = []
        skipped = []
        for pk, title, explanation, existing in pending.values_list("pk", "title", "explanation", "audio"):
            text = spoken_text(title, explanation)
            if text:
                # ``spoken``, not ``text``: this is the narration, not the grammar's field.
                rows.append(SimpleNamespace(pk=pk, spoken=text, existing=existing or ""))
            else:
                skipped.append(pk)
        self.stdout.write(f"Pending: {len(rows)}")
        if skipped:
            self.stdout.write(f"Skipped, no German text: {skipped}")
        if options["dry_run"]:
            return
        if options["limit"]:
            rows = rows[:options["limit"]]
        generated = 0
        failures = []

        def publish(grammar, path):
            relpath = f"grammars/audio/{path.name}"
            updated = Grammar.objects.filter(pk=grammar.pk, is_published=True)
            if grammar.existing:
                # Only claim the row if it still points at the file just replaced.
                updated = updated.filter(audio=grammar.existing)
            else:
                updated = updated.filter(Q(audio="") | Q(audio__isnull=True))
            updated = updated.update(audio=relpath)
            if not updated:
                path.unlink(missing_ok=True)
            else:
                self.stdout.write(f"OK {grammar.pk} {relpath}")
                self.stdout.flush()
            return updated

        # Workers do network/file work only; DB publication stays on this thread.
        if options["workers"] > 1:
            with ThreadPoolExecutor(max_workers=options["workers"]) as pool:
                jobs = {}
                for row in rows:
                    job = pool.submit(self.generate, row, options["retries"])
                    jobs[job] = row

                for job in as_completed(jobs):
                    grammar = jobs[job]
                    path = None
                    try:
                        path = job.result()
                        if publish(grammar, path):
                            generated += 1
                    except Exception as exc:
                        if path is not None:
                            path.unlink(missing_ok=True)
                        failures.append(grammar.pk)
                        self.stderr.write(f"FAIL {grammar.pk}: {exc}")
        else:
            for grammar in rows:
                path = None
                try:
                    path = self.generate(grammar, options["retries"])
                    if publish(grammar, path):
                        generated += 1
                except Exception as exc:
                    if path is not None:
                        path.unlink(missing_ok=True)
                    failures.append(grammar.pk)
                    self.stderr.write(f"FAIL {grammar.pk}: {exc}")
        self.stdout.write(f"Generated: {generated}; failures: {len(failures)}")
        if failures:
            raise CommandError(f"Failed grammar IDs: {failures}")
