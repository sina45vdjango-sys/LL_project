/* Learning path enhancement.
 *
 * The server already renders the whole trail — every step, in order, each with a
 * real title, duration and link — so the page is fully usable and readable with
 * this script absent or blocked. What only the browser can know is which steps
 * are done and which one is next; that is what gets painted here, from
 * `progress.js` (storage) and `lesson_status.js` (classification).
 *
 * Copy note: the status labels and calls to action differ from the dashboard's
 * on purpose — this page talks about "the next step" rather than "continue" —
 * but the *decision* about which step that is comes from the shared module.
 */
(() => {
  'use strict';

  const root = document.querySelector('[data-path-root]');
  const dataEl = document.getElementById('path-lessons');
  const progress = window.GamProgress;
  const Status = window.GamStatus;

  if (!root || !dataEl || !progress || !Status) return;

  let lessons = [];
  try {
    lessons = JSON.parse(dataEl.textContent) || [];
  } catch (_) {
    return;
  }
  if (!lessons.length) return;

  const byId = new Map(lessons.map((lesson) => [lesson.id, lesson]));
  const state = progress.read();
  const status = Status.resolve(lessons, state);
  const label = {
    [Status.COMPLETED]: 'کامل‌شده',
    [Status.CURRENT]: 'قدم بعدی',
    [Status.STARTED]: 'شروع‌شده',
    [Status.UPCOMING]: 'شروع نشده',
    [Status.AVAILABLE]: 'شروع نشده',
  };
  const reopened = (id) => !!state.lessons[id];

  // ------------------------------------------------------------- the steps
  root.querySelectorAll('[data-lesson]').forEach((step) => {
    const lesson = byId.get(Number(step.dataset.lesson));
    if (!lesson) return;

    const stepStatus = status.of(lesson.id);
    step.classList.add(`is-${stepStatus}`);

    const chip = step.querySelector('[data-step-state]');
    if (chip) chip.textContent = label[stepStatus];

    const cta = step.querySelector('[data-step-cta]');
    if (!cta) return;
    if (stepStatus === Status.COMPLETED) {
      cta.textContent = 'مرور درس';
    } else if (stepStatus === Status.CURRENT || stepStatus === Status.STARTED) {
      cta.textContent = reopened(lesson.id) ? `ادامهٔ درس ${lesson.order}` : `شروع درس ${lesson.order}`;
    } else {
      cta.textContent = 'مشاهدهٔ درس';
    }
  });

  // --------------------------------------------------------- overall progress
  // Progress means finished lessons, the same measure the dashboard uses.
  const bar = root.querySelector('[data-path-bar]');
  if (bar) bar.setAttribute('aria-valuenow', String(status.percent));
  const fill = root.querySelector('[data-path-fill]');
  if (fill) fill.style.width = `${status.percent}%`;

  const note = root.querySelector('[data-path-progress]');
  if (note) note.textContent = progressNote();

  // ------------------------------------------------------------- next step
  const nextTitle = root.querySelector('[data-path-next-title]');
  const nextLink = root.querySelector('[data-path-next-link]');
  const current = status.currentId === null ? null : byId.get(status.currentId);
  if (current) {
    if (nextTitle) nextTitle.textContent = current.title;
    if (nextLink) {
      nextLink.textContent = reopened(current.id) ? `ادامهٔ درس ${current.order}` : `شروع درس ${current.order}`;
      nextLink.href = current.url;
    }
  } else if (status.finished && nextTitle && nextLink) {
    nextTitle.textContent = 'همهٔ درس‌ها را کامل کرده‌ای';
    nextLink.textContent = `مرور از درس ${lessons[0].order}`;
    nextLink.href = lessons[0].url;
  }

  // --------------------------------------------------- per-course counters
  // Hidden until there is something to say, so a new learner sees no noise.
  root.querySelectorAll('[data-group-done]').forEach((el) => {
    const list = root.querySelector(`[data-steps-group="${el.dataset.groupDone}"]`);
    if (!list) return;
    const steps = list.querySelectorAll('[data-lesson]').length;
    const done = list.querySelectorAll('.path-step.is-completed').length;
    if (!done) return;
    el.textContent = `${done} از ${steps} کامل`;
    el.hidden = false;
  });

  function progressNote() {
    if (!progress.available && !progress.serverBacked) {
      return 'این مرورگر اجازهٔ ذخیره‌سازی محلی نمی‌دهد، پس پیشرفت نگه داشته نمی‌شود.';
    }
    // Where progress is kept is a fact, not a preference: a signed-in learner has real
    // rows on the server, and telling them otherwise is simply wrong.
    const kept = progress.serverBacked
      ? 'پیشرفت روی حساب کاربری‌ات نگه داشته می‌شود.'
      : 'پیشرفت روی همین مرورگر نگه داشته می‌شود.';
    if (status.finished) return `همهٔ ${status.total} درس کامل شده است — ${kept}`;
    if (!status.completed) {
      const opened = status.started ? `${status.started} درس شروع شده` : 'هیچ درسی کامل نشده';
      return `${opened} — ${kept}`;
    }
    return `${status.completed} از ${status.total} درس کامل‌شده — ${kept}`;
  }
})();
