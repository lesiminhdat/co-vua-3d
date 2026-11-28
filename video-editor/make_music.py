"""
Tạo nhạc nền TỰ SÁNG TÁC bằng code (tổng hợp âm thanh từ sóng sin + nhiễu).
Không dùng bất kỳ đoạn nhạc/sample có sẵn nào => không bị Content ID của
TikTok / Facebook / YouTube nhận diện bản quyền.

Mỗi "seed" khác nhau cho ra giai điệu, tông, hợp âm rải khác nhau.

Dùng riêng:  python make_music.py energetic 40 out.wav [seed]
"""
import sys
import wave
import numpy as np

SR = 44100

STYLES = {
    # bpm, vòng hợp âm (độ cao MIDI của nốt gốc, loại hợp âm), beats/đoạn cắt
    "energetic": dict(bpm=124, prog=[(57, "m"), (53, "M"), (48, "M"), (55, "M")], pump=0.65),
    "chill":     dict(bpm=92,  prog=[(53, "M7"), (52, "m7"), (50, "m7"), (48, "M7")], pump=0.0),
    "luxury":    dict(bpm=100, prog=[(50, "m9"), (46, "M7"), (43, "m7"), (45, "7")], pump=0.25),
}

CHORDS = {
    "M": [0, 4, 7, 12], "m": [0, 3, 7, 12],
    "M7": [0, 4, 7, 11], "m7": [0, 3, 7, 10], "7": [0, 4, 7, 10], "m9": [0, 3, 7, 14],
}


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


class Mix:
    def __init__(self, seconds):
        n = int(seconds * SR) + SR
        self.L = np.zeros(n)
        self.R = np.zeros(n)

    def add(self, t, sig, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i >= len(self.L) or i < 0:
            return
        sig = sig[: len(self.L) - i] * gain
        self.L[i:i + len(sig)] += sig * (1 - pan) * 0.5 ** 0.5 * 1.41
        self.R[i:i + len(sig)] += sig * (1 + pan) * 0.5 ** 0.5 * 1.41


def tvec(dur):
    return np.arange(int(dur * SR)) / SR


def tone(freq, dur, harm=6, power=1.5, detune=0.0):
    t = tvec(dur)
    out = np.zeros_like(t)
    for k in range(1, harm + 1):
        out += np.sin(2 * np.pi * freq * k * t * (1 + detune)) / k ** power
    return out


def env_ad(n_or_t, attack, decay):
    t = n_or_t
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / decay)


def kick(rng):
    t = tvec(0.45)
    f = 45 + 115 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t / 0.28)
    s[:60] += rng.uniform(-0.4, 0.4, 60)  # click
    return np.tanh(1.8 * s)


def hat(rng, dur=0.06, decay=0.025):
    n = rng.uniform(-1, 1, int(dur * SR))
    n = np.diff(n, prepend=0)  # lọc thông cao đơn giản
    return n * np.exp(-tvec(dur) / decay) * 0.5


def clap(rng):
    dur = 0.25
    n = rng.uniform(-1, 1, int(dur * SR))
    n = np.convolve(np.diff(n, prepend=0), np.ones(4) / 4, mode="same")
    t = tvec(dur)
    e = np.exp(-t / 0.09)
    for off in (0.0, 0.011, 0.022):
        e += 0.6 * np.exp(-np.clip(t - off, 0, None) / 0.006) * (t >= off)
    return n * e * 0.6


