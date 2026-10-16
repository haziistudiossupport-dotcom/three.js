# CHARGIX city

A scroll-driven 3D street for the CHARGIX Shopify theme: two small businesses (Miga cookies, NORTE clothing) find CHARGIX, pick a package and open online, from morning to sunrise.

- `blender/` builds the city, the shop fit-outs and the two characters (Blender + MPFB), exported as GLB.
- `site/` is the three.js experience: `js/story.js` holds the whole film as pure functions of scroll time T (0–100).
- `dev/build.mjs` bundles the code with esbuild and compresses the GLBs with meshopt into `dist/`.
- `dev/make-theme.mjs` turns `site/index.html` into the theme section `dist/theme/sections/cx-city.liquid`.

```
npm install
npm run build
```

Open `site/index.html` (or `dist/test.html`) from a local web server at the repo root. Dev URL params: `T=<0..100>` to freeze the film at a moment, `noui` to hide the copy.
