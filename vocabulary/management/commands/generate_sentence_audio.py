"""Generate German speech for published sentences which have no audio."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from types import SimpleNamespace
import os
import tempfile
import time
from pathlib import Path

import subprocess
from django.core.management.base import CommandError

import edge_tts

from django.conf import settings
from django.core.management.base import BaseCommand

from django.db.models import Q

from vocabulary.models import Sentence


class Command(BaseCommand):
    help = "Generate German MP3 audio for published sentences missing audio."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List pending count without changes.")
        parser.add_argument("--retries", type=int, default=2, help="Additional attempts per sentence.")
        parser.add_argument("--limit", type=int, default=0, help="Maximum rows; zero means all.")
        parser.add_argument("--workers", type=int, default=1, help="Concurrent synthesis workers (1–8).")

    def generate(self, sentence, retries):
        directory = Path(settings.MEDIA_ROOT) / "sentences/audio"
        directory.mkdir(parents=True, exist_ok=True)
        last_error = None
        for attempt in range(retries + 1):
            fd, name = tempfile.mkstemp(prefix=f"sentence-{sentence.pk}-", suffix=".mp3", dir=directory)
            os.close(fd)
            path = Path(name)
            try:
                asyncio.run(edge_tts.Communicate(sentence.text, voice="de-DE-KatjaNeural").save(str(path)))
                subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path),
                                "-f", "null", "-"], check=True, capture_output=True, timeout=30)
                return path
            except Exception as exc:
                path.unlink(missing_ok=True)
                last_error = exc
                if attempt < retries:
                    time.sleep(min(2 ** attempt, 8))
        raise RuntimeError(str(last_error)) from last_error


    def handle(self, *args, **options):
        if not 1 <= options["workers"] <= 8 or not 0 <= options["retries"] <= 5 or options["limit"] < 0:
            raise CommandError("workers must be 1–8, retries 0–5, limit nonnegative")
        pending = Sentence.objects.filter(is_published=True).filter(Q(audio="") | Q(audio__isnull=True)).order_by("pk")
        self.stdout.write(f"Pending: {pending.count()}")
        if options["dry_run"]:
            return
        if options["limit"]:
            pending = pending[:options["limit"]]
        rows = [SimpleNamespace(pk=pk, text=text) for pk, text in pending.values_list("pk", "text")]
        generated, failures = 0, []

        def publish(sentence, path):
            relpath = f"sentences/audio/{path.name}"
            updated = Sentence.objects.filter(pk=sentence.pk, is_published=True, text=sentence.text).filter(
                Q(audio="") | Q(audio__isnull=True)
            ).update(audio=relpath)
            if not updated:
                path.unlink(missing_ok=True)
            else:
                self.stdout.write(f"OK {sentence.pk} {relpath}")
                self.stdout.flush()
            return updated

        # Workers do network/file work only; DB publication stays on this thread.
        with ThreadPoolExecutor(max_workers=options["workers"]) as pool:
            jobs = {pool.submit(self.generate, row, options["retries"]): row for row in rows} if options["workers"] > 1 else {}
            results = ((jobs[job], job) for job in as_completed(jobs)) if jobs else ((row, None) for row in rows)
            for sentence, job in results:
                path = None
                try:
                    path = job.result() if job else self.generate(sentence, options["retries"])
                    generated += publish(sentence, path)
                except Exception as exc:
                    if path is not None:
                        path.unlink(missing_ok=True)
                    failures.append(sentence.pk)
                    self.stderr.write(f"FAIL {sentence.pk}: {exc}")
        self.stdout.write(f"Generated: {generated}; failures: {len(failures)}")
        if failures:
            raise CommandError(f"Failed sentence IDs: {failures}")


