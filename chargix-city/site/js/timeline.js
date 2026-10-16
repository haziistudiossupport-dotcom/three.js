// Timeline helpers: every visual state is a pure function of the story time T (scrubbable forwards and backwards).
import * as THREE from 'three';

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
export const smoother = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * t * (t * (t * 6 - 15) + 10); };
export const lerp = (a, b, t) => a + (b - a) * t;
export const range = (a, b, x) => clamp((x - a) / (b - a));
export const easeInOut = (t) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

// Camera / scalar key tracks. keys: [{T, ...values}], vectors are THREE.Vector3.
// Between keys the motion follows a Catmull-Rom spline with eased progress, so the camera settles on every key.
export function sampleKeys(keys, T, fields) {
  if (T <= keys[0].T) return pick(keys[0], fields);
  const n = keys.length;
  if (T >= keys[n - 1].T) return pick(keys[n - 1], fields);
  let i = 0;
  while (i < n - 2 && T > keys[i + 1].T) i++;
  const k0 = keys[Math.max(0, i - 1)], k1 = keys[i], k2 = keys[i + 1], k3 = keys[Math.min(n - 1, i + 2)];
  const raw = (T - k1.T) / (k2.T - k1.T);
  const e = k1.ease === 'linear' ? raw : k1.ease === 'in' ? raw * raw : k1.ease === 'out' ? 1 - (1 - raw) * (1 - raw) : smoother(0, 1, raw);
  const out = {};
  for (const f of fields) {
    const a = k1[f], b = k2[f];
    if (a === undefined) continue;
    if (a.isVector3) {
      const p0 = k0[f] || a, p3 = k3[f] || b;
      out[f] = catmull(p0, a, b, p3, e);
    } else if (typeof a === 'number') {
      out[f] = lerp(a, b ?? a, e);
    } else out[f] = a;
  }
  return out;
}

function pick(k, fields) { const o = {}; for (const f of fields) if (k[f] !== undefined) o[f] = k[f].isVector3 ? k[f].clone() : k[f]; return o; }

function catmull(p0, p1, p2, p3, t) {
  const t2 = t * t, t3 = t2 * t;
  return new THREE.Vector3(
    0.5 * ((2 * p1.x) + (-p0.x + p2.x) * t + (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 + (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3),
    0.5 * ((2 * p1.y) + (-p0.y + p2.y) * t + (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 + (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3),
    0.5 * ((2 * p1.z) + (-p0.z + p2.z) * t + (2 * p0.z - 5 * p1.z + 4 * p2.z - p3.z) * t2 + (-p0.z + 3 * p1.z - 3 * p2.z + p3.z) * t3));
}

// Character movement track: segments of walking along polylines and standing.
// seg: { t0, t1, path:[Vector3...] } walks the path (eased start/stop), or { t0, t1, at:Vector3, heading } stands.
export class Track {
  constructor(segs, { cycle = 1.28 } = {}) {
    this.segs = segs; this.cycle = cycle;
    for (const s of segs) {
      if (s.path) {
        s.len = 0; s.cum = [0];
        for (let i = 1; i < s.path.length; i++) { s.len += s.path[i].distanceTo(s.path[i - 1]); s.cum.push(s.len); }
      }
    }
    // walk-cycle phase continuity: accumulate distance over earlier walking segments
    let acc = 0;
    for (const s of segs) { s.dist0 = acc; if (s.path) acc += s.len; }
  }

  // Headings ease across segment boundaries so nobody snaps round on the spot: a stand turns from the
  // direction of the walk that led into it (stepping while it turns), and a walk turns out of the stand.
  at(T) {
    const r = this.raw(T);
    const i = this.segs.indexOf(r.seg);
    if (i <= 0) return r;
    const s = r.seg, turn = s.turn ?? 0.7;
    if (T >= s.t0 + turn) return r;
    const prev = this.raw(s.t0 - 1e-4).heading;
    let d = r.heading - prev;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    const k = smooth(s.t0, s.t0 + turn, T);
    r.heading = prev + d * k;
    if (!s.path) {
      const step = Math.min(1, Math.abs(d) / 1.2);
      r.speed = Math.max(r.speed, 0.45 * step * Math.sin(Math.PI * k));
      r.dist += Math.abs(d) * 0.32 * k;
    }
    return r;
  }

  raw(T) {
    let s = this.segs[0];
    for (const g of this.segs) { if (T >= g.t0) s = g; }
    if (T < this.segs[0].t0) s = this.segs[0];
    if (!s.path) {
      return { pos: s.at.clone(), heading: s.heading ?? 0, speed: 0, dist: s.dist0, seg: s };
    }
    const u = range(s.t0, s.t1, T);
    // ease in/out over the first/last 1.6 m so feet accelerate naturally
    const e = s.ease === false ? u : easeWalk(u, s.len);
    const d = e * s.len;
    let i = 1;
    while (i < s.cum.length - 1 && s.cum[i] < d) i++;
    const a = s.path[i - 1], b = s.path[i];
    const f = (d - s.cum[i - 1]) / Math.max(1e-6, s.cum[i] - s.cum[i - 1]);
    const pos = a.clone().lerp(b, clamp(f));
    const dir = b.clone().sub(a);
    // smooth heading through corners: look slightly ahead
    const ahead = this.pointAt(s, Math.min(s.len, d + 0.6));
    const hdir = ahead.clone().sub(pos); if (hdir.lengthSq() < 1e-6) hdir.copy(dir);
    const heading = Math.atan2(hdir.x, hdir.z);
    const du = 1e-3, e2 = easeWalk(clamp(u + du), s.len);
    const speed = (e2 - e) / du; // relative speed 0..~1.x
    return { pos, heading, speed: clamp(speed / 1.0, 0, 1.3), dist: s.dist0 + d, seg: s };
  }

  pointAt(s, d) {
    let i = 1;
    while (i < s.cum.length - 1 && s.cum[i] < d) i++;
    const a = s.path[i - 1], b = s.path[i];
    const f = (d - s.cum[i - 1]) / Math.max(1e-6, s.cum[i] - s.cum[i - 1]);
    return a.clone().lerp(b, clamp(f));
  }
}

function easeWalk(u, len) {
  // trapezoidal velocity profile: accelerate over k, cruise, decelerate over k (k in normalised units)
  const k = Math.min(0.35, 1.6 / Math.max(len, 0.01));
  const vmax = 1 / (1 - k);
  if (u < k) return 0.5 * vmax * u * u / k;
  if (u > 1 - k) { const r = 1 - u; return 1 - 0.5 * vmax * r * r / k; }
  return 0.5 * vmax * k + vmax * (u - k);
}
