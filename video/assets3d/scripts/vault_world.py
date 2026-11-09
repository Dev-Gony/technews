"""9:16 '살짝 열린 금고' 장면 (보안 뉴스 배경).

책상 장면과 같은 받침 원판 위:
- 가운데 뒤: 큰 금고. 문이 살짝 열려 있고 문틈으로 빨간 빛이 새어 나온다 (천천히 숨 쉬듯 밝아졌다 어두워짐)
- 문 다이얼이 조금씩 돌아간다, 금색 꼬마가 문틈을 엿보며 갸웃
- 왼쪽: 빨간 방패(금테, 열쇠 구멍), 오른쪽: 큰 금색 자물쇠
- 앞: 꼬마 3명이 순찰하듯 돈다 (열쇠 / 문서 / 빈손)
백도어, 토큰·키 유출, 인증, 취약점 뉴스에 쓴다.

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/vault_world.py
    blender -b -P assets3d/scripts/vault_world.py -- --still-only
출력: video/public/assets3d/vault_world.png, vault_world_loop.webm (1080x1920, 투명 배경)
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import chibi_kit as ck  # noqa: E402
import iso_kit as kit  # noqa: E402

FRAMES = 360  # 12초 루프: 꼬마가 정확히 한 바퀴 돌아 제자리로 (끊김 없음)
STEPS = 36  # 초당 3걸음 (짝수여야 끊김 없음)
SIZE = 2.1
M = ck.M
ANIM = {}

SAFE_C = (0.15, -1.35)  # 금고 바닥 가운데
SAFE_W, SAFE_D, SAFE_H = 2.6, 1.9, 2.8
DOOR_OPEN = 30  # 도


def safe():
    kit.use_collection("Safe")
    x, y = SAFE_C
    front = y + SAFE_D / 2
    body = kit.box("Safe_Body", (x, y, SAFE_H / 2 + 0.12), (SAFE_W, SAFE_D, SAFE_H), M["steel"], bevel=0.06, segments=4)
    # 문 자리 파내기 (안쪽이 보이게)
    cutter = kit.box("Safe_Cut", (x, front - 0.55, SAFE_H / 2 + 0.12), (SAFE_W - 0.36, 1.2, SAFE_H - 0.36), M["ink"], bevel=0)
    kit.cut(body, cutter)
    # 받침 다리
    for sx in (-1, 1):
        for sy in (-1, 1):
            kit.cylinder(f"Safe_Foot{sx}{sy}", (x + sx * (SAFE_W / 2 - 0.25), y + sy * (SAFE_D / 2 - 0.25), 0.06), 0.13, 0.12, M["ink"], bevel=0.02, vertices=24)
    # 안쪽: 빨갛게 빛나는 뒷벽 + 빨간 점광 (문틈으로 새는 빛)
    red_glow = ck.glow("Leak", "red", 2.2)
    ANIM["leak"] = red_glow
    kit.box("Safe_Inner", (x, front - 1.0, SAFE_H / 2 + 0.12), (SAFE_W - 0.4, 0.05, SAFE_H - 0.4), red_glow, bevel=0)
    for k, z in enumerate((0.75, 1.55)):  # 선반 위 금괴
        kit.box(f"Safe_Shelf{k}", (x, front - 0.55, z), (SAFE_W - 0.4, 0.9, 0.05), M["dark"], bevel=0)
    for k, dx in enumerate((-0.45, 0.0, 0.45)):
        kit.box(f"Safe_Bar{k}", (x + dx, front - 0.5, 0.88), (0.36, 0.5, 0.2), M["gold"], bevel=0.03)
    data = bpy.data.lights.new("L_Leak", "POINT")
    data.energy = 420
    data.color = (1.0, 0.28, 0.2)
    data.shadow_soft_size = 0.4
    lamp = bpy.data.objects.new("L_Leak", data)
    bpy.context.scene.collection.objects.link(lamp)
    lamp.location = (x - 0.3, front - 0.35, 1.3)
    ANIM["lamp"] = data

    # 문: 경첩은 화면 왼쪽(+x) 모서리. 살짝 바깥으로 열린다
    hinge = kit.empty("Door_Hinge")
    hinge.location = (x + SAFE_W / 2 - 0.12, front + 0.11, 0)
    hinge.rotation_euler.z = math.radians(-DOOR_OPEN)
    dw, dh = SAFE_W - 0.3, SAFE_H - 0.3
    kit.box("Door", (-dw / 2, 0, SAFE_H / 2 + 0.12), (dw, 0.2, dh), M["steel"], bevel=0.05, segments=4, parent=hinge)
    kit.box("Door_Panel", (-dw / 2, 0.105, SAFE_H / 2 + 0.12), (dw - 0.36, 0.02, dh - 0.36), M["dark"], bevel=0.03, parent=hinge)
    for k, z in enumerate((0.55, SAFE_H - 0.3)):  # 경첩
        kit.cylinder(f"Door_Pin{k}", (0.02, 0.0, z), 0.07, 0.32, M["ink"], bevel=0.015, vertices=24, parent=hinge)
    # 다이얼 + 손잡이 바퀴 (천천히 돈다)
    dial = kit.empty("Dial", parent=hinge)
    dial.location = (-dw / 2, 0.13, SAFE_H / 2 + 0.25)
    kit.cylinder("Dial_Ring", (0, 0, 0), 0.42, 0.06, M["gold"], bevel=0.015, vertices=64, axis="Y", parent=dial)
    kit.cylinder("Dial_Face", (0, 0.03, 0), 0.32, 0.04, M["ink"], bevel=0.01, vertices=64, axis="Y", parent=dial)
    kit.cylinder("Dial_Hub", (0, 0.07, 0), 0.1, 0.08, M["gold"], bevel=0.02, vertices=32, axis="Y", parent=dial)
    for k in range(3):
        spoke = kit.empty(f"Dial_Spoke{k}", parent=dial)
        spoke.rotation_euler.y = k * 2 * math.pi / 3
        kit.cylinder(f"Dial_SpokeBar{k}", (0, 0.1, 0.33), 0.035, 0.5, M["gold"], bevel=0.008, vertices=16, parent=spoke)
        ck.sphere(f"Dial_Knob{k}", (0, 0.1, 0.6), 0.075, M["red"], parent=spoke, segments=20)
    for k in range(12):  # 눈금
        tick = kit.empty(f"Tick{k}", parent=dial)
        tick.rotation_euler.y = k * math.pi / 6
        kit.box(f"Tick_Bar{k}", (0, 0.052, 0.27), (0.02, 0.01, 0.06 if k % 3 else 0.1), M["white"], bevel=0, parent=tick)
    ANIM["dial"] = dial
    # 문 가장자리 빗장 (금색 막대)
    for k, z in enumerate((0.75, 1.55, 2.35)):
        kit.cylinder(f"Door_Bolt{k}", (-dw - 0.02, 0, z), 0.06, 0.28, M["gold"], bevel=0.01, vertices=20, axis="X", parent=hinge)
    return hinge


def shield(cx, cy):
    kit.use_collection("Props")
    pts = []
    pts += ck.bezier_points((0.0, -1.0), (0.78, -0.55), (0.78, 0.55), 14)  # 오른쪽 아래 → 위
    pts += ck.bezier_points((0.78, 0.55), (0.78, 0.86), (0.4, 0.92), 6)[1:]
    pts += ck.bezier_points((0.4, 0.92), (0.0, 1.0), (-0.4, 0.92), 6)[1:]
    pts += ck.bezier_points((-0.4, 0.92), (-0.78, 0.86), (-0.78, 0.55), 6)[1:]
    pts += ck.bezier_points((-0.78, 0.55), (-0.78, -0.55), (0.0, -1.0), 14)[1:-1]
    rig = kit.empty("Shield_Rig")
    rig.location = (cx, cy, 1.12)
    rig.rotation_euler = (math.radians(-8), 0, math.radians(-18))
    rim = ck.extruded("Shield_Rim", [(x * 1.12, z * 1.1) for x, z in pts], 0.16, M["gold"], center=(0, -0.03, 0), bevel=0.04, parent=rig)
    face = ck.extruded("Shield_Face", pts, 0.2, M["red"], center=(0, 0.02, 0), bevel=0.05, parent=rig)
    # 열쇠 구멍
    kit.cylinder("Shield_KeyTop", (0, 0.13, 0.18), 0.17, 0.04, M["gold"], bevel=0.01, vertices=40, axis="Y", parent=rig)
    kh = ck.extruded("Shield_KeyLeg", [(-0.12, -0.45), (0.12, -0.45), (0.06, 0.12), (-0.06, 0.12)], 0.04, M["gold"], center=(0, 0.13, 0), bevel=0.01, parent=rig)
    # 받침 다리 (뒤에서 받치는 막대)
    kit.box("Shield_Stand", (cx + 0.1, cy - 0.45, 0.45), (0.12, 0.7, 0.12), M["ink"], bevel=0.03).rotation_euler.x = math.radians(-35)
    return rig, rim, face, kh


def padlock(cx, cy):
    kit.use_collection("Props")
    rig = kit.empty("Lock_Rig")
    rig.location = (cx, cy, 0)
    rig.rotation_euler.z = math.radians(-12)
    kit.box("Lock_Body", (0, 0, 0.5), (1.05, 0.5, 0.88), M["gold"], bevel=0.12, segments=5, parent=rig)
    # 고리 (반원 + 다리)
    ring = ck.torus("Lock_Shackle", (0, 0, 1.12), 0.33, 0.085, M["white"], rotation=(math.pi / 2, 0, 0), parent=rig)
    cutter = kit.box("Lock_ShackleCut", (cx, cy, 0.85), (1.2, 1.2, 0.54), M["ink"], bevel=0)
    bpy.context.view_layer.update()
    # 부모 공간과 상관없이 아래 반쪽을 지우기 위해 잠깐 부모를 떼고 자른다
    world = ring.matrix_world.copy()
    ring.parent = None
    ring.matrix_world = world
    kit.cut(ring, cutter)
    ring.parent = rig
    ring.matrix_parent_inverse = rig.matrix_world.inverted()
    for sx in (-1, 1):
        kit.cylinder(f"Lock_Leg{sx}", (sx * 0.33, 0, 1.0), 0.085, 0.3, M["white"], bevel=0.02, vertices=24, parent=rig)
    kit.cylinder("Lock_Hole", (0, 0.26, 0.6), 0.09, 0.03, M["ink"], bevel=0.005, vertices=32, axis="Y", parent=rig)
    kit.box("Lock_HoleLeg", (0, 0.26, 0.45), (0.07, 0.03, 0.2), M["ink"], bevel=0.005, parent=rig)
    return rig


def build_characters():
    walkers = []
    specs = [("Key", M["gold"], "key"), ("Doc", M["white"], "doc"), ("Blue", M["blue"], None)]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.05), radii=(2.4, 0.7)))
    # 문틈을 엿보는 빨간 꼬마
    rig, body, feet = ck.chibi("Peeker", M["red"], None)
    rig.scale = (SIZE * 0.85,) * 3
    rig.location = (-1.4, 0.3, 0.0)
    rig.rotation_euler.z = math.radians(-115)  # 문틈 쪽을 본다 (옆얼굴이 카메라에 보이게)
    return walkers, (rig, body, feet)


def animate(cam_rig, walkers, peeker):
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t  # 4초 박자 (깜빡임·흔들림은 4초에 정수 번)
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        _, body, feet = peeker
        ck.sway(f, T, body, degrees=10, cycles=1)
        ck.hop(f, T, body, feet, hops=4, height=0.03)
        # 다이얼(12초에 한 번): 왼쪽으로 1/3 바퀴 돌고 다시 돌아오기 (바퀴살이 3개라 어디서 멈춰도 같은 모양)
        ANIM["dial"].rotation_euler.y = (2 * math.pi / 3) * (0.5 - 0.5 * math.cos(2 * math.pi * t))
        ANIM["dial"].keyframe_insert("rotation_euler", index=1, frame=f)
        # 새는 빛: 숨 쉬듯 2번
        ck.pulse(f, T, ANIM["leak"], 1.4, 3.0, 2)
        ANIM["lamp"].energy = 320 + 200 * (0.5 + 0.5 * math.sin(2 * math.pi * 2 * T))
        ANIM["lamp"].keyframe_insert("energy", frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    safe()
    shield(2.45, -0.55)
    padlock(-2.45, -0.35)
    walkers, peeker = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, rig = ck.frame_camera()
    animate(rig, walkers, peeker)

    print("STILL", kit.render_still("vault_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("vault_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
