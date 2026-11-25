// Tạo thư mục www/ từ ../index.html: bỏ script Gemini chèn vào, tải thư viện về để chạy offline.
import fs from 'node:fs';
import path from 'node:path';
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
if (/https?:\/\/(cdn|fonts)\./.test(html)) console.warn('Cảnh báo: vẫn còn link CDN trong HTML');
fs.writeFileSync(path.join(www, 'index.html'), html);
console.log('www/index.html ready');
