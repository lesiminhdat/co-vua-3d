"""
Ghép nhiều video/ảnh sản phẩm thành 1 video quảng cáo ~40 giây:
  - cắt theo nhịp nhạc, chuyển cảnh đẹp, zoom chuyển động nhẹ, chỉnh màu
  - chữ tiêu đề / điểm nổi bật / kêu gọi mua hàng
  - nhạc nền tự sáng tác bằng code (không bản quyền)

Cách dùng:
    python edit_video.py <thư_mục_dự_án>

Thư mục dự án chứa các file .mp4/.mov/.jpg/.png và file project.json
(nếu chưa có, script tự tạo file mẫu). Kết quả: <thư_mục>/output/video_final.mp4
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_music  # noqa: E402

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
FPS = 30

FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}

STYLE = {
    "energetic": dict(xfade=0.25, cuts=[4, 4, 4, 4, 2, 2, 4, 2, 2, 4],
                      trans=["slideleft", "coverleft", "smoothup", "circleopen", "wipeleft",
                             "slideup", "smoothleft", "radial", "slideright", "squeezev"],
                      grade="eq=contrast=1.08:saturation=1.28:brightness=0.01,unsharp=5:5:0.6"),
    "chill": dict(xfade=0.5, cuts=[4],
                  trans=["fade", "smoothleft", "dissolve", "smoothup", "fade", "circleopen"],
                  grade="eq=contrast=1.03:saturation=1.08:brightness=0.03,colorbalance=rm=0.04:bm=-0.03"),
    "luxury": dict(xfade=0.5, cuts=[4],
                   trans=["fade", "fadeblack", "smoothup", "circlecrop", "fade", "smoothleft"],
                   grade="eq=contrast=1.12:saturation=0.92,vignette=PI/5"),
}

TEMPLATE = {
    "title": "TÊN SẢN PHẨM",
    "subtitle": "Câu slogan ngắn gọn",
    "features": ["Điểm nổi bật 1", "Điểm nổi bật 2", "Điểm nổi bật 3"],
    "cta": "MUA NGAY HÔM NAY",
    "price": "",
    "style": "energetic",
    "format": "9:16",
    "fit": "crop",
    "duration": 40,
    "accent": "#FF6FA5",
    "font": "Mali-Bold.ttf",
    "beauty": 2,
    "music": "",
    "music_seed": 0,
}

HERE = os.path.dirname(os.path.abspath(__file__))
# độ rộng chữ tương đối của từng phông (để tự co chữ vừa khung)
FONT_WIDTH = {"Mali-Bold.ttf": 1.12, "Pacifico-Regular.ttf": 1.0, "Itim-Regular.ttf": 0.95,
              "Sriracha-Regular.ttf": 0.95, "PatrickHand-Regular.ttf": 0.85, "arialbd.ttf": 1.0}


def find_font(name):
    for p in (name, os.path.join(HERE, "fonts", name), os.path.join(r"C:\Windows\Fonts", name)):
        if p and os.path.isfile(p):
            return p
    return r"C:\Windows\Fonts\arialbd.ttf"


def beauty_chain(level):
    """Làm đẹp da: mịn da, trắng hồng, sáng trong, glow mềm. level 0..3."""
    if not level:
        return None
    k = min(int(level), 3) / 2.0  # 0.5 / 1.0 / 1.5
    lift = 0.06 * k
    return (f"smartblur=lr={2.5 + 1.5 * k:.1f}:ls={min(0.45 * k + 0.1, 1.0):.2f}:lt=6,"
            f"eq=saturation=1.1:contrast=0.98,format=rgb24,"
            f"curves=master='0/{0.02 * k:.3f} 0.35/{0.35 + lift * 2:.3f} 0.7/{0.7 + lift * 2.3:.3f} 1/1',"
            f"selectivecolor=correction_method=relative:reds='{-0.04 * k:.3f} {0.03 * k:.3f} {-0.22 * k:.3f} {-0.18 * k:.3f}'"
            f":yellows='0 0 {-0.3 * k:.3f} {-0.12 * k:.3f}',"
            f"colorbalance=rm={0.02 * k:.3f}:bm={0.01 * k:.3f}:rh={0.025 * k:.3f}:bh={0.015 * k:.3f},"
            f"format=gbrp,split[bg1][bg2];[bg2]gblur=sigma=14[bgb];"
            f"[bg1][bgb]blend=all_mode=screen:all_opacity={0.13 * k:.3f},format=yuv420p,unsharp=3:3:0.35")


def find_tool(name):
    p = shutil.which(name)
    if p:
        return p
    base = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    hits = glob.glob(os.path.join(base, "*FFmpeg*", "*", "bin", name + ".exe"))
    if hits:
        return hits[0]
    sys.exit(f"Không tìm thấy {name}. Cài bằng: winget install Gyan.FFmpeg")


FFMPEG = find_tool("ffmpeg")
FFPROBE = find_tool("ffprobe")


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-3000:])
        sys.exit("Lỗi ffmpeg (xem ở trên).")
    return r


def probe_duration(path):
    r = run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "json", path])
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except (KeyError, ValueError):
        return 0.0


def scan_quality(path, rate=10):
    """Trả về mảng True/False theo từng 1/rate giây: khung hình có 'tốt' không
    (loại khung bị tay che ống kính, nhòe, tối/đơn sắc)."""
    import numpy as np
    w, h = 48, 64
    r = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-vf", f"fps={rate},scale={w}:{h},format=gray",
                        "-f", "rawvideo", "-"], capture_output=True)
    buf = np.frombuffer(r.stdout, dtype=np.uint8)
    n = len(buf) // (w * h)
    if n == 0:
        return None, rate
    f = buf[: n * w * h].reshape(n, h, w).astype(float)
    edge = np.abs(np.diff(f, axis=1)).mean(axis=(1, 2)) + np.abs(np.diff(f, axis=2)).mean(axis=(1, 2))
    std = f.std(axis=(1, 2))
    good = (edge > 0.45 * np.median(edge)) & (std > 0.45 * np.median(std))
    # nới vùng xấu thêm 0.3s mỗi phía (lúc tay đang tiến lại gần)
    pad = int(0.3 * rate)
    bad = ~good
    grown = bad.copy()
    for k in range(1, pad + 1):
        grown[k:] |= bad[:-k]
        grown[:-k] |= bad[k:]
    return ~grown, rate


def load_config(folder):
    path = os.path.join(folder, "project.json")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(TEMPLATE, f, ensure_ascii=False, indent=2)
        print(f"Đã tạo file mẫu {path} – sửa nội dung chữ rồi chạy lại để có video đúng ý.")
    with open(path, encoding="utf-8-sig") as f:
        cfg = {**TEMPLATE, **json.load(f)}
    return cfg


def collect_media(folder):
    items = []
    for p in sorted(os.listdir(folder)):
        ext = os.path.splitext(p)[1].lower()
        full = os.path.join(folder, p)
        if ext in VIDEO_EXT:
            d = probe_duration(full)
            if d > 0.3:
                good, rate = scan_quality(full)
                if good is not None:
                    print(f"  {p}: {100 * (1 - good.mean()):.0f}% khung hình bị che/nhòe -> bỏ qua")
                items.append(dict(path=full, name=p, image=False, dur=d, good=good, rate=rate))
        elif ext in IMAGE_EXT:
            items.append(dict(path=full, name=p, image=True, dur=999))
    return items


def plan_segments(media, cfg, beat):
    st = STYLE[cfg["style"]]
    T = st["xfade"]
    total = float(cfg["duration"])
    min_last = 3.5
    lens = []
    i = 0
    while True:
        L = st["cuts"][i % len(st["cuts"])] * beat
        if sum(lens) + L + min_last > total:
            break
        lens.append(L)
        i += 1
    last = total - sum(lens)  # đoạn cuối (CTA) dài hơn
    n = len(lens) + 1

    # thứ tự clip: luân phiên; đoạn cuối dùng file tên chứa "end"/"cta" nếu có
    end_clip = next((m for m in media if any(k in m["name"].lower() for k in ("end", "cta"))), None)
    pool = [m for m in media if m is not end_clip] or media
    order = [pool[k % len(pool)] for k in range(n - 1)] + [end_clip or pool[0]]

    # mỗi clip được dùng bao nhiêu lần -> chia đều thời lượng clip
    uses = {}
    for m in order:
        uses[m["path"]] = uses.get(m["path"], 0) + 1
    seen = {}
    segs = []
    for k, m in enumerate(order):
        d_out = (lens[k] + T) if k < n - 1 else last
        j = seen.get(m["path"], 0)
        seen[m["path"]] = j + 1
        cnt = uses[m["path"]]
        if m["image"]:
            segs.append(dict(media=m, start=0, src_dur=d_out, out=d_out, speed=1.0))
            continue
        D = m["dur"]
        # bỏ đầu clip (lúc chỉnh máy) và cuối clip (lúc với tay tắt quay)
        head = min(0.5, D * 0.05)
        tail = min(1.2, D * 0.08)
        margin = head
        usable = D - head - tail
        good = m.get("good")
        cands = []
        if good is not None:
            rate = m["rate"]
            need = int(round(d_out * rate))
            s0, s1 = int(head * rate), int((D - tail - d_out) * rate)
            cands = [s for s in range(s0, s1 + 1) if s + need <= len(good) and good[s:s + need].all()]
        if cands:
            start = cands[min(len(cands) - 1, int(len(cands) * (j + 0.5) / cnt))] / m["rate"]
            segs.append(dict(media=m, start=start, src_dur=d_out, out=d_out, speed=1.0))
        elif usable >= d_out:
            span = usable - d_out
            start = head + span * ((j + 0.5) / cnt)
            segs.append(dict(media=m, start=start, src_dur=d_out, out=d_out, speed=1.0))
        else:
            # clip quá ngắn -> slow motion cho đủ thời lượng
            segs.append(dict(media=m, start=margin, src_dur=usable, out=d_out, speed=d_out / usable))
    return segs, lens, T


def render_segment(seg, k, cfg, W, H, tmp):
    st = STYLE[cfg["style"]]
    m = seg["media"]
    out = os.path.join(tmp, f"seg_{k:02d}.mp4")
    frames = int(round(seg["out"] * FPS))
    W2, H2 = W * 2, H * 2  # phóng to trước khi zoompan để chuyển động mượt

    if m["image"]:
        inp = ["-loop", "1", "-framerate", str(FPS), "-t", f"{seg['out']:.3f}", "-i", m["path"]]
        pre = ""
    else:
        inp = ["-ss", f"{seg['start']:.3f}", "-t", f"{seg['src_dur']:.3f}", "-i", m["path"]]
        pre = f"setpts={seg['speed']:.4f}*PTS," if seg["speed"] > 1.001 else "setpts=PTS-STARTPTS,"
    pre += f"fps={FPS},"

    if cfg["fit"] == "blur":
        base = (f"[0:v]{pre}split[a][b];"
                f"[a]scale={W2}:{H2}:force_original_aspect_ratio=increase,crop={W2}:{H2},boxblur=30:3,eq=brightness=-0.08[bg];"
                f"[b]scale={W2}:{H2}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2")
    else:
        base = f"[0:v]{pre}scale={W2}:{H2}:force_original_aspect_ratio=increase,crop={W2}:{H2}"

    # luân phiên: zoom vào / zoom ra / lia ngang
    mode = k % 3
    N = max(frames, 1)
    if mode == 0:
        z, x, y = f"1+0.10*on/{N}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mode == 1:
        z, x, y = f"1.10-0.10*on/{N}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:
        z, x, y = "1.08", f"(iw-iw/zoom)*on/{N}", "ih/2-(ih/zoom/2)"
    zp = f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS}"

    look = beauty_chain(cfg.get("beauty", 0)) or st["grade"]
    vf = f"{base},{zp},{look},setsar=1,format=yuv420p[v]"
    run([FFMPEG, "-y", "-hide_banner", *inp, "-filter_complex", vf, "-map", "[v]",
         "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", out])
    return out


def hex_color(c):
    return "0x" + c.lstrip("#")


FONT_SCALE = 1.0


def char_w(text, fontsize):
    return fontsize * (0.70 if text.upper() == text else 0.56) * FONT_SCALE


def fit_text(text, fontsize, W, min_ratio=0.82):
    """Thu nhỏ chữ (tối đa còn 72%) cho vừa 1 dòng; nếu vẫn dài thì xuống dòng."""
    import math
    text = text.replace("•", "–")  # nhiều phông dễ thương không có dấu chấm tròn
    maxw = W * 0.88
    size = fontsize
    while len(text) * char_w(text, size) > maxw and size > fontsize * min_ratio:
        size -= 1
    if len(text) * char_w(text, size) <= maxw:
        return text, size
    # vẫn dài: chia đều thành nhiều dòng ở cỡ chữ ~90%
    size = int(fontsize * 0.9)
    per_line = max(8, int(maxw / char_w(text, size)))
    n_lines = math.ceil(len(text) / per_line)
    lines = textwrap.wrap(text, math.ceil(len(text) / n_lines) + 3)
    return "\n".join(lines) or text, size


def text_layers(cfg, W, H, lens, T, total, tmp):
    """Trả về chuỗi filter drawtext nối nhau."""
    global FONT_SCALE
    font = find_font(cfg.get("font") or "arialbd.ttf")
    FONT_SCALE = FONT_WIDTH.get(os.path.basename(font), 1.0)
    shutil.copy(font, os.path.join(tmp, "font.ttf"))
    accent = hex_color(cfg["accent"])
    s = W / 1080  # tỉ lệ cỡ chữ
    layers = []
    idx = [0]

    def add(text, t0, t1, y, size, color="white", box=None, border=6, bcolor="black@0.85", min_ratio=0.82):
        if not text:
            return
        wrapped, size = fit_text(text, size, W, min_ratio)
        fade = 0.25
        alpha = (f"if(lt(t,{t0}),0,if(lt(t,{t0 + fade}),(t-{t0})/{fade},"
                 f"if(lt(t,{t1 - fade}),1,if(lt(t,{t1}),({t1}-t)/{fade},0))))")
        # mỗi dòng vẽ riêng để khoảng cách dòng đều, không phụ thuộc phông
        for li, line in enumerate(wrapped.split("\n")):
            fn = f"t{idx[0]}.txt"
            idx[0] += 1
            with open(os.path.join(tmp, fn), "w", encoding="utf-8") as f:
                f.write(line)
            ly = int(y) + int(li * (size * 1.3 + (44 * s if box else 0)))
            # trượt lên 40px khi xuất hiện
            yexpr = f"{ly}+40*max(0,1-(t-{t0})/{fade})"
            opts = ["fontfile=font.ttf", f"textfile={fn}", "expansion=none", f"fontsize={int(size)}",
                    f"fontcolor={color}", "x=(w-text_w)/2", f"y='{yexpr}'", f"alpha='{alpha}'",
                    f"enable='between(t,{t0},{t1})'"]
            if box:
                opts += ["box=1", f"boxcolor={box}", f"boxborderw={int(22 * s)}"]
            else:
                opts += [f"borderw={border}", f"bordercolor={bcolor}", "shadowx=3", "shadowy=4",
                         "shadowcolor=black@0.35"]
            layers.append("drawtext=" + ":".join(opts))

    # Tiêu đề + slogan
    add(cfg["title"], 0.3, 3.6, f"{int(H * 0.16)}", 92 * s, border=int(9 * s), bcolor=accent, min_ratio=0.62)
    add(cfg["subtitle"], 0.7, 3.6, f"{int(H * 0.16 + 230 * s)}", 50 * s, box=f"{accent}@0.92")

    # Điểm nổi bật: chia đều phần giữa
    feats = [f for f in cfg.get("features", []) if f]
    cta_start = sum(lens) + T
    if feats:
        a, b = 4.2, cta_start - 0.6
        slot = (b - a) / len(feats)
        for i, ftxt in enumerate(feats):
            t0 = a + i * slot
            add(ftxt, round(t0, 2), round(t0 + slot - 0.3, 2), f"{int(H * 0.70)}", 60 * s, color=accent, box="white@0.9")

    # Kêu gọi mua hàng
    add(cfg.get("price", ""), round(cta_start, 2), total - 0.2, f"{int(H * 0.60)}", 80 * s, border=int(8 * s), bcolor=accent)
    add(cfg["cta"], round(cta_start + 0.3, 2), total - 0.2, f"{int(H * 0.72)}", 70 * s, box=f"{accent}@0.95")
    return layers


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    folder = os.path.abspath(sys.argv[1])
    cfg = load_config(folder)
    if cfg["style"] not in STYLE:
        sys.exit(f"style phải là một trong: {', '.join(STYLE)}")
    W, H = FORMATS.get(cfg["format"], FORMATS["9:16"])
    total = float(cfg["duration"])

    media = collect_media(folder)
    if not media:
        sys.exit("Không có video/ảnh nào trong thư mục.")
    print(f"Tìm thấy {len(media)} file: " + ", ".join(m["name"] for m in media))

    out_dir = os.path.join(folder, "output")
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="vedit_")

    # 1) Nhạc
    T = STYLE[cfg["style"]]["xfade"]
    seed = int(cfg.get("music_seed") or 0) or int(hashlib.md5(cfg["title"].encode()).hexdigest()[:6], 16)
    music_path = cfg.get("music")
    if music_path:
        if not os.path.isabs(music_path):
            music_path = os.path.join(folder, music_path)
        beat = 60 / make_music.STYLES[cfg["style"]]["bpm"]
        print("Dùng nhạc của bạn:", music_path)
    else:
        music_path = os.path.join(out_dir, "nhac_nen.wav")
        # lưới phách lệch T giây để mỗi lần chuyển cảnh kết thúc đúng phách
        bpm = make_music.generate(cfg["style"], total, music_path, seed=seed, offset=T)
        beat = 60 / bpm
        print(f"Đã tạo nhạc nền tự sáng tác ({cfg['style']}, {bpm} BPM, seed {seed})")

    # 2) Lên kế hoạch cắt + render từng đoạn
    segs, lens, T = plan_segments(media, cfg, beat)
    print(f"Chia thành {len(segs)} cảnh, đang render...")
    files = []
    for k, sg in enumerate(segs):
        files.append(render_segment(sg, k, cfg, W, H, tmp))
        print(f"  cảnh {k + 1}/{len(segs)}  ({sg['media']['name']}, {sg['out']:.2f}s)")

    # 3) Ghép + chuyển cảnh + chữ + nhạc
    trans = STYLE[cfg["style"]]["trans"]
    drop_k = 4 if cfg["style"] == "energetic" else None
    parts = []
    prev = "0:v"
    offset = 0.0
    for k in range(1, len(files)):
        offset += lens[k - 1]
        tname = "fadewhite" if k == drop_k else trans[(k - 1) % len(trans)]
        lab = f"x{k}"
        parts.append(f"[{prev}][{k}:v]xfade=transition={tname}:duration={T}:offset={offset:.3f}[{lab}]")
        prev = lab
    texts = text_layers(cfg, W, H, lens, T, total, tmp)
    vchain = f"[{prev}]" + ",".join(texts + [f"fade=t=out:st={total - 0.6}:d=0.6", "format=yuv420p"]) + "[vout]"
    parts.append(vchain)
    ai = len(files)
    parts.append(f"[{ai}:a]atrim=0:{total},asetpts=PTS-STARTPTS,afade=t=in:d=0.05,"
                 f"afade=t=out:st={total - 2.5}:d=2.5,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
    graph = ";\n".join(parts)
    with open(os.path.join(tmp, "graph.txt"), "w", encoding="utf-8") as f:
        f.write(graph)

    out = os.path.join(out_dir, "video_final.mp4")
    cmd = [FFMPEG, "-y", "-hide_banner"]
    for p in files:
        cmd += ["-i", os.path.basename(p)]
    cmd += ["-i", os.path.abspath(music_path), "-/filter_complex", "graph.txt",
            "-map", "[vout]", "-map", "[aout]", "-t", f"{total}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
    print("Đang ghép video cuối...")
    run(cmd, cwd=tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nXONG! Video: {out}  ({probe_duration(out):.1f}s)")


if __name__ == "__main__":
    main()
