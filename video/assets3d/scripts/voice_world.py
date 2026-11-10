"""9:16 '스튜디오 마이크와 음파 막대, 헤드폰' 장면 (음성·TTS·STT·오디오·음악·팟캐스트 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 가운데 뒤: 받침대에 선 큰 스튜디오 마이크 (금색 몸, 먹색 그물 머리, 빨간 띠)
- 마이크 앞: 음파 막대 9개가 오르내린다 (가운데가 높다)
- 둘레: 마이크에서 퍼지는 금색 음파 고리
- 왼쪽 앞: 받침에 걸린 헤드폰, 오른쪽 앞: 음표 2개가 둥실
- 앞: 꼬마들이 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/voice_world.py
    blender -b -P assets3d/scripts/voice_world.py -- --still-only
출력: video/public/assets3d/voice_world.png, voice_world_loop.webm (1080x1920, 투명 배경)
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import chibi_kit as ck  # noqa: E402
import iso_kit as kit  # noqa: E402

FRAMES = 360
STEPS = 36
SIZE = 2.1
M = ck.M
ANIM = {"bars": [], "rings": [], "notes": []}

MIC = (0.1, -1.45)


def mic():
    kit.use_collection("Mic")
    x, y = MIC
    kit.cylinder("Mic_Base", (x, y, 0.06), 0.55, 0.12, M["ink"], bevel=0.04, vertices=48)
    kit.cylinder("Mic_Pole", (x, y, 0.65), 0.05, 1.1, M["ink"], bevel=0.01, vertices=16)
    rig = kit.empty("Mic")
    rig.location = (x, y, 1.25)
    rig.rotation_euler = (math.radians(-12), 0, math.radians(-20))
    ck.torus("Mic_Yoke", (0, 0, 0.35), 0.42, 0.04, M["ink"], rotation=(0, math.pi / 2, 0), parent=rig)
    kit.cylinder("Mic_Body", (0, 0, 0.45), 0.3, 0.6, M["gold"], bevel=0.05, vertices=48, parent=rig)
    kit.cylinder("Mic_Band", (0, 0, 0.78), 0.315, 0.08, M["red"], bevel=0.02, vertices=48, parent=rig)
    grille = kit.material("M_Grille", "#3A3833", 0.35, 0.5)
    ck.sphere("Mic_Head", (0, 0, 1.02), 0.34, grille, scale=(1, 1, 1.15), parent=rig, segments=40)
    for k in range(5):
        z = 0.82 + k * 0.1
        r = math.sqrt(max(0.0, 0.34 ** 2 - ((z - 1.02) / 1.15) ** 2)) + 0.006
        ck.torus(f"Mic_Ring{k}", (0, 0, z), r, 0.012, M["steel"], parent=rig)
    ring_mat = ck.glow("Wave", "gold", 1.0)
    for k in range(3):
        r = ck.torus(f"WaveRing{k}", (0, 0, 1.02), 0.42, 0.018, ring_mat, rotation=(math.pi / 2, 0, 0), parent=rig)
        ANIM["rings"].append((r, k))


def bars():
    kit.use_collection("Bars")
    rig = kit.empty("Bars")
    rig.location = (MIC[0] + 0.05, MIC[1] + 1.25, 0)
    rig.rotation_euler.z = math.radians(-20)
    kit.box("Bars_Base", (0, 0, 0.04), (2.9, 0.4, 0.08), M["ink"], bevel=0.03, parent=rig)
    n = 9
    for k in range(n):
        x = -1.2 + k * 0.3
        mat = M["red"] if k == n // 2 else (M["gold"] if abs(k - n // 2) == 1 else M["white"])
        b = kit.box(f"Bar{k}", (x, 0, 0.5), (0.2, 0.2, 1.0), mat, bevel=0.05, parent=rig)
        for v in b.data.vertices:  # 원점 = 막대 바닥 (위로만 늘어난다)
            v.co.z += 0.5
        b.location.z = 0.08
        peak = 1.0 - 0.75 * abs(k - n // 2) / (n // 2)
        ANIM["bars"].append((b, peak, k))


def headphones(x, y):
    kit.use_collection("Phones")
    kit.cylinder("Hp_Base", (x, y, 0.06), 0.38, 0.12, M["ink"], bevel=0.04, vertices=40)
    kit.cylinder("Hp_Pole", (x, y, 0.55), 0.04, 0.9, M["ink"], bevel=0.01, vertices=16)
    rig = kit.empty("Headphones")
    rig.location = (x, y, 1.0)
    rig.rotation_euler.z = math.radians(-20)
    pts = [(0.42 * math.cos(a), 0, 0.42 * math.sin(a)) for a in [math.pi * i / 16 for i in range(17)]]
    ck.tube("Hp_Band", pts, 0.05, M["red"], parent=rig)
    for sx in (-1, 1):
        kit.cylinder(f"Hp_Cup{sx}", (sx * 0.44, 0, -0.08), 0.2, 0.16, M["ink"], bevel=0.05, vertices=32, axis="X", parent=rig)
        kit.cylinder(f"Hp_Pad{sx}", (sx * 0.34, 0, -0.08), 0.17, 0.06, M["white"], bevel=0.025, vertices=32, axis="X", parent=rig)


def notes(x, y):
    kit.use_collection("Notes")
    for k, (dx, dz, mat) in enumerate(((0.0, 1.1, M["red"]), (-0.5, 1.6, M["gold"]))):
        rig = kit.empty(f"Note{k}")
        rig.location = (x + dx, y, dz)
        rig.rotation_euler.z = math.radians(-20)
        ck.sphere(f"Note{k}_Head", (0, 0, 0), 0.17, mat, scale=(1.25, 0.7, 0.9), parent=rig)
        kit.box(f"Note{k}_Stem", (0.17, 0, 0.38), (0.06, 0.06, 0.76), mat, bevel=0.015, parent=rig)
        flag = kit.box(f"Note{k}_Flag", (0.3, 0, 0.66), (0.28, 0.06, 0.12), mat, bevel=0.03, parent=rig)
        flag.rotation_euler.y = math.radians(30)
        ANIM["notes"].append((rig, dz, k))


def build_characters():
    walkers = []
    specs = [("White", M["white"], None), ("Blue", M["blue"], "doc"), ("Red", M["red"], None)]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.25), radii=(2.3, 0.6)))
    return walkers


def animate(cam_rig, walkers):
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        for b, peak, k in ANIM["bars"]:
            h = 0.25 + peak * (0.55 + 0.45 * math.sin(2 * math.pi * 4 * T + k * 0.9)) * (0.75 + 0.25 * math.sin(2 * math.pi * 2 * T))
            b.scale.z = h
            b.keyframe_insert("scale", index=2, frame=f)
        for r, k in ANIM["rings"]:
            u = (2 * T + k / 3) % 1.0
            s = (1 + 0.9 * u) * min(1.0, (1 - u) / 0.25)  # 퍼지다 끝에서 오므라들며 사라진다
            r.scale = (s, s, s)
            r.keyframe_insert("scale", frame=f)
        for rig, z, k in ANIM["notes"]:
            rig.location.z = z + 0.12 * math.sin(2 * math.pi * T + k * 2.4)
            rig.rotation_euler.y = math.radians(10) * math.sin(2 * math.pi * 2 * T + k)
            rig.keyframe_insert("location", index=2, frame=f)
            rig.keyframe_insert("rotation_euler", index=1, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    mic()
    bars()
    headphones(2.25, 0.4)
    notes(-2.1, 0.3)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    # 마이크: 퍼지는 음파 고리는 빼고 몸·머리·받침대만. 헤드폰: 띠(커브)는 경계 상자가 커서 컵·받침만
    mic_parts = [obj[n] for n in ("Mic_Base", "Mic_Pole", "Mic_Yoke", "Mic_Body", "Mic_Band", "Mic_Head")]
    print("ANCHORS", ck.export_anchors("voice_world", {
        "mic": (mic_parts, "object", "받침대에 선 큰 금색 스튜디오 마이크 (음성 입력·녹음·STT)"),
        "bars": (obj["Bars"], "object", "오르내리는 음파 막대 9개 (소리·음성 합성·TTS 출력)"),
        "headphones": ([obj[n] for n in ("Hp_Base", "Hp_Pole", "Hp_Cup-1", "Hp_Cup1")], "object", "받침에 걸린 빨간 헤드폰 (듣기·오디오·음악 감상)"),
        "notes": ([obj["Note0"], obj["Note1"]], "object", "둥실 떠 있는 빨강·금색 음표 2개 (음악·작곡 AI)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 빈손으로 걸어 다닌다 (청취자·사용자)"),
        "blue": (walkers[1].rig, "character", "파란 꼬마: 문서를 들고 걸어 다닌다 (대본·받아쓰기 결과)"),
        "red": (walkers[2].rig, "character", "빨간 꼬마: 빈손으로 걸어 다닌다 (화자·진행자)"),
    }, FRAMES, "voice3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("voice_world", resolution=1080, height=1920, frame=20))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("voice_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
