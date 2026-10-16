// Material library for the CHARGIX city. Blender material names map to physically based three.js materials.
// UV0 in the city GLB is in metres, so each tiling texture repeats by its physical tile size.
import * as THREE from 'three';

const TILE = { plaster: 2.0, cantera: 2.4, sidewalk: 2.4, asphalt: 4.0, roof: 3.0, tiles: 0.8, shutter: 1.0, wood: 1.0 };

// low-frequency world-space tone variation breaks up visible texture repeats: [amount, frequency per metre]
const MACRO = { sidewalk: [0.1, 0.22], asphalt: [0.09, 0.12], plaster: [0.06, 0.3], cantera: [0.07, 0.35], roof: [0.12, 0.2] };

function addMacro(m, amt, freq) {
  m.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vMacroP;')
      .replace('#include <fog_vertex>', '#include <fog_vertex>\nvMacroP = (modelMatrix * vec4(transformed, 1.0)).xyz;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        varying vec3 vMacroP;
        float mHash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float mNoise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(mHash(i), mHash(i + vec2(1, 0)), f.x), mix(mHash(i + vec2(0, 1)), mHash(i + vec2(1, 1)), f.x), f.y); }`)
      .replace('#include <map_fragment>', `#include <map_fragment>
        {
          vec2 q = vec2(vMacroP.x + vMacroP.z * 0.7, vMacroP.y * 1.3 + vMacroP.z * 0.6) * ${freq.toFixed(3)};
          float n = mNoise(q) * 0.6 + mNoise(q * 2.7 + 13.1) * 0.4;
          diffuseColor.rgb *= 1.0 + ${amt.toFixed(3)} * (n - 0.5) * 2.0;
        }`);
  };
  m.customProgramCacheKey = () => `macro${amt}_${freq}`;
}

export const PALETTE = {
  ochre: '#d3a65e', terracotta: '#c0704f', cream: '#eadfc8', sage: '#a7b49a', rose: '#d9a497',
  white: '#ece8df', gray: '#b9b6ae',
};

export class MaterialLibrary {
  constructor(renderer, base) {
    this.renderer = renderer;
    this.base = base;
    this.loader = new THREE.TextureLoader();
    this.tex = {};
    this.mats = {};
    this.uniforms = {
      uNight: { value: 0 },          // 0 day .. 1 night (window lights, lamps)
      uTime: { value: 0 },
      uRooms: { value: null },
      uSunDir: { value: new THREE.Vector3(0, 1, 0) },
    };
  }

  texture(name, srgb = true, tile = 1) {
    const key = name + (srgb ? ':s' : ':l');
    if (!this.tex[key]) {
      const t = this.loader.load(this.base + 'cx-tex-' + name + '.webp');
      t.wrapS = t.wrapT = THREE.RepeatWrapping;
      t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      t.anisotropy = Math.min(8, this.renderer.capabilities.getMaxAnisotropy());
      t.repeat.set(1 / tile, 1 / tile);
      this.tex[key] = t;
    }
    return this.tex[key];
  }

  pbr(kind, color, opts = {}) {
    const tile = TILE[kind];
    const ns = opts.ns ?? 0.8; delete opts.ns;
    const macro = opts.macro ?? MACRO[kind]; delete opts.macro;
    const m = new THREE.MeshStandardMaterial({
      color: new THREE.Color(color),
      map: tile ? this.texture(kind + '-a', true, tile) : null,
      normalMap: tile ? this.texture(kind + '-n', false, tile) : null,
      roughness: 0.9, metalness: 0, ...opts,
    });
    if (m.normalMap) m.normalScale.set(ns, ns);
    if (macro) addMacro(m, macro[0], macro[1]);
    return m;
  }

  // residential windows: reflective glass over a fake interior; random rooms light up at night
  glassRes() {
    const rooms = this.texture('rooms-a', true, 1);
    rooms.wrapS = rooms.wrapT = THREE.ClampToEdgeWrapping;
    this.uniforms.uRooms.value = rooms;
    const m = new THREE.MeshStandardMaterial({ color: 0x0d1013, roughness: 0.04, metalness: 0.0, envMapIntensity: 1.25 });
    m.onBeforeCompile = (sh) => {
      sh.uniforms.uNight = this.uniforms.uNight;
      sh.uniforms.uRooms = this.uniforms.uRooms;
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nattribute vec2 uv1;\nvarying vec2 vWin;\nvarying vec3 vViewT;')
        .replace('#include <fog_vertex>', `#include <fog_vertex>
          vWin = uv1;
          vec3 wp = (modelMatrix * vec4(transformed, 1.0)).xyz;
          vViewT = normalize(cameraPosition - wp);`);
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', `#include <common>
          uniform float uNight; uniform sampler2D uRooms; varying vec2 vWin; varying vec3 vViewT;
          float h11(float n){ return fract(sin(n*127.1)*43758.5453); }`)
        .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
          float wid = floor(vWin.x * 0.5);
          vec2 lu = vec2(fract(vWin.x * 0.5) * 2.0, vWin.y);
          float r1 = h11(wid), r2 = h11(wid + 17.0), r3 = h11(wid + 41.0);
          // cheap parallax: shift the room picture against the view direction
          vec2 cell = vec2(floor(r1 * 8.0), floor(r2 * 4.0));
          vec2 par = clamp(lu + vec2(-vViewT.x, vViewT.y) * 0.06, 0.02, 0.98);
          vec3 room = texture2D(uRooms, (cell + par) / vec2(8.0, 4.0) * vec2(1.0, 1.0)).rgb;
          float lit = step(0.42, r3) * uNight;
          vec3 warm = mix(vec3(1.0, 0.78, 0.52), vec3(1.0, 0.88, 0.7), r2);
          float curtain = smoothstep(0.0, 0.25, lu.y) * 0.4 + 0.6;
          diffuseColor.rgb = mix(diffuseColor.rgb, room * 0.16, 0.85);
          totalEmissiveRadiance += room * warm * lit * 1.6 * curtain + room * 0.015 * (1.0 - uNight);`);
    };
    m.customProgramCacheKey = () => 'glassRes';
    return m;
  }

  // flat background massing with a procedural window grid that glows at night
  far(color) {
    const m = new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: 0.95 });
    m.onBeforeCompile = (sh) => {
      sh.uniforms.uNight = this.uniforms.uNight;
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWP; varying vec3 vWN;')
        .replace('#include <fog_vertex>', '#include <fog_vertex>\nvWP = (modelMatrix * vec4(transformed,1.0)).xyz; vWN = normalize(mat3(modelMatrix) * objectNormal);');
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', `#include <common>
          uniform float uNight; varying vec3 vWP; varying vec3 vWN;
          float h21(vec2 p){ return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }`)
        .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
          if (abs(vWN.y) < 0.5) {
            float u = abs(vWN.x) > 0.5 ? vWP.z : vWP.x;
            vec2 g = vec2(u / 2.6, (vWP.y - 0.6) / 3.1);
            vec2 f = fract(g); vec2 id = floor(g);
            float win = step(0.28, f.x) * step(f.x, 0.72) * step(0.3, f.y) * step(f.y, 0.82) * step(1.0, vWP.y);
            diffuseColor.rgb *= 1.0 - win * 0.55;
            float on = step(0.55, h21(id + floor(vWP.xz * 0.01))) * uNight;
            totalEmissiveRadiance += win * on * vec3(1.0, 0.75, 0.48) * 0.9;
          }`);
    };
    m.customProgramCacheKey = () => 'far';
    return m;
  }

  make(name) {
    if (this.mats[name]) return this.mats[name];
    let m;
    const P = PALETTE;
    const [head, tail] = name.split('_');
    if (head === 'plaster' && P[tail]) m = this.pbr('plaster', P[tail], { roughness: 0.93 });
    else if (head === 'party' && P[tail]) m = this.pbr('plaster', new THREE.Color(P[tail]).multiplyScalar(0.86), { roughness: 0.95 });
    else if (head === 'trim' && P[tail]) m = this.pbr('plaster', new THREE.Color(P[tail]).lerp(new THREE.Color('#ffffff'), 0.15), { roughness: 0.85, ns: 0.4 });
    else if (head === 'far') m = this.far({ a: '#b7ab98', b: '#a9a49b', c: '#c2a891', d: '#9ea3a0' }[tail] || '#aaa');
    else switch (name) {
      case 'cantera': case 'cantera_reveal': m = this.pbr('cantera', '#ffffff', { roughness: 0.88, ns: 1.0 }); break;
      case 'plaster_reveal': m = this.pbr('plaster', '#d9d2c4', { roughness: 0.95 }); break;
      case 'sill': case 'coping': case 'step': m = this.pbr('cantera', '#efe6dc', { roughness: 0.85, ns: 0.5 }); break;
      case 'concrete': m = this.pbr('plaster', '#bdb7ad', { roughness: 0.95 }); break;
      case 'steel': m = new THREE.MeshStandardMaterial({ color: 0x26292b, roughness: 0.42, metalness: 0.55 }); break;
      case 'steel_light': m = new THREE.MeshStandardMaterial({ color: 0x5b6063, roughness: 0.4, metalness: 0.6 }); break;
      case 'iron': m = new THREE.MeshStandardMaterial({ color: 0x1b1c1e, roughness: 0.5, metalness: 0.65 }); break;
      case 'brass': m = new THREE.MeshStandardMaterial({ color: 0xc8a26a, roughness: 0.3, metalness: 1.0 }); break;
      case 'glass_res': m = this.glassRes(); break;
      case 'glass_shopfront': case 'glass_story': case 'glass_clear':
        m = new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.03, metalness: 0, transparent: true, opacity: 0.16,
          envMapIntensity: 1.4, depthWrite: false, side: THREE.DoubleSide });
        break;
      case 'void': m = new THREE.MeshBasicMaterial({ color: 0x050505 }); break;
      case 'shop_floor': m = this.pbr('tiles', '#cfc6b6', { roughness: 0.6, ns: 0.4 }); break;
      case 'shop_back': m = new THREE.MeshStandardMaterial({ color: 0xb8a58c, roughness: 0.8, emissive: 0x241a10 }); break;
      case 'shop_side': m = new THREE.MeshStandardMaterial({ color: 0xcfc3b0, roughness: 0.9, emissive: 0x1c140c }); break;
      case 'shop_ceiling': m = new THREE.MeshStandardMaterial({ color: 0xe8e0d0, roughness: 0.9, emissive: 0x3a2e20 }); break;
      case 'shutter': case 'shutter_story': m = this.pbr('shutter', '#b4b6b5', { roughness: 0.5, metalness: 0.55, ns: 1.0 }); break;
      case 'shutter_box': m = new THREE.MeshStandardMaterial({ color: 0x8d9191, roughness: 0.5, metalness: 0.5 }); break;
      case 'door_steel': m = new THREE.MeshStandardMaterial({ color: 0x2f3a33, roughness: 0.55, metalness: 0.4 }); break;
      case 'roof_red': m = this.pbr('roof', '#b25a40', { roughness: 0.9 }); break;
      case 'roof_gray': m = this.pbr('roof', '#aaa69e', { roughness: 0.92 }); break;
      case 'tinaco': m = new THREE.MeshStandardMaterial({ color: 0x18191b, roughness: 0.55 }); break;
      case 'gas_tank': m = new THREE.MeshStandardMaterial({ color: 0xd8d4ca, roughness: 0.45, metalness: 0.3 }); break;
      case 'sidewalk': m = this.pbr('sidewalk', '#ffffff', { roughness: 0.92, ns: 0.9 }); break;
      case 'curb': m = this.pbr('sidewalk', '#d8d3c8', { roughness: 0.9, ns: 0.4 }); break;
      case 'asphalt': m = this.pbr('asphalt', '#ffffff', { roughness: 0.95, ns: 0.6 }); break;
      case 'paint_white': m = new THREE.MeshStandardMaterial({ color: 0xe6e3da, roughness: 0.75, polygonOffset: true, polygonOffsetFactor: -2 }); break;
      case 'ground_dark': m = new THREE.MeshStandardMaterial({ color: 0x55524c, roughness: 1 }); break;
      case 'ground_far': m = new THREE.MeshStandardMaterial({ color: 0x8a867e, roughness: 1 }); break;
      case 'manhole': case 'drain': m = new THREE.MeshStandardMaterial({ color: 0x2e2f30, roughness: 0.6, metalness: 0.5, polygonOffset: true, polygonOffsetFactor: -2 }); break;
      case 'lamp_metal': m = new THREE.MeshStandardMaterial({ color: 0x2d302e, roughness: 0.45, metalness: 0.6 }); break;
      case 'lamp_glow': m = new THREE.MeshStandardMaterial({ color: 0xe9e6dd, roughness: 0.3, emissive: 0xffc98a, emissiveIntensity: 0 });
        m.userData.nightEmissive = 7.0; break;
      case 'soil': m = new THREE.MeshStandardMaterial({ color: 0x3b3128, roughness: 1 }); break;
      case 'bark': m = new THREE.MeshStandardMaterial({ color: 0x5a5148, roughness: 0.95 }); break;
      case 'foliage': m = this.pbr('plaster', '#6d8752', { roughness: 0.95, ns: 1.6 }); break;
      case 'kiosk_green': m = new THREE.MeshStandardMaterial({ color: 0x2e5f49, roughness: 0.5, metalness: 0.3 }); break;
      case 'kiosk_awning': m = new THREE.MeshStandardMaterial({ color: 0xb8463a, roughness: 0.8 }); break;
      case 'kiosk_goods': m = new THREE.MeshStandardMaterial({ color: 0xd0c4b0, roughness: 0.8 }); break;
      case 'bin_green': m = new THREE.MeshStandardMaterial({ color: 0x2f5a46, roughness: 0.5, metalness: 0.3 }); break;
      case 'bin_dark': m = new THREE.MeshStandardMaterial({ color: 0x222423, roughness: 0.5, metalness: 0.3 }); break;
      case 'sign_frame': m = new THREE.MeshStandardMaterial({ color: 0xe8e6e0, roughness: 0.5 }); break;
      case 'tiles': m = this.pbr('tiles', '#ffffff', { roughness: 0.45, ns: 0.6 }); break;
      case 'wood': m = this.pbr('wood', '#ffffff', { roughness: 0.6 }); break;
      // shop fit-out
      case 'oak': m = this.pbr('wood', '#c99c6c', { roughness: 0.55, ns: 0.5 }); break;
      case 'oak_dark': m = this.pbr('wood', '#7e5a3e', { roughness: 0.6, ns: 0.5 }); break;
      case 'stone_white': m = this.pbr('plaster', '#f3eee6', { roughness: 0.32, ns: 0.15, macro: [0.03, 1.5] }); break;
      case 'steel_brushed': m = new THREE.MeshStandardMaterial({ color: 0xb9bdbe, roughness: 0.32, metalness: 0.85 }); break;
      case 'aluminium': m = new THREE.MeshStandardMaterial({ color: 0xc9cccd, roughness: 0.28, metalness: 0.9 }); break;
      case 'oven_glass': m = new THREE.MeshStandardMaterial({ color: 0x0c0c0d, roughness: 0.08, metalness: 0.2, emissive: 0xff8a3c, emissiveIntensity: 0 }); break;
      case 'mixer': m = new THREE.MeshStandardMaterial({ color: 0xe9dcc6, roughness: 0.28, metalness: 0.1 }); break;
      case 'kraft': m = this.pbr('plaster', '#b88d5f', { roughness: 0.85, ns: 0.3, macro: [0.04, 3] }); break;
      case 'kraft_lid': m = this.pbr('plaster', '#a98157', { roughness: 0.85, ns: 0.3, macro: [0.04, 3] }); break;
      case 'label_cream': m = new THREE.MeshStandardMaterial({ color: 0xf2e9d6, roughness: 0.7 }); break;
      case 'cookie_choc': m = this.pbr('plaster', '#6a4229', { roughness: 0.8, ns: 2.6, macro: [0.12, 9] }); break;
      case 'cookie_red': m = this.pbr('plaster', '#9b3a31', { roughness: 0.8, ns: 2.6, macro: [0.12, 9] }); break;
      case 'cookie_matcha': m = this.pbr('plaster', '#8c9d62', { roughness: 0.8, ns: 2.6, macro: [0.12, 9] }); break;
      case 'cookie_oat': m = this.pbr('plaster', '#c7975d', { roughness: 0.8, ns: 2.6, macro: [0.12, 9] }); break;
      case 'jar_glass':
        m = new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.05, transparent: true, opacity: 0.22, envMapIntensity: 1.3, depthWrite: false });
        break;
      case 'bulb': m = new THREE.MeshStandardMaterial({ color: 0xfff1d8, roughness: 0.3, emissive: 0xffc27a, emissiveIntensity: 0 }); break;
      case 'ceramic': m = new THREE.MeshStandardMaterial({ color: 0xe8e2d6, roughness: 0.42 }); break;
      case 'mat': m = new THREE.MeshStandardMaterial({ color: 0x2c2a27, roughness: 1 }); break;
      // NORTE workshop
      case 'cotton_sage': m = this.pbr('plaster', '#8a9a7b', { roughness: 0.95, ns: 0.35, macro: [0.05, 6] }); break;
      case 'cotton_cream': m = this.pbr('plaster', '#e9e4d8', { roughness: 0.95, ns: 0.35, macro: [0.04, 6] }); break;
      case 'cotton_black': m = this.pbr('plaster', '#26272a', { roughness: 0.92, ns: 0.35, macro: [0.05, 6] }); break;
      case 'cotton_rust': m = this.pbr('plaster', '#b9573a', { roughness: 0.95, ns: 0.35, macro: [0.05, 6] }); break;
      case 'cotton_ink': m = this.pbr('plaster', '#2d3a52', { roughness: 0.95, ns: 0.35, macro: [0.05, 6] }); break;
      case 'rubber': m = new THREE.MeshStandardMaterial({ color: 0x1a1a1b, roughness: 0.75 }); break;
      case 'screen_mesh': m = new THREE.MeshStandardMaterial({ color: 0xd9c25a, roughness: 0.6, transparent: true, opacity: 0.55, side: THREE.DoubleSide }); break;
      case 'dryer_glow': m = new THREE.MeshStandardMaterial({ color: 0x1a0d08, roughness: 0.3, emissive: 0xff5a28, emissiveIntensity: 0 }); break;
      case 'cutting_mat': m = new THREE.MeshStandardMaterial({ color: 0x3f5a4c, roughness: 0.8 }); break;
      case 'poly_mailer': m = new THREE.MeshStandardMaterial({ color: 0xcfd0cc, roughness: 0.45 }); break;
      case 'plant_leaves': {
        const t = this.texture('leaves-a', true, 1); t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
        m = new THREE.MeshStandardMaterial({ map: t, alphaTest: 0.42, side: THREE.DoubleSide, roughness: 0.6, color: 0xe6f0dc });
        break;
      }
      default:
        m = new THREE.MeshStandardMaterial({ color: 0xc8c2b8, roughness: 0.85 });
        m.userData.fallback = true;
    }
    m.name = name;
    this.mats[name] = m;
    return m;
  }

  setNight(n) {
    this.uniforms.uNight.value = n;
    for (const m of Object.values(this.mats)) {
      if (m.userData.nightEmissive) m.emissiveIntensity = m.userData.nightEmissive * n;
    }
  }
}
