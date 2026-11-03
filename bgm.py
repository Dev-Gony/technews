"""Shorts 배경음을 코드로 만든다.

외부 음원을 쓰지 않으므로 저작권 신고(Content ID) 걱정이 없다.
잔잔한 로파이 느낌: 7화음 패드 + 베이스 + 부드러운 킥 + 작은 하이햇.
같은 날짜(seed)는 항상 같은 곡, 날짜가 바뀌면 진행과 템포가 바뀐다.
"""

import zlib
import wave
import random

import numpy as np


SAMPLE_RATE = 44100

# MIDI 음 번호. 각 진행은 4개 화음(한 화음 = 한 마디)
PROGRESSIONS = [
    [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 65]],  # Am7 Fmaj7 Cmaj7 G7
    [[50, 53, 57, 60], [55, 59, 62, 65], [48, 52, 55, 59], [57, 60, 64, 67]],  # Dm7 G7 Cmaj7 Am7
    [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]],  # Fmaj7 Em7 Dm7 Cmaj7
    [[45, 48, 52, 55], [50, 53, 57, 60], [43, 47, 50, 53], [48, 52, 55, 59]],  # Am7 Dm7 G7 Cmaj7
]


def midi_to_hz(note):
    return 440.0 * 2 ** ((note - 69) / 12)


def envelope(length, attack, release):
    env = np.ones(length)
    attack = min(attack, length // 2)
    release = min(release, length // 2)

    if attack:
        env[:attack] = np.linspace(0, 1, attack)

    if release:
        env[-release:] = np.linspace(1, 0, release)

    return env


def pad_chord(notes, length, rng):
    t = np.arange(length) / SAMPLE_RATE
    out = np.zeros(length)

    for note in notes:
        freq = midi_to_hz(note)

        # 살짝 어긋난 두 음을 겹쳐 따뜻한 코러스 느낌을 낸다.
        for detune in (-0.12, 0.12):
            f = freq * 2 ** (detune / 12)
            phase = rng.uniform(0, 2 * np.pi)
            out += np.sin(2 * np.pi * f * t + phase) + 0.25 * np.sin(4 * np.pi * f * t + phase)

    # 느린 트레몰로
    out *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.5 * t)

    return out * envelope(length, int(0.25 * SAMPLE_RATE), int(0.35 * SAMPLE_RATE)) / (len(notes) * 2)


def bass_note(note, length):
    t = np.arange(length) / SAMPLE_RATE
    freq = midi_to_hz(note - 12)
    decay = np.exp(-t * 3.0)

    return np.sin(2 * np.pi * freq * t) * decay * envelope(length, 200, 2000)


def kick(length):
    t = np.arange(length) / SAMPLE_RATE
    # 120Hz → 45Hz로 떨어지는 사인파
    freq = 45 + 75 * np.exp(-t * 30)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE

    return np.sin(phase) * np.exp(-t * 12)


def hihat(length, rng):
    noise = rng.normal(0, 1, length)
    # 고역만 남기도록 차분(간단한 하이패스)
    high = np.diff(noise, prepend=0)

    return high * np.exp(-np.arange(length) / SAMPLE_RATE * 60)


def generate_bgm(duration, seed):
    """duration(초) 길이의 배경음을 float 배열(-1~1)로 만든다."""
    rng = np.random.default_rng(zlib.crc32(str(seed).encode("utf-8")))
    picker = random.Random(seed)

    progression = picker.choice(PROGRESSIONS)
    bpm = picker.choice([80, 84, 88, 92])
    beat = int(SAMPLE_RATE * 60 / bpm)
    bar = beat * 4
    total = int(duration * SAMPLE_RATE) + bar

    pad = np.zeros(total)
    bass = np.zeros(total)
    drums = np.zeros(total)

    kick_sound = kick(int(0.4 * SAMPLE_RATE))
    hat_sound = hihat(int(0.08 * SAMPLE_RATE), rng)

    for bar_index, start in enumerate(range(0, total, bar)):
        chord = progression[bar_index % len(progression)]
        length = min(bar + int(0.3 * SAMPLE_RATE), total - start)

        pad[start:start + length] += pad_chord(chord, length, rng)[:length]

        for step in range(4):
            beat_start = start + step * beat

            if beat_start >= total:
                break

            if step in (0, 2):
                n = min(beat * 2, total - beat_start)
                bass[beat_start:beat_start + n] += bass_note(chord[0], n)[:n]

                n = min(len(kick_sound), total - beat_start)
                drums[beat_start:beat_start + n] += kick_sound[:n]

            hat_start = beat_start + beat // 2
            n = min(len(hat_sound), max(total - hat_start, 0))
            drums[hat_start:hat_start + n] += hat_sound[:n] * 0.15

    mix = pad * 0.55 + bass * 0.35 + drums * 0.45
    mix = mix[: int(duration * SAMPLE_RATE)]

    # 처음 1초 페이드인, 마지막 2초 페이드아웃
    mix *= envelope(len(mix), int(1.0 * SAMPLE_RATE), int(2.0 * SAMPLE_RATE))

    peak = np.max(np.abs(mix)) or 1.0

    return mix / peak * 0.9


def write_wav(samples, path):
    stereo = np.repeat((samples * 32767).astype("<i2")[:, None], 2, axis=1)

    with wave.open(path, "wb") as file:
        file.setnchannels(2)
        file.setsampwidth(2)
        file.setframerate(SAMPLE_RATE)
        file.writeframes(stereo.tobytes())

    return path
