// Tạo thư mục www/ từ ../index.html: bỏ script Gemini chèn vào, tải thư viện về để chạy offline.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const src = path.resolve(root, '..', 'index.html');
const www = path.join(root, 'www');
const vendor = path.join(www, 'vendor');
fs.mkdirSync(path.join(vendor, 'webfonts'), { recursive: true });
fs.mkdirSync(path.join(vendor, 'fonts'), { recursive: true });

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';
async function get(url, binary = false) {
  const r = await fetch(url, { headers: { 'User-Agent': UA } });
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return binary ? Buffer.from(await r.arrayBuffer()) : r.text();
}
async function save(url, file, binary = false) {
  if (fs.existsSync(file)) return fs.readFileSync(file, binary ? undefined : 'utf8');
  const data = await get(url, binary);
  fs.writeFileSync(file, data);
  console.log('downloaded', path.relative(root, file));
  return data;
}

// 1. Thư viện JS
await save('https://cdn.tailwindcss.com/3.4.17', path.join(vendor, 'tailwind.js'));
const chessSrc = await save('https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js', path.join(vendor, 'chess.min.js'));
fs.writeFileSync(path.join(vendor, 'chess-src.js'), 'window.__CHESS_SRC=' + JSON.stringify(chessSrc) + ';\n');

// 2. Font Awesome (css + webfonts)
const FA = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0';
let faCss = await save(`${FA}/css/all.min.css`, path.join(vendor, 'fontawesome.css'));
for (const f of new Set([...faCss.matchAll(/\.\.\/webfonts\/([\w.-]+)/g)].map(m => m[1]))) {
  await save(`${FA}/webfonts/${f}`, path.join(vendor, 'webfonts', f), true);
}
fs.writeFileSync(path.join(vendor, 'fontawesome.css'), faCss.replaceAll('../webfonts/', 'webfonts/'));

// 3. Google Font Be Vietnam Pro
const fontCssFile = path.join(vendor, 'fonts.css');
if (!fs.existsSync(fontCssFile)) {
  let css = await get('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');
  let i = 0;
  for (const url of new Set([...css.matchAll(/url\((https:[^)]+)\)/g)].map(m => m[1]))) {
    const name = `bvp-${i++}.woff2`;
    await save(url, path.join(vendor, 'fonts', name), true);
    css = css.replaceAll(url, `fonts/${name}`);
  }
  fs.writeFileSync(fontCssFile, css);
}

// 4. HTML
let html = fs.readFileSync(src, 'utf8');
const start = html.indexOf('<meta charset="UTF-8">');
if (start < 0) throw new Error('Không tìm thấy <meta charset> trong index.html');
html = '<!DOCTYPE html>\n<html lang="vi"><head>\n    ' + html.slice(start);
const rep = (a, b) => { if (!html.includes(a)) throw new Error('Không tìm thấy: ' + a); html = html.replaceAll(a, b); };
rep('<meta name="viewport" content="width=device-width, initial-scale=1.0">',
    '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">');
rep('<script src="https://cdn.tailwindcss.com"></script>', '<script src="vendor/tailwind.js"></script>');
rep('<script src="https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js" crossorigin="anonymous"></script>',
    '<script src="vendor/chess.min.js"></script>\n    <script src="vendor/chess-src.js"></script>');
rep('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css', 'vendor/fontawesome.css');
rep('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&amp;display=swap', 'vendor/fonts.css');
// Worker chạy từ blob: không importScripts được file cục bộ -> nhúng mã chess.js vào trước.
rep("importScripts('https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js');", '');
rep('new Blob([WORKER_CODE]', 'new Blob([window.__CHESS_SRC, ";", WORKER_CODE]');
// Bản app: ẩn nút "Tải file HTML", chừa vùng tai thỏ / thanh điều hướng trên điện thoại.
rep('</head>', `<style>
      [onclick*="downloadStandaloneHTML"]{display:none!important}
      body{padding-top:max(env(safe-area-inset-top),0.5rem)!important;padding-bottom:max(env(safe-area-inset-bottom),0.5rem)!important}
      html,body{-webkit-tap-highlight-color:transparent;overscroll-behavior:none}
    </style>
</head>`);
// Dự phòng engine khi Web Worker không chạy (iOS) -> tránh treo bàn cờ.
fs.copyFileSync(path.join(root, 'scripts', 'engine-fallback.js'), path.join(vendor, 'engine-fallback.js'));
rep('</body>', '<script src="vendor/engine-fallback.js"></script>\n</body>');
// Web app (PWA): icon, manifest, service worker, nút/hướng dẫn cài lên màn hình chính.
for (const f of fs.readdirSync(path.join(root, 'assets', 'pwa'))) fs.copyFileSync(path.join(root, 'assets', 'pwa', f), path.join(www, f));
fs.copyFileSync(path.join(root, 'scripts', 'pwa-install.js'), path.join(vendor, 'pwa-install.js'));
fs.writeFileSync(path.join(www, 'manifest.webmanifest'), JSON.stringify({
  name: 'Cờ Vua 3D', short_name: 'Cờ Vua 3D', description: 'Cờ Vua 3D - Stockfridge AI & Đánh Giá Nước Đi',
  lang: 'vi', start_url: './', scope: './', display: 'standalone', orientation: 'any',
  background_color: '#171717', theme_color: '#171717',
  icons: [
    { src: 'icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
    { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
    { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' }
  ]
}, null, 2));
rep('<title>', `<link rel="manifest" href="manifest.webmanifest">
    <link rel="icon" type="image/png" href="favicon.png">
    <link rel="apple-touch-icon" href="apple-touch-icon.png">
    <meta name="theme-color" content="#171717">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Cờ Vua 3D">
    <title>`);
rep('</body>', '<script src="vendor/pwa-install.js"></script>\n</body>');
if (/https?:\/\/(cdn|fonts)\./.test(html)) console.warn('Cảnh báo: vẫn còn link CDN trong HTML');
fs.writeFileSync(path.join(www, 'index.html'), html);

// Service worker: lưu sẵn toàn bộ file để chạy offline; đổi phiên bản cache mỗi khi nội dung đổi.
const listFiles = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap(d =>
  d.isDirectory() ? listFiles(path.join(dir, d.name)) : [path.join(dir, d.name)]);
const files = listFiles(www).map(f => path.relative(www, f).split(path.sep).join('/')).filter(f => f !== 'sw.js').sort();
const hash = crypto.createHash('sha256');
for (const f of files) hash.update(f).update(fs.readFileSync(path.join(www, f)));
const cacheName = 'covua3d-' + hash.digest('hex').slice(0, 12);
fs.writeFileSync(path.join(www, 'sw.js'), `// Tự sinh bởi scripts/prepare.mjs
const CACHE = ${JSON.stringify(cacheName)};
const FILES = ${JSON.stringify(['./', ...files], null, 1)};
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(hit => hit || fetch(e.request).catch(() =>
    e.request.mode === 'navigate' ? caches.match('./') : Response.error())));
});
`);
console.log('www/index.html ready (' + files.length + ' files, cache ' + cacheName + ')');
