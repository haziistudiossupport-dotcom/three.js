// Post-processing: MSAA scene render -> tilt-shift / depth-of-field -> bloom -> tone map (AgX) -> grade, grain, vignette.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const DofShader = {
  uniforms: {
    tDiffuse: { value: null }, tDepth: { value: null },
    uRes: { value: new THREE.Vector2(1, 1) },
    uNear: { value: 0.1 }, uFar: { value: 1000 },
    uFocus: { value: 10 },          // focus distance (m)
    uAperture: { value: 1.0 },      // depth-based blur strength
    uTiltCenter: { value: 0.5 },    // screen-space tilt-shift band centre (0 bottom .. 1 top)
    uTiltWidth: { value: 0.22 },
    uTilt: { value: 0.0 },          // tilt-shift amount 0..1
    uMaxBlur: { value: 9.0 },       // px at 1080p
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: /* glsl */`
    #include <packing>
    uniform sampler2D tDiffuse, tDepth; uniform vec2 uRes; uniform float uNear, uFar, uFocus, uAperture, uTiltCenter, uTiltWidth, uTilt, uMaxBlur;
    varying vec2 vUv;
    float viewZ(vec2 uv){ float d = texture2D(tDepth, uv).x; return -perspectiveDepthToViewZ(d, uNear, uFar); }
    float coc(vec2 uv, float z){
      float c = abs(1.0/max(uFocus,0.01) - 1.0/max(z,0.01)) * uFocus * uAperture;
      float band = smoothstep(uTiltWidth, uTiltWidth + 0.32, abs(uv.y - uTiltCenter)) * uTilt;
      return clamp(max(c, band), 0.0, 1.0);
    }
    void main(){
      float z = viewZ(vUv);
      float c0 = coc(vUv, z);
      float scale = uRes.y / 1080.0;
      float R = c0 * uMaxBlur * scale;
      vec4 base = texture2D(tDiffuse, vUv);
      if (R < 0.6) { gl_FragColor = base; return; }
      vec3 acc = base.rgb; float wsum = 1.0;
      const float GA = 2.39996323;
      for (int i = 1; i < 40; i++) {
        float fi = float(i);
        float r = sqrt(fi / 40.0) * R;
        vec2 off = vec2(cos(fi * GA), sin(fi * GA)) * r / uRes;
        vec2 suv = vUv + off;
        float sz = viewZ(suv);
        float sc = coc(suv, sz) * uMaxBlur * scale;
        // a sample counts if its own blur reaches us, or it lies behind the focus of the centre pixel
        float w = smoothstep(r - 1.5, r, max(sc, sz > z ? R : 0.0));
        acc += texture2D(tDiffuse, suv).rgb * w; wsum += w;
      }
      gl_FragColor = vec4(acc / wsum, base.a);
    }`,
};

const GradeShader = {
  uniforms: {
    tDiffuse: { value: null }, uTime: { value: 0 }, uRes: { value: new THREE.Vector2(1, 1) },
    uVignette: { value: 0.28 }, uGrain: { value: 0.035 }, uLift: { value: new THREE.Vector3(0, 0, 0) },
    uGain: { value: new THREE.Vector3(1, 1, 1) }, uSat: { value: 1.0 }, uContrast: { value: 0.0 }, uSplit: { value: 0.0 }, uFade: { value: 0.0 }, uFadeColor: { value: new THREE.Color(0xf4efe6) },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse; uniform float uTime, uVignette, uGrain, uSat, uFade, uContrast, uSplit; uniform vec2 uRes; uniform vec3 uLift, uGain, uFadeColor;
    varying vec2 vUv;
    float hash(vec2 p){ p = fract(p * vec2(443.897, 441.423)); p += dot(p, p.yx + 19.19); return fract((p.x + p.y) * p.x); }
    void main(){
      vec3 c = texture2D(tDiffuse, vUv).rgb;
      float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
      c = mix(vec3(l), c, uSat);
      c = c * uGain + uLift * (1.0 - c);
      // gentle filmic S-curve and split toning: cool shade, warm light
      c = clamp(c, 0.0, 1.0);
      c = mix(c, c * c * (3.0 - 2.0 * c), uContrast);
      float ll = dot(c, vec3(0.2126, 0.7152, 0.0722));
      c += uSplit * (mix(vec3(-0.012, 0.0, 0.022), vec3(0.02, 0.006, -0.02), smoothstep(0.15, 0.75, ll)));
      vec2 q = vUv - 0.5; q.x *= uRes.x / uRes.y;
      c *= 1.0 - uVignette * smoothstep(0.35, 1.05, length(q));
      float g = hash(vUv * uRes + fract(uTime * 7.31) * 113.0) - 0.5;
      c += g * uGrain * (0.6 + 0.4 * (1.0 - l));
      c = mix(c, uFadeColor, uFade);
      gl_FragColor = vec4(c, 1.0);
    }`,
};

export class Post {
  constructor(renderer, scene, camera, { quality = 'high' } = {}) {
    this.renderer = renderer; this.scene = scene; this.camera = camera; this.quality = quality;
    const size = renderer.getDrawingBufferSize(new THREE.Vector2());
    const rt = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: quality === 'high' ? 4 : 0 });
    rt.depthTexture = new THREE.DepthTexture(size.x, size.y);
    rt.depthTexture.type = THREE.UnsignedIntType;
    this.composer = new EffectComposer(renderer, rt);
    this.renderPass = new RenderPass(scene, camera);
    this.composer.addPass(this.renderPass);
    // ambient occlusion grounds the miniature: reveals, corners, feet on the pavement
    if (quality !== 'low') {
      this.gtao = new GTAOPass(scene, camera, size.x, size.y);
      this.gtao.updateGtaoMaterial({ radius: 1.8, distanceExponent: 1.0, thickness: 2.5, scale: 1.5, samples: quality === 'high' ? 16 : 12, distanceFallOff: 1.0 });
      this.gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 16 });
      this.gtao.blendIntensity = 1.0;
      this.composer.addPass(this.gtao);
    }
    this.dof = new ShaderPass(DofShader);
    this.dof.needsSwap = true;
    this.composer.addPass(this.dof);
    this.bloom = new UnrealBloomPass(new THREE.Vector2(size.x / 2, size.y / 2), 0.35, 0.55, 0.92);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());
    this.grade = new ShaderPass(GradeShader);
    this.composer.addPass(this.grade);
    this.rt = rt;
  }

  setSize(w, h, dpr) {
    this.composer.setPixelRatio(dpr);
    this.composer.setSize(w, h);
    const W = Math.round(w * dpr), H = Math.round(h * dpr);
    this.dof.uniforms.uRes.value.set(W, H);
    this.grade.uniforms.uRes.value.set(W, H);
  }

  render(t) {
    const d = this.dof.uniforms;
    // with GTAO the colour buffers swap before the DOF pass, so sample GTAO's own depth to avoid a feedback loop
    d.tDepth.value = this.gtao ? this.gtao.depthTexture : (this.composer.readBuffer.depthTexture || this.rt.depthTexture);
    d.uNear.value = this.camera.near; d.uFar.value = this.camera.far;
    this.grade.uniforms.uTime.value = t;
    this.composer.render();
  }
}
