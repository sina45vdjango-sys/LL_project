/* Recording a lesson from its sample check.
 *
 * The runner already grades every question and shows the score in its own result panel; it
 * deliberately exposes no callback, so this page watches that panel instead. When it appears,
 * the score is compared with the pass line the server put in the markup
 * (lessons/check.py::pass_needed) and the matching outcome is revealed: pass, and the learner
 * may record the lesson as read through the same endpoint the finish button posts to; fail,
 * and they are pointed back at the lesson.
 *
 * Revealed here rather than in the HTML for the same reason every other control in this
 * product is: with no JavaScript the result is never computed, so a button that offered to
 * record a check that never ran would be a lie.
 */
(() => {
  'use strict';

  const root = document.querySelector('[data-check]');
  if (!root) return;

  const done = root.querySelector('[data-check-done]');
  const results = root.querySelector('[data-runner-results]');
  const button = root.querySelector('[data-check-complete]');
  const state = root.querySelector('[data-check-state]');
  const passLead = root.querySelector('[data-check-pass]');
  const failLead = root.querySelector('[data-check-fail]');
  if (!done || !results || !button || !state || !passLead || !failLead) return;

  const progressUrl = root.dataset.progressUrl || '';
  const lessonId = Number(root.dataset.lessonId);
  const passNeeded = Number(root.dataset.passNeeded);
  const csrfToken = document.querySelector('meta[name="csrf-token"]');
  const progress = window.GamProgress;

  function correctCount() {
    const el = root.querySelector('[data-results-correct]');
    if (!el) return 0;
    return Number(el.textContent) || 0;
  }

  // A poll rather than an event: the runner owns the score and has no callback to hook.
  let shownForScore = null;

  setInterval(() => {
    if (results.hidden) {
      // A retry hides the result panel again; the outcome must not stay on screen.
      if (shownForScore !== null) {
        shownForScore = null;
        done.hidden = true;
      }
      return;
    }

    const score = correctCount();
    if (score === shownForScore) return;
    shownForScore = score;

    const passed = score >= passNeeded;
    done.hidden = false;
    passLead.hidden = !passed;
    failLead.hidden = passed;
    button.hidden = !passed;
  }, 300);

  button.addEventListener('click', () => {
    if (!progressUrl) return;

    // Ask the server first: showing «ثبت شد» for a save that failed would be a lie the
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
        state.textContent = 'این درس کامل‌شده ثبت شد.';
        button.hidden = true;
      });
  });
})();
