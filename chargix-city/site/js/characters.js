// Rigged characters: clip blending driven by the scroll timeline (pure functions of time), two-bone arm IK,
// head look-at and a hand-held phone with a live screen.
import * as THREE from 'three';

const _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _v = new THREE.Vector3(), _v2 = new THREE.Vector3(), _v3 = new THREE.Vector3();
const _m = new THREE.Matrix4();

function worldQuat(o, out) { return o.getWorldQuaternion(out); }

// rotate bone so that (in world space) direction `from` turns to `to`, blended by w
function rotateBoneWorld(bone, from, to, w = 1) {
  const q = new THREE.Quaternion().setFromUnitVectors(from.clone().normalize(), to.clone().normalize());
  if (w < 1) q.slerp(new THREE.Quaternion(), 1 - w);
  const pw = new THREE.Quaternion(); bone.parent.getWorldQuaternion(pw);
  const bw = new THREE.Quaternion(); bone.getWorldQuaternion(bw);
  const nw = q.multiply(bw);
  bone.quaternion.copy(pw.invert().multiply(nw));
  bone.updateMatrixWorld(true);
}

export class Character {
  constructor(gltf, name) {
    this.name = name;
    this.root = new THREE.Group();
    this.root.name = 'char_' + name;
    this.model = gltf.scene;
    this.root.add(this.model);
    this.bones = {};
    this.model.traverse((o) => {
      if (o.isBone) this.bones[o.name.replace('mixamorig', '')] = o;
      if (o.isMesh) {
        o.castShadow = true; o.receiveShadow = true;
        o.frustumCulled = false;
        const m = o.material;
        if (m && m.name === 'M_eye') { m.roughness = 0.05; m.envMapIntensity = 1.5; }
        if (m && m.name === 'M_skin') { m.roughness = 0.55; }
        if (m && m.name === 'M_hair') { m.roughness = 0.45; m.envMapIntensity = 0.6; }
      }
    });
    this.mixer = new THREE.AnimationMixer(this.model);
    this.actions = {};
    for (const clip of gltf.animations) {
      const a = this.mixer.clipAction(clip);
      a.play(); a.weight = 0; a.enabled = true;
      this.actions[clip.name] = a;
    }
    this.ik = { left: null, right: null };
    this.look = null;
    this.props = {};
  }

  // pose = { x, z, heading, clips: { walk: {w, t}, idle: {w, t}, ... } }
  pose(p) {
    this.root.position.set(p.x, p.y ?? 0.15, p.z);
    this.root.rotation.set(0, p.heading ?? 0, 0);
    for (const [name, a] of Object.entries(this.actions)) {
      const c = p.clips[name];
      a.weight = c ? c.w : 0;
      if (c) a.time = ((c.t % a.getClip().duration) + a.getClip().duration) % a.getClip().duration;
    }
    // AnimationMixer only writes a bone when its sampled value changes, so a held pose would keep last
    // frame's IK result and accumulate. Restore the pre-IK pose first, then let the mixer overwrite it.
    if (!this._ikBones) this._ikBones = ['Neck', 'Head', 'LeftArm', 'LeftForeArm', 'LeftHand', 'RightArm', 'RightForeArm', 'RightHand']
      .map((n) => this.bones[n]).filter(Boolean).map((b) => ({ b, q: b.quaternion.clone() }));
    for (const s of this._ikBones) s.b.quaternion.copy(s.q);
    this.mixer.update(0);
    for (const s of this._ikBones) s.q.copy(s.b.quaternion);
    this.root.updateMatrixWorld(true);
    this.applyIK(p);
    // a held prop (the phone) turns its face toward a world point, so the screen faces the eyes whatever the wrist does
    if (p.faceProp && this.props[p.faceProp.name]) {
      const o = this.props[p.faceProp.name];
      o.parent.updateMatrixWorld(true);
      o.lookAt(p.faceProp.target);
      o.updateMatrixWorld(true);
    }
  }

