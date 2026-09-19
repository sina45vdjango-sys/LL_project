"""Generate German speech for published grammars which have no audio.

Grammar explanations are written for Persian speakers, so the German material
(paradigms and examples) sits on the same lines as the Persian rule text. Only the
German remainder is narrated -- ``vocabulary.german_text`` does that extraction.
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

from vocabulary.german_text import spoken_text
from vocabulary.models import Grammar

VOICE = "de-DE-KatjaNeural"


class Command(BaseCommand):
    help = "Generate German MP3 audio for published grammars missing audio."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List pending count without changes.")
        parser.add_argument("--retries", type=int, default=2, help="Additional attempts per grammar.")
        parser.add_argument("--limit", type=int, default=0, help="Maximum rows; zero means all.")
        parser.add_argument("--workers", type=int, default=1, help="Concurrent synthesis workers (1-8).")

    def generate(self, grammar, retries):
        directory = Path(settings.MEDIA_ROOT) / "grammars/audio"
        directory.mkdir(parents=True, exist_ok=True)
        last_error = None
        for attempt in range(retries + 1):
            fd, name = tempfile.mkstemp(prefix=f"grammar-{grammar.pk}-", suffix=".mp3", dir=directory)
            os.close(fd)
            path = Path(name)
            try:
                asyncio.run(edge_tts.Communicate(grammar.text, voice=VOICE).save(str(path)))
                subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path),
                                "-f", "null", "-"], check=True, capture_output=True, timeout=60)
                return path
            except Exception as exc:
                path.unlink(missing_ok=True)
                last_error = exc
                if attempt < retries:
                    time.sleep(min(2 ** attempt, 8))
        raise RuntimeError(str(last_error)) from last_error

    def handle(self, *args, **options):
        if not 1 <= options["workers"] <= 8 or not 0 <= options["retries"] <= 5 or options["limit"] < 0:
            raise CommandError("workers must be 1-8, retries 0-5, limit nonnegative")
        pending = Grammar.objects.filter(is_published=True).filter(
            Q(audio="") | Q(audio__isnull=True)
        ).order_by("pk")
        rows, skipped = [], []
        for pk, title, explanation in pending.values_list("pk", "title", "explanation"):
            text = spoken_text(title, explanation)
            if text:
                rows.append(SimpleNamespace(pk=pk, text=text))
            else:
                skipped.append(pk)
        self.stdout.write(f"Pending: {len(rows)}")
        if skipped:
            self.stdout.write(f"Skipped, no German text: {skipped}")
        if options["dry_run"]:
            return
        if options["limit"]:
            rows = rows[:options["limit"]]
        generated, failures = 0, []

        def publish(grammar, path):
            relpath = f"grammars/audio/{path.name}"
            updated = Grammar.objects.filter(pk=grammar.pk, is_published=True).filter(
                Q(audio="") | Q(audio__isnull=True)
            ).update(audio=relpath)
            if not updated:
                path.unlink(missing_ok=True)
            else:
                self.stdout.write(f"OK {grammar.pk} {relpath}")
                self.stdout.flush()
            return updated

        # Workers do network/file work only; DB publication stays on this thread.
        with ThreadPoolExecutor(max_workers=options["workers"]) as pool:
            jobs = {pool.submit(self.generate, row, options["retries"]): row for row in rows} if options["workers"] > 1 else {}
            results = ((jobs[job], job) for job in as_completed(jobs)) if jobs else ((row, None) for row in rows)
            for grammar, job in results:
                path = None
                try:
                    path = job.result() if job else self.generate(grammar, options["retries"])
                    generated += publish(grammar, path)
                except Exception as exc:
                    if path is not None:
                        path.unlink(missing_ok=True)
                    failures.append(grammar.pk)
                    self.stderr.write(f"FAIL {grammar.pk}: {exc}")
        self.stdout.write(f"Generated: {generated}; failures: {len(failures)}")
        if failures:
            raise CommandError(f"Failed grammar IDs: {failures}")
