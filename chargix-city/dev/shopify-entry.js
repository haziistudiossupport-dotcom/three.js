// Shopify entry: the theme section sets window.CX_ASSETS to its asset folder before this module runs.
import { start } from '../site/js/main.js';

const root = document.querySelector('[data-cx-city]');
if (root) start(root).catch((e) => { console.error(e); root.classList.add('is-failed'); });
