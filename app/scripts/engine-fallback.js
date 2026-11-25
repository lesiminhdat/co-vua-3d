// Dự phòng cho engine AI: nếu Web Worker không chạy được (ví dụ WKWebView trên iOS)
// hoặc không trả lời, chạy cùng đoạn mã engine ngay trên luồng chính thay vì treo game.
(function () {
  var WORKER_TIMEOUT_MS = 6000;
  var workerOk = null; // null = chưa biết, true = chạy tốt, false = hỏng -> luôn dùng dự phòng
  var local = null;

  function getLocalEngine() {
    if (local) return local;
    var pending = new Map();
    var fakeSelf = {
      onmessage: null,
      postMessage: function (msg) {
        var cb = pending.get(msg.id);
        if (cb) { pending.delete(msg.id); cb(msg.result); }
      }
    };
    // WORKER_CODE dùng biến toàn cục Chess (đã nạp sẵn ở trang chính).
    new Function('self', 'importScripts', WORKER_CODE)(fakeSelf, function () {});
    local = { self: fakeSelf, pending: pending };
    return local;
  }

  function runLocal(type, payload, id) {
    return new Promise(function (resolve) {
      var engine;
      try { engine = getLocalEngine(); } catch (e) { console.error('Engine fallback init failed', e); resolve(null); return; }
      engine.pending.set(id, resolve);
      // Nhường một nhịp cho giao diện cập nhật ("AI đang nghĩ...") trước khi tính.
      setTimeout(function () {
        try { engine.self.onmessage({ data: { id: id, type: type, payload: payload } }); }
        catch (e) { console.error('Engine fallback error', e); engine.pending.delete(id); resolve(null); }
      }, 30);
    });
  }

  window.runWorkerTask = function (type, payload) {
    var id = ++workerTaskId;
    if (workerOk === false) return runLocal(type, payload, id);

    return new Promise(function (resolve) {
      var done = false;
      function finish(r) { if (!done) { done = true; resolve(r); } }
      function fallback() {
        if (done) return;
        workerOk = false;
        workerCallbacks.delete(id);
        runLocal(type, payload, id).then(finish);
      }
      try {
        if (!engineWorker) initEngineWorker();
        if (!engineWorker) throw new Error('Worker unavailable');
        engineWorker.onerror = function (e) { console.warn('Worker error, switching to fallback', e); fallback(); };
        workerCallbacks.set(id, function (r) { workerOk = true; finish(r); });
        engineWorker.postMessage({ id: id, type: type, payload: payload });
      } catch (e) {
        console.warn('Worker fallback:', e);
        fallback();
        return;
      }
      if (workerOk !== true) setTimeout(function () { if (!done && workerOk !== true) fallback(); }, WORKER_TIMEOUT_MS);
    });
  };
})();