  applyIK(p) {
    // head look-at (world target), clamped
    if (p.look && p.look.w > 0) {
      const head = this.bones.Head, neck = this.bones.Neck;
      for (const [bone, share] of [[neck, 0.4], [head, 0.6]]) {
        bone.getWorldPosition(_v);
        const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(this.root.quaternion);
        const want = _v2.copy(p.look.target).sub(_v).normalize();
        // limit yaw/pitch relative to body forward
        const ang = fwd.angleTo(want);
        const lim = THREE.MathUtils.degToRad(70);
        const dir = ang > lim ? fwd.clone().lerp(want, lim / ang).normalize() : want;
        rotateBoneWorld(bone, fwd.clone().applyAxisAngle(new THREE.Vector3(1, 0, 0).applyQuaternion(this.root.quaternion), 0), dir, p.look.w * share);
      }
    }
    for (const side of ['Left', 'Right']) {
      const t = p.hands && p.hands[side.toLowerCase()];
      if (t && t.w > 0) this.solveArm(side, t.pos, t.pole, t.w, t.handDir);
    }
  }

  // analytic two-bone IK in world space
  solveArm(side, target, pole, w, handDir) {
    const A = this.bones[side + 'Arm'], Bn = this.bones[side + 'ForeArm'], H = this.bones[side + 'Hand'];
    const a = A.getWorldPosition(new THREE.Vector3());
    const b = Bn.getWorldPosition(new THREE.Vector3());
    const c = H.getWorldPosition(new THREE.Vector3());
    const lab = a.distanceTo(b), lcb = b.distanceTo(c);
    const tgt = target.clone();
    const lat = THREE.MathUtils.clamp(a.distanceTo(tgt), 0.05, lab + lcb - 0.002);
    // current
    const ac = c.clone().sub(a), ab = b.clone().sub(a);
    // desired elbow position: in the plane of (a, target, pole)
    const at = tgt.clone().sub(a).normalize();
    const cosA = THREE.MathUtils.clamp((lab * lab + lat * lat - lcb * lcb) / (2 * lab * lat), -1, 1);
    const sinA = Math.sqrt(1 - cosA * cosA);
    const pv = pole.clone().sub(a);
    const perp = pv.sub(at.clone().multiplyScalar(pv.dot(at))).normalize();
    const elbow = a.clone().addScaledVector(at, cosA * lab).addScaledVector(perp, sinA * lab);
    // rotate upper arm: ab -> (elbow - a)
    rotateBoneWorld(A, ab, elbow.clone().sub(a), w);
    const b2 = Bn.getWorldPosition(new THREE.Vector3()), c2 = H.getWorldPosition(new THREE.Vector3());
    const want = a.clone().addScaledVector(at, lat);
    const tw = tgt.clone().lerp(want, 0); // exact
    rotateBoneWorld(Bn, c2.clone().sub(b2), tw.clone().sub(b2), w);
    if (handDir) {
      const m = this.bones[side + 'HandMiddle1'];
      if (m) {
        const hc = H.getWorldPosition(new THREE.Vector3()), mc = m.getWorldPosition(new THREE.Vector3());
        rotateBoneWorld(H, mc.sub(hc), handDir, w);
      }
    }
  }

  attach(name, obj, boneName, offset = new THREE.Vector3(), rot = new THREE.Euler()) {
    const bone = this.bones[boneName];
    obj.position.copy(offset); obj.rotation.copy(rot);
    bone.add(obj);
    this.props[name] = obj;
    return obj;
  }
}

// a modern phone with a CanvasTexture screen (UI is drawn by screens.js)
export function makePhone(screenTex) {
  const g = new THREE.Group();
  const W = 0.072, H = 0.152, D = 0.008;
  const body = new THREE.Mesh(new THREE.BoxGeometry(W, H, D), new THREE.MeshStandardMaterial({ color: 0x1b1c1f, roughness: 0.35, metalness: 0.7 }));
  body.castShadow = true;
  const scr = new THREE.Mesh(new THREE.PlaneGeometry(W - 0.006, H - 0.006),
    new THREE.MeshBasicMaterial({ map: screenTex, toneMapped: false }));
  scr.position.z = D / 2 + 0.0004;
  g.add(body, scr);
  g.userData.screen = scr;
  return g;
}
