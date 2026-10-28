const crossfader = document.getElementById('crossfader');
const statusEl = document.getElementById('status');

const decks = {
  A: {
    audio: document.getElementById('audioA'),
    select: document.getElementById('selectA'),
    playBtn: document.getElementById('playBtnA'),
    cover: document.getElementById('coverA'),
    title: document.getElementById('titleA'),
    sub: document.getElementById('subA'),
    section: document.getElementById('deckA'),
    playing: false,
  },

  B: {
    audio: document.getElementById('audioB'),
    select: document.getElementById('selectB'),
    playBtn: document.getElementById('playBtnB'),
    cover: document.getElementById('coverB'),
    title: document.getElementById('titleB'),
    sub: document.getElementById('subB'),
    section: document.getElementById('deckB'),
    playing: false,
  },
};


async function loadIntoDeck(name, filename) {
  statusEl.textContent = '';

  const deck = decks[name];

  const res = await fetch(
    `/track?name=${encodeURIComponent(filename)}`
  );

  if (!res.ok) {
    statusEl.textContent = `Server returned ${res.status}`;
    return;
  }

  const raw = new Uint8Array(await res.arrayBuffer());
  const decrypted = await DRM(raw);

  const blob = new Blob(
    [decrypted],
    { type: 'audio/mpeg' }
  );

  const url = URL.createObjectURL(blob);

  deck.audio.pause();
  deck.audio.src = url;

  deck.audio.onerror = () => {
    statusEl.textContent =
      "Couldn't decode that as audio — not a valid track file.";
  };

  if (deck.playing) {
    try {
      await deck.audio.play();
    } catch (e) {
      console.error("Playback failed:", e);
    }
  }
}


function setupDeck(name) {
  const deck = decks[name];

  deck.select.addEventListener('change', () => {
    const opt = deck.select.selectedOptions[0];

    deck.cover.style.setProperty(
      '--track-color',
      opt.dataset.color
    );

    deck.title.textContent = opt.dataset.title;
    deck.sub.textContent = opt.dataset.sub;

    loadIntoDeck(name, opt.value);
  });

  deck.playBtn.addEventListener('click', () => {
    deck.playing = !deck.playing;

    deck.section.classList.toggle(
      'playing',
      deck.playing
    );

    if (deck.playing) {
      deck.audio.play().catch(() => {});
      deck.playBtn.textContent = '⏸';
    } else {
      deck.audio.pause();
      deck.playBtn.textContent = '▶';
    }
  });


  loadIntoDeck(name, deck.select.value);
}


setupDeck('A');
setupDeck('B');


crossfader.addEventListener('input', () => {
  const v = Number(crossfader.value) / 100;

  decks.A.audio.volume = 1 - v;
  decks.B.audio.volume = v;
});

crossfader.dispatchEvent(new Event('input'));