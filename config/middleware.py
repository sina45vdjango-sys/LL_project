"""The one response Django renders without a template: 405.

Django ships a default view for 403, 404 and 500, and each of those looks for a template
in the project (``templates/403.html`` and friends), so those three pages are the site's
own pages with the sidebar, font and colours. There is no such default for 405: a view
that only implements ``post`` answers a ``GET`` with ``HttpResponseNotAllowed``, whose body
is empty. A learner who opens ``/exam/start/`` by hand — an address that is a form action,
not a page — therefore saw a completely blank screen, which is the one thing a broken page
and a working page cannot be told apart by.

So this middleware does the missing half of what Django does for the other status codes:
when a response is a 405, it renders ``templates/405.html`` in the site shell instead of
the empty body.

Three rules keep it narrow and safe:

* **Only 405.** Everything else passes through untouched. In particular the JSON
  endpoints (``exercises:exercise-submit`` and the exam's own) keep answering with the
  JSON they were written to answer with — a fetch() that calls one with the wrong method
  must not suddenly receive a full HTML page.
* **Only HTML.** A request that did not ask for HTML is left alone, so a script, a curl
  call or an API client still sees the plain empty 405 it can interpret.
* **The status stays 405.** The reason the response exists is preserved; only the body
  changes.
"""

from django.shortcuts import render


class MethodNotAllowedMiddleware:
    """Render ``405.html`` for an HTML request that Django answered with a bare 405."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code != 405:
            return response

        if not wants_html(request):
            return response

        return render(request, "405.html", status=405)


def wants_html(request):
    """Whether this request asked for HTML rather than for data.

    Read from the ``Accept`` header rather than from the URL: the same address answers a
    browser navigation and a fetch() call, and only the browser wants a page back. A
    request with no ``Accept`` at all (a plain HTTP client) is treated as not wanting HTML.
    """
    accept = request.headers.get("Accept", "")

    if "text/html" in accept:
        return True

    return False
