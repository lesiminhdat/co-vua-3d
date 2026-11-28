// Web app (PWA): đăng ký service worker để chạy offline và hiện nút / hướng dẫn cài lên màn hình chính.
// Chỉ chạy khi mở bằng trình duyệt qua https (không chạy trong bản Electron / Capacitor).
(function () {
  var isWeb = location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  var isNativeShell = !!window.Capacitor || /Electron/i.test(navigator.userAgent);
  if (!isWeb || isNativeShell) return;

  if ('serviceWorker' in navigator) {
    // Khi có phiên bản game mới, service worker mới tiếp quản -> tải lại trang một lần để dùng bản mới
    // (trừ khi đang giữa ván online thì để lần mở sau).
    var hadController = !!navigator.serviceWorker.controller;
    var reloaded = false;
    navigator.serviceWorker.addEventListener('controllerchange', function () {
      if (!hadController || reloaded) return;
      var midGame = typeof game !== 'undefined' && game.history().length > 0;
      if (midGame) return;
      reloaded = true;
      location.reload();
    });
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('sw.js').then(function (reg) { reg.update(); })
        .catch(function (e) { console.warn('SW register failed', e); });
    });
  }

  var standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  if (standalone) return;

  var ua = navigator.userAgent;
  var isIOS = /iPhone|iPad|iPod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var isIOSSafari = isIOS && !/CriOS|FxiOS|EdgiOS|OPiOS|Zalo|FBAN|FBAV|Instagram|Line\//i.test(ua);
  var dismissedKey = 'pwa-banner-dismissed';
  try { if (sessionStorage.getItem(dismissedKey)) return; } catch (e) {}

  var deferredPrompt = null;

  function el(tag, style, html) { var e = document.createElement(tag); if (style) e.style.cssText = style; if (html != null) e.innerHTML = html; return e; }

  function showBanner(contentHtml, actionLabel, onAction) {
    if (document.getElementById('pwa-banner')) return;
    var bar = el('div',
      'position:fixed;left:12px;right:12px;bottom:calc(12px + env(safe-area-inset-bottom));z-index:99999;' +
      'background:#1f2937;color:#f9fafb;border:1px solid #f59e0b55;border-radius:16px;padding:14px 14px 14px 16px;' +
      'box-shadow:0 10px 30px rgba(0,0,0,.45);font-family:"Be Vietnam Pro",system-ui,sans-serif;font-size:14px;line-height:1.45;' +
      'display:flex;gap:12px;align-items:center;max-width:520px;margin:0 auto');
    bar.id = 'pwa-banner';
    var icon = el('img', 'width:44px;height:44px;border-radius:10px;flex:none');
    icon.src = 'apple-touch-icon.png'; icon.alt = '';
    var text = el('div', 'flex:1;min-width:0', contentHtml);
    bar.appendChild(icon); bar.appendChild(text);
    if (actionLabel) {
      var btn = el('button', 'flex:none;background:#f59e0b;color:#111827;font-weight:800;border:0;border-radius:10px;padding:10px 14px;font-size:14px;cursor:pointer', actionLabel);
      btn.onclick = onAction; bar.appendChild(btn);
    }
    var close = el('button', 'flex:none;background:transparent;color:#9ca3af;border:0;font-size:22px;line-height:1;padding:4px 6px;cursor:pointer', '&times;');
    close.setAttribute('aria-label', 'Đóng');
    close.onclick = function () { bar.remove(); try { sessionStorage.setItem(dismissedKey, '1'); } catch (e) {} };
    bar.appendChild(close);
    document.body.appendChild(bar);
  }

  // Android / Chrome / Edge: nút cài đặt một chạm.
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredPrompt = e;
    showBanner('<b>Cài Cờ Vua 3D</b><br><span style="color:#d1d5db">Chơi như app, không cần mạng</span>', 'Cài đặt', function () {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () { deferredPrompt = null; var b = document.getElementById('pwa-banner'); if (b) b.remove(); });
    });
  });
  window.addEventListener('appinstalled', function () { var b = document.getElementById('pwa-banner'); if (b) b.remove(); });

  // iPhone / iPad: Apple không cho trang web tự cài -> hướng dẫn 2 bước.
  window.addEventListener('load', function () {
    if (!isIOS) return;
    var shareIcon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px"><path d="M12 3v12"/><path d="M7 8l5-5 5 5"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>';
    if (isIOSSafari) {
      showBanner('<b>Cài Cờ Vua 3D lên iPhone</b><br>Bấm ' + shareIcon + ' <b>Chia sẻ</b> ở thanh dưới &rarr; chọn <b>Thêm vào MH chính</b>');
    } else {
      showBanner('<b>Cài Cờ Vua 3D lên iPhone</b><br>Mở trang này bằng <b>Safari</b> rồi bấm ' + shareIcon + ' <b>Chia sẻ</b> &rarr; <b>Thêm vào MH chính</b>',
        'Copy link', function () {
          var url = location.href.split('#')[0];
          (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(
            function () { alert('Đã copy link. Mở Safari và dán link vào.'); },
            function () { prompt('Copy link này và mở bằng Safari:', url); });
        });
    }
  });
})();
