// Turns site/index.html into the theme section (sections/cx-city.liquid) and a local test page for the built bundle.
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const html = fs.readFileSync(path.join(ROOT, 'site/index.html'), 'utf8');
const m = html.match(/<section class="cx-city"[\s\S]*?\n<\/section>/);
if (!m) throw new Error('city markup not found');
// the theme's own header carries navigation, so the city drops its local nav
const city = m[0].replace(/\s*<header class="cx-nav">[\s\S]*?<\/header>/, '');
if (/\{\{|\{%/.test(city)) throw new Error('markup contains Liquid delimiters');

const section = `{%- comment -%} CHARGIX city: a scroll-driven 3D street. Built from chargix-city/site by dev/make-theme.mjs; edit the source, not this file. {%- endcomment -%}
{%- assign cx_base = 'cx-city.glb' | asset_url | split: 'cx-city.glb' | first -%}
<link rel="modulepreload" href="{{ 'cx-city.js' | asset_url }}">
{{ 'cx-city.css' | asset_url | stylesheet_tag }}
<script>window.CX_ASSETS = {{ cx_base | json }};</script>
${city}
<script type="module" src="{{ 'cx-city.js' | asset_url }}"></script>

{% schema %}
{
  "name": "CHARGIX city",
  "settings": [],
  "presets": [{ "name": "CHARGIX city" }]
}
{% endschema %}
`;
const out = path.join(ROOT, 'dist/theme/sections');
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, 'cx-city.liquid'), section);

const test = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CHARGIX · City (built)</title>
<link rel="stylesheet" href="cx-city.css">
<style>html,body{margin:0;background:#0a0a0b}.fake-hdr{position:fixed;inset:0 0 auto;height:76px;z-index:60;background:linear-gradient(rgba(10,10,11,.86),rgba(10,10,11,0));color:#ece8e0;font:600 12px/76px system-ui;letter-spacing:.3em;padding-left:32px}</style>
<script>window.CX_ASSETS = './';</script>
</head><body><div class="fake-hdr">CHARGIX · THEME HEADER</div>
${city}
<section id="packages" style="height:60vh;color:#ece8e0;font:700 40px system-ui;padding:80px">Theme packages section</section>
<script type="module" src="cx-city.js"></script>
<script>new MutationObserver(() => { if (document.querySelector('.cx-city.is-ready') && !document.title.startsWith('done')) document.title = 'done ' + document.title; }).observe(document.body, { subtree: true, attributes: true, attributeFilter: ['class'] });</script>
</body></html>
`;
fs.writeFileSync(path.join(ROOT, 'dist/test.html'), test);
console.log('section', section.length, 'bytes');
