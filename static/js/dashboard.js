/* Dashboard enhancement.
 *
 * The server renders a complete, useful page (start here + the first lessons).
 * This script layers on what only the browser can know: which lessons this
 * device has opened, where to continue, and how far along the learner is.
 * If it never runs, or localStorage is unavailable, the page still works.
 *
 * "Where to continue" and every lesson's status come from `lesson_status.js`,
 * the same module the learning path uses — the two pages cannot disagree.
 */
(() => {
  'use strict';

  const page = document.querySelector('[data-dashboard]');
  const dataEl = document.getElementById('dashboard-lessons');
  const progress = window.GamProgress;
  const Status = window.GamStatus;

  if (!page || !dataEl || !progress || !Status || !page.querySelector('[data-path]')) return;

  let lessons = [];
  try {
    lessons = JSON.parse(dataEl.textContent) || [];
  } catch (_) {
    return;
  }
  if (!lessons.length) return;

  const byId = new Map(lessons.map((lesson) => [lesson.id, lesson]));
  const state = progress.read();
  const summary = progress.summary();
  const status = Status.resolve(lessons, state);
  const current = status.currentId === null ? null : byId.get(status.currentId);

  const text = (selector, value) => {
    const el = page.querySelector(selector);
    if (el) el.textContent = value;
  };

  // ---------------------------------------------------------- next action
  if (current) {
    const reopened = !!state.lessons[current.id];
    text('[data-continue-title]', current.title);
    text('[data-continue-meta]', `درس ${current.order} · ${current.minutes} دقیقه`);
    text('[data-continue-eyebrow]', reopened ? 'قدم بعدی' : 'از اینجا شروع کن');
    const link = page.querySelector('[data-continue-link]');
    if (link) {
      link.textContent = reopened ? `ادامهٔ درس ${current.order}` : `شروع درس ${current.order}`;
      link.href = current.url;
    }
  } else if (status.finished) {
    // Never leave the card offering lesson 1 of a course that is finished.
    text('[data-continue-eyebrow]', 'دوره کامل شد');
    text('[data-continue-title]', 'همهٔ درس‌ها را کامل کرده‌ای');
    text('[data-continue-meta]', `${status.total} درس`);
    const link = page.querySelector('[data-continue-link]');
    if (link) {
      link.textContent = `مرور از درس ${lessons[0].order}`;
      link.href = lessons[0].url;
    }
  }

  // ------------------------------------------------------- progress bar
  // Progress means finished lessons, the same measure the learning path uses.
  text('[data-progress-count]', `${status.completed} از ${status.total} درس کامل‌شده`);
  const fill = page.querySelector('[data-progress-fill]');
  if (fill) fill.style.width = `${status.percent}%`;
  const bar = page.querySelector('[data-progress-bar]');
  if (bar) bar.setAttribute('aria-valuenow', String(status.percent));

  // Only when there is nowhere at all to keep it: a signed-in learner is unaffected by a
  // browser that blocks localStorage.
  if (!progress.available && !progress.serverBacked) {
    text('[data-progress-note]', 'این مرورگر اجازهٔ ذخیره‌سازی محلی نمی‌دهد، پس پیشرفت نگه داشته نمی‌شود.');
  }

  // ---------------------------------------------------- recent activity
  // Only shown when there is real local data behind it.
  const lastOpened = summary.lastLessonId != null ? byId.get(summary.lastLessonId) : null;
  const activity = page.querySelector('[data-activity]');
  if (activity && lastOpened) {
    text('[data-activity-lesson]', `${lastOpened.title} (درس ${lastOpened.order})`);
    text('[data-activity-when]', whenLabel(summary.lastVisitedAt));
    text('[data-activity-started]', `${status.started} درس`);
    activity.hidden = false;
  }

  // ---------------------------------------------------------------- path
  const path = page.querySelector('[data-path]');
  if (path && current) {
    const index = lessons.findIndex((lesson) => lesson.id === current.id);
    const size = Math.min(4, lessons.length);
    // Anchor on the current lesson, but slide back near the end of the course
    // so the preview never collapses to a stub.
    const start = Math.max(0, Math.min(index, lessons.length - size));
    path.replaceChildren(...lessons.slice(start, start + size).map((lesson) => pathRow(lesson, current)));
  }

  /** "امروز" / "دیروز" / "N روز پیش" — nothing longer than a month gets a count. */
  function whenLabel(iso) {
    const time = Date.parse(iso || '');
    if (!time) return '—';
    const days = Math.floor((Date.now() - time) / 86400000);
    if (days <= 0) return 'امروز';
    if (days === 1) return 'دیروز';
    if (days < 30) return `${days} روز پیش`;
    return new Date(time).toLocaleDateString('fa-IR');
  }

  function pathRow(lesson, currentLesson) {
    const rowStatus = status.of(lesson.id);
    const row = document.createElement('li');
    row.className = 'dash-path__item';
    if (currentLesson && lesson.id === currentLesson.id) row.classList.add('is-current');
    row.dataset.pathItem = String(lesson.id);

    const num = document.createElement('span');
    num.className = 'dash-path__num';
    num.setAttribute('aria-hidden', 'true');
    num.textContent = String(lesson.order);

    const title = document.createElement('a');
    title.className = 'dash-path__title';
    // No `dir` is set here. The payload's `title` is `Lesson.display_title`, which is
    // authored Persian (lessons/views.py::_lesson_payload), so it lays out correctly under
    // the page's own RTL direction — a German word inside it stays LTR on its own. The
    // `dir="auto"` that used to be set here was this project's forbidden heuristic in a
    // place the template check could not see: it resolves from the first strong character
    // and reorders mixed content instead of isolating it (vocabulary/text_direction.py).
    title.href = lesson.url;
    title.textContent = lesson.title;

    const meta = document.createElement('span');
    meta.className = 'dash-path__meta';
    meta.textContent = `${lesson.minutes} دقیقه`;

    const state_ = document.createElement('span');
    state_.className = 'dash-path__state';
    state_.dataset.pathState = '';  // same hook the server-rendered rows carry
    if (rowStatus === Status.COMPLETED) {
      state_.textContent = 'کامل‌شده';
      state_.classList.add('is-done');
    } else if (rowStatus === Status.CURRENT || rowStatus === Status.STARTED) {
      state_.textContent = 'در حال یادگیری';
      state_.classList.add('is-started');
    } else {
      state_.textContent = 'شروع نشده';
    }

    const aside = document.createElement('span');
    aside.className = 'dash-path__aside';
    aside.append(meta, state_);

    row.append(num, title, aside);
    return row;
  }
})();
