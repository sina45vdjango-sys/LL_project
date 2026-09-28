/* The one audio behaviour for the whole product.
 *
 * Moved here in Phase 7 from lessons/static/lessons/js/lesson_audio.js: the control is
 * rendered by lessons, vocabulary and exercises now, and the exercise page never loaded
 * the old script at all (its question audio would have rendered a button that did
 * nothing). Loaded globally by base.html, like progress.js.
 *
 * Each button owns one real <audio> element, revealed on demand. Playing one stops every
 * other player on the page, the word-lookup popover included. A failed play says so in
 * the control's own status line instead of failing silently.
 */
(() => {
  'use strict';

  const items = Array.from(document.querySelectorAll('.audio-toggle')).map((button) => ({
    button,
    audio: document.getElementById(button.getAttribute('aria-controls')),
    panel: button.closest('.audio-control'),
    playLabel: button.getAttribute('aria-label'),
  })).filter((item) => item.audio && item.panel);
  if (!items.length) return;

  const collapse = (item) => {
    item.audio.pause();
    item.audio.hidden = true;
    item.button.setAttribute('aria-expanded', 'false');
    item.button.setAttribute('aria-label', item.playLabel);
  };
  // `keep` is the audio element that is allowed to keep playing, if any.
  const stopOthers = (keep) => items.forEach((item) => { if (item.audio !== keep) collapse(item); });

  items.forEach((item) => {
    const status = item.panel.querySelector('.audio-status');
    // The buttons ship hidden so a no-JavaScript page has no dead control; revealing
    // them is the first thing this script does.
    item.button.hidden = false;
    item.button.addEventListener('click', async () => {
      if (!item.audio.hidden) { collapse(item); return; }
      stopOthers(item.audio);
      item.audio.hidden = false;
      item.button.setAttribute('aria-expanded', 'true');
      try {
        await item.audio.play();
      } catch (_) {
        if (status) { status.textContent = 'پخش صوت ممکن نشد. دوباره تلاش کنید.'; status.hidden = false; }
        collapse(item);
      }
    });
    item.audio.addEventListener('play', () => {
      if (status) status.hidden = true;
      item.button.setAttribute('aria-label', 'توقف پخش');
    });
    ['pause', 'ended'].forEach((event) => item.audio.addEventListener(event, () => {
      item.button.setAttribute('aria-label', item.playLabel);
    }));
  });

  // Only one pronunciation plays at a time, the word popover included.
  document.addEventListener('play', (event) => {
    if (event.target.tagName !== 'AUDIO') return;
    stopOthers(event.target);
    document.querySelectorAll('audio').forEach((audio) => { if (audio !== event.target) audio.pause(); });
  }, true);
})();
