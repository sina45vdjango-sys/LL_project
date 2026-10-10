(() => {
  'use strict';
  // Any container that publishes a lookup endpoint, not one particular layout.
  const reader = document.querySelector('[data-lookup-url]');
  if (!reader) return;
  const popup = document.getElementById('word-popover');
  const body = popup.querySelector('[data-lookup-body]');
  const cache = new Map();
  let active = null, timer, hideTimer, generation = 0;
  const pattern = /[A-Za-zÄÖÜäöüß]+(?:[-’'][A-Za-zÄÖÜäöüß]+)*/gu;
  // Only elements that opt in with `data-lookup` are tokenised — prose blocks,
  // grammar explanations and German sentences. Vocabulary cards are left alone on
  // purpose: their term is already a link to the word page, and nesting a lookup
  // button inside a link would nest interactive elements.
  reader.querySelectorAll('[data-lookup]').forEach(container => {
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      const text = node.textContent;
      const matches = [...text.matchAll(pattern)];
      if (!matches.length) return;
      const fragment = document.createDocumentFragment();
      let end = 0;
      matches.forEach(match => {
        fragment.append(text.slice(end, match.index));
        const token = document.createElement('span');
        token.className = 'lookup-word';
        token.tabIndex = 0;
        token.setAttribute('role', 'button');
        token.setAttribute('aria-haspopup', 'dialog');
        token.setAttribute('aria-expanded', 'false');
        token.setAttribute('aria-controls', 'word-popover');
        token.setAttribute('aria-label', `معنی ${match[0]}`);
        token.lang = 'de';
        // German is always announced left-to-right and laid out that way, even inside a
        // Persian sentence: without this the bidi algorithm is free to reorder a token
        // that carries punctuation ("z.B.", "Guten Tag!") against the sentence around it.
        token.dir = 'ltr';
        token.textContent = match[0];
        fragment.append(token);
        end = match.index + match[0].length;
      });
      fragment.append(text.slice(end));
      node.replaceWith(fragment);
    });
  });
  const position = () => {
    if (!active || popup.hidden) return;
    const rect = active.getBoundingClientRect();
    const width = popup.offsetWidth, height = popup.offsetHeight;
    // On phones the bottom navigation is fixed over the page, so the popover has to stay
    // above it. Measure the bar itself rather than reading `--bottom-nav-h`: the bar adds
    // the phone's safe-area inset on top of that token, so the token alone would let the
    // popover sit under the last few pixels of the bar.
    const nav = document.querySelector('.bottom-nav');
    const navHeight = nav ? nav.getBoundingClientRect().height : 0;
    const bottomGuard = innerWidth < 900 ? navHeight + 12 : 8;
    popup.style.left = `${Math.max(8, Math.min(innerWidth - width - 8, rect.left + rect.width / 2 - width / 2))}px`;
    popup.style.top = `${Math.max(8, rect.top >= height + 12 ? rect.top - height - 8 : Math.min(innerHeight - height - bottomGuard, rect.bottom + 8))}px`;
  };
  const close = () => {
    clearTimeout(timer); clearTimeout(hideTimer); generation++;
    if (active) active.setAttribute('aria-expanded', 'false');
    active = null; popup.hidden = true;
    popup.querySelectorAll('audio').forEach(audio => audio.pause());
  };
  const show = async token => {
    clearTimeout(timer); clearTimeout(hideTimer);
    if (active === token && !popup.hidden) return;
    close(); active = token;
    const request = ++generation;
    token.setAttribute('aria-expanded', 'true');
    body.textContent = 'در حال دریافت معنی…'; popup.hidden = false; position();
    const query = token.textContent;
    try {
      let results = cache.get(query.toLocaleLowerCase('de'));
      if (!results) {
        const url = new URL(reader.dataset.lookupUrl, location.origin);
        url.searchParams.set('q', query);
        const response = await fetch(url, {headers: {'Accept': 'application/json'}});
        if (!response.ok) throw new Error('lookup failed');
        results = (await response.json()).results;
        if (cache.size >= 200) cache.delete(cache.keys().next().value);
        cache.set(query.toLocaleLowerCase('de'), results);
      }
      if (request !== generation) return;
      body.replaceChildren();
      if (!results.length) body.textContent = `«${query}» در واژه‌نامه ثبت نشده است؛ شکل صرف‌شده ممکن است مدخل جداگانه نداشته باشد.`;
      results.forEach(word => {
        const item = document.createElement('section');
        const heading = document.createElement('strong'); heading.dir = 'ltr'; heading.lang = 'de';
        heading.textContent = [word.article, word.word].filter(Boolean).join(' '); item.append(heading);
        const meaning = document.createElement('p'); meaning.textContent = word.meaning_fa; item.append(meaning);
        for (const [label, value] of [['نوع', word.word_type], ['جمع', word.plural], ['تلفظ', word.pronunciation], ['انگلیسی', word.meaning_en]]) {
          if (!value) continue;
          const row = document.createElement('p'); row.className = 'lookup-meta'; row.append(`${label}: `);
          const isolated = document.createElement('bdi'); isolated.textContent = value; row.append(isolated); item.append(row);
        }
        if (word.audio) {
          const audio = document.createElement('audio'); audio.controls = true; audio.preload = 'none'; audio.src = word.audio;
          audio.setAttribute('aria-label', 'تلفظ واژه'); item.append(audio);
        }
        const link = document.createElement('a'); link.href = word.url; link.textContent = 'جزئیات واژه ←'; item.append(link);
        body.append(item);
      });
    } catch (_) {
      if (request !== generation) return;
      body.textContent = 'دریافت معنی انجام نشد. دوباره روی واژه بزنید.';
    }
    position();
  };
  reader.addEventListener('pointerover', event => {
    const token = event.target.closest('.lookup-word');
    if (!token || event.pointerType === 'touch') return;
    clearTimeout(hideTimer); clearTimeout(timer); timer = setTimeout(() => show(token), 280);
  });
  reader.addEventListener('pointerout', event => {
    if (!event.target.closest('.lookup-word')) return;
    clearTimeout(timer); hideTimer = setTimeout(close, 400);
  });
  reader.addEventListener('focusin', event => { const token = event.target.closest('.lookup-word'); if (token) show(token); });
  reader.addEventListener('click', event => {
    const token = event.target.closest('.lookup-word');
    if (token) { event.preventDefault(); show(token); }
  });
  reader.addEventListener('keydown', event => {
    const token = event.target.closest('.lookup-word');
    if (token && ['Enter', ' '].includes(event.key)) { event.preventDefault(); show(token); }
  });
  popup.addEventListener('pointerenter', () => clearTimeout(hideTimer));
  popup.addEventListener('pointerleave', () => { hideTimer = setTimeout(close, 400); });
  popup.querySelector('[data-lookup-close]').addEventListener('click', close);
  document.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
  document.addEventListener('pointerdown', event => { if (!popup.contains(event.target) && !event.target.closest('.lookup-word')) close(); });
  document.addEventListener('focusin', event => { if (active && !popup.contains(event.target) && !event.target.closest('.lookup-word')) close(); });
  window.addEventListener('scroll', position, {passive: true});
  window.addEventListener('resize', close);
})();
