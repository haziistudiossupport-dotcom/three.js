// CHARGIX city experience: bootstrap, loading, scroll, render loop.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { World, B } from './world.js';
import { MaterialLibrary } from './materials.js';
import { Post } from './post.js';
import { Character, makePhone } from './characters.js';
import { buildStory, T_MAX, CHAPTERS } from './story.js';
import { posterTexture, posterBackTexture, shopSignTexture, forRentTexture, streetSignTexture, PhoneScreen, SiteScreen, migaMenuTexture, norteWallTexture } from './screens.js';
import { clamp, range, smooth, lerp } from './timeline.js';
import { Trees } from './trees.js';

const params = new URLSearchParams(location.search);
const DEV = location.hostname === 'localhost' || params.has('cxdev');
const ASSETS = (window.CX_ASSETS || '../site/assets/');
const ASSET = (name) => (window.CX_ASSET_URLS && window.CX_ASSET_URLS[name]) || ASSETS + name;

export async function start(root) {
  const canvas = root.querySelector('canvas');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const mobile = Math.min(window.innerWidth, window.innerHeight) < 700 || /Mobi|Android/i.test(navigator.userAgent);
  const quality = params.get('q') || (mobile ? 'low' : 'high');

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance', stencil: false });
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.localClippingEnabled = true;   // fit-outs draw themselves in with a rising clip plane
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const world = new World(renderer, { quality });
  const scene = world.scene;
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 1400);
  const mats = new MaterialLibrary(renderer, ASSETS);

  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  const progress = root.querySelector('[data-cx-progress]');
  const total = { n: 0, d: 0 };
  const load = (url) => new Promise((res, rej) => {
    total.n++;
    loader.load(url, (g) => { total.d++; if (progress) progress.style.setProperty('--p', total.d / total.n); res(g); }, undefined, rej);
  });

  const [city, gMateo, gLucia, gTrees, meta] = await Promise.all([
    load(ASSET('cx-city.glb')), load(ASSET('cx-char-mateo.glb')), load(ASSET('cx-char-lucia.glb')), load(ASSET('cx-trees.glb')),
    fetch(ASSET('cx-city-meta.json')).then((r) => r.json()),
  ]);

  // ------------------------------------------------------------------ city materials
  const sets = new Sets();
  city.scene.traverse((o) => {
    if (!o.isMesh) return;
    const list = Array.isArray(o.material) ? o.material : [o.material];
    const mapped = list.map((m) => mats.make(m.name));
    o.material = Array.isArray(o.material) ? mapped : mapped[0];
    o.receiveShadow = true;
    o.castShadow = !/far_|ground|asphalt|sidewalk|paint|glass/.test(o.name);
  });
  scene.add(city.scene);
  // swap canvas textures onto story surfaces
  const poster = posterTexture(), posterBack = posterBackTexture();
  setMat(city.scene, 'poster_chargix', new THREE.MeshStandardMaterial({ map: poster, emissiveMap: poster, emissive: 0xffffff, emissiveIntensity: 0.55, roughness: 0.25 }));
  setMat(city.scene, 'poster_back', new THREE.MeshStandardMaterial({ map: posterBack, emissiveMap: posterBack, emissive: 0xffffff, emissiveIntensity: 0.4, roughness: 0.25 }));
  setMat(city.scene, 'sign_street_a', new THREE.MeshStandardMaterial({ map: streetSignTexture('C. DURANGO'), roughness: 0.5 }), true);
  setMat(city.scene, 'sign_street_b', new THREE.MeshStandardMaterial({ map: streetSignTexture('C. ORIZABA'), roughness: 0.5 }), true);
  const sites = { miga: new SiteScreen('mateo'), norte: new SiteScreen('lucia') };
  const screenMat = (t) => new THREE.MeshStandardMaterial({ map: t, emissiveMap: t, emissive: 0xffffff, emissiveIntensity: 0.85, roughness: 0.25 });
  setMat(city.scene, 'MIGA_screen', screenMat(sites.miga.texture));
  setMat(city.scene, 'NORTE_screen', screenMat(sites.norte.texture));
  setMat(city.scene, 'MIGA_menu', new THREE.MeshStandardMaterial({ map: migaMenuTexture(), roughness: 0.8 }));
  setMat(city.scene, 'NORTE_wall', new THREE.MeshStandardMaterial({ map: norteWallTexture(), roughness: 0.92 }));
  // these four quads carry their UV2 with v=0 at the bottom edge, so their canvases flip the other way
  for (const t of [sites.miga.texture, sites.norte.texture]) t.flipY = true;
  city.scene.traverse((o) => { if (o.isMesh && /^(MIGA_menu|NORTE_wall)$/.test(o.material.name)) o.material.map.flipY = true; });
  sets.init(city.scene, mats, meta, scene);
  const trees = new Trees(gTrees, meta, mats, { quality });
  scene.add(trees.group);

  // ------------------------------------------------------------------ characters
  const mateo = new Character(gMateo, 'mateo');
  const lucia = new Character(gLucia, 'lucia');
  scene.add(mateo.root, lucia.root);
  lucia.root.visible = false;
  const phones = {};
  for (const [key, ch] of [['mateo', mateo], ['lucia', lucia]]) {
    const screen = new PhoneScreen(key);
    const phone = makePhone(screen.texture);
    ch.attach('phone', phone, 'RightHand', new THREE.Vector3(0.0, 0.09, 0.03), new THREE.Euler(-0.2, 0, Math.PI));
    phone.visible = false;
    // the screen lights the face a little at night; the light always exists so shaders never recompile
    const glow = new THREE.PointLight(0xdfe8ff, 0, 0.8, 2);
    scene.add(glow);
    phones[key] = { phone, screen, glow };
  }
  const _n = new THREE.Vector3();
  // hand props: the cookie box changes hands over the counter; Lucía carries a mailer at sunrise
  const kraftBox = () => {
    const g = new THREE.Group();
    const b = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.085, 0.24), mats.make('kraft'));
    const lid = new THREE.Mesh(new THREE.BoxGeometry(0.248, 0.02, 0.248), mats.make('kraft_lid'));
    lid.position.y = 0.035; b.castShadow = lid.castShadow = true;
    g.add(b, lid); return g;
  };
  const props = { boxMateo: kraftBox(), boxLucia: kraftBox() };
  mateo.attach('box', props.boxMateo, 'RightHand', new THREE.Vector3(0, 0.12, 0.06), new THREE.Euler(0, 0, 0));
  lucia.attach('box', props.boxLucia, 'RightHand', new THREE.Vector3(0, 0.12, 0.06), new THREE.Euler(0, 0, 0));
  props.mailer = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.03, 0.24), mats.make('poly_mailer'));
  props.mailer.castShadow = true;
  lucia.attach('mailer', props.mailer, 'LeftHand', new THREE.Vector3(0, 0.1, 0.05), new THREE.Euler(0, 0, Math.PI / 2));
  for (const pr of Object.values(props)) pr.visible = false;

  const post = new Post(renderer, scene, camera, { quality });
  if (params.has('noui')) root.querySelectorAll('.cx-copy,.cx-nav,.cx-rail,.cx-skip,.cx-phone').forEach((e) => (e.style.display = 'none'));
  const story = buildStory({ world, chars: { mateo, lucia }, sets, phones, sites, props });

  // ------------------------------------------------------------------ scroll
  const track = root.querySelector('[data-cx-track]');
  let Ttarget = params.has('T') ? +params.get('T') : 0;
  let Tcur = Ttarget;
  const fixedT = params.has('T');
  function readScroll() {
    if (fixedT) return;
    const r = track.getBoundingClientRect();
    const span = r.height - window.innerHeight;
    Ttarget = clamp(-r.top / Math.max(1, span)) * T_MAX;
  }
  window.addEventListener('scroll', readScroll, { passive: true });

  let W = 0, H = 0, dpr = 1;
  function resize() {
    W = root.clientWidth || window.innerWidth; H = window.innerHeight;
    const maxDpr = quality === 'high' ? 1.5 : quality === 'mid' ? 1.25 : 1.0;
    dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
    renderer.setPixelRatio(dpr); renderer.setSize(W, H, false);
    camera.aspect = W / H; camera.updateProjectionMatrix();
    post.setSize(W, H, dpr);
  }
  window.addEventListener('resize', resize);
  resize();
  readScroll();

  // dev-only look overrides: ?tm=neutral|aces|agx&ex=1&env=1&hemi=1&sun=1&fog=1&con=0&sat=1&split=0
  const num = (k, d) => (params.has(k) ? +params.get(k) : d);
  const TM = { agx: THREE.AgXToneMapping, neutral: THREE.NeutralToneMapping, aces: THREE.ACESFilmicToneMapping };
  if (params.has('tm')) renderer.toneMapping = TM[params.get('tm')];
  const g = post.grade.uniforms;
  g.uContrast.value = 0.25; g.uSat.value = 1.06; g.uSplit.value = 1.0;
  g.uContrast.value = num('con', g.uContrast.value); g.uSat.value = num('sat', g.uSat.value); g.uSplit.value = num('split', g.uSplit.value);
  if (params.has('aodbg') && post.gtao) post.gtao.output = +params.get('aodbg');
  const devLook = ['ex', 'env', 'hemi', 'sun', 'fog'].some((k) => params.has(k));
  const dev = devLook && (() => {
    renderer.toneMappingExposure *= num('ex', 1);
    scene.environmentIntensity *= num('env', 1);
    world.hemi.intensity *= num('hemi', 1);
    world.sun.intensity *= num('sun', 1);
    scene.fog.density *= num('fog', 1);
  });
  const hud = new Hud(root);
  hud.setPhones(phones);
  const timer = new THREE.Timer();
  let frames = 0;
  const frame = (now) => {
    timer.update(now);
    const dt = Math.min(0.1, timer.getDelta());
    const t = timer.getElapsed();
    Tcur += (Ttarget - Tcur) * (reduced ? 1 : 1 - Math.exp(-dt * 5.5));
    if (Math.abs(Ttarget - Tcur) < 1e-4) Tcur = Ttarget;
    const s = story(Tcur, params.has('freeze') ? 2.0 : t, params);
    world.setHour(s.hour, s.focusPoint);
    if (dev) dev();
    mats.setNight(world.night);
    if (params.has('cam')) {  // dev: cam=x,y,z,tx,ty,tz,fov in Blender coords
      const c = params.get('cam').split(',').map(Number);
      s.camera.pos = B(c[0], c[1], c[2]); s.camera.tgt = B(c[3], c[4], c[5]); if (c[6]) s.camera.fov = c[6];
    }
    for (const ph of Object.values(phones)) {
      let on = world.night > 0.02;
      for (let o = ph.phone; o && on; o = o.parent) on = o.visible;
      ph.glow.intensity = on ? 0.045 * world.night : 0;
      if (on) {
        const scr = ph.phone.userData.screen;
        scr.getWorldPosition(ph.glow.position);
        ph.glow.position.add(_n.set(0, 0, 1).transformDirection(scr.matrixWorld).multiplyScalar(0.07));
      }
    }
    camera.position.copy(s.camera.pos);
    camera.fov = s.camera.fov; camera.updateProjectionMatrix();
    camera.lookAt(s.camera.tgt);
    camera.updateMatrixWorld();
    trees.update(params.has('freeze') ? 2.0 : t, world, camera);
    const d = post.dof.uniforms;
    d.uFocus.value = s.camera.focus ? camera.position.distanceTo(s.focusPoint) : camera.position.distanceTo(s.camera.tgt);
    d.uAperture.value = s.camera.ap ?? 0.5;
    d.uTilt.value = s.camera.tilt ?? 0;
    d.uTiltCenter.value = s.camera.tiltC ?? 0.5;
    // bloom only catches lamps, signs and glints by day; widens at night
    post.bloom.strength = 0.22 + 0.5 * world.night;
    post.bloom.threshold = 3.2 - 2.4 * world.night;
    post.render(t);
    hud.update(Tcur, s);
    frames++;
    if (frames === 3) { if (DEV) document.title = 'done ' + document.title; root.classList.add('is-ready'); }
    if (!params.has('once') || frames < 4) requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
  window.__cx = { world, camera, scene, story, renderer, mats, setT: (v) => { Ttarget = Tcur = v; } };
}

