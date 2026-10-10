/* Completing a lesson from its revision page.
 *
 * The journey ends with «درس را کامل کردم», and that is the right place for it — but the
 * journey is eight screens of the lesson's own material, so reaching that button is a long
 * walk. This page shows the same rows as one scannable list, and reading the lesson the
 * short way has to count as reading it, or the day's first step could only ever be finished
 * one way.
 *
 * So this button posts to the very same endpoint with the very same payload the stepper
 * sends, which is what keeps the two pages from disagreeing about what "read" means:
 * lessons:lesson-progress, `{step: "finish", complete: true}`. The endpoint is in the
 * markup as `data-progress-url`, and it is only there for a signed-in learner — a visitor
 * has no row to write, so the button is never revealed for them.
 *
 * Hidden in the HTML and revealed here, for the same reason the stepper's button is: with
 * no JavaScript nothing could be recorded, and a control that does nothing is a lie.
 */
(() => {
  'use strict';

  const root = document.querySelector('[data-review]');
  if (!root) return;

  const progressUrl = root.dataset.progressUrl || '';
  const button = root.querySelector('[data-review-complete]');
  const state = root.querySelector('[data-review-state]');
  if (!button || !state || !progressUrl) return;

  const csrfToken = document.querySelector('meta[name="csrf-token"]');
  const lessonId = Number(root.dataset.lessonId);
  const progress = window.GamProgress;

  // Reflect what is already stored, so a lesson finished earlier says so instead of
  // offering to finish it again.
  function sync() {
    if (!progress) return;

    const entry = progress.read().lessons[lessonId];
    const done = !!entry && entry.status === progress.COMPLETED;
    button.disabled = done;
    button.textContent = done ? 'کامل‌شده' : 'درس را خواندم';

    if (done) {
      state.textContent = 'این درس کامل‌شده ثبت شده است.';
      state.hidden = false;
    }
  }

  button.hidden = false;

  button.addEventListener('click', () => {
    // Ask the server first: showing «کامل‌شده» for a save that failed would be a lie the
    // learner only discovers on their next visit.
    button.disabled = true;
    state.textContent = 'در حال ثبت…';
    state.hidden = false;

    fetch(progressUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken ? csrfToken.content : '',
      },
      body: JSON.stringify({ step: 'finish', complete: true }),
    })
      .then((response) => (response.ok ? response.json() : null))
      .catch(() => null)
      .then((saved) => {
        if (!saved) {
          button.disabled = false;
          state.textContent = 'ثبت نشد؛ ارتباط برقرار نشد. دوباره تلاش کن.';
          return;
        }

        if (progress) progress.markCompleted(lessonId);
        sync();
      });
  });

  sync();
})();
