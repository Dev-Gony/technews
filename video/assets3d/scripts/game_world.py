"""9:16 '큰 게임 패드와 픽셀 하트, 조이스틱' 장면 (게임·게임 개발·에뮬레이터·콘솔 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 가운데 뒤: 비스듬히 선 큰 게임 패드. 십자키와 버튼 4개가 차례로 눌리고 가운데 불이 깜빡인다
- 왼쪽 앞: 빙글 도는 픽셀 하트 (빨간 정육면체로 쌓은 하트)
- 오른쪽 앞: 이리저리 흔들리는 아케이드 조이스틱 (빨간 공 손잡이)
- 둘레: 금색 픽셀 동전 3개가 떠서 돈다
- 앞: 꼬마들이 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/game_world.py
    blender -b -P assets3d/scripts/game_world.py -- --still-only
출력: video/public/assets3d/game_world.png, game_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"buttons": [], "coins": []}

HEART = ["01100110", "11111111", "11111111", "11111111", "01111110", "00111100", "00011000"]


def gamepad():
    kit.use_collection("Pad")
    base = kit.empty("PadRig")
    base.location = (0.05, -1.35, 0)
    base.rotation_euler.z = math.radians(-20)
    kit.box("Pad_Stand", (0, 0.1, 0.12), (1.4, 0.7, 0.24), M["ink"], bevel=0.05, parent=base)
    pad = kit.empty("Pad", parent=base)
    pad.location = (0, 0, 1.15)
    pad.rotation_euler.x = math.radians(18)
    body = kit.material("M_PadBody", "#ECE8DF", 0.45, 0.3)
    kit.box("Pad_Body", (0, 0, 0), (2.4, 0.45, 1.05), body, bevel=0.42, segments=8, parent=pad)
    for sx in (-1, 1):
        ck.sphere(f"Pad_Grip{sx}", (sx * 0.95, 0, -0.45), 0.48, body, scale=(1, 0.5, 1.1), parent=pad)
    face = 0.235
    # 십자키 (화면 왼쪽 = +x)
    kit.box("Pad_DpadH", (0.72, face, 0.05), (0.5, 0.08, 0.16), M["ink"], bevel=0.03, parent=pad)
    kit.box("Pad_DpadV", (0.72, face, 0.05), (0.16, 0.08, 0.5), M["ink"], bevel=0.03, parent=pad)
    # 버튼 4개 (화면 오른쪽 = -x)
    colors = ["red", "gold", "blue", "sage"]
    offs = [(0, 0.17), (0.17, 0), (0, -0.17), (-0.17, 0)]
    for k, ((dx, dz), c) in enumerate(zip(offs, colors)):
        b = kit.empty(f"Btn{k}", parent=pad)
        b.location = (-0.72 + dx, face, 0.05 + dz)
        kit.cylinder(f"Btn{k}_Cap", (0, 0, 0), 0.09, 0.1, M[c], bevel=0.03, vertices=24, axis="Y", parent=b)
        ANIM["buttons"].append((b, k))
    for k, dx in enumerate((0.16, -0.16)):
        kit.box(f"Pad_Pill{k}", (dx, face, 0.18), (0.18, 0.05, 0.06), M["steel"], bevel=0.025, parent=pad)
    led = ck.glow("PadLed", "red", 2.0)
    kit.cylinder("Pad_Led", (0, face, -0.1), 0.07, 0.04, led, bevel=0.01, vertices=24, axis="Y", parent=pad)
    ANIM["led"], ANIM["pad"] = led, pad


def heart(x, y):
    kit.use_collection("Heart")
    kit.cylinder("Heart_Base", (x, y, 0.06), 0.42, 0.12, M["ink"], bevel=0.04, vertices=40)
    kit.cylinder("Heart_Stem", (x, y, 0.35), 0.05, 0.5, M["ink"], bevel=0.01, vertices=16)
    rig = kit.empty("Heart")
    rig.location = (x, y, 1.15)
    s = 0.13
    for r, row in enumerate(HEART):
        for c, bit in enumerate(row):
            if bit == "1":
                mat = M["white"] if (r, c) in ((1, 1), (1, 2), (2, 1)) else M["red"]
                kit.box(f"Heart_{r}_{c}", ((3.5 - c) * s, 0, (3 - r) * s), (s * 0.94, s * 0.94, s * 0.94), mat, bevel=0.012, parent=rig)
    ANIM["heart"] = rig


def joystick(x, y):
    kit.use_collection("Stick")
    rig = kit.empty("StickBox")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-20)
    kit.box("Stick_Box", (0, 0, 0.25), (1.0, 0.8, 0.5), M["ink"], bevel=0.06, parent=rig)
    kit.box("Stick_Top", (0, 0, 0.51), (0.9, 0.7, 0.03), M["red"], bevel=0.01, parent=rig)
    for k, c in enumerate(("gold", "blue")):
        kit.cylinder(f"Stick_Btn{k}", (-0.28 + k * 0.0, 0.18 - k * 0.3, 0.55), 0.08, 0.06, M[c], bevel=0.02, vertices=24, parent=rig)
    lever = kit.empty("Stick_Lever", parent=rig)
    lever.location = (0.18, 0, 0.53)
    kit.cylinder("Stick_Shaft", (0, 0, 0.25), 0.04, 0.5, M["steel"], bevel=0.01, vertices=16, parent=lever)
    ck.sphere("Stick_Ball", (0, 0, 0.55), 0.17, M["red"], parent=lever)
    ANIM["lever"] = lever


def coins():
    kit.use_collection("Coins")
    for k in range(3):
        c = kit.empty(f"PixCoin{k}")
        kit.cylinder(f"PixCoin{k}_Body", (0, 0, 0), 0.2, 0.06, M["gold"], bevel=0.0, vertices=8, axis="Y", parent=c)
        kit.box(f"PixCoin{k}_Mark", (0, 0.035, 0), (0.05, 0.01, 0.18), kit.material("M_CoinMark", "#E0A93D", 0.4, 0.4), bevel=0, parent=c)
        ANIM["coins"].append((c, k))


def build_characters():
    walkers = []
    specs = [("White", M["white"], None), ("Red", M["red"], None), ("Blue", M["blue"], "coin")]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.2), radii=(2.3, 0.62)))
    return walkers


def animate(cam_rig, walkers):
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        ph = T % 1.0
        for b, k in ANIM["buttons"]:  # 4초에 두 바퀴, 버튼이 차례로 꾹
            u = (ph * 2 * 4 - k) % 4
            press = math.sin(math.pi * u / 0.6) if u < 0.6 else 0.0
            b.location.y = 0.235 - 0.05 * press
            b.keyframe_insert("location", index=1, frame=f)
        ck.pulse(f, T, ANIM["led"], 0.4, 2.6, 4, square=True)
        pad = ANIM["pad"]
        pad.location.z = 1.15 + 0.05 * math.sin(2 * math.pi * T)
        pad.keyframe_insert("location", index=2, frame=f)
        h = ANIM["heart"]
        h.rotation_euler.z = 2 * math.pi * t
        s = 1 + 0.08 * max(0.0, math.sin(2 * math.pi * 4 * T)) ** 4  # 두근
        h.scale = (s, s, s)
        h.keyframe_insert("rotation_euler", index=2, frame=f)
        h.keyframe_insert("scale", frame=f)
        lv = ANIM["lever"]
        lv.rotation_euler.x = math.radians(20) * math.sin(2 * math.pi * 3 * T)
        lv.rotation_euler.y = math.radians(20) * math.sin(2 * math.pi * 2 * T + 1)
        lv.keyframe_insert("rotation_euler", frame=f)
        for c, k in ANIM["coins"]:
            a = 2 * math.pi * (t + k / 3)
            c.location = (-1.1 + k * 1.1, -2.0 + 0.15 * math.sin(a), 1.95 + 0.12 * math.sin(2 * math.pi * T + k))
            c.rotation_euler.z = 2 * math.pi * 2 * t + k
            c.keyframe_insert("location", frame=f)
            c.keyframe_insert("rotation_euler", index=2, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    gamepad()
    heart(2.2, 0.35)
    joystick(-2.1, 0.45)
    coins()
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)

    print("STILL", kit.render_still("game_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("game_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