function setMat(root, name, mat, keepUv1) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    if (Array.isArray(o.material)) o.material = o.material.map((m) => (m.name === name ? withUv1(mat) : m));
    else if (o.material.name === name) o.material = withUv1(mat);
  });
  function withUv1(m) {
    // glTF UVs put v=0 at the top of the image, so canvas textures on them must not be flipped
    if (m.map) { m.map.channel = 1; m.map.flipY = false; }
    if (m.emissiveMap) { m.emissiveMap.channel = 1; m.emissiveMap.flipY = false; }
    m.name = name;
    return m;
  }
}

// story-controlled pieces of the set (shop shells, shutters, signs, doors, fit-outs, interior light)
class Sets {
  init(root, mats, meta, scene) {
    this.o = {};
    root.traverse((o) => { if (o.name && /^(MIGA|NORTE|CX)_[a-z]+$/.test(o.name) && !this.o[o.name]) this.o[o.name] = o; });
    this.base = {};
    for (const [k, o] of Object.entries(this.o)) this.base[k] = o.position.clone();
    // signs: vacant paint until the shop opens
    this.signTex = { MIGA: shopSignTexture('MIGA'), NORTE: shopSignTexture('NORTE'), vacant: shopSignTexture('vacant') };
    this.signMat = {};
    for (const k of ['MIGA', 'NORTE']) {
      const m = new THREE.MeshStandardMaterial({ map: this.signTex.vacant, roughness: 0.5, emissiveMap: this.signTex[k], emissive: 0x000000 });
      m.map.channel = 1; this.signTex[k].channel = 1;
      for (const t of Object.values(this.signTex)) t.flipY = false;
      setMat(this.o[k + '_sign'], k + '_sign', m);
      this.signMat[k] = m;
      // story shop interiors: warm plaster
      setMat(this.o[k + '_room'], k + '_wall', new THREE.MeshStandardMaterial({ color: k === 'MIGA' ? 0xe9dfcd : 0xe4e2dc, roughness: 0.9 }));
      setMat(this.o[k + '_room'], k + '_ceiling', new THREE.MeshStandardMaterial({ color: 0xf1ece2, roughness: 0.95 }));
      for (const part of ['_front', '_door']) setMat(this.o[k + part], k + '_frame', new THREE.MeshStandardMaterial({ color: k === 'MIGA' ? 0x2c3b35 : 0x1d1f22, roughness: 0.45, metalness: 0.4 }));
      setMat(this.o[k + '_sign'], k + '_signbase', new THREE.MeshStandardMaterial({ color: 0x8a8378, roughness: 0.7 }));
    }
    // "se renta" paper on the MIGA shutter
    const fr = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.44), new THREE.MeshStandardMaterial({ map: forRentTexture(), roughness: 0.8 }));
    const sh = this.o.MIGA_shutter;
    const bb = new THREE.Box3().setFromObject(sh);
    fr.position.set((bb.min.x + bb.max.x) / 2 + 1.2, 1.55, bb.max.z + 0.012);
    this.forRent = fr;
    sh.add(fr);
    for (const k of ['MIGA', 'NORTE']) {
      const s = this.o[k + '_shutter'];
      s.userData.top = new THREE.Box3().setFromObject(s).max.y;
    }

    // fit-out pieces: each gets its own material copies and a horizontal clip plane that rises to draw it in
    this.pieces = {};
    this.glow = {};
    for (const key of ['MIGA', 'NORTE']) {
      const glow = this.glow[key] = { bulb: [], oven_glass: [], dryer_glow: [] };
      this.pieces[key] = ((meta.story && meta.story[key] && meta.story[key].pieces) || []).map((suf) => {
        const o = root.getObjectByName(`${key}_${suf}`);
        if (!o) return null;
        const plane = new THREE.Plane(new THREE.Vector3(0, -1, 0), 1e3);
        const box = new THREE.Box3().setFromObject(o);
        const conv = (mm) => {
          const c = mm.clone();
          c.onBeforeCompile = mm.onBeforeCompile; c.customProgramCacheKey = mm.customProgramCacheKey;
          c.clippingPlanes = [plane]; c.clipShadows = true;
          if (glow[mm.name]) glow[mm.name].push(c);
          return c;
        };
        o.traverse((mm) => { if (mm.isMesh) mm.material = Array.isArray(mm.material) ? mm.material.map(conv) : conv(mm.material); });
        return { o, plane, suf, y0: box.min.y - 0.01, y1: box.max.y + 0.01 };
      }).filter(Boolean);
    }

    // doors swing inward on a hinge at their outer edge (MIGA: west jamb, NORTE: east jamb in world x)
    this.doors = {};
    for (const key of ['MIGA', 'NORTE']) {
      const d = this.o[key + '_door'];
      if (!d) continue;
      const box = new THREE.Box3().setFromObject(d);
      const hinge = new THREE.Vector3(key === 'MIGA' ? box.min.x : box.max.x, 0, (box.min.z + box.max.z) / 2);
      const pivot = new THREE.Group(); pivot.name = key + '_doorPivot';
      pivot.position.copy(hinge);
      d.parent.add(pivot);
      d.position.sub(hinge);
      pivot.add(d);
      this.doors[key] = pivot;
    }

    // interior light: one warm point light per shop, under the ceiling
    this.lights = {};
    for (const [key, at] of [['MIGA', [-6.3, 9.3, 3.3]], ['NORTE', [3.6, -9.6, 3.3]]]) {
      const l = new THREE.PointLight(0xffc98f, 0, 0, 2);
      l.position.copy(B(...at));
      scene.add(l);
      this.lights[key] = l;
    }
  }

  state(key, st) {
    const sh = this.o[key + '_shutter'];
    if (sh && st.shutter !== undefined) {
      // roll up: slide the shutter up into its box and squash it
      const k = st.shutter;
      sh.scale.y = Math.max(0.001, 1 - k);
      sh.position.y = this.base[key + '_shutter'].y + sh.userData.top * k;
      sh.visible = k < 0.999;
    }
    if (st.sign !== undefined) {
      const m = this.signMat[key];
      const want = st.sign > 0.5 ? this.signTex[key] : this.signTex.vacant;
      if (m.map !== want) { m.map = want; m.map.channel = 1; m.needsUpdate = true; }
      m.emissive.setScalar(st.signGlow ?? 0);
    }
    const P = this.pieces[key] || [];
    if (st.build !== undefined || st.pieces) {
      P.forEach((pc, i) => {
        let u = 1;
        if (st.build !== undefined) { const a = (i / P.length) * 0.78; u = range(a, a + 0.26, st.build); }
        if (st.pieces && st.pieces[pc.suf] !== undefined) u = st.pieces[pc.suf];
        pc.o.visible = u > 0.001;
        pc.plane.constant = u >= 0.999 ? 1e3 : lerp(pc.y0, pc.y1, smooth(0, 1, u));
      });
    }
    const g = this.glow[key];
    if (g && st.light !== undefined) {
      for (const m of g.bulb) m.emissiveIntensity = 3.5 * st.light;
      this.lights[key].intensity = (key === 'NORTE' ? 18 : 20) * st.light;
    }
    if (g && st.oven !== undefined) for (const m of g.oven_glass) m.emissiveIntensity = 1.6 * st.oven;
    if (g && st.dryer !== undefined) for (const m of g.dryer_glow) m.emissiveIntensity = 2.2 * st.dryer;
    if (st.door !== undefined && this.doors[key]) this.doors[key].rotation.y = 1.35 * smooth(0, 1, st.door);
  }
}

