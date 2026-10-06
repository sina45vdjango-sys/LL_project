/* Move the progress a visitor made in this browser onto the account they just made.
 *
 * The product lets a visitor learn without an account, so their progress lives in
 * localStorage (static/js/progress.js). The moment they sign up, the dashboard starts
 * showing the server's answer — which is empty — and the work they did is no longer
 * looked at. That is a silent loss, so the dashboard asks instead of pretending.
 *
 * Three rules:
 *   1. **The panel is hidden in the HTML.** It is revealed here only when there is
 *      something to move, so nobody is ever offered an import that would import nothing,
 *      and with JavaScript off nothing is offered at all — no dead button.
 *   2. **The browser is a claim, not a source of truth.** What is sent is a lesson id and
 *      the word the browser used ("started" or "completed"); the server decides what that
 *      is allowed to do (lessons/progress.py::import_guest_progress). Nothing else from
 *      localStorage is sent, and it is only ever written to the learner's own account.
 *   3. **Declining deletes it.** «نه، پاکش کن» clears the browser's copy, because the
 *      alternative is being asked again on every visit about progress the learner has
 *      already said they do not want.
 */
(() => {
  'use strict';

  const panel = document.querySelector('[data-progress-import]');
  if (!panel) { return; }

  const progress = window.GamProgress;
  if (!progress || !progress.available) { return; }

  /* A signed-in learner only. The template already decides who sees the markup; this is
   * the second check, because a page cached from before signing in must not post into a
   * session that no longer exists. */
  if (!progress.serverBacked) { return; }

  const guest = progress.guestRead();
  const server = progress.read();
  const candidates = {};

  /* A lesson counts as importable when the account does not know about it at all, or when
   * the browser says it is finished and the account has only started it. The other
   * direction is never sent: the browser must not be able to un-finish a lesson. */
  Object.keys(guest.lessons).forEach((id) => {
    const local = guest.lessons[id];
    if (!local || !local.status) { return; }

    const known = server.lessons[id];
    if (!known) {
      candidates[id] = local.status;
      return;
    }
    if (known.status === 'completed') { return; }
    if (local.status === 'completed') { candidates[id] = 'completed'; }
  });

  const ids = Object.keys(candidates);
  if (!ids.length) { return; }

  const count = panel.querySelector('[data-import-count]');
  const state = panel.querySelector('[data-import-state]');
  const accept = panel.querySelector('[data-import-accept]');
  const dismiss = panel.querySelector('[data-import-dismiss]');
  const csrfToken = document.querySelector('meta[name="csrf-token"]');

  if (count) { count.textContent = String(ids.length); }
  panel.hidden = false;

  function say(message) {
    if (!state) { return; }
    state.textContent = message;
    state.hidden = false;
  }

  accept.addEventListener('click', () => {
    accept.disabled = true;
    if (dismiss) { dismiss.disabled = true; }

    fetch(panel.dataset.importUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken ? csrfToken.content : '',
      },
      body: JSON.stringify({ lessons: candidates }),
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (!payload) {
          accept.disabled = false;
          if (dismiss) { dismiss.disabled = false; }
          say('منتقل نشد. یک‌بار دیگر امتحان کن.');
          return;
        }

        /* The browser's copy has been handed over, so keeping it would make the next
         * visit offer the same import again. The reload then shows the progress the
         * server now has — which is the only honest confirmation there is. */
        progress.clear();
        say('منتقل شد. صفحه دوباره بارگذاری می‌شود…');
        window.setTimeout(() => window.location.reload(), 900);
      })
      .catch(() => {
        accept.disabled = false;
        if (dismiss) { dismiss.disabled = false; }
        say('ارتباط برقرار نشد. یک‌بار دیگر امتحان کن.');
      });
  });

  dismiss.addEventListener('click', () => {
    progress.clear();
    panel.hidden = true;
  });
})();
