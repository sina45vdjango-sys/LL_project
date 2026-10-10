"""Serve ``MEDIA_ROOT`` with HTTP Range support.

Why this module exists
----------------------
``django.views.static.serve`` sends the whole file with a ``200`` and never reads the
``Range`` request header. That is fine for a stylesheet and useless for audio: an
``<audio>`` element asks for ``Range: bytes=…`` in order to seek, gets the whole file
back with ``200`` instead of a ``206`` and a ``Content-Range``, and the scrub bar snaps
back to where it was. This project generates long clips — grammar topics and lesson
content run 13-40 seconds — so without this the player could start and never be moved.
Measured before this module existed: a request for ``bytes=100-199`` of an 11,232-byte
word clip answered ``200`` with all 11,232 bytes.

This is only for the two local cases: ``DEBUG``, and ``DJANGO_SERVE_MEDIA`` for running
the project on a laptop for other people on the LAN. A real deployment puts nginx or
Apache in front, and those do Range, caching and ETags properly; see ``config/urls.py``.

It is deliberately a small function rather than a file-server class. What it adds over
``django.views.static.serve`` is Range, and it keeps that view's two behaviours that
matter here: ``If-Modified-Since`` (so audio is not re-downloaded) and a path that
cannot climb out of ``MEDIA_ROOT``.
"""

import mimetypes
import os
import re

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotModified
from django.utils.http import http_date, parse_http_date_safe

#: One ``Range: bytes=…`` value. The three shapes a browser sends are ``bytes=100-``
#: (from an offset to the end), ``bytes=-100`` (the last hundred bytes) and
#: ``bytes=100-199``. A header with several ranges in it is ignored rather than guessed
#: at — one range is all any media element asks for.
RANGE_PATTERN = re.compile(r"^bytes=(\d*)-(\d*)$")


def serve_media(request, path):
    """Send one file from ``MEDIA_ROOT``, answering a Range request when there is one.

    ``path`` is what the URL pattern captures after ``/media/``. Anything that is not a
    real file inside ``MEDIA_ROOT`` is a 404.
    """
    root = os.path.realpath(settings.MEDIA_ROOT)
    target = os.path.realpath(os.path.join(root, path))

    # A path that climbs out of MEDIA_ROOT (``..``) is not ours to serve. Comparing the
    # real paths also stops a symlink inside MEDIA_ROOT from reaching outside it.
    if target != root and not target.startswith(root + os.sep):
        raise Http404("media file not found")
    if not os.path.isfile(target):
        raise Http404("media file not found")

    size = os.path.getsize(target)
    modified = os.path.getmtime(target)

    # Conditional request first, the way every web server orders it: a browser that
    # already has the clip is told to keep it, and seeking then works from its copy.
    since = parse_http_date_safe(request.headers.get("If-Modified-Since", ""))
    if since is not None and int(modified) <= since:
        return HttpResponseNotModified()

    content_type, _ = mimetypes.guess_type(target)
    if content_type is None:
        content_type = "application/octet-stream"

    match = RANGE_PATTERN.match(request.headers.get("Range", ""))

    if match is None:
        # No usable Range: the whole file, exactly as ``static.serve`` served it.
        # ``Accept-Ranges`` is the header that tells the browser it may ask for one.
        response = FileResponse(open(target, "rb"), content_type=content_type)
        response["Content-Length"] = size
        response["Last-Modified"] = http_date(modified)
        response["Accept-Ranges"] = "bytes"
        return response

    first = match.group(1)
    last = match.group(2)

    if first == "" and last == "":
        # ``bytes=-`` names no bytes at all: unsatisfiable, not "send everything".
        start = 0
        end = -1
    elif first == "":
        # ``bytes=-N``: the last N bytes.
        wanted = int(last)
        if wanted > size:
            wanted = size
        start = size - wanted
        end = size - 1
    else:
        start = int(first)
        if last == "":
            end = size - 1
        else:
            end = int(last)
            if end > size - 1:
                end = size - 1

    # A range that starts past the end of the file is unsatisfiable. The answer is a
    # 416 carrying the real size, so the browser can recover instead of retrying the
    # same impossible range forever.
    if start >= size or end < start:
        response = HttpResponse(status=416)
        response["Content-Range"] = "bytes */" + str(size)
        response["Accept-Ranges"] = "bytes"
        return response

    length = end - start + 1

    if request.method == "HEAD":
        # A HEAD answer carries the same headers and no body.
        response = HttpResponse(content_type=content_type)
    elif start == 0 and length == size:
        # The range is the whole file — a browser asking ``bytes=0-`` does this. Stream
        # it from disk instead of reading it into memory.
        response = FileResponse(open(target, "rb"), status=206, content_type=content_type)
    else:
        # A partial range is a seek window, so it is small by definition: read it and
        # send it as one piece.
        with open(target, "rb") as stream:
            stream.seek(start)
            response = HttpResponse(
                stream.read(length), status=206, content_type=content_type
            )

    response["Content-Length"] = length
    response["Content-Range"] = "bytes " + str(start) + "-" + str(end) + "/" + str(size)
    response["Last-Modified"] = http_date(modified)
    response["Accept-Ranges"] = "bytes"
    return response
