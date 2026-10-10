/* The lesson stepper.
 *
 * Every step is already in the DOM, rendered in full by the server; all this does
 * is show one at a time and keep the progress, the chips and the URL in sync. If
 * it never runs, the `.js` class is absent, the CSS never hides a step, and the
 * lesson reads as a single long document — with no lost content and no dead
 * controls, because the navigation is revealed here rather than in the HTML.
 *
 * Where the learner is gets remembered in one of two places, and this page is the
 * only one that knows which step they are on. A signed-in learner's progress is saved
 * to their LessonProgress rows with one small POST per step — the endpoint is in the
 * markup as `data-progress-url`, and the step to open on comes back as
 * `data-resume-step`. Everyone else keeps the localStorage behaviour through
 * `GamProgress`, which is the same module the dashboard and the path read.
 */
(() => {
  'use strict';

  const root = document.querySelector('[data-journey]');
  if (!root) return;

  const steps = Array.from(root.querySelectorAll('[data-journey-step]'));
  if (!steps.length) return;

  const keys = steps.map((step) => step.dataset.journeyStep);

  // Present only for a signed-in learner: where to save steps, and the token the POST
  // needs (the same meta tag the exercise runner reads).
  const progressUrl = root.dataset.progressUrl || '';
  const csrfToken = document.querySelector('meta[name="csrf-token"]');
  const nav = root.querySelector('.journey-steps');
  const chips = nav ? Array.from(nav.querySelectorAll('[data-journey-chip]')) : [];
  const labels = chips.map((chip) => {
    const label = chip.querySelector('.journey-chip__label');
    return label ? label.textContent.trim() : '';
  });
  const navBar = root.querySelector('[data-journey-nav]');
  const prevBtn = root.querySelector('[data-journey-prev]');
  const nextBtn = root.querySelector('[data-journey-next]');
  const bar = root.querySelector('[data-journey-bar]');
  const fill = root.querySelector('[data-journey-fill]');
  const currentEls = Array.from(root.querySelectorAll('[data-journey-current]'));
  const labelEl = root.querySelector('[data-journey-label]');
  const pctEl = root.querySelector('[data-journey-pct]');
  const resumeEl = root.querySelector('[data-journey-resume]');
  const noteEl = root.querySelector('[data-journey-note]');
  const progress = window.GamProgress;
  const lessonId = Number(root.dataset.lessonId);
  const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let index = 0;

  function hashStep() {
    const match = /^#step-([a-z]+)$/.exec(location.hash || '');
    return match ? keys.indexOf(match[1]) : -1;
  }

  /* ------------------------------------------------------- telling the server ----
   * The step the learner is on is the one fact only this page knows, so this page is
   * what saves it — one small POST when they reach a step. The guard skips two
   * identical sends in a row and nothing more: walking back and forth must still tell
   * the server where the learner really is.
   */
  let lastSentStep = null;

  function sendToServer(body) {
    if (!progressUrl) return Promise.resolve(null);

    return fetch(progressUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken ? csrfToken.content : '',
      },
      body: JSON.stringify(body),
    })
      .then((response) => (response.ok ? response.json() : null))
      .catch(() => null);
  }

  function rememberStep(stepKey) {
    if (!progressUrl || stepKey === lastSentStep) return;
    lastSentStep = stepKey;
    sendToServer({ step: stepKey, complete: false });
  }

  function activate(next, options) {
    const opts = options || {};
    index = Math.max(0, Math.min(steps.length - 1, next));

  steps.forEach((step, i) => step.classList.toggle('is-active', i === index));
  // The chips double as a trail: the steps behind the learner show a check instead of
  // their number, so it is obvious what is done and what is still ahead.
  chips.forEach((chip, i) => {
    const isBehind = i < index;
    chip.classList.toggle('is-active', i === index);
    chip.classList.toggle('is-done', isBehind);
    if (i === index) chip.setAttribute('aria-current', 'step');
    else chip.removeAttribute('aria-current');
    const number = chip.querySelector('.journey-chip__num');
    if (number) number.textContent = isBehind ? '✓' : String(i + 1);
  });

  if (chips[index]) {
    chips[index].scrollIntoView({ behavior: calm ? 'auto' : 'smooth', inline: 'center', block: 'nearest' });
  }

  const percent = Math.round(((index + 1) / steps.length) * 100);
    if (fill) fill.style.width = `${percent}%`;
    if (bar) bar.setAttribute('aria-valuenow', String(percent));
    if (pctEl) pctEl.textContent = `${percent}%`;
    currentEls.forEach((el) => { el.textContent = String(index + 1); });
    if (labelEl && labels[index]) labelEl.textContent = labels[index];

    const last = index === steps.length - 1;
    if (prevBtn) prevBtn.disabled = index === 0;
    if (nextBtn) {
      nextBtn.disabled = last;
      // Naming the next step makes the primary action self-explanatory.
      nextBtn.textContent = !last && labels[index + 1] ? `بعدی: ${labels[index + 1]}` : 'بعدی';
    }

    if (opts.history !== false) history.replaceState(null, '', `#step-${keys[index]}`);

    // Each call is a no-op for the mode it does not belong to: setLessonPosition does
    // nothing for a signed-in learner, and rememberStep does nothing without an
    // endpoint.
    if (progress) progress.setLessonPosition(lessonId, index);
    rememberStep(keys[index]);

    if (opts.focusHeading) {
      const heading = steps[index].querySelector('.journey-step__title');
      if (heading) heading.focus({ preventScroll: true });
    }
    if (opts.scroll) {
      steps[index].scrollIntoView({
        behavior: opts.scroll === 'smooth' && !calm ? 'smooth' : 'auto',
        block: 'start',
      });
    }
  }

  // Where to open: an explicit #step-… in the URL wins (the vocabulary step's
  // pagination links carry one), then the step the server says this learner stopped
  // on, then wherever this device left off.
  const fromHash = hashStep();
  const fromServer = root.dataset.resumeStep === undefined ? -1 : Number(root.dataset.resumeStep);
  const remembered = progress ? progress.lessonPosition(lessonId) : null;
  const start =
    fromHash >= 0 ? fromHash : fromServer >= 0 ? fromServer : typeof remembered === 'number' ? remembered : 0;
  activate(start, { scroll: start > 0 ? 'auto' : false });

  // Reopening the lesson lands on the step the learner left, so say so: coming back reads
  // as a continuation instead of as starting over. An explicit #step-… in the URL is the
  // learner's own choice, and step 0 is not a resume, so neither shows the line.
  if (resumeEl && fromHash < 0 && fromServer > 0) {
    resumeEl.textContent = `از همان‌جایی که رها کرده بودی ادامه دادی: قدم «${labels[fromServer]}».`;
    resumeEl.hidden = false;
  }

  // The note under the buttons promises that the place is kept. With nowhere to keep it
  // (blocked localStorage and no account) that would be a promise the page breaks, so it
  // is dropped rather than shown as a lie.
  if (noteEl && (!progress || (!progress.available && !progress.serverBacked))) {
    noteEl.hidden = true;
  }

  if (navBar) navBar.hidden = false;

  if (prevBtn) prevBtn.addEventListener('click', () => activate(index - 1, { scroll: 'smooth' }));
  if (nextBtn) nextBtn.addEventListener('click', () => activate(index + 1, { scroll: 'smooth' }));

  // Both the chip row and the intro/finish agendas link to #step-…, so one
  // delegated handler covers every way into a step.
  root.addEventListener('click', (event) => {
    const link = event.target.closest('a[href^="#step-"]');
    if (!link || !root.contains(link)) return;
    const target = keys.indexOf(link.getAttribute('href').slice('#step-'.length));
    if (target < 0) return;
    event.preventDefault();
    activate(target, { focusHeading: true, scroll: 'smooth' });
  });

  window.addEventListener('hashchange', () => {
    const target = hashStep();
    if (target >= 0 && target !== index) activate(target, { scroll: 'auto' });
  });

  // ------------------------------------------------- marking the lesson complete
  // The button is revealed here rather than in the HTML because, with nowhere to
  // record anything, it would be a control that does nothing. When the browser blocks
  // localStorage *and* there is no server to save to, the learner is told why instead
  // of being handed a dead button.
  const completeBtn = root.querySelector('[data-finish-complete]');
  const completeState = root.querySelector('[data-finish-state]');
  const completeEyebrow = root.querySelector('[data-finish-eyebrow]');
  if (completeBtn && completeState && progress) {
    if (!progress.available && !progress.serverBacked) {
      completeState.textContent = 'این مرورگر اجازهٔ ذخیره‌سازی محلی نمی‌دهد، پس نمی‌توان این درس را کامل‌شده ثبت کرد.';
      completeState.hidden = false;
      return;
    }

    const sync = () => {
      const entry = progress.read().lessons[lessonId];
      const done = !!entry && entry.status === progress.COMPLETED;
      completeBtn.disabled = done;
      completeBtn.textContent = done ? 'کامل‌شده' : 'درس را کامل کردم';
      // The summary header says what is true: a recap while the lesson is still open,
      // and the completion itself once the server has stored it.
      if (completeEyebrow) {
        completeEyebrow.textContent = done ? 'درس را کامل کردی' : 'جمع‌بندی این درس';
      }
      if (done) {
        completeState.textContent = progress.serverBacked
          ? 'این درس روی حساب کاربری‌ات کامل‌شده ثبت شده است.'
          : 'این درس روی همین مرورگر کامل‌شده ثبت شده است.';
        completeState.hidden = false;
      }
    };

    completeBtn.hidden = false;
    completeBtn.addEventListener('click', () => {
      // Anonymous visitors have no row to write, so the browser keeps the record.
      if (!progressUrl) {
        progress.markCompleted(lessonId);
        sync();
        return;
      }

      // Ask the server first: showing "کامل‌شده" for a save that failed would be a lie
      // the learner only discovers on their next visit.
      completeBtn.disabled = true;
      completeState.textContent = 'در حال ثبت…';
      completeState.hidden = false;
      sendToServer({ step: keys[index], complete: true }).then((saved) => {
        if (!saved) {
          completeBtn.disabled = false;
          completeState.textContent = 'ثبت نشد؛ ارتباط برقرار نشد. دوباره تلاش کن.';
          return;
        }
        lastSentStep = saved.current_step;
        progress.markCompleted(lessonId);
        sync();
      });
    });

    sync();
  }
})();
