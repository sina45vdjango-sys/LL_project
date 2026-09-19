(() => {
  const audio = document.getElementById('word-audio');
  const button = document.getElementById('audio-toggle');
  const status = document.getElementById('audio-status');
  if (!audio || !button) return;
  const sync = () => {
    button.setAttribute('aria-pressed', String(!audio.paused));
    button.setAttribute('aria-label', audio.paused ? 'پخش تلفظ' : 'توقف تلفظ');
  };
  const fail = () => {
    status.hidden = false;
    status.textContent = 'پخش فایل ممکن نشد. اتصال یا فایل صوتی را بررسی و دوباره تلاش کنید.';
    sync();
  };
  button.addEventListener('click', async () => {
    status.hidden = true;
    if (!audio.paused) { audio.pause(); return; }
    try { if (audio.error) audio.load(); await audio.play(); } catch (_) { fail(); }
  });
  ['play', 'pause', 'ended'].forEach(event => audio.addEventListener(event, sync));
  audio.addEventListener('error', fail);
})();
