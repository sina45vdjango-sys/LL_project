/* Exam clock — the display half of the deadline, and the way a sitting closes.
 *
 * The deadline itself is the server's: the page was handed an instant (the run's own
 * `started_at` plus the paper's 65 minutes) and this file only counts down to it. A timer
 * that started when the page loaded would give the learner back the seconds a slow load, a
 * refresh or a closed tab cost them, and it would also be the only thing standing between
 * an expired exam and another answer — the submission endpoint refuses those itself.
 *
 * Finishing is a POST to exams:exam-finish, which is idempotent: the clock reaching zero
 * and the learner pressing «پایان آزمون» both arrive here, and the second one is a no-op.
 * The answer comes back with the URL of the closed sitting, which is the same URL showing
 * the score.
 */
(() => {
  'use strict';

  const timer = document.querySelector('[data-exam-timer]');
  if (!timer) return;

  const value = timer.querySelector('.exam-timer__value');
  const deadline = new Date(timer.dataset.examDeadline).getTime();
  const csrf = document.querySelector('meta[name="csrf-token"]');

  // The last five minutes are worth pointing at, but nothing is hidden or blocked until
  // the time is really over.
  const WARNING_MINUTES = 5;

  let finishing = false;

  function finishUrl() {
    if (timer.dataset.examFinishUrl) return timer.dataset.examFinishUrl;
    const button = document.querySelector('[data-exam-finish-url]');
    return button ? button.dataset.examFinishUrl : '';
  }

  function finish(ask) {
    if (finishing) return;
    if (ask && !window.confirm('آزمون تمام شود و نتیجه ثبت شود؟')) return;

    finishing = true;

    fetch(finishUrl(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf ? csrf.content : '',
      },
      body: '{}',
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        // Reloading the sitting's URL is what shows the score: the page reads the run, not
        // the response.
        window.location.href = data && data.url ? data.url : window.location.href;
      })
      .catch(() => window.location.reload());
  }

  function render() {
    const millisecondsLeft = deadline - Date.now();

    if (millisecondsLeft <= 0) {
      if (value) value.textContent = 'زمان تمام شد';
      timer.classList.add('is-expired');
      finish(false);
      return;
    }

    const secondsLeft = Math.floor(millisecondsLeft / 1000);
    const minutes = Math.floor(secondsLeft / 60);
    const seconds = secondsLeft % 60;

    if (value) value.textContent = `${minutes}:${String(seconds).padStart(2, '0')}`;
    timer.classList.toggle('is-low', minutes < WARNING_MINUTES);
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-exam-finish]');
    if (!button) return;
    finish(true);
  });

  render();
  setInterval(render, 1000);
})();