class Hud {
  constructor(root) {
    this.root = root;
    this.beats = [...root.querySelectorAll('[data-cx-beat]')].map((el) => ({ el, a: +el.dataset.from, b: +el.dataset.to }));
    this.rail = [...root.querySelectorAll('[data-cx-chapter]')];
    this.bar = root.querySelector('[data-cx-rail-progress]');
    this.pkgs = [...root.querySelectorAll('[data-cx-pkg]')];
    this.phone = root.querySelector('[data-cx-phone]');
    this.screens = {};
    // chapter rail: jump to the start of each chapter
    const track = root.querySelector('[data-cx-track]');
    this.rail.forEach((el, i) => el.addEventListener('click', (e) => {
      e.preventDefault();
      const r = track.getBoundingClientRect();
      const span = r.height - window.innerHeight;
      const top = window.scrollY + r.top + (CHAPTERS[i].T / T_MAX) * span + 2;
      window.scrollTo({ top, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    }));
  }
  // the same canvas that textures the 3D phone, shown large so the messages can be read
  setPhones(phones) {
    if (!this.phone) return;
    const slot = this.phone.querySelector('.cx-phone__screen');
    for (const [k, v] of Object.entries(phones)) { v.screen.c.dataset.owner = k; v.screen.c.hidden = true; slot.appendChild(v.screen.c); this.screens[k] = v.screen.c; }
  }
  update(T, s = {}) {
    for (const b of this.beats) {
      const on = T >= b.a && T < b.b;
      if (on !== b.on) { b.on = on; b.el.classList.toggle('is-on', on); }
    }
    let cur = 0;
    CHAPTERS.forEach((c, i) => { if (T >= c.T) cur = i; });
    this.rail.forEach((el, i) => el.classList.toggle('is-current', i === cur));
    if (this.bar) this.bar.style.transform = `scaleY(${T / T_MAX})`;
    if (this.phone && s.phone !== this.phoneOwner) {
      this.phoneOwner = s.phone;
      if (s.phone) for (const [k, c] of Object.entries(this.screens)) c.hidden = k !== s.phone;
      this.phone.classList.toggle('is-on', !!s.phone);
    }
    if (s.pick !== this.pick) {
      this.pick = s.pick;
      this.pkgs.forEach((el) => el.classList.toggle('is-picked', el.dataset.cxPkg === s.pick));
    }
  }
}
