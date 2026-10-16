// Scene, sky, sun, fog and the time-of-day system.
import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';

// Blender authoring coordinates (Z up, +Y north) -> three.js (Y up, -Z north)
export const B = (x, y, z = 0) => new THREE.Vector3(x, z, -y);

const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;

// key lighting states by hour of day (Mexico City, mid October)
const KEYS = [
  { h: 4.8, elev: -14, az: 95, sun: '#6f7fb0', sunI: 0.0, hemiSky: '#2a3552', hemiGround: '#151618', hemiI: 0.35, fog: '#3a4560', fogD: 0.0075, night: 1.0, exposure: 1.05, turb: 2, ray: 0.6 },
  { h: 6.2, elev: -2.5, az: 100, sun: '#ff9c66', sunI: 0.15, hemiSky: '#8291b8', hemiGround: '#3a3430', hemiI: 0.55, fog: '#b8a6a8', fogD: 0.0072, night: 0.65, exposure: 1.0, turb: 6, ray: 2.2 },
  { h: 6.9, elev: 4, az: 108, sun: '#ffb27a', sunI: 1.6, hemiSky: '#c9cde0', hemiGround: '#6b5a4a', hemiI: 0.6, fog: '#e8c9b2', fogD: 0.0068, night: 0.15, exposure: 0.95, turb: 7, ray: 2.5 },
  { h: 8.5, elev: 24, az: 128, sun: '#ffe6c4', sunI: 3.0, hemiSky: '#c7d6ea', hemiGround: '#8a7a68', hemiI: 0.7, fog: '#d9dfe6', fogD: 0.0062, night: 0.0, exposure: 0.9, turb: 4, ray: 1.6 },
  { h: 12.5, elev: 60, az: 180, sun: '#fff6ea', sunI: 3.6, hemiSky: '#c8d8ec', hemiGround: '#8d8170', hemiI: 0.75, fog: '#dfe5ea', fogD: 0.006, night: 0.0, exposure: 0.85, turb: 3, ray: 1.3 },
  { h: 16.8, elev: 24, az: 245, sun: '#ffd9a8', sunI: 3.0, hemiSky: '#c9d3e2', hemiGround: '#8e7a62', hemiI: 0.7, fog: '#e6dccb', fogD: 0.0064, night: 0.0, exposure: 0.88, turb: 5, ray: 1.8 },
  { h: 17.9, elev: 8, az: 252, sun: '#ffb070', sunI: 2.4, hemiSky: '#b7b9cf', hemiGround: '#7a5e48', hemiI: 0.62, fog: '#efc9a2', fogD: 0.0068, night: 0.08, exposure: 0.92, turb: 8, ray: 2.6 },
  { h: 18.6, elev: 0.5, az: 256, sun: '#ff8a50', sunI: 0.9, hemiSky: '#8f8fb4', hemiGround: '#4f3f38', hemiI: 0.55, fog: '#c99a8e', fogD: 0.007, night: 0.45, exposure: 1.0, turb: 9, ray: 3.0 },
  { h: 19.3, elev: -6, az: 262, sun: '#7d7fb8', sunI: 0.0, hemiSky: '#46507a', hemiGround: '#242226', hemiI: 0.42, fog: '#4c5274', fogD: 0.0074, night: 0.85, exposure: 1.05, turb: 3, ray: 1.0 },
  { h: 21.5, elev: -20, az: 280, sun: '#6f7fb0', sunI: 0.0, hemiSky: '#222a44', hemiGround: '#141416', hemiI: 0.32, fog: '#2c344c', fogD: 0.0078, night: 1.0, exposure: 1.1, turb: 2, ray: 0.5 },
];

// global balance for Neutral tone mapping: a strong key light against a modest sky fill
const LOOK = { sun: 1.3, hemi: 0.6, env: 0.5, fog: 0.5, exposure: 1.3 };

function sample(h) {
  // clamp into the keyed range so the ends also come back as Colors (the raw keys hold hex strings)
  h = Math.min(KEYS[KEYS.length - 1].h, Math.max(KEYS[0].h + 1e-4, h));
  for (let i = 0; i < KEYS.length - 1; i++) {
    const a = KEYS[i], b = KEYS[i + 1];
    if (h <= b.h) {
      const t = smooth(0, 1, (h - a.h) / (b.h - a.h));
      const o = {};
      for (const k of Object.keys(a)) {
        if (typeof a[k] === 'number') o[k] = lerp(a[k], b[k], t);
        else o[k] = new THREE.Color(a[k]).lerp(new THREE.Color(b[k]), t);
      }
      return o;
    }
  }
  return KEYS[KEYS.length - 1];
}

