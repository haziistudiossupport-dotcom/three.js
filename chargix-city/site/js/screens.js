// Canvas-drawn surfaces: phone and laptop UIs, the CHARGIX poster, shop signs and street signs.
// Everything here is illustration inside the story; no metrics, reviews or sales figures are shown.
import * as THREE from 'three';

export const BRAND = { brass: '#c8a26a', day: '#fff4de', steel: '#a9afb6', ink: '#16171a', paper: '#f6f1e7' };
const F = { sans: '"CX Archivo", "Archivo", system-ui, sans-serif', ui: '"CX Inter", "Inter Tight", system-ui, sans-serif', serif: '"CX Serif", "Instrument Serif", Georgia, serif' };

export const PACKAGES = [
  { id: 'essential', name: 'Essential Website', price: '$750', points: ['Up to 5 pages', 'Premium theme, customised', '10 products set up', '~10 business days'] },
  { id: '3d', name: '3D Experience', price: '$1,650', points: ['Real interactive 3D scene', 'Custom motion & visual direction', '20 products set up', '3–4 weeks'] },
  { id: 'launch', name: 'Business Launch', price: '$2,750', points: ['Everything in 3D Experience', 'Brand refresh + mini guide', 'US / Mexico markets, social setup', '4–5 weeks'] },
];

function canvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function rr(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function tex(c) { const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; }

function wordmark(ctx, x, y, size, color = BRAND.ink, align = 'left') {
  ctx.save();
  ctx.font = `800 ${size}px ${F.sans}`; ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = 'alphabetic';
  if ('letterSpacing' in ctx) ctx.letterSpacing = `${size * 0.06}px`;
  ctx.fillText('CHARGIX', x, y);
  ctx.restore();
}

// ------------------------------------------------------------------------------------------- poster
export function posterTexture() {
  const c = canvas(640, 1100), x = c.getContext('2d');
  const g = x.createLinearGradient(0, 0, 0, 1100);
  g.addColorStop(0, '#f7efe0'); g.addColorStop(1, '#efe2c8');
  x.fillStyle = g; x.fillRect(0, 0, 640, 1100);
  // an abstract storefront drawn like an architectural elevation
  x.strokeStyle = BRAND.ink; x.lineWidth = 3;
  x.strokeRect(90, 330, 460, 380);
  x.fillStyle = 'rgba(200,162,106,0.22)'; x.fillRect(120, 470, 400, 240);
  x.strokeRect(120, 470, 250, 240); x.strokeRect(390, 470, 130, 240);
  for (let i = 0; i < 4; i++) { x.strokeRect(130 + i * 105, 360, 70, 80); }
  x.fillStyle = BRAND.brass; x.fillRect(120, 440, 400, 22);
  x.beginPath(); x.arc(320, 270, 34, 0, Math.PI * 2); x.fillStyle = BRAND.brass; x.fill();
  wordmark(x, 60, 120, 76);
  x.fillStyle = BRAND.ink; x.font = `400 64px ${F.serif}`; x.textBaseline = 'alphabetic';
  x.font = `italic 400 56px ${F.serif}`;
  x.fillText('Your shop deserves', 60, 800);
  x.fillText('a website as good', 60, 862);
  x.fillText('as what you make.', 60, 924);
  x.font = `600 24px ${F.ui}`; x.fillStyle = '#5b5348';
  x.fillText('Websites  ·  3D experiences  ·  Launch', 60, 1000);
  x.font = `700 26px ${F.ui}`; x.fillStyle = BRAND.ink; x.fillText('chargix.store', 60, 1050);
  return tex(c);
}

export function posterBackTexture() {
  const c = canvas(640, 1100), x = c.getContext('2d');
  x.fillStyle = '#2f4a44'; x.fillRect(0, 0, 640, 1100);
  x.fillStyle = '#e6dccb'; x.font = `800 92px ${F.sans}`; x.fillText('MERCADO', 50, 210); x.fillText('DE LA', 50, 300); x.fillText('ROMA', 50, 390);
  x.font = `500 34px ${F.ui}`; x.fillText('Sábados y domingos', 50, 470);
  x.strokeStyle = '#e6dccb'; x.lineWidth = 4;
  for (let i = 0; i < 6; i++) { x.beginPath(); x.arc(320, 760, 60 + i * 40, Math.PI, 0); x.stroke(); }
  return tex(c);
}

// ------------------------------------------------------------------------------------------- signs
export function shopSignTexture(kind) {
  const c = canvas(2048, 180), x = c.getContext('2d');
  if (kind === 'MIGA') {
    x.fillStyle = '#2c3b35'; x.fillRect(0, 0, 2048, 180);
    x.fillStyle = '#f2e6cf'; x.font = `italic 400 132px ${F.serif}`; x.textAlign = 'center'; x.textBaseline = 'middle';
    x.fillText('Miga', 1024 - 170, 98);
    x.font = `600 40px ${F.ui}`; if ('letterSpacing' in x) x.letterSpacing = '10px';
    x.fillText('GALLETAS DE BARRIO', 1024 + 260, 96);
    x.fillStyle = BRAND.brass; x.fillRect(1024 + 30, 60, 3, 70);
  } else if (kind === 'NORTE') {
    x.fillStyle = '#e9e4d8'; x.fillRect(0, 0, 2048, 180);
    x.fillStyle = '#1d1f22'; x.font = `800 120px ${F.sans}`; x.textAlign = 'center'; x.textBaseline = 'middle';
    if ('letterSpacing' in x) x.letterSpacing = '36px';
    x.fillText('NORTE', 1024 - 160, 96);
    x.font = `600 34px ${F.ui}`; if ('letterSpacing' in x) x.letterSpacing = '8px'; x.fillStyle = '#e2683c';
    x.fillText('STUDIO · CDMX', 1024 + 380, 98);
  } else {  // vacant: weathered paint
    x.fillStyle = '#b8ab9a'; x.fillRect(0, 0, 2048, 180);
    x.fillStyle = 'rgba(80,70,60,0.12)';
    for (let i = 0; i < 40; i++) x.fillRect(Math.random() * 2048, Math.random() * 180, 60 + Math.random() * 200, 4 + Math.random() * 12);
  }
  return tex(c);
}

export function forRentTexture() {
  const c = canvas(512, 360), x = c.getContext('2d');
  x.fillStyle = '#f4f0e6'; x.fillRect(0, 0, 512, 360);
  x.strokeStyle = '#c2262e'; x.lineWidth = 10; x.strokeRect(14, 14, 484, 332);
  x.fillStyle = '#c2262e'; x.font = `800 112px ${F.sans}`; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillText('SE', 256, 110); x.fillText('RENTA', 256, 212);
  x.font = `600 30px ${F.ui}`; x.fillStyle = '#3b3b3b'; x.fillText('INFORMES AQUÍ', 256, 300);
  return tex(c);
}

export function streetSignTexture(name, col = 'COL. ROMA NORTE') {
  const c = canvas(1024, 240), x = c.getContext('2d');
  x.fillStyle = '#f2f1ec'; x.fillRect(0, 0, 1024, 240);
  x.fillStyle = '#1f3c88'; x.fillRect(0, 0, 1024, 18); x.fillRect(0, 222, 1024, 18);
  x.fillStyle = '#1b1b1b'; x.font = `800 104px ${F.sans}`; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillText(name, 512, 104);
  x.font = `600 34px ${F.ui}`; x.fillStyle = '#4a4a4a'; x.fillText(col, 512, 186);
  return tex(c);
}

// ------------------------------------------------------------------------------------------- phone UI
export class PhoneScreen {
  constructor(owner) {
    this.owner = owner; // 'mateo' | 'lucia'
    this.c = canvas(540, 1140);
    this.x = this.c.getContext('2d');
    this.texture = tex(this.c);
    this.state = null;
  }

  draw(state, p = 0) {
    const key = state + ':' + Math.round(p * 40);
    if (key === this.state) return;
    this.state = key;
    const x = this.x, W = 540, H = 1140;
    x.save();
    x.clearRect(0, 0, W, H);
    x.fillStyle = '#fbf8f2'; x.fillRect(0, 0, W, H);
    // status bar
    x.fillStyle = '#16171a'; x.font = `600 24px ${F.ui}`; x.textBaseline = 'middle'; x.fillText('9:41', 36, 40);
    x.fillRect(W - 86, 32, 44, 18);
    const m = this.owner === 'mateo';
    if (state === 'messages') this.messages(m, p);
    else if (state === 'chargix') this.chargix(p);
    else if (state === 'packages') this.packages(p);
    else if (state === 'building') this.building(m, p);
    else if (state === 'live') this.live(m, p);
    else if (state === 'order') { this.live(m, 1); this.toast(m, p); }
    x.restore();
    this.texture.needsUpdate = true;
  }

  messages(m, p) {
    const x = this.x;
    x.fillStyle = '#16171a'; x.font = `700 40px ${F.ui}`; x.fillText('Messages', 36, 120);
    const msgs = m
      ? ['Do you deliver to Condesa?', 'What flavours are there today?', 'Where can I see the menu?', 'Can I order a box for Friday?', 'Do you have a website?']
      : ['Is the hoodie still available?', 'What sizes do you have?', 'Can you ship to Monterrey?', 'Where can I see the full drop?', 'Do you have a website?'];
    const n = Math.max(1, Math.round(1 + p * (msgs.length - 1)));
    for (let i = 0; i < n; i++) {
      const y = 190 + i * 150;
      x.fillStyle = '#ece6da'; rr(x, 36, y, 400, 104, 28); x.fill();
      x.fillStyle = '#16171a'; x.font = `500 26px ${F.ui}`; x.fillText(msgs[i], 64, y + 52);
    }
  }

  chargix(p) {
    const x = this.x, W = 540;
    x.fillStyle = '#f6efe2'; x.fillRect(0, 70, W, 1070);
    wordmark(x, 36, 150, 40);
    x.fillStyle = '#16171a'; x.font = `italic 400 66px ${F.serif}`;
    x.fillText('Websites', 36, 300); x.fillText('that open', 36, 370); x.fillText('doors.', 36, 440);
    x.font = `500 25px ${F.ui}`; x.fillStyle = '#5b5348';
    x.fillText('Shopify stores and 3D experiences', 36, 520);
    x.fillText('for independent businesses.', 36, 556);
    x.fillStyle = '#16171a'; rr(x, 36, 620, 260, 74, 37); x.fill();
    x.fillStyle = '#fff4de'; x.font = `700 25px ${F.ui}`; x.fillText('See packages', 70, 658);
    // little elevation drawing
    x.strokeStyle = '#16171a'; x.lineWidth = 2; x.strokeRect(36, 760, 468, 300);
    x.fillStyle = 'rgba(200,162,106,0.3)'; x.fillRect(60, 900, 260, 160);
    x.strokeRect(60, 900, 260, 160); x.strokeRect(350, 900, 120, 160);
    x.fillStyle = BRAND.brass; x.fillRect(60, 870, 410, 16);
  }

  packages(p) {
    const x = this.x, W = 540;
    x.fillStyle = '#16171a'; x.font = `700 38px ${F.ui}`; x.fillText('Packages', 36, 120);
    // the highlight walks down the cards and settles on the owner's pick (Mateo: Business Launch, Lucía: 3D Experience)
    const pick = this.owner === 'mateo' ? 2 : 1;
    const sel = Math.min(pick, Math.floor(p * (pick + 1)));
    PACKAGES.forEach((pk, i) => {
      const y = 170 + i * 310;
      const on = i === sel;
      x.fillStyle = on ? '#16171a' : '#efe9dd'; rr(x, 30, y, W - 60, 286, 30); x.fill();
      x.fillStyle = on ? '#fff4de' : '#16171a';
      x.font = `700 30px ${F.ui}`; x.fillText(pk.name, 62, y + 56);
      x.font = `800 52px ${F.sans}`; x.fillStyle = on ? BRAND.brass : '#16171a'; x.fillText(pk.price, 62, y + 124);
      x.font = `500 22px ${F.ui}`; x.fillStyle = on ? '#e9e2d4' : '#4b463e';
      pk.points.forEach((t, k) => x.fillText('·  ' + t, 62, y + 172 + k * 30));
    });
  }

  building(m, p) {
    const x = this.x, W = 540;
    x.fillStyle = '#16171a'; x.font = `700 36px ${F.ui}`; x.fillText(m ? 'Your Miga site' : 'Your NORTE site', 36, 120);
    const steps = m ? ['Visual direction', 'Menu & products', 'Photos', 'Ordering & checkout', 'Launch'] : ['Brand refresh', 'Product catalogue', '3D product scene', 'Markets: MX + US', 'Launch'];
    steps.forEach((s, i) => {
      const y = 200 + i * 120;
      const done = p > (i + 1) / (steps.length + 0.4);
      const active = !done && p > i / (steps.length + 0.4);
      x.fillStyle = done ? BRAND.brass : active ? '#16171a' : '#d9d2c4';
      x.beginPath(); x.arc(64, y, 18, 0, Math.PI * 2); x.fill();
      if (done) { x.strokeStyle = '#fff'; x.lineWidth = 4; x.beginPath(); x.moveTo(55, y); x.lineTo(62, y + 8); x.lineTo(74, y - 8); x.stroke(); }
      x.fillStyle = done || active ? '#16171a' : '#9a9286'; x.font = `600 28px ${F.ui}`; x.fillText(s, 104, y);
    });
    x.fillStyle = '#ece6da'; rr(x, 36, 860, W - 72, 14, 7); x.fill();
    x.fillStyle = BRAND.brass; rr(x, 36, 860, (W - 72) * Math.min(1, p), 14, 7); x.fill();
  }

  live(m, p) {
    const x = this.x, W = 540;
    if (m) {
      x.fillStyle = '#2c3b35'; x.fillRect(0, 70, W, 520);
      x.fillStyle = '#f2e6cf'; x.font = `italic 400 96px ${F.serif}`; x.fillText('Miga', 40, 220);
      x.font = `600 22px ${F.ui}`; x.fillText('GALLETAS DE BARRIO · CDMX', 44, 270);
      for (let i = 0; i < 3; i++) { x.beginPath(); x.arc(110 + i * 160, 450, 62, 0, Math.PI * 2); x.fillStyle = ['#b9824e', '#8c5a34', '#c99a62'][i]; x.fill(); }
      x.fillStyle = '#16171a'; x.font = `700 32px ${F.ui}`; x.fillText('Order for pickup or delivery', 36, 660);
      x.fillStyle = '#2c3b35'; rr(x, 36, 710, W - 72, 82, 41); x.fill();
      x.fillStyle = '#f2e6cf'; x.font = `700 26px ${F.ui}`; x.fillText('Build a box', 70, 752);
    } else {
      x.fillStyle = '#e9e4d8'; x.fillRect(0, 70, W, 560);
      x.fillStyle = '#1d1f22'; x.font = `800 84px ${F.sans}`; if ('letterSpacing' in x) x.letterSpacing = '18px'; x.fillText('NORTE', 40, 200);
      if ('letterSpacing' in x) x.letterSpacing = '0px';
      x.fillStyle = '#8a9a7b'; rr(x, 110, 290, 320, 300, 26); x.fill();
      x.fillStyle = '#e9e4d8'; x.fillRect(210, 330, 120, 40);
      x.fillStyle = '#1d1f22'; x.font = `700 32px ${F.ui}`; x.fillText('Drop 04 · Hoodies', 36, 700);
      x.fillStyle = '#e2683c'; rr(x, 36, 740, W - 72, 82, 41); x.fill();
      x.fillStyle = '#fff'; x.font = `700 26px ${F.ui}`; x.fillText('Shop the drop', 70, 782);
    }
  }

  toast(m, p) {
    const x = this.x, W = 540;
    const y = 90 + (1 - Math.min(1, p * 3)) * -160;
    x.fillStyle = 'rgba(22,23,26,0.94)'; rr(x, 24, y, W - 48, 120, 30); x.fill();
    x.fillStyle = '#fff4de'; x.font = `700 26px ${F.ui}`; x.fillText('New order received', 60, y + 46);
    x.fillStyle = '#c9c2b4'; x.font = `500 22px ${F.ui}`; x.fillText(m ? 'Pickup · today' : 'Ships · tomorrow', 60, y + 84);
  }
}

// ------------------------------------------------------------------------------------------- in-shop surfaces
export function migaMenuTexture() {
  const c = canvas(600, 400), x = c.getContext('2d');
  x.fillStyle = '#23302b'; x.fillRect(0, 0, 600, 400);
  x.fillStyle = '#f2e6cf'; x.font = `italic 400 64px ${F.serif}`; x.textBaseline = 'alphabetic'; x.fillText('Miga', 40, 80);
  x.font = `600 16px ${F.ui}`; if ('letterSpacing' in x) x.letterSpacing = '4px'; x.fillText('HORNEADAS HOY', 210, 74);
  if ('letterSpacing' in x) x.letterSpacing = '0px';
  x.fillStyle = BRAND.brass; x.fillRect(40, 100, 520, 2);
  const items = ['Chocolate y sal de mar', 'Red velvet', 'Matcha y chocolate blanco', 'Avena y canela', 'Caja de 6 · caja de 12'];
  x.font = `500 26px ${F.ui}`; x.fillStyle = '#f2e6cf';
  items.forEach((t, i) => x.fillText(t, 40, 150 + i * 50));
  return tex(c);
}

export function norteWallTexture() {
  const c = canvas(960, 540), x = c.getContext('2d');
  x.fillStyle = '#e4e2dc'; x.fillRect(0, 0, 960, 540);
  x.fillStyle = '#1d1f22'; x.font = `800 210px ${F.sans}`; x.textAlign = 'center'; x.textBaseline = 'middle';
  if ('letterSpacing' in x) x.letterSpacing = '40px';
  x.fillText('NORTE', 500, 250);
  if ('letterSpacing' in x) x.letterSpacing = '10px';
  x.font = `600 34px ${F.ui}`; x.fillStyle = '#b9573a'; x.fillText('TALLER DE PLAYERAS · CDMX', 480, 420);
  return tex(c);
}

// A laptop screen: the owner's site being built, then live. Drawn like a browser window.
export class SiteScreen {
  constructor(owner) {
    this.owner = owner;
    this.c = canvas(1024, 660);
    this.x = this.c.getContext('2d');
    this.texture = tex(this.c);
    this.state = null;
  }

  draw(state, p = 0) {
    const key = state + ':' + Math.round(p * 30);
    if (key === this.state) return;
    this.state = key;
    const x = this.x, W = 1024, H = 660, m = this.owner === 'mateo';
    x.save();
    x.fillStyle = '#eceae4'; x.fillRect(0, 0, W, H);
    x.fillStyle = '#d9d5cc'; x.fillRect(0, 0, W, 44);
    ['#e0897a', '#e4c27a', '#9cc48a'].forEach((col, i) => { x.beginPath(); x.arc(26 + i * 22, 22, 7, 0, Math.PI * 2); x.fillStyle = col; x.fill(); });
    x.fillStyle = '#f6f4ef'; rr(x, 120, 10, 640, 24, 12); x.fill();
    if (state === 'off') { x.fillStyle = '#16171a'; x.fillRect(0, 0, W, H); }
    else if (state === 'build') this.build(m, p);
    else { this.site(m, 1); if (state === 'order') this.toast(m, p); }
    x.restore();
    this.texture.needsUpdate = true;
  }

  // wireframe blocks fill in, left to right, top to bottom
  build(m, p) {
    const x = this.x;
    const blocks = [[40, 70, 944, 300], [40, 390, 290, 220], [367, 390, 290, 220], [694, 390, 290, 220]];
    this.site(m, 1);
    blocks.forEach((b, i) => {
      const done = Math.max(0, Math.min(1, p * 4 - i * 0.9));
      if (done >= 1) return;
      x.fillStyle = '#eceae4'; x.fillRect(b[0] - 2, b[1] - 2, b[2] + 4, b[3] + 4);
      x.strokeStyle = '#a49d90'; x.setLineDash([10, 8]); x.lineWidth = 2; x.strokeRect(b[0], b[1], b[2], b[3]); x.setLineDash([]);
      if (done > 0) { x.fillStyle = 'rgba(200,162,106,0.35)'; x.fillRect(b[0], b[1], b[2] * done, b[3]); }
    });
  }

  site(m, p) {
    const x = this.x;
    if (m) {
      x.fillStyle = '#2c3b35'; x.fillRect(40, 70, 944, 300);
      x.fillStyle = '#f2e6cf'; x.font = `italic 400 120px ${F.serif}`; x.textBaseline = 'alphabetic'; x.fillText('Miga', 80, 230);
      x.font = `600 22px ${F.ui}`; x.fillText('GALLETAS DE BARRIO · ROMA NORTE', 86, 280);
      x.fillStyle = '#c8a26a'; rr(x, 86, 306, 200, 44, 22); x.fill();
      x.fillStyle = '#16171a'; x.font = `700 20px ${F.ui}`; x.fillText('Build a box', 128, 335);
      ['#6a4229', '#9b3a31', '#8c9d62'].forEach((col, i) => {
        x.fillStyle = '#f6f2ea'; x.fillRect(40 + i * 327, 390, 290, 220);
        x.beginPath(); x.arc(185 + i * 327, 470, 62, 0, Math.PI * 2); x.fillStyle = col; x.fill();
        x.fillStyle = '#16171a'; x.font = `600 20px ${F.ui}`; x.fillText(['Chocolate', 'Red velvet', 'Matcha'][i], 60 + i * 327, 580);
      });
    } else {
      x.fillStyle = '#e4e2dc'; x.fillRect(40, 70, 944, 300);
      x.fillStyle = '#1d1f22'; x.font = `800 96px ${F.sans}`; x.textBaseline = 'alphabetic';
      if ('letterSpacing' in x) x.letterSpacing = '20px'; x.fillText('NORTE', 80, 200); if ('letterSpacing' in x) x.letterSpacing = '0px';
      x.font = `600 22px ${F.ui}`; x.fillText('Drop 04 · heavyweight hoodies', 86, 250);
      // the 3D product scene: a hoodie on a turntable
      x.fillStyle = '#d6d2c8'; x.beginPath(); x.ellipse(760, 330, 150, 26, 0, 0, Math.PI * 2); x.fill();
      x.fillStyle = '#8a9a7b'; rr(x, 680, 110, 160, 210, 22); x.fill();
      x.fillStyle = '#7a8a6b'; x.beginPath(); x.arc(760, 120, 44, Math.PI, 0); x.fill();
      x.fillStyle = '#e2683c'; rr(x, 86, 290, 200, 44, 22); x.fill();
      x.fillStyle = '#fff'; x.font = `700 20px ${F.ui}`; x.fillText('Shop the drop', 120, 319);
      ['#26272a', '#e9e4d8', '#b9573a'].forEach((col, i) => {
        x.fillStyle = '#f6f2ea'; x.fillRect(40 + i * 327, 390, 290, 220);
        x.fillStyle = col; rr(x, 125 + i * 327, 410, 120, 140, 14); x.fill();
        x.fillStyle = '#16171a'; x.font = `600 20px ${F.ui}`; x.fillText(['Black tee', 'Cream tee', 'Rust hoodie'][i], 60 + i * 327, 590);
      });
    }
  }

  toast(m, p) {
    const x = this.x, W = 1024;
    const k = Math.min(1, p * 3);
    const y = 60 + (1 - k) * -120;
    x.fillStyle = 'rgba(22,23,26,0.94)'; rr(x, W - 400, y, 360, 96, 22); x.fill();
    x.fillStyle = '#fff4de'; x.font = `700 24px ${F.ui}`; x.fillText('New order received', W - 370, y + 42);
    x.fillStyle = '#c9c2b4'; x.font = `500 19px ${F.ui}`; x.fillText(m ? 'Box of 6 · pickup today' : 'Rust hoodie · ships tomorrow', W - 370, y + 74);
  }
}
