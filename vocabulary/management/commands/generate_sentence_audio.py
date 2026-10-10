"""Generate German speech for published sentences which have no audio.

A sentence needs no extraction step: its ``text`` field is already pure German, so it
is narrated as it stands. The voice and the speaking rate come from
``vocabulary.audio``, the one place they are set.
"""

import asyncio
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

import edge_tts
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from vocabulary import audio
from vocabulary.models import Sentence


class Command(BaseCommand):
    help = "Generate German MP3 audio for published sentences missing audio."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List pending count without changes.")
        parser.add_argument("--retries", type=int, default=2, help="Additional attempts per sentence.")
        parser.add_argument("--limit", type=int, default=0, help="Maximum rows; zero means all.")
        parser.add_argument("--workers", type=int, default=1, help="Concurrent synthesis workers (1-8).")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-narrate rows that already have audio, replacing each file in place.",
        )

    def generate(self, sentence, retries):
        directory = Path(settings.MEDIA_ROOT) / "sentences/audio"
        directory.mkdir(parents=True, exist_ok=True)
        last_error = None
        for attempt in range(retries + 1):
            fd, name = tempfile.mkstemp(prefix=f"sentence-{sentence.pk}-", suffix=".mp3", dir=directory)
            os.close(fd)
            staging = Path(name)
            try:
                asyncio.run(
                    edge_tts.Communicate(sentence.text, voice=audio.VOICE, rate=audio.RATE).save(str(staging))
                )

                # The file must be a real MP3, so ffmpeg reads it once as a check.
                command = [
                    "ffmpeg", "-v", "error", "-xerror",
                    "-i", str(staging), "-f", "null", "-",
                ]
                subprocess.run(command, check=True, capture_output=True, timeout=30)
                if sentence.existing:
                    # Re-narrating: replace the file the row already points at, so the old
                    # recording is gone rather than left behind as an orphan. The replace
                    # happens only after the check above passed, so a failure leaves the
                    # existing audio untouched.
                    target = Path(settings.MEDIA_ROOT) / sentence.existing
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
        pending = Sentence.objects.filter(is_published=True)
        if not options["force"]:
            pending = pending.filter(Q(audio="") | Q(audio__isnull=True))
        pending = pending.order_by("pk")
        self.stdout.write(f"Pending: {pending.count()}")
        if options["dry_run"]:
            return
        if options["limit"]:
            pending = pending[:options["limit"]]
        rows = []
        for pk, text, existing in pending.values_list("pk", "text", "audio"):
            # ``text`` is the sentence's own field, narrated as it stands.
            rows.append(SimpleNamespace(pk=pk, text=text, existing=existing or ""))
        generated = 0
        failures = []

        def publish(sentence, path):
            relpath = f"sentences/audio/{path.name}"
            updated = Sentence.objects.filter(pk=sentence.pk, is_published=True, text=sentence.text)
            if sentence.existing:
                # Only claim the row if it still points at the file just replaced.
                updated = updated.filter(audio=sentence.existing)
            else:
                updated = updated.filter(Q(audio="") | Q(audio__isnull=True))
            updated = updated.update(audio=relpath)
            if not updated:
                path.unlink(missing_ok=True)
            else:
                self.stdout.write(f"OK {sentence.pk} {relpath}")
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
                    sentence = jobs[job]
                    path = None
                    try:
                        path = job.result()
                        if publish(sentence, path):
                            generated += 1
                    except Exception as exc:
                        if path is not None:
                            path.unlink(missing_ok=True)
                        failures.append(sentence.pk)
                        self.stderr.write(f"FAIL {sentence.pk}: {exc}")
        else:
            for sentence in rows:
                path = None
                try:
                    path = self.generate(sentence, options["retries"])
                    if publish(sentence, path):
                        generated += 1
                except Exception as exc:
                    if path is not None:
                        path.unlink(missing_ok=True)
                    failures.append(sentence.pk)
                    self.stderr.write(f"FAIL {sentence.pk}: {exc}")
        self.stdout.write(f"Generated: {generated}; failures: {len(failures)}")
        if failures:
            raise CommandError(f"Failed sentence IDs: {failures}")


