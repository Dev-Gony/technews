"""9:16 '큰 칩과 웨이퍼' 장면 (칩·반도체·GPU·NPU·하드웨어 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 가운데: 금색 다리가 사방으로 난 큰 칩. 가운데 다이의 격자가 빛나고, 빨간 코어가 숨 쉬듯 밝아진다
  칩에서 원판 가장자리로 금색 회로 선이 뻗고, 빛 알갱이가 칩 쪽으로 흘러 들어온다
- 뒤: 받침에 선 웨이퍼(은색 원판에 다이 격자)가 천천히 돈다
- 왼쪽 앞: 팬이 도는 냉각 모듈
- 앞: 꼬마들이 코드 / 동전을 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/chip_world.py
    blender -b -P assets3d/scripts/chip_world.py -- --still-only
출력: video/public/assets3d/chip_world.png, chip_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"packets": []}

CHIP = (0.1, -0.55)
CHIP_S = 1.7
CHIP_Z = 0.32  # 칩 윗면 높이


def chip():
    kit.use_collection("Chip")
    x, y = CHIP
    rig = kit.empty("Chip")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-20)
    kit.box("Chip_Board", (0, 0, 0.06), (CHIP_S + 0.7, CHIP_S + 0.7, 0.12), kit.material("M_Pcb", "#2F5A45", 0.6, 0.3), bevel=0.04, parent=rig)
    kit.box("Chip_Body", (0, 0, CHIP_Z - 0.09), (CHIP_S, CHIP_S, 0.2), M["ink"], bevel=0.05, parent=rig)
    n = 9
    for side in range(4):
        for k in range(n):
            off = -CHIP_S / 2 + 0.2 + k * (CHIP_S - 0.4) / (n - 1)
            if side < 2:
                sx = 1 if side == 0 else -1
                kit.box(f"Pin{side}_{k}", (sx * (CHIP_S / 2 + 0.12), off, 0.15), (0.26, 0.07, 0.04), M["gold"], bevel=0.008, parent=rig)
            else:
                sy = 1 if side == 2 else -1
                kit.box(f"Pin{side}_{k}", (off, sy * (CHIP_S / 2 + 0.12), 0.15), (0.07, 0.26, 0.04), M["gold"], bevel=0.008, parent=rig)
    kit.box("Chip_Lid", (0, 0, CHIP_Z + 0.02), (CHIP_S - 0.2, CHIP_S - 0.2, 0.04), M["steel"], bevel=0.03, parent=rig)
    die = kit.box("Chip_Die", (0, 0, CHIP_Z + 0.05), (0.95, 0.95, 0.04), M["screenBg"], bevel=0.02, parent=rig)
    grid = ck.glow("DieGrid", "gold", 1.2)
    for k in range(5):
        o = -0.38 + k * 0.19
        kit.box(f"Die_GridX{k}", (o, 0, CHIP_Z + 0.075), (0.02, 0.85, 0.008), grid, bevel=0, parent=rig)
        kit.box(f"Die_GridY{k}", (0, o, CHIP_Z + 0.075), (0.85, 0.02, 0.008), grid, bevel=0, parent=rig)
    core = ck.glow("DieCore", "red", 1.5)
    for cx in (-1, 1):
        for cy in (-1, 1):
            kit.box(f"Die_Core{cx}{cy}", (cx * 0.095, cy * 0.095, CHIP_Z + 0.08), (0.15, 0.15, 0.012), core, bevel=0.005, parent=rig)
    kit.cylinder("Chip_Dot", (CHIP_S / 2 - 0.25, CHIP_S / 2 - 0.25, CHIP_Z + 0.045), 0.06, 0.01, M["white"], bevel=0, vertices=16, parent=rig)
    ANIM["grid"], ANIM["core"] = grid, core
    del die


def traces():
    kit.use_collection("Traces")
    x, y = CHIP
    gold = kit.material("M_Trace", "gold", 0.35, 0.5)
    red, white = ck.glow("PacketRed", "red", 3.0), ck.glow("PacketWhite", "white", 1.8)
    ends = [(3.0, -0.3), (2.6, 1.3), (-2.9, -0.2), (-2.6, 1.25), (1.3, 2.4), (-1.0, 2.5)]
    for k, (ex, ey) in enumerate(ends):
        # 원판 가장자리 → 꺾여서 칩 가장자리로 (회로 기판 선처럼 직각에 가깝게)
        sx = x + (0.9 if ex > x else -0.9)
        pts = [(ex, ey, 0.015), (ex * 0.6 + sx * 0.4, ey, 0.015), (sx, y + (ey - y) * 0.25, 0.015)]
        ck.tube(f"Trace{k}", pts, 0.035, gold)
        kit.cylinder(f"TracePad{k}", (ex, ey, 0.02), 0.09, 0.03, gold, bevel=0.008, vertices=24)
        for i in range(2):
            p = ck.sphere(f"Packet{k}_{i}", (0, 0, 0), 0.07, red if (i + k) % 2 else white, segments=16)
            ANIM["packets"].append((p, pts, i, 2))


def wafer(x, y):
    kit.use_collection("Wafer")
    rig = kit.empty("Wafer")
    rig.location = (x, y, 1.15)
    rig.rotation_euler.z = math.radians(-20)
    # 받침: 웨이퍼 뒤(-y)에 숨은 기둥 하나
    kit.box("Wafer_Foot", (0, -0.12, -1.1), (0.9, 0.45, 0.1), M["ink"], bevel=0.03, parent=rig)
    kit.box("Wafer_Post", (0, -0.12, -0.55), (0.12, 0.1, 1.1), M["ink"], bevel=0.02, parent=rig)
    spin = kit.empty("Wafer_Spin", parent=rig)
    silver = kit.material("M_Wafer", "#C9CDD2", 0.18, 0.8)
    kit.cylinder("Wafer_Disc", (0, 0, 0), 0.95, 0.05, silver, bevel=0.01, vertices=96, axis="Y", parent=spin)
    tones = [M["blue"], M["gold"], kit.material("M_DieB", "#8FA7C4", 0.25, 0.6), M["red"]]
    step = 0.21
    for i in range(-4, 5):
        for j in range(-4, 5):
            cx, cz = i * step, j * step
            if math.hypot(cx, cz) > 0.8:
                continue
            mat = tones[(i * 3 + j * 5) % 4] if (i + j) % 3 == 0 else kit.material("M_DieA", "#A9B6C6", 0.25, 0.6)
            kit.box(f"Wafer_Die{i}_{j}", (cx, 0.03, cz), (step - 0.03, 0.012, step - 0.03), mat, bevel=0.005, parent=spin)
    ANIM["wafer"] = spin


def fan(x, y):
    kit.use_collection("Fan")
    rig = kit.empty("FanBox")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-30)
    kit.box("Fan_Sink", (0, 0, 0.12), (1.0, 1.0, 0.24), M["steel"], bevel=0.03, parent=rig)
    for k in range(7):
        kit.box(f"Fan_Fin{k}", (-0.42 + k * 0.14, 0, 0.36), (0.05, 0.95, 0.26), kit.material("M_Fin", "#9EA3A8", 0.3, 0.7), bevel=0.01, parent=rig)
    kit.box("Fan_Frame", (0, 0, 0.57), (1.0, 1.0, 0.16), M["ink"], bevel=0.05, parent=rig)
    hub = kit.empty("Fan_Hub", parent=rig)
    hub.location = (0, 0, 0.67)
    kit.cylinder("Fan_Center", (0, 0, 0.02), 0.13, 0.08, M["red"], bevel=0.02, vertices=32, parent=hub)
    for k in range(5):
        blade = kit.empty(f"Fan_BladeRig{k}", parent=hub)
        blade.rotation_euler.z = k * 2 * math.pi / 5
        b = kit.box(f"Fan_Blade{k}", (0.24, 0, 0.0), (0.3, 0.13, 0.02), M["white"], bevel=0.02, parent=blade)
        b.rotation_euler.x = math.radians(25)
    ANIM["fan"] = hub


def build_characters():
    walkers = []
    specs = [("Code", M["white"], "code"), ("Coin", M["red"], "coin"), ("Gold", M["gold"], None)]
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
        for obj, pts, i, n in ANIM["packets"]:
            u = (i / n + T) % 1.0
            p = ck.sample(pts, u)
            obj.location = (p.x, p.y, p.z + 0.04)
            obj.keyframe_insert("location", frame=f)
            s = math.sin(math.pi * u) ** 0.35
            obj.scale = (s, s, s)
            obj.keyframe_insert("scale", frame=f)
        ck.pulse(f, T, ANIM["grid"], 0.6, 2.2, 2)
        ck.pulse(f, T, ANIM["core"], 0.8, 3.2, 4)
        ANIM["wafer"].rotation_euler.y = 2 * math.pi * t  # 루프 동안 한 바퀴
        ANIM["wafer"].keyframe_insert("rotation_euler", index=1, frame=f)
        ANIM["fan"].rotation_euler.z = 2 * math.pi * t * 9  # 루프 동안 9바퀴 (끊김 없음)
        ANIM["fan"].keyframe_insert("rotation_euler", index=2, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    chip()
    traces()
    wafer(-0.05, -2.05)
    fan(2.35, 0.75)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("chip_world", {
        "chip": (obj["Chip"], "object", "금색 다리 달린 큰 칩, 가운데 코어가 빛난다 (반도체·GPU·NPU)"),
        "wafer": (obj["Wafer"], "object", "받침 위에서 천천히 도는 은색 웨이퍼 (생산·파운드리·공정)"),
        "fan": (obj["FanBox"], "object", "팬이 빙빙 도는 냉각 모듈 (발열·전력·데이터센터)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 코드를 들고 걸어 다닌다 (개발자·소프트웨어)"),
        "red": (walkers[1].rig, "character", "빨간 꼬마: 동전을 들고 걸어 다닌다 (투자·가격·매출)"),
        "yellow": (walkers[2].rig, "character", "노란 꼬마: 빈손으로 걸어 다닌다 (사용자·고객사)"),
    }, FRAMES, "chip3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("chip_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("chip_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
