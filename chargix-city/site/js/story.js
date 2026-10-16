// The film: camera keys, time of day, character tracks and set states, all as functions of story time T.
// Everything is a pure function of T, so the page scrubs the same forwards and backwards.
import * as THREE from 'three';
import { B } from './world.js';
import { sampleKeys, Track, smooth, range, lerp, clamp } from './timeline.js';

const V = (x, y, z = 0.15) => B(x, y, z);

// T runs 0..100 for the whole page.
export const CHAPTERS = [
  { id: 'prologue', label: 'Arrival', T: 0 },
  { id: 'mateo', label: 'Miga · cookies', T: 4 },
  { id: 'lucia', label: 'NORTE · clothing', T: 60 },
  { id: 'invite', label: 'Your street', T: 94 },
];
export const T_MAX = 100;

// landmarks (Blender coords)
const MIGA_DOOR = V(-4.45, 7.2);
const NORTE_DOOR = V(0.85, -7.2);
const POSTER = V(7.43, 5.3, 1.45);
const PICK = { mateo: 'launch', lucia: '3d' };

export function buildStory(ctx) {
  const { chars, sets, phones, sites, props } = ctx;
  const { mateo, lucia } = chars;

  // ------------------------------------------------------------------ camera keys (Blender coords)
  const K = (T, p, t, fov, o = {}) => ({ T, pos: B(...p), tgt: B(...t), fov, tilt: o.tilt ?? 0.1, tiltC: o.tiltC ?? 0.5, ap: o.ap ?? 1.0, focus: o.focus ?? 1, ease: o.ease });
  const cam = [
    // A: arrival over the neighbourhood, down to the street
    K(0.0, [-66, -48, 52], [-16, 8, 0], 30, { tilt: 0.85, tiltC: 0.46, ap: 0, focus: 0 }),
    K(3.5, [-52, -30, 30], [-26, 6.6, 1], 30, { tilt: 0.8, tiltC: 0.44, ap: 0, focus: 0 }),
    K(7.5, [-36, -1.0, 11.0], [-20, 6.6, 1.0], 32, { tilt: 0.55, tiltC: 0.42, ap: 0.6 }),
    // on the sidewalk ahead of him: Mateo walks toward the lens
    K(10.6, [-7.6, 5.3, 1.45], [-15.5, 6.5, 1.25], 40, { tilt: 0.2, ap: 1.0 }),
    // B: the shutter
    K(12.6, [-1.2, 1.8, 1.8], [-9.8, 6.2, 1.6], 38, { tilt: 0.15 }),
    K(16.0, [-2.0, 2.6, 1.7], [-9.5, 6.3, 1.65], 34, { tilt: 0.12, ap: 1.1 }),
    K(19.0, [-2.8, 3.3, 1.62], [-9.2, 6.4, 1.7], 30, { ap: 1.2 }),
    // B: the messages, over his shoulder
    K(20.8, [-5.72, 4.07, 1.62], [-6.9, 6.05, 1.5], 31, { ap: 1.2 }),
    K(23.4, [-5.9, 4.35, 1.6], [-6.9, 6.05, 1.5], 28, { ap: 1.3 }),
    // C: down the block to the bus stop
    K(24.8, [-2.0, 2.2, 1.6], [-3.8, 5.6, 1.3], 36),
    K(27.0, [1.0, 2.6, 1.6], [3.4, 5.3, 1.3], 34),
    K(28.8, [2.0, 4.55, 1.75], [7.4, 5.35, 1.5], 30, { focus: 0, ap: 0.8 }),
    // D: the packages on his phone
    K(30.6, [6.22, 4.33, 1.62], [4.4, 5.15, 1.5], 31, { ap: 1.2 }),
    K(35.4, [6.0, 4.43, 1.6], [4.4, 5.15, 1.5], 28, { ap: 1.3 }),
    // E: back to the shop; the shutter goes up and the fit-out builds in
    K(36.4, [5.5, 1.2, 2.4], [2.0, 5.5, 1.4], 36),
    K(38.8, [-1.8, -0.6, 2.3], [-5.6, 8.0, 1.6], 38),
    K(42.0, [-6.0, -1.8, 2.1], [-6.4, 9.0, 1.9], 40, { ap: 0.6, focus: 0 }),
    K(47.6, [-6.0, 1.0, 1.9], [-6.4, 9.5, 1.7], 38, { ap: 0.7, focus: 0 }),
    // F: golden hour, a neighbour crosses the street and comes in
    K(50.2, [2.6, -2.8, 1.65], [-4.0, 6.5, 1.6], 36),
    K(52.6, [-3.0, 4.3, 1.7], [-6.0, 10.5, 1.4], 40),
    K(53.8, [-3.9, 9.0, 1.65], [-6.2, 10.9, 1.35], 40, { ap: 1.2 }),
    K(55.2, [-3.8, 8.9, 1.65], [-6.2, 10.9, 1.35], 38, { ap: 1.2 }),
    // G: dusk, pull back over the street
    K(56.8, [-4.0, -2.0, 4.5], [-5.5, 9.0, 2.0], 40, { ap: 0.4, focus: 0 }),
    K(59.0, [-24, -28, 24], [-2, 2, 0], 34, { tilt: 0.8, tiltC: 0.46, ap: 0, focus: 0 }),
    // Chapter 2: NORTE at night, across the street
    K(61.2, [3.0, -2.6, 2.4], [3.4, -11.0, 1.4], 40, { ap: 0.6, focus: 0 }),
    K(63.8, [3.4, -4.6, 1.7], [3.6, -11.6, 1.35], 36),
    K(65.0, [2.94, -9.63, 1.72], [3.7, -11.8, 1.42], 31, { ap: 1.2 }),
    K(67.8, [3.06, -9.95, 1.68], [3.7, -11.8, 1.42], 28, { ap: 1.3 }),
    K(69.2, [3.6, -4.6, 1.7], [1.0, -7.6, 1.3], 36),
    K(71.8, [0.53, -6.8, 1.8], [6.0, 2.8, 1.6], 34, { focus: 0, ap: 0.8 }),
    K(74.0, [3.05, -4.87, 1.62], [1.3, -6.2, 1.42], 31, { ap: 1.2 }),
    K(78.0, [2.8, -5.06, 1.58], [1.3, -6.2, 1.42], 28, { ap: 1.3 }),
    K(79.8, [2.4, -3.6, 2.0], [4.6, -12.0, 1.4], 40),
    K(82.0, [2.6, -10.4, 1.75], [5.4, -13.4, 1.25], 38),
    K(85.0, [1.6, -7.9, 1.9], [4.4, -12.6, 1.5], 44, { ap: 0.6 }),
    // sunrise: the storefront opens
    K(88.0, [4.6, 1.5, 2.3], [3.6, -9.0, 2.7], 44, { ap: 0.5, focus: 0 }),
    K(91.6, [3.0, -3.0, 1.75], [1.4, -6.6, 1.3], 36),
    // H: invitation, rise over both shops
    K(94.2, [2.0, -6.0, 7.0], [-1.0, 1.0, 1.0], 38, { tilt: 0.4, ap: 0, focus: 0 }),
    K(97.6, [-50, -2, 26], [-2, 0, 0], 30, { tilt: 0.8, tiltC: 0.46, ap: 0, focus: 0 }),
    K(100, [-60, -6, 34], [-2, 0, 0], 30, { tilt: 0.85, tiltC: 0.46, ap: 0, focus: 0 }),
  ];

  // ------------------------------------------------------------------ Mateo
  const walk1 = [V(-40, 6.6), V(-24, 6.6), V(-12.4, 6.6), V(-8.6, 6.45), V(-6.9, 6.05)];
  const STOP = V(4.4, 5.15);
  const COUNTER = V(-6.15, 11.65);
  const mt = new Track([
    { t0: 0.0, t1: 1.5, at: walk1[0], heading: Math.PI / 2 },
    { t0: 1.5, t1: 13.2, path: walk1 },
    { t0: 13.2, t1: 19.4, at: V(-6.9, 6.05), heading: Math.PI },
    // he turns his back to the shutter and gets his phone out
    { t0: 19.4, t1: 23.6, at: V(-6.9, 6.05), heading: 0.1, turn: 1.0 },
    { t0: 23.6, t1: 28.2, path: [V(-6.9, 6.05), V(-5.4, 5.4), STOP] },
    { t0: 28.2, t1: 36.6, at: STOP, heading: Math.PI / 2 },
    { t0: 36.6, t1: 42.0, path: [STOP, V(-2.5, 5.5), V(-4.4, 6.4), V(-4.45, 7.6), V(-4.5, 9.6), V(-4.95, 11.5), COUNTER] },
    { t0: 42.0, t1: 101, at: COUNTER, heading: 0 },
  ]);

  // ------------------------------------------------------------------ Lucía
  const L_DOOR = V(0.85, -6.55), L_TABLE = V(3.7, -11.8), L_OUT = V(1.3, -6.2), L_PRESS = V(4.7, -12.6), L_BENCH = V(2.0, -8.75);
  const cross = [V(0.6, -4.3), V(0.3, -3.85, 0.0), V(-2.4, 3.85, 0.0), V(-2.7, 4.3)];
  const inMiga = [V(-4.3, 6.3), V(-4.45, 7.6), V(-5.4, 9.4), V(-6.15, 9.95)];
  const inNorte = [V(0.85, -7.4), V(0.85, -9.0), V(1.9, -11.0)];
  const toPoster = Math.atan2(POSTER.x - L_OUT.x, POSTER.z - L_OUT.z);
  const lt = new Track([
    { t0: 0.0, t1: 48.0, at: L_DOOR, heading: 0 },
    { t0: 48.0, t1: 53.2, path: [L_DOOR, ...cross, ...inMiga] },
    { t0: 53.2, t1: 55.0, at: inMiga[3], heading: Math.PI },
    { t0: 55.0, t1: 58.6, path: [...inMiga.slice().reverse(), ...cross.slice().reverse(), L_DOOR] },
    { t0: 58.6, t1: 60.0, at: L_TABLE, heading: Math.PI },
    { t0: 60.0, t1: 68.4, at: L_TABLE, heading: Math.PI },
    { t0: 68.4, t1: 71.4, path: [L_TABLE, V(2.0, -11.8), ...inNorte.slice().reverse(), L_OUT] },
    { t0: 71.4, t1: 79.4, at: L_OUT, heading: toPoster },
    { t0: 79.4, t1: 81.6, path: [L_OUT, ...inNorte, V(3.4, -12.4), L_PRESS] },
    { t0: 81.6, t1: 84.0, at: L_PRESS, heading: 0.63 },
    { t0: 84.0, t1: 85.2, path: [L_PRESS, V(3.0, -11.9), V(1.9, -11.6), V(1.6, -9.6), L_BENCH] },
    { t0: 85.2, t1: 89.6, at: L_BENCH, heading: Math.PI },
    { t0: 89.6, t1: 91.6, path: [L_BENCH, V(0.9, -8.9), V(0.85, -7.4), V(1.3, -6.1)] },
    { t0: 91.6, t1: 101, at: V(1.3, -6.1), heading: Math.PI * 0.92 },
  ]);

  const hourKeys = [
    { T: 0, h: 8.25 }, { T: 20, h: 9.1 }, { T: 36.6, h: 11.2 }, { T: 42, h: 12.0 }, { T: 48, h: 16.8 }, { T: 55, h: 18.7 },
    { T: 60, h: 20.6 }, { T: 64, h: 22.0 }, { T: 81.5, h: 22.6 }, { T: 88, h: 30.2 }, { T: 94, h: 31.3 }, { T: 100, h: 32.4 },
  ].map((k) => ({ ...k, ease: 'linear' }));

  // body-relative helpers (three.js coords)
  const UP = new THREE.Vector3(0, 1, 0);
  const frame = (pos, heading) => {
    const fwd = new THREE.Vector3(Math.sin(heading), 0, Math.cos(heading));
    const right = new THREE.Vector3(-Math.cos(heading), 0, Math.sin(heading));
    return { pos, fwd, right };
  };
  const at = (f, fwd, right, up) => f.pos.clone().addScaledVector(f.fwd, fwd).addScaledVector(f.right, right).addScaledVector(UP, up);
  // hold a phone in front of the chest, screen toward the face
  const phoneHold = (f, w, h) => ({
    pos: at(f, 0.27, 0.07, h), pole: at(f, -0.25, 0.55, h - 0.5), w,
    handDir: f.fwd.clone().multiplyScalar(0.35).addScaledVector(UP, 0.9).addScaledVector(f.right, -0.15).normalize(),
  });
  // both hands working on a surface in front (folding, printing, packing)
  const work = (f, w, h, reach, clock, speed = 1) => {
    const s = Math.sin(clock * 2.2 * speed), c = Math.cos(clock * 1.7 * speed);
    return {
      left: { pos: at(f, reach + 0.04 * s, -0.17 - 0.03 * c, h), pole: at(f, -0.3, -0.6, h - 0.4), w },
      right: { pos: at(f, reach - 0.04 * s, 0.17 + 0.03 * c, h + 0.01 * c), pole: at(f, -0.3, 0.6, h - 0.4), w },
    };
  };
  const walkClips = (m, clock) => {
    const walkW = smooth(0.05, 0.4, m.speed);
    return { walk: { w: walkW, t: m.dist / 1.28 * 0.9667 }, idle: { w: 1 - walkW, t: clock * 0.9 } };
  };
  const addGesture = (clips, name, a, b, T, rate = 2.6, peak = 0.9) => {
    const u = range(a, b, T);
    if (u <= 0 || u >= 1) return;
    const k = Math.sin(u * Math.PI);
    clips[name] = { w: k * peak, t: u * rate };
    clips.idle.w *= 1 - k * peak;
  };

  return function update(T, clock, dev = new URLSearchParams()) {
    const hk = sampleKeys(hourKeys, T, ['h']);
    let hour = dev.has('hour') ? +dev.get('hour') : hk.h;
    hour = ((hour % 24) + 24) % 24;

    // camera, with a gentle handheld drift at street level
    const c = sampleKeys(cam, T, ['pos', 'tgt', 'fov', 'tilt', 'tiltC', 'ap', 'focus']);
    const street = 1 - smooth(4, 20, c.pos.y);
    const n = (a, f) => Math.sin(clock * f + a) * 0.5 + Math.sin(clock * f * 1.7 + a * 3.1) * 0.5;
    c.pos.x += n(1.3, 0.21) * 0.035 * street; c.pos.y += n(2.1, 0.17) * 0.025 * street;
    c.tgt.x += n(4.2, 0.13) * 0.02 * street;

    // ---------------------------------------------------------------- Mateo
    const m = mt.at(T);
    const mf = frame(m.pos, m.heading);
    const mc = walkClips(m, clock);
    if (!dev.has('noshake')) addGesture(mc, 'shake', 15.2, 17.6, T);
    addGesture(mc, 'shake', 22.0, 23.4, T, 2.4, 0.6);
    addGesture(mc, 'nod', 34.4, 36.0, T, 2.2, 0.85);
    const mPhone = (T >= 20 && T < 23.6) || (T >= 30 && T < 36.4);
    const mPhoneW = smooth(20, 20.6, T) * (1 - smooth(23.0, 23.6, T)) + smooth(30, 30.6, T) * (1 - smooth(35.8, 36.4, T));
    const mHands = {};
    if (mPhoneW > 0) mHands.right = phoneHold(mf, mPhoneW, 1.24);
    // handing the box across the counter
    const give = smooth(52.9, 53.6, T) * (1 - smooth(54.1, 54.8, T));
    if (give > 0) mHands.right = { pos: V(-6.15, 10.95, 1.32), pole: at(mf, -0.2, 0.6, 1.0), w: give, handDir: mf.fwd.clone().addScaledVector(UP, 0.2).normalize() };
    let mLook = { w: dev.has('nolook') ? 0 : smooth(12.8, 14, T) * (1 - smooth(19, 20, T)), target: V(-6.5, 7.2, 2.4) };
    if (mPhoneW > 0.01) mLook = { w: mPhoneW * 0.9, target: mHands.right.pos };
    else if (T > 26.5 && T < 30.2) mLook = { w: smooth(26.5, 28, T) * (1 - smooth(29.6, 30.2, T)), target: POSTER };
    else if (T > 51.5 && T < 55.5) mLook = { w: smooth(51.5, 52.5, T) * (1 - smooth(54.8, 55.5, T)) * 0.8, target: lucia.root.position.clone().add(new THREE.Vector3(0, 1.5, 0)) };
    const mFace = mPhoneW > 0.01 ? { name: 'phone', target: at(mf, 0.06, 0, 1.62) } : null;
    mateo.pose({ x: m.pos.x, y: m.pos.y, z: m.pos.z, heading: m.heading, clips: mc, look: mLook, hands: mHands, faceProp: mFace });
    phones.mateo.phone.visible = mPhone;
    if (mPhone) {
      if (T < 23.6) phones.mateo.screen.draw('messages', range(20.2, 22.8, T));
      else if (T < 31.4) phones.mateo.screen.draw('chargix', 0);
      else phones.mateo.screen.draw('packages', range(31.6, 34.6, T));
    }
    props.boxMateo.visible = T >= 52.9 && T < 54.0;

    // ---------------------------------------------------------------- Lucía
    const lucVisible = (T >= 47.6 && T < 57.9) || T >= 59.6 || dev.has('lucia');
    lucia.root.visible = lucVisible;
    if (dev.has('lucia')) {
      const [lx, ly, lh] = dev.get('lucia').split(',').map(Number);
      lucia.pose({ x: V(lx, ly).x, y: 0.15, z: V(lx, ly).z, heading: lh, clips: { idle: { w: 1, t: clock * 0.9 + 0.7 } } });
    } else if (lucVisible) {
      const l = lt.at(T);
      const lf = frame(l.pos, l.heading);
      const lc = walkClips(l, clock + 1.3);
      addGesture(lc, 'shake', 66.4, 68.0, T, 2.4, 0.75);
      addGesture(lc, 'nod', 77.0, 78.6, T, 2.2, 0.85);
      const lPhoneW = smooth(64, 64.6, T) * (1 - smooth(67.8, 68.4, T)) + smooth(73, 73.6, T) * (1 - smooth(78.8, 79.4, T));
      let hands = {};
      if (T >= 60 && T < 64.4) hands = work(lf, smooth(60, 60.6, T) * (1 - smooth(63.8, 64.4, T)), 1.1, 0.42, clock);
      if (T >= 81.6 && T < 84) hands = work(lf, smooth(81.6, 82.2, T) * (1 - smooth(83.4, 84, T)), 1.28, 0.5, clock, 0.7);
      if (T >= 85.2 && T < 88.4) hands = work(lf, smooth(85.2, 85.8, T) * (1 - smooth(87.8, 88.4, T)), 1.08, 0.4, clock, 1.2);
      if (lPhoneW > 0) hands = { right: phoneHold(lf, lPhoneW, 1.16) };
      const take = smooth(53.6, 54.1, T) * (1 - smooth(54.6, 55.2, T));
      if (take > 0) hands = { right: { pos: V(-6.15, 10.6, 1.25), pole: at(lf, -0.2, 0.6, 0.9), w: take } };
      let lLook = { w: 0, target: POSTER };
      if (lPhoneW > 0.01) lLook = { w: lPhoneW * 0.9, target: hands.right.pos };
      else if (T > 70.6 && T < 73.4) lLook = { w: smooth(70.6, 71.6, T) * (1 - smooth(72.8, 73.4, T)), target: POSTER };
      else if (T > 52.6 && T < 55) lLook = { w: 0.7 * smooth(52.6, 53.2, T) * (1 - smooth(54.6, 55, T)), target: mateo.root.position.clone().add(new THREE.Vector3(0, 1.6, 0)) };
      else if (hands.left) lLook = { w: 0.6, target: hands.left.pos.clone().lerp(hands.right.pos, 0.5) };
      const lFace = lPhoneW > 0.01 ? { name: 'phone', target: at(lf, 0.06, 0, 1.52) } : null;
      lucia.pose({ x: l.pos.x, y: l.pos.y, z: l.pos.z, heading: l.heading, clips: lc, look: lLook, hands, faceProp: lFace });
      const lPhone = (T >= 64 && T < 68.4) || (T >= 73 && T < 79.4);
      phones.lucia.phone.visible = lPhone;
      if (lPhone) {
        if (T < 68.4) phones.lucia.screen.draw('messages', range(64.2, 66.6, T));
        else if (T < 74.4) phones.lucia.screen.draw('chargix', 0);
        else phones.lucia.screen.draw('packages', range(74.6, 77.0, T));
      }
    }
    props.boxLucia.visible = lucVisible && T >= 54.0 && T < 57.9;
    props.mailer.visible = lucVisible && T >= 88.4;

    // ---------------------------------------------------------------- sets
    const doorNear = (door, ...who) => {
      let d = 99;
      for (const ch of who) if (ch.root.visible) d = Math.min(d, Math.hypot(ch.root.position.x - door.x, ch.root.position.z - door.z));
      return smooth(1.9, 0.8, d);
    };
    sets.state('MIGA', {
      shutter: smooth(37.4, 39.6, T),
      sign: T >= 46.5 || dev.has('sign') ? 1 : 0,
      signGlow: (T >= 46.5 ? 0.25 + 0.6 * smooth(48, 54, T) : 0) + (dev.has('sign') ? 0.6 : 0),
      build: range(42.0, 47.0, T),
      light: smooth(46.5, 49, T),
      oven: smooth(43.6, 45, T) * 0.9,
      door: doorNear(MIGA_DOOR, mateo, lucia),
    });
    sites.miga.draw(T < 42 ? 'off' : T < 47.5 ? 'build' : (T >= 53 && T < 56.5) ? 'order' : 'live', T < 47.5 ? range(42, 47, T) : range(53, 54.6, T));
    sets.state('NORTE', {
      shutter: lerp(0.5, 1, smooth(88, 89.8, T)),
      sign: T >= 86.4 ? 1 : 0,
      signGlow: T >= 86.4 ? 0.9 : 0,
      pieces: { wall: range(83, 85.5, T) },
      light: T < 60 ? 0.5 : T < 88 ? 1 : 1 - 0.5 * smooth(88, 92, T),
      dryer: smooth(80, 81, T) * (1 - smooth(87.5, 88.5, T)),
      door: doorNear(NORTE_DOOR, lucia),
    });
    sites.norte.draw(T < 81.5 ? (T < 60 ? 'off' : 'live') : T < 86.5 ? 'build' : (T >= 90 && T < 94) ? 'order' : 'live', T < 86.5 ? range(81.5, 86.2, T) : range(90, 91.6, T));

    // focus: whoever the shot is about
    const focusOn = T < 47.6 ? mateo : T < 52 ? lucia : T < 56 ? mateo : lucia;
    return {
      hour,
      camera: c,
      focusPoint: focusOn.root.position.clone().add(new THREE.Vector3(0, 1.2, 0)),
      pick: (T >= 31.4 && T < 36.2) ? PICK.mateo : (T >= 74.4 && T < 79.2) ? PICK.lucia : null,
      // the phone screen shown full size beside the shot (packages are shown as cards instead)
      phone: (T >= 20.4 && T < 23.4) || (T >= 30.2 && T < 31.4) ? 'mateo' : (T >= 64.4 && T < 68.2) || (T >= 73.2 && T < 74.4) ? 'lucia' : null,
    };
  };
}
