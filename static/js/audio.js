/* Global Audio Singleton for the whole product.
 *
 * Each audio control (templates/includes/audio_control.html) is a lightweight 44x44
 * icon button carrying its audio source on `data-audio-src`.
 *
 * Rather than creating dozens of redundant <audio> DOM elements per page (50+ on a single
 * lesson), this script uses a single shared Audio element (Audio Singleton).
 *
 * Why the native <audio> controls are not always shown:
 * Revealing a full player for a one-second vocabulary word makes rows unnecessarily tall.
 * The native player (scrubber/progress) is dynamically attached to the active control
 * only for clips long enough to want seeking (>= 5s, such as grammar topics and prose blocks).
 *
 * The five states for the active control:
 *   idle     nothing is playing. Button shows play icon; player is detached/hidden.
 *   loading  playback was requested and the clip is buffering.
 *   playing  the clip is currently running.
 *   paused   the learner paused playback. Long clips keep their scrubber visible so scrubbing works.
 *   error    playback failed; button indicates error state and status message is shown.
 *
 * Loaded globally by base.html.
 */
(() => {
  'use strict';

  // Clips shorter than this are the button and nothing else.
  const LONG_CLIP_SECONDS = 5;

  // Error label displayed on playback failure
  const PLAY_FAILED = 'خطای پخش صدا';

  // Lazy Audio Singleton
  let singletonAudio = null;
  const getAudio = () => {
    if (!singletonAudio) {
      singletonAudio = document.createElement('audio');
      singletonAudio.preload = 'none';
      singletonAudio.controls = true;
      singletonAudio.hidden = true;
      singletonAudio.className = 'audio-singleton-player';
    }
    return singletonAudio;
  };

  const panels = Array.from(document.querySelectorAll('.audio-control'));
  const items = panels.map((panel) => {
    const button = panel.querySelector('.audio-toggle');
    const src = button
      ? (button.getAttribute('data-audio-src') || panel.getAttribute('data-audio-src'))
      : null;
    if (!button || !src) return null;
    return {
      panel: panel,
      button: button,
      src: src,
      status: panel.querySelector('.audio-status'),
      label: button.getAttribute('data-label') || button.getAttribute('aria-label') || '',
      state: 'idle',
    };
  }).filter((item) => item !== null);

  if (!items.length) return;

  let activeItem = null;

  const isActive = (item) => item && (item.state === 'playing' || item.state === 'loading' || item.state === 'paused');

  const render = (item) => {
    if (!item) return;
    const active = isActive(item);
    item.panel.setAttribute('data-audio-state', item.state);
    item.button.setAttribute('aria-expanded', active ? 'true' : 'false');
    const spoken = (active ? 'توقف ' : 'پخش ') + item.label;
    item.button.setAttribute('aria-label', spoken);
    item.button.setAttribute('title', spoken);

    const audio = getAudio();
    const longEnough = audio.duration >= LONG_CLIP_SECONDS;
    const showPlayer = longEnough && active && (activeItem === item);

    audio.hidden = !showPlayer;
    if (showPlayer) {
      if (audio.parentElement !== item.panel) {
        item.panel.appendChild(audio);
      }
    } else if (audio.parentElement === item.panel && !active) {
      audio.remove();
    }
  };

  const idle = (item) => {
    if (!item) return;
    item.state = 'idle';
    if (activeItem === item) {
      const audio = getAudio();
      audio.pause();
      audio.hidden = true;
      if (audio.parentElement) {
        audio.remove();
      }
      activeItem = null;
    }
    render(item);
  };

  const stopOthers = (keepItem) => {
    items.forEach((item) => {
      if (item !== keepItem && item.state !== 'idle') {
        idle(item);
      }
    });
  };

  const fail = (item) => {
    if (!item) return;
    item.state = 'error';
    render(item);
    if (item.status) {
      item.status.textContent = PLAY_FAILED;
      item.status.hidden = false;
    }
    if (activeItem === item) {
      activeItem = null;
    }
  };

  const play = async (item) => {
    stopOthers(item);
    activeItem = item;
    if (item.status) item.status.hidden = true;
    item.state = 'loading';
    render(item);

    const audio = getAudio();
    if (audio.src !== item.src && !audio.src.endsWith(item.src)) {
      audio.src = item.src;
    }

    try {
      await audio.play();
      if (activeItem === item) {
        item.state = 'playing';
        render(item);
      }
    } catch (_) {
      if (activeItem === item) {
        fail(item);
      }
    }
  };

  // Bind singleton audio events once
  const audio = getAudio();

  audio.addEventListener('loadedmetadata', () => {
    if (activeItem) render(activeItem);
  });

  audio.addEventListener('play', () => {
    if (activeItem && activeItem.state !== 'playing') {
      activeItem.state = 'playing';
      render(activeItem);
    }
  });

  audio.addEventListener('pause', () => {
    if (activeItem && (activeItem.state === 'playing' || activeItem.state === 'loading')) {
      activeItem.state = 'paused';
      render(activeItem);
    }
  });

  audio.addEventListener('ended', () => {
    if (activeItem) idle(activeItem);
  });

  audio.addEventListener('error', () => {
    if (activeItem) fail(activeItem);
  });

  // Setup items
  items.forEach((item) => {
    item.button.hidden = false;
    render(item);

    item.button.addEventListener('click', () => {
      if (isActive(item)) {
        idle(item);
        return;
      }
      play(item);
    });
  });

  // Stop singleton if any external media starts playing (e.g., reader popup audio)
  document.addEventListener('play', (event) => {
    if (event.target !== singletonAudio) {
      if (activeItem) idle(activeItem);
    }
  }, true);
})();
