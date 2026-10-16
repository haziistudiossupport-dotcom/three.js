// Builds dist/: one minified JS bundle, the stylesheet with flat asset URLs, meshopt-compressed GLBs and the rest of the assets.
import { build } from 'esbuild';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const DIST = path.join(ROOT, 'dist');
// three.js lives in ./three (a link to the repo root) or, inside the three.js repo, one level up
const THREE_DIR = fs.existsSync(path.join(ROOT, 'three/build')) ? path.join(ROOT, 'three') : path.join(ROOT, '..');
const A = path.join(ROOT, 'site/assets');
fs.mkdirSync(DIST, { recursive: true });

const three = {
  name: 'three',
  setup(b) {
    b.onResolve({ filter: /^three(\/.*)?$/ }, (args) => {
      if (args.path === 'three') return { path: path.join(THREE_DIR, 'build/three.module.js') };
      return { path: path.join(THREE_DIR, 'examples/jsm', args.path.replace(/^three\/addons\//, '')) };
    });
  },
};
await build({
  entryPoints: [path.join(ROOT, 'dev/shopify-entry.js')], bundle: true, format: 'esm', minify: true, target: 'es2020',
  outfile: path.join(DIST, 'cx-city.js'), plugins: [three], legalComments: 'none', logLevel: 'warning',
});

const css = fs.readFileSync(path.join(ROOT, 'site/css/city.css'), 'utf8').replace(/url\("\.\.\/assets\//g, 'url("');
fs.writeFileSync(path.join(DIST, 'cx-city.css'), css);

const G = path.join(ROOT, 'node_modules/.bin/gltf-transform');
for (const f of fs.readdirSync(A)) {
  const src = path.join(A, f), out = path.join(DIST, f);
  if (f.endsWith('.glb')) {
    if (process.env.SKIP_GLB && fs.existsSync(out)) continue;
    execFileSync(G, ['meshopt', src, out, '--level', 'medium'], { stdio: 'ignore' });
  } else fs.copyFileSync(src, out);
}
for (const f of fs.readdirSync(DIST).sort()) console.log(f.padEnd(28), (fs.statSync(path.join(DIST, f)).size / 1024).toFixed(0).padStart(7), 'KB');