export class World {
  constructor(renderer, { quality }) {
    this.renderer = renderer;
    this.quality = quality;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color('#dfe5ea');
    this.scene.fog = new THREE.FogExp2('#dfe5ea', 0.006);

    this.sky = new Sky();
    this.sky.scale.setScalar(4500);
    const su = this.sky.material.uniforms;
    su.mieCoefficient.value = 0.004; su.mieDirectionalG.value = 0.82;
    su.cloudCoverage.value = 0.35; su.cloudDensity.value = 0.35; su.cloudScale.value = 0.00018;
    this.sky.material.fog = false;
    this.scene.add(this.sky);

    this.sun = new THREE.DirectionalLight('#fff', 3);
    this.sun.castShadow = true;
    const sm = quality === 'high' ? 4096 : quality === 'mid' ? 2048 : 1024;
    this.sun.shadow.mapSize.set(sm, sm);
    const sc = this.sun.shadow.camera;
    sc.left = -34; sc.right = 34; sc.top = 34; sc.bottom = -34; sc.near = 1; sc.far = 400;
    this.sun.shadow.bias = -0.00025;
    this.sun.shadow.normalBias = 0.035;
    this.sun.shadow.radius = 3;
    this.scene.add(this.sun, this.sun.target);

    this.hemi = new THREE.HemisphereLight('#c8d8ec', '#8d8170', 0.7);
    this.scene.add(this.hemi);

    // environment (sky-only scene, re-baked when the time of day moves enough)
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.envScene = new THREE.Scene();
    this.envSky = new Sky();
    this.envSky.scale.setScalar(1000);
    Object.assign(this.envSky.material.uniforms.cloudCoverage, { value: 0.0 });
    this.envScene.add(this.envSky);
    this.envGround = new THREE.Mesh(new THREE.CircleGeometry(900, 24).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: '#6d665d' }));
    this.envGround.position.y = -2;
    this.envScene.add(this.envGround);
    this.envRT = null;
    this.lastEnvH = -99;
    this.hour = 9;
    this.state = sample(9);
    this.focus = new THREE.Vector3();
  }

  setHour(h, focus) {
    const s = sample(h);
    this.hour = h; this.state = s;
    const el = THREE.MathUtils.degToRad(s.elev), az = THREE.MathUtils.degToRad(s.az);
    const dir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el));
    this.sunDir = dir;
    for (const sky of [this.sky, this.envSky]) {
      const u = sky.material.uniforms;
      u.sunPosition.value.copy(dir);
      u.turbidity.value = s.turb; u.rayleigh.value = s.ray;
    }
    // keep the shadow frustum centred on what the camera looks at
    if (focus) this.focus.copy(focus);
    const lightDir = dir.clone(); if (lightDir.y < 0.06) lightDir.y = 0.06; lightDir.normalize();
    this.sun.position.copy(this.focus).addScaledVector(lightDir, 150);
    this.sun.target.position.copy(this.focus);
    this.sun.color.copy(s.sun);
    this.sun.intensity = s.sunI * LOOK.sun * smooth(-1.5, 3, s.elev);
    this.sun.castShadow = this.sun.intensity > 0.05;
    this.hemi.color.copy(s.hemiSky); this.hemi.groundColor.copy(s.hemiGround); this.hemi.intensity = s.hemiI * LOOK.hemi;
    this.scene.fog.color.copy(s.fog); this.scene.fog.density = s.fogD * LOOK.fog;
    this.renderer.toneMappingExposure = s.exposure * LOOK.exposure;
    this.night = s.night;
    if (Math.abs(h - this.lastEnvH) > 0.12) this.bakeEnv(s);
    this.scene.environmentIntensity = (0.55 + 0.45 * (1 - s.night)) * LOOK.env;
  }

  bakeEnv(s) {
    this.lastEnvH = this.hour;
    this.envGround.material.color.copy(s.hemiGround).multiplyScalar(0.8);
    const rt = this.pmrem.fromScene(this.envScene, 0, 0.1, 2000, { size: this.quality === 'low' ? 64 : 128 });
    if (this.envRT) this.envRT.dispose();
    this.envRT = rt;
    this.scene.environment = rt.texture;
    this.scene.environmentIntensity = (0.55 + 0.45 * (1 - s.night)) * LOOK.env;
  }
}
