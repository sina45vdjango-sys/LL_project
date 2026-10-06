/* sprechen_recorder.js — hear the model, say it, hear yourself, judge yourself.
 *
 * Concept 24 («بلند بگو») on the page the product already had. The oral section is 15 of
 * the exam's 100 points and nothing here grades it, because the official marking is two
 * examiners against criteria — so this adds the three things that are honestly possible:
 * the model recording to listen to, your own voice played back, and your own verdict.
 *
 * Four rules it keeps:
 *   1. **Nothing is uploaded.** The clip lives in the page as an object URL and is dropped
 *      when the page is left. There is no request in this file.
 *   2. **Nothing is stored.** The «گفتم / هنوز نه» verdict is a class on a list item and a
 *      number on the page. Speaking cannot be graded here, so a self-report is not written
 *      down as if it were a result.
 *   3. **Progressive.** Without MediaRecorder (or without permission) the record buttons
 *      are removed and the page keeps working — the model audio and the self-report need no
 *      microphone at all, which is why the self-report is wired before the recorder is
 *      checked for.
 *   4. **One recorder at a time.** Starting a new phrase stops the previous one, so a
 *      forgotten open microphone cannot keep recording.
 */
(() => {
  /* ------------------------------------------------------------- self-report ---- */

  const phrases = Array.from(document.querySelectorAll('[data-phrase]'));
  const saidCount = document.querySelector('[data-said-count]');

  function refreshSaid() {
    if (!saidCount) { return; }

    let total = 0;
    phrases.forEach(phrase => {
      if (phrase.classList.contains('is-said')) { total += 1; }
    });
    saidCount.textContent = String(total);
  }

  phrases.forEach(phrase => {
    const said = phrase.querySelector('.js-said');
    const notSaid = phrase.querySelector('.js-not-said');

    if (said) {
      said.addEventListener('click', () => {
        phrase.classList.add('is-said');
        refreshSaid();
      });
    }

    if (notSaid) {
      notSaid.addEventListener('click', () => {
        phrase.classList.remove('is-said');
        refreshSaid();
      });
    }
  });

  /* -------------------------------------------------------------- recorder ---- */

  const buttons = document.querySelectorAll('.js-record');
  if (!buttons.length) { return; }

  // No recorder in this browser: take the record buttons away and leave the rest of the
  // page — the model audio and the self-report — exactly as it is.
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    buttons.forEach(button => { button.remove(); });
    return;
  }

  let active = null;      // The element currently recording, or null.
  let recorder = null;    // Its MediaRecorder.
  let chunks = [];

  function stopStream(stream) {
    stream.getTracks().forEach(track => track.stop());
  }

  function finish() {
    if (active) {
      active.classList.remove('is-recording');
      active.textContent = '🎙️ دوباره بگو';
    }
    active = null;
    recorder = null;
  }

  function markVerdict(box, text) {
    const previous = box.querySelector('.phrase-verdict');
    if (previous) { previous.remove(); }

    const note = document.createElement('span');
    note.className = 'phrase-verdict';
    note.textContent = text;
    box.appendChild(note);
  }

  function playBack(host, url) {
    // Replace any previous clip beside this phrase rather than stacking them up.
    const previous = host.querySelector('.phrase-playback');
    if (previous) { previous.remove(); }

    const box = document.createElement('span');
    box.className = 'phrase-playback';

    const audio = document.createElement('audio');
    audio.controls = true;
    audio.src = url;
    box.appendChild(audio);

    // The same verdict as the always-available «گفتم / هنوز نه», offered here because
    // hearing yourself is the moment you know which one it is.
    const good = document.createElement('button');
    good.type = 'button';
    good.className = 'btn btn--sm';
    good.textContent = 'خوب گفتم';
    good.addEventListener('click', () => {
      host.classList.add('is-said');
      refreshSaid();
      markVerdict(box, 'خوب گفتم — همین‌طور ادامه بده.');
    });

    const hard = document.createElement('button');
    hard.type = 'button';
    hard.className = 'btn btn--sm';
    hard.textContent = 'سخت بود';
    hard.addEventListener('click', () => {
      host.classList.remove('is-said');
      refreshSaid();
      markVerdict(
        box,
        'این جمله را در تمرین همین جمله دوباره کار کن؛ چیزی به‌عنوان نمره ثبت نمی‌شود.'
      );
    });

    box.appendChild(good);
    box.appendChild(hard);
    host.appendChild(box);
  }

  function start(button) {
    const host = button.closest('.exam-phrase');

    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      active = button;
      chunks = [];
      recorder = new MediaRecorder(stream);

      recorder.addEventListener('dataavailable', event => {
        if (event.data.size > 0) { chunks.push(event.data); }
      });

      recorder.addEventListener('stop', () => {
        stopStream(stream);
        const blob = new Blob(chunks, { type: recorder.mimeType });
        playBack(host, URL.createObjectURL(blob));
        finish();
      });

      recorder.start();
      button.classList.add('is-recording');
      button.textContent = '⏹ پایان ضبط';
    }).catch(() => {
      // Permission refused, or no microphone. Say so once, on the button that was pressed.
      button.textContent = '🎙️ میکروفون در دسترس نیست';
      button.disabled = true;
    });
  }

  buttons.forEach(button => {
    button.addEventListener('click', () => {
      if (active === button && recorder && recorder.state === 'recording') {
        recorder.stop();
        return;
      }
      if (recorder && recorder.state === 'recording') {
        recorder.stop();
        return;
      }
      start(button);
    });
  });
})();