def generate(style="energetic", seconds=40.0, out_path="music.wav", seed=1, offset=0.0):
    """Trả về bpm. Lưới phách bắt đầu tại `offset` giây."""
    cfg = STYLES[style]
    rng = np.random.default_rng(seed)
    bpm = cfg["bpm"]
    beat = 60.0 / bpm
    bar = 4 * beat
    transpose = int(rng.integers(-3, 3))
    prog = [(r + transpose, c) for r, c in cfg["prog"]]
    rot = int(rng.integers(0, len(prog)))
    prog = prog[rot:] + prog[:rot]

    mix = Mix(seconds + 2)
    n_bars = int((seconds - offset) / bar) + 2
    drop_bar = 4 if style == "energetic" else 2
    arp_patterns = [[0, 1, 2, 3, 2, 1, 0, 1], [0, 2, 1, 3, 0, 2, 3, 1], [3, 2, 1, 0, 1, 2, 3, 2], [0, 1, 3, 2, 0, 3, 1, 2]]
    arp = arp_patterns[int(rng.integers(0, len(arp_patterns)))]
    penta = [0, 2, 4, 7, 9, 12, 14, 16]
    motif = [int(x) for x in rng.integers(0, len(penta), 8)]
    motif_rhythm = [int(x) for x in rng.integers(0, 2, 8)]

    # Đường "pump" (sidechain) cho pad/bass
    total_n = len(mix.L)
    tt = np.arange(total_n) / SR
    pump = 1 - cfg["pump"] * np.exp(-((tt - offset) % beat) / 0.09) * (tt >= offset)

    pad_bus = Mix(seconds + 2)
    for b in range(n_bars):
        t0 = offset + b * bar
        if t0 > seconds:
            break
        root, ctype = prog[b % len(prog)]
        notes = [root + 12 + iv for iv in CHORDS[ctype]]
        full = b >= drop_bar
        build = b >= drop_bar - 2

        # PAD hợp âm
        t = tvec(bar + 0.3)
        pe = np.clip(t / 0.25, 0, 1) * np.clip((bar + 0.3 - t) / 0.3, 0, 1)
        for i, m in enumerate(notes):
            for dt in (-0.003, 0.003):
                pad_bus.add(t0, tone(mtof(m), bar + 0.3, harm=5, power=1.8, detune=dt) * pe,
                            0.05, pan=(-0.5 if dt < 0 else 0.5))

        # BASS
        if build:
            bf = mtof(root - 12)
            if style == "energetic":
                for k in range(8):
                    if k % 2 == 1 or b >= drop_bar:
                        tb = tvec(beat / 2)
                        mix_t = t0 + k * beat / 2
                        pad_bus.add(mix_t, tone(bf, beat / 2, harm=5, power=1.0) * env_ad(tb, 0.005, 0.16), 0.22)
            else:
                for k in (0, 2):
                    tb = tvec(beat * 1.9)
                    pad_bus.add(t0 + k * beat, tone(bf, beat * 1.9, harm=3, power=2.0) * env_ad(tb, 0.01, 0.6), 0.3)

        # TRỐNG
        for k in range(4):
            tk = t0 + k * beat
            if build or style != "energetic":
                if style == "energetic" or k in (0, 2) or (k == 3 and rng.random() < 0.3):
                    if not (style != "energetic" and b < 1):
                        mix.add(tk, kick(rng), 0.85 if style == "energetic" else 0.6)
            if (full or (style != "energetic" and b >= 1)) and k in (1, 3):
                mix.add(tk, clap(rng), 0.5 if style == "energetic" else 0.35)
            # hi-hat
            subdiv = 2 if style == "energetic" else 4
            for s in range(subdiv):
                th = tk + s * beat / subdiv
                if style == "chill" and s % 2 == 1:
                    th += beat / subdiv * 0.18  # swing
                if style == "energetic" and s == 0 and not full:
                    continue
                vel = 0.55 if (style == "energetic" and s == 1) else 0.3 + 0.15 * rng.random()
                mix.add(th, hat(rng), vel, pan=0.25)

        # HỢP ÂM RẢI (pluck)
        if b >= drop_bar or (style != "energetic" and b >= 1):
            steps = 16 if style == "energetic" else 8
            st = bar / steps
            for s in range(steps):
                m = notes[arp[s % 8] % len(notes)] + 12
                tp = tvec(st * 1.5)
                sig = tone(mtof(m), st * 1.5, harm=4, power=1.2) * env_ad(tp, 0.002, 0.09 if style == "energetic" else 0.18)
                mix.add(t0 + s * st, sig, 0.09, pan=(-0.4 if s % 2 else 0.4))

        # GIAI ĐIỆU chuông (chill/luxury) – nửa sau
        if style != "energetic" and b >= drop_bar:
            for s in range(8):
                if motif_rhythm[(s + b) % 8] == 0:
                    continue
                m = root + 24 + penta[motif[(s + b) % 8]] - (12 if style == "luxury" else 0)
                tb = tvec(1.2)
                f = mtof(m)
                bell = (np.sin(2 * np.pi * f * tb) + 0.3 * np.sin(2 * np.pi * f * 2.76 * tb) * np.exp(-tb / 0.15))
                mix.add(t0 + s * bar / 8, bell * env_ad(tb, 0.003, 0.45), 0.09, pan=0.2)

    # Riser + impact trước điểm "drop"
    t_drop = offset + drop_bar * bar
    if t_drop < seconds - 4:
        rd = bar if style == "energetic" else bar / 2
        tr = tvec(rd)
        noise = np.diff(rng.uniform(-1, 1, len(tr)), prepend=0)
        mix.add(t_drop - rd, noise * (tr / rd) ** 2.5, 0.35)
        ti = tvec(1.5)
        boom = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-ti / 0.1)) / SR) * np.exp(-ti / 0.6)
        crash = np.diff(rng.uniform(-1, 1, len(ti)), prepend=0) * np.exp(-ti / 0.5)
        mix.add(t_drop, boom * 0.7 + crash * 0.25, 0.8)

    L = mix.L + pad_bus.L * pump
    R = mix.R + pad_bus.R * pump

    n = int(seconds * SR)
    L, R = L[:n], R[:n]
    # fade in/out ngắn, nén mềm, chuẩn hoá
    fade = np.ones(n)
    fi = int(0.02 * SR)
    fo = int(2.5 * SR)
    fade[:fi] = np.linspace(0, 1, fi)
    fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
    L, R = np.tanh(1.3 * L) * fade, np.tanh(1.3 * R) * fade
    peak = max(np.abs(L).max(), np.abs(R).max(), 1e-6)
    L, R = L / peak * 0.89, R / peak * 0.89

    data = np.empty(2 * n, dtype=np.int16)
    data[0::2] = (L * 32767).astype(np.int16)
    data[1::2] = (R * 32767).astype(np.int16)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return bpm


if __name__ == "__main__":
    style = sys.argv[1] if len(sys.argv) > 1 else "energetic"
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 40
    out = sys.argv[3] if len(sys.argv) > 3 else f"music_{style}.wav"
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    print("BPM:", generate(style, secs, out, seed))
    print("Đã tạo:", out)
