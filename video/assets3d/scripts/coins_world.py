"""9:16 '저울과 동전, 긴 영수증' 장면 (비용·절감 뉴스 배경).

책상 장면과 같은 받침 원판 위:
- 가운데 뒤: 큰 양팔 저울. 동전이 잔뜩 쌓인 쪽(화면 왼쪽)으로 기울어 천천히 흔들린다.
  가벼운 접시에는 파란 꼬마가 앉아 갸웃
- 왼쪽: 영수증 출력기에서 길게 늘어진 영수증 (끝에 빨간 합계 줄)
- 오른쪽: 점점 낮아지는 동전 탑 3개 (절감) + 빨간 아래 화살표, 맨 위에 빙글 도는 동전
- 앞: 꼬마 3명이 동전 / 영수증 / 빈손으로 돈다
AI 비용, 토큰 낭비, 가격 인하, % 절감 뉴스에 쓴다.

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/coins_world.py
    blender -b -P assets3d/scripts/coins_world.py -- --still-only
출력: video/public/assets3d/coins_world.png, coins_world_loop.webm (1080x1920, 투명 배경)
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import chibi_kit as ck  # noqa: E402
import iso_kit as kit  # noqa: E402

FRAMES = 360  # 12초 루프: 꼬마가 정확히 한 바퀴 돌아 제자리로 (끊김 없음)
STEPS = 36  # 초당 3걸음 (짝수여야 끊김 없음)
SIZE = 2.1
M = ck.M
ANIM = {}

PIVOT = (0.0, -1.5, 2.85)
ARM = 1.55  # 저울대 반 길이
HANG = 1.1  # 저울대 끝에서 접시까지
TILT, WOBBLE = 13, 2.5  # 도


def coin(name, center, mat=None, r=0.36, h=0.11, axis="Z", parent=None):
    return kit.cylinder(name, center, r, h, mat or M["gold"], bevel=0.025, vertices=48, axis=axis, parent=parent)


def scale_balance():
    kit.use_collection("Scale")
    px, py, pz = PIVOT
    kit.cylinder("Scale_Base", (px, py, 0.08), 0.62, 0.16, M["ink"], bevel=0.04, vertices=64)
    kit.cylinder("Scale_Foot", (px, py, 0.22), 0.32, 0.14, M["steel"], bevel=0.03, vertices=48)
    kit.cylinder("Scale_Pillar", (px, py, (0.28 + pz) / 2), 0.12, pz - 0.28, M["steel"], bevel=0.02, vertices=32)
    ck.sphere("Scale_Pivot", (px, py, pz), 0.17, M["gold"])
    kit.cylinder("Scale_Needle", (px, py + 0.12, pz + 0.38), 0.035, 0.7, M["red"], bevel=0.01, vertices=16)
    beam = kit.empty("Scale_Beam")
    beam.location = PIVOT
    kit.box("Beam_Bar", (0, 0, 0), (2 * ARM + 0.2, 0.2, 0.18), M["steel"], bevel=0.05, parent=beam)
    for sx in (-1, 1):
        ck.sphere(f"Beam_End{sx}", (sx * (ARM + 0.08), 0, 0), 0.11, M["gold"], parent=beam)
    pans = []
    for sx, name in ((1, "Heavy"), (-1, "Light")):
        pan = kit.empty(f"Pan_{name}")
        kit.cylinder(f"Pan_{name}_Dish", (0, 0, -HANG), 0.66, 0.1, M["white"], bevel=0.04, vertices=64, parent=pan)
        ck.torus(f"Pan_{name}_Rim", (0, 0, -HANG + 0.05), 0.66, 0.035, M["gold"], parent=pan)
        for k in range(3):  # 줄 3가닥: 저울대 끝에서 접시 테두리로
            a = k * 2 * math.pi / 3 + 0.5
            rx, ry = 0.58 * math.cos(a), 0.58 * math.sin(a)
            length = math.sqrt(rx * rx + ry * ry + HANG * HANG)
            rod = kit.cylinder(f"Pan_{name}_Rod{k}", (0, 0, 0), 0.014, length, M["ink"], bevel=0, vertices=8, parent=pan)
            rod.location = (rx / 2, ry / 2, -HANG / 2)  # 위(저울대 끝) → 아래(테두리) 가운데
            rod.rotation_euler = Vector((rx, ry, -HANG)).to_track_quat("Z", "Y").to_euler()
        pans.append((pan, sx))
    # 무거운 접시: 동전 더미 / 가벼운 접시: 동전 하나 + 꼬마
    heavy, light = pans[0][0], pans[1][0]
    for k, (dx, dy, n) in enumerate(((-0.18, -0.12, 5), (0.2, 0.1, 4), (0.05, 0.3, 3))):
        for j in range(n):
            c = coin(f"Heavy_Coin{k}_{j}", (dx + 0.02 * math.sin(j * 2.1), dy, -HANG + 0.1 + j * 0.115), r=0.24, h=0.1, parent=heavy)
            c.rotation_euler.z = j * 0.5
    coin("Light_Coin", (0.25, 0.15, -HANG + 0.1), r=0.2, h=0.08, parent=light)
    return beam, pans


def receipt_printer(x, y):
    """영수증 출력기(화면 왼쪽)에서 종이가 바닥으로 흘러 화면 가운데 쪽으로 길게 깔린다.
    카메라가 앞(+y)에서 보므로 종이는 x 방향으로 깔아야 길이가 다 보인다."""
    kit.use_collection("Receipt")
    kit.box("Printer", (x, y, 0.4), (0.85, 1.0, 0.8), M["white"], bevel=0.12, segments=4)
    kit.box("Printer_Slot", (x - 0.43, y, 0.66), (0.04, 0.72, 0.07), M["ink"], bevel=0.01)
    kit.cylinder("Printer_Light", (x - 0.1, y + 0.5, 0.58), 0.05, 0.03, ck.glow("PrinterLed", "red", 2.0), bevel=0.005, vertices=16, axis="Y")
    # 종이 길 (x, z): 슬롯 → 바닥 → 화면 가운데 쪽으로 → 끝이 말림
    x0 = x - 0.45
    path = ck.bezier_points((x0, 0.66), (x0 - 0.45, 0.66), (x0 - 0.6, 0.02), 12)
    flat_from = len(path)
    path += [(x0 - 0.6 - 0.1 * i, 0.02) for i in range(1, 19)]
    flat_to = len(path)
    end = path[-1][0]
    for i in range(1, 15):
        a = 1.6 * math.pi * i / 14
        path.append((end - 0.15 * math.sin(a), 0.17 - 0.15 * math.cos(a)))
    ck.ribbon("Receipt_Paper", [(px, y, pz) for px, pz in path], 0.62, M["paper"], axis=(0, 1, 0), thickness=0.012)
    # 인쇄 줄 (바닥에 깔린 부분): 품목 줄 여러 개 + 마지막에 빨간 합계 줄
    for k, i in enumerate(range(flat_from + 1, flat_to - 1, 2)):
        px = path[i][0]
        total = i >= flat_to - 3
        width = 0.46 if total else 0.2 + 0.2 * ((k * 37) % 5) / 4
        kit.box(f"Receipt_Ln{k}", (px, y - 0.22 + width / 2, 0.034), (0.05 if total else 0.03, width, 0.004), M["red"] if total else M["ink"], bevel=0)


def savings_stacks():
    kit.use_collection("Props")
    stacks = [(-1.75, -0.55, 8), (-2.3, 0.15, 5), (-2.65, 0.9, 3)]
    for k, (x, y, n) in enumerate(stacks):
        for j in range(n):
            c = coin(f"Stack{k}_{j}", (x + 0.03 * math.sin(j * 1.7 + k), y + 0.03 * math.cos(j * 2.3), 0.07 + j * 0.125))
            c.rotation_euler.z = j * 0.4
        kit.cylinder(f"Stack{k}_Mark", (x, y, 0.07 + (n - 1) * 0.125 + 0.06), 0.22, 0.01, M["red"], bevel=0.003, vertices=40)
    # 맨 위에서 빙글 도는 큰 동전
    x, y, n = stacks[0]
    spin = kit.empty("SpinCoin")
    spin.location = (x, y, 0.07 + n * 0.125 + 0.42)
    coin("SpinCoin_Body", (0, 0, 0), r=0.34, h=0.08, axis="Y", parent=spin)
    kit.cylinder("SpinCoin_Mark", (0, 0, 0), 0.2, 0.1, M["red"], bevel=0.01, vertices=40, axis="Y", parent=spin)
    ANIM["spin"] = spin
    # 흩어진 동전
    for k, (dx, dy) in enumerate(((-1.15, 0.35), (-1.45, 1.1))):
        c = coin(f"Loose{k}", (dx, dy, 0.05), r=0.2, h=0.08)
        c.rotation_euler = (math.radians(8), 0, k)
    # 빨간 아래 화살표 (탑이 낮아지는 쪽을 가리킴, 카메라를 본다)
    arrow = [(-0.12, 0.55), (0.12, 0.55), (0.12, 0.0), (0.3, 0.0), (0.0, -0.4), (-0.3, 0.0), (-0.12, 0.0)]
    a = ck.extruded("Arrow", arrow, 0.12, M["red"], center=(-3.05, 0.25, 1.15), bevel=0.03)
    a.rotation_euler = (0, math.radians(30), math.radians(-22))
    ANIM["arrow"] = a


def build_characters():
    walkers = []
    specs = [("Coin", M["red"], "coin"), ("Doc", M["white"], "doc"), ("Gold", M["gold"], None)]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.05), radii=(2.3, 0.7)))
    return walkers


def animate(cam_rig, walkers, beam, pans, sitter):
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t  # 4초 박자 (깜빡임·흔들림은 4초에 정수 번)
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        theta = math.radians(TILT + WOBBLE * math.sin(2 * math.pi * 2 * T))
        beam.rotation_euler.y = theta
        beam.keyframe_insert("rotation_euler", index=1, frame=f)
        for pan, sx in pans:  # 접시는 기울지 않고 저울대 끝을 따라 움직인다
            pan.location = (PIVOT[0] + sx * ARM * math.cos(theta), PIVOT[1], PIVOT[2] - sx * ARM * math.sin(theta))
            pan.keyframe_insert("location", frame=f)
        ANIM["spin"].rotation_euler.z = 2 * math.pi * 2 * T
        ANIM["spin"].keyframe_insert("rotation_euler", index=2, frame=f)
        ANIM["spin"].location.z = ANIM["spin_z"] + 0.06 * math.sin(2 * math.pi * 2 * T)
        ANIM["spin"].keyframe_insert("location", index=2, frame=f)
        ANIM["arrow"].location.z = 1.15 - 0.08 * (0.5 + 0.5 * math.sin(2 * math.pi * 2 * T))
        ANIM["arrow"].keyframe_insert("location", index=2, frame=f)
        _, body, feet = sitter
        ck.sway(f, T, body, degrees=9, cycles=2)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    beam, pans = scale_balance()
    receipt_printer(2.75, 0.25)
    savings_stacks()
    ANIM["spin_z"] = ANIM["spin"].location.z
    walkers = build_characters()
    # 가벼운 접시에 앉은 파란 꼬마
    sitter = ck.chibi("Sitter", M["blue"], None)
    rig = sitter[0]
    rig.scale = (SIZE * 0.6,) * 3
    rig.parent = pans[1][0]
    rig.location = (-0.15, -0.05, -HANG + 0.05)
    rig.rotation_euler.z = math.radians(25)
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers, beam, pans, sitter)

    print("STILL", kit.render_still("coins_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("coins_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
