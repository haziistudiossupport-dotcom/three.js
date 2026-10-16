// Street trees: three branching variants (cx-trees.glb) instanced at the pits listed in the city meta.
// Foliage is alpha-cut leaf cards with canopy-shaped normals, light that glows through the leaves when
// you look toward the sun, and a slow sway driven by story time so scrubbing stays deterministic.
import * as THREE from 'three';
import { B } from './world.js';

export class Trees {
  constructor(gltf, meta, mats, { quality = 'high' } = {}) {
    this.group = new THREE.Group();
    this.group.name = 'trees';
    this.uniforms = {
      uTime: { value: 0 },
      uSunView: { value: new THREE.Vector3(0, 1, 0) },
      uSunCol: { value: new THREE.Color(1, 1, 1) },
    };
    const leafMap = mats.texture('leaves-a', true, 1);
    leafMap.wrapS = leafMap.wrapT = THREE.ClampToEdgeWrapping;
    const leaves = new THREE.MeshStandardMaterial({
      map: leafMap, alphaTest: 0.42, side: THREE.DoubleSide, roughness: 0.72, metalness: 0,
      color: new THREE.Color(0.93, 0.97, 0.9), alphaToCoverage: quality === 'high',
    });
    leaves.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, this.uniforms);
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nuniform float uTime;')
        .replace('#include <begin_vertex>', `#include <begin_vertex>
          // sway grows with height above the fork; phase varies across the canopy
          float hgt = max(0.0, transformed.y - 2.6);
          vec3 ip = vec3(0.0);
          #ifdef USE_INSTANCING
            ip = instanceMatrix[3].xyz;
          #endif
          float ph = dot(transformed + ip, vec3(0.7, 0.3, 0.9));
          transformed.x += sin(uTime * 1.1 + ph) * 0.018 * hgt;
          transformed.z += cos(uTime * 0.9 + ph * 1.3) * 0.014 * hgt;`);
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform vec3 uSunView; uniform vec3 uSunCol;')
        // keep the canopy normal on both faces of a card so the crown shades as one soft volume
        .replace('normal *= faceDirection;', '')
        .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
          vec3 vdir = normalize(vViewPosition);
          float through = pow(max(dot(vdir, uSunView), 0.0), 3.0);
          totalEmissiveRadiance += diffuseColor.rgb * uSunCol * through * 0.45;`);
    };
    leaves.customProgramCacheKey = () => 'cxLeaves';

    const bark = new THREE.MeshStandardMaterial({
      map: mats.texture('bark-a', true, 1), normalMap: mats.texture('bark-n', false, 1), roughness: 0.92, color: 0xd8d2c8,
    });

    const byVar = [[], [], []];
    for (const t of meta.trees || []) byVar[t[3]].push(t);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
    const tint = new THREE.Color();
    this.meshes = [];
    byVar.forEach((list, v) => {
      if (!list.length) return;
      for (const part of ['bark', 'leaves']) {
        const src = gltf.scene.getObjectByName(`tree${v}_${part}`);
        if (!src) continue;
        const mesh = new THREE.InstancedMesh(src.geometry, part === 'bark' ? bark : leaves, list.length);
        mesh.name = `trees${v}_${part}`;
        list.forEach((t, i) => {
          q.setFromAxisAngle(up, t[4]); s.setScalar(t[5]);
          m.compose(B(t[0], t[1], t[2]), q, s);
          mesh.setMatrixAt(i, m);
          if (part === 'leaves') {
            const k = ((t[0] * 12.9898 + t[1] * 78.233) % 1 + 1) % 1;
            tint.setRGB(0.92 + 0.12 * k, 0.96 + 0.06 * (1 - k), 0.88 + 0.1 * k);
            mesh.setColorAt(i, tint);
          }
        });
        mesh.castShadow = true; mesh.receiveShadow = true;
        mesh.computeBoundingSphere();
        this.group.add(mesh);
        this.meshes.push(mesh);
      }
    });
  }

  update(time, world, camera) {
    this.uniforms.uTime.value = time;
    if (world.sunDir) this.uniforms.uSunView.value.copy(world.sunDir).transformDirection(camera.matrixWorldInverse).negate();
    this.uniforms.uSunCol.value.copy(world.sun.color).multiplyScalar(world.sun.intensity * 0.35);
  }
}
