"""9:16 '실험대와 점수판, 시상대' 장면 (모델 연구·벤치마크 뉴스 배경).

책상 장면과 같은 받침 원판 위:
- 뒤: 큰 점수판. 막대 4개가 오르내리고, 빨간 막대(우리 모델)가 제일 높다
- 가운데 앞: 시상대 1·2·3등. 1등 금색 꼬마가 트로피를 들고 통통
- 왼쪽: 실험대 위 플라스크들, 빨강·금색 액체에서 기포가 올라온다
- 오른쪽: 논문 더미
- 앞: 꼬마 2명이 플라스크 / 문서를 들고 돈다
모델 가중치, 학습, 벤치마크 점수, 안전성 연구 뉴스에 쓴다.

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/lab_world.py
    blender -b -P assets3d/scripts/lab_world.py -- --still-only
출력: video/public/assets3d/lab_world.png, lab_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"bars": [], "bubbles": []}

BOARD = (0.0, -1.75)  # 점수판 바닥 가운데
BOARD_W, BOARD_H = 3.3, 2.2
BAR_BASE = 0.55  # 점수판 안 막대 바닥 높이 (판 기준)


def scoreboard():
    kit.use_collection("Board")
    x, y = BOARD
    for sx in (-1, 1):
        kit.box(f"Board_Leg{sx}", (x + sx * (BOARD_W / 2 - 0.35), y, 0.3), (0.14, 0.14, 0.6), M["ink"], bevel=0.04)
        kit.box(f"Board_Foot{sx}", (x + sx * (BOARD_W / 2 - 0.35), y, 0.03), (0.5, 0.6, 0.06), M["ink"], bevel=0.02)
    rig = kit.empty("Board")
    rig.location = (x, y, 0.55)
    kit.box("Board_Frame", (0, 0, BOARD_H / 2), (BOARD_W, 0.16, BOARD_H), M["steel"], bevel=0.06, segments=4, parent=rig)
    kit.box("Board_Screen", (0, 0.085, BOARD_H / 2), (BOARD_W - 0.24, 0.01, BOARD_H - 0.24), M["screenBg"], bevel=0.01, parent=rig)
    # 바닥선 + 눈금선
    line = ck.glow("BoardLine", "paper", 0.5)
    kit.box("Board_Axis", (0, 0.095, BAR_BASE - 0.05), (BOARD_W - 0.6, 0.004, 0.025), line, bevel=0, parent=rig)
    for k in range(1, 4):
        kit.box(f"Board_Grid{k}", (0, 0.092, BAR_BASE - 0.05 + k * 0.4), (BOARD_W - 0.6, 0.002, 0.01), ck.glow("BoardGrid", "#3A4757", 0.8), bevel=0, parent=rig)
    # 막대 4개 (빨강이 1등). 높이는 애니메이션으로 오르내린다
    specs = [("screen", 0.62, 0.0), ("paper", 0.8, 1.3), ("gold", 0.95, 2.1), ("red", 1.32, 0.6)]
    for k, (color, height, phase) in enumerate(specs):
        bx = 1.05 - k * 0.7  # 화면 오른쪽(-x)으로 갈수록 높아진다
        bar = kit.box(f"Board_Bar{k}", (bx, 0.1, BAR_BASE - 0.04), (0.42, 0.02, 1.0), ck.glow(f"Bar{k}", color, 1.3), bevel=0, parent=rig)
        # 바닥 기준으로 늘어나도록 메시를 위로 올려 둔다 (원점 = 막대 바닥)
        for v in bar.data.vertices:
            v.co.z += 0.5
        ANIM["bars"].append((bar, height, phase))
    # 1등 막대 위 왕관 점
    crown = ck.sphere("Board_Star", (-1.05, 0.12, 0), 0.08, ck.glow("Star", "gold", 2.2), parent=rig, segments=16)
    ANIM["crown"] = crown
    return rig


def podium():
    kit.use_collection("Podium")
    steps = [(0.0, 0.85, M["gold"], "1"), (0.95, 0.55, M["white"], "2"), (-0.95, 0.38, M["red"], "3")]
    tops = {}
    for x, h, mat, num in steps:
        px, py = x, 0.35
        kit.box(f"Podium_{num}", (px, py, h / 2), (0.92, 0.85, h), M["white"] if num != "1" else M["paper"], bevel=0.05, segments=3)
        kit.box(f"Podium_{num}_Top", (px, py, h + 0.015), (0.92, 0.85, 0.03), mat, bevel=0.012)
        ck.label(f"Podium_{num}_Num", num, (px, py + 0.43, h / 2), 0.36, M["ink"] if num != "3" else M["red"], depth=0.025)
        tops[num] = (px, py, h + 0.03)
    return tops


def flask(name, x, y, liquid, scale=1.0, tall=False):
    glass = kit.material("M_Glass", "#DCE8EE", 0.15, 0.6)
    s = scale
    if tall:  # 시험관 모양
        kit.cylinder(f"{name}_Tube", (x, y, 0.4 * s), 0.12 * s, 0.8 * s, glass, bevel=0.03, vertices=32)
        kit.cylinder(f"{name}_Liquid", (x, y, 0.27 * s), 0.125 * s, 0.45 * s, liquid, bevel=0.03, vertices=32)
        top = 0.8 * s
        r = 0.08 * s
    else:  # 둥근 플라스크
        ck.sphere(f"{name}_Bulb", (x, y, 0.32 * s), 0.32 * s, glass)
        ck.sphere(f"{name}_Liquid", (x, y, 0.27 * s), 0.3 * s, liquid, scale=(1.08, 1.08, 0.8))
        kit.cylinder(f"{name}_Neck", (x, y, 0.75 * s), 0.09 * s, 0.4 * s, glass, bevel=0.02, vertices=24)
        kit.cylinder(f"{name}_Lip", (x, y, 0.96 * s), 0.12 * s, 0.05 * s, glass, bevel=0.015, vertices=24)
        top = 0.96 * s
        r = 0.06 * s
    return top, r


def lab_bench(x, y):
    kit.use_collection("Bench")
    kit.box("Bench_Top", (x, y, 0.62), (1.5, 1.1, 0.1), M["white"], bevel=0.04)
    for sx in (-1, 1):
        for sy in (-1, 1):
            kit.box(f"Bench_Leg{sx}{sy}", (x + sx * 0.62, y + sy * 0.42, 0.3), (0.09, 0.09, 0.6), M["ink"], bevel=0.02)
    red, gold = ck.glow("LiquidRed", "red", 0.9), ck.glow("LiquidGold", "gold", 0.9)
    bubble_mat = kit.material("M_Bubble", "#F6F4EE", 0.2, 0.5, emission="#F6F4EE", strength=0.4)
    items = [(x + 0.35, y - 0.15, red, 1.0, False), (x - 0.35, y - 0.2, gold, 0.95, True), (x - 0.15, y + 0.3, gold, 0.6, False), (x + 0.45, y + 0.35, red, 0.85, True)]
    for k, (fx, fy, liquid, s, tall) in enumerate(items):
        bpy.context.view_layer.update()
        top, r = flask(f"Flask{k}", 0, 0, liquid, s, tall)
        # flask() 는 원점 기준으로 만들었으니 실험대 위로 옮긴다
        for obj in [o for o in bpy.data.objects if o.name.startswith(f"Flask{k}_")]:
            obj.location = (obj.location.x + fx, obj.location.y + fy, obj.location.z + 0.67)
        if k < 2:
            for i in range(3):
                b = ck.sphere(f"Bubble{k}_{i}", (0, 0, 0), 0.045 * (1 + 0.3 * (i % 2)), bubble_mat, segments=12)
                ANIM["bubbles"].append((b, (fx, fy, 0.67 + top), r, i, k))


def papers(x, y):
    kit.use_collection("Props")
    for k in range(6):
        p = kit.box(f"Paper{k}", (x + 0.03 * math.sin(k * 1.9), y + 0.03 * math.cos(k * 2.7), 0.03 + k * 0.055), (0.75, 0.95, 0.05), M["paper"] if k % 2 else M["white"], bevel=0.01)
        p.rotation_euler.z = math.radians(-12 + 7 * math.sin(k * 1.3))
    top = 0.03 + 5 * 0.055 + 0.03
    for k in range(4):
        kit.box(f"Paper_Ln{k}", (x, y + 0.28 - k * 0.14, top), (0.5 if k else 0.35, 0.04, 0.005), M["red"] if k == 0 else M["ink"], bevel=0).rotation_euler.z = math.radians(-12 + 7 * math.sin(5 * 1.3))


def build_characters(tops):
    walkers = []
    for i, (n, mat, carry) in enumerate((("Flask", M["white"], "flask"), ("Doc", M["blue"], "doc"))):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / 2, SIZE, center=(0.0, 2.2), radii=(2.4, 0.62)))
    hoppers = []
    for num, mat, carry, size in (("1", M["gold"], "trophy", 0.8), ("2", M["white"], None, 0.68), ("3", M["red"], None, 0.68)):
        rig, body, feet = ck.chibi(f"Winner{num}", mat, carry)
        rig.scale = (SIZE * size,) * 3
        rig.location = tops[num]
        rig.rotation_euler.z = math.radians(15)
        hoppers.append((body, feet, {"1": 0.0, "2": 1.1, "3": 2.0}[num], {"1": 0.07, "2": 0.04, "3": 0.04}[num]))
    return walkers, hoppers


def animate(cam_rig, walkers, hoppers):
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t  # 4초 박자 (깜빡임·흔들림은 4초에 정수 번)
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        for body, feet, phase, height in hoppers:
            ck.hop(f, T, body, feet, hops=8, height=height, phase=phase)
        for bar, height, phase in ANIM["bars"]:
            h = height * (0.92 + 0.08 * math.sin(2 * math.pi * 2 * T + phase))
            bar.scale.z = h
            bar.keyframe_insert("scale", index=2, frame=f)
            if bar.name.endswith("3"):  # 1등 막대 위 별이 막대를 따라간다
                ANIM["crown"].location.z = bar.location.z + h + 0.14
                ANIM["crown"].keyframe_insert("location", index=2, frame=f)
        for b, (bx, by, bz), r, i, k in ANIM["bubbles"]:
            u = (i / 3 + T * 2) % 1.0  # 4초에 두 번 올라온다
            b.location = (bx + r * 0.5 * math.sin(2 * math.pi * (u * 2 + k)), by, bz - 0.1 + 0.75 * u)
            b.keyframe_insert("location", frame=f)
            s = math.sin(math.pi * u) ** 0.5  # 입구에서 커지고 위에서 사라진다
            b.scale = (s, s, s)
            b.keyframe_insert("scale", frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    scoreboard()
    tops = podium()
    lab_bench(2.35, -0.35)
    papers(-2.45, -0.3)
    walkers, hoppers = build_characters(tops)
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers, hoppers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("lab_world", {
        "board": ([o for o in obj if o.name.startswith("Board")], "object", "막대 4개가 오르내리는 점수판, 빨간 막대가 1등 (벤치마크 점수)"),
        "podium": ([o for o in obj if o.name.startswith("Podium_")], "object", "1·2·3등 시상대 (순위·경쟁 모델)"),
        "bench": ([o for o in obj if o.name.startswith(("Bench_", "Flask"))], "object", "실험대 위 플라스크들, 액체에서 기포가 오른다 (연구·학습·실험)"),
        "papers": ([o for o in obj if o.name.startswith("Paper")], "object", "쌓인 논문 더미 (논문·연구 결과)"),
        "white_flask": (walkers[0].rig, "character", "흰 꼬마: 플라스크를 들고 걷는다 (연구자·실험)"),
        "blue": (walkers[1].rig, "character", "파란 꼬마: 문서를 들고 걷는다 (논문·보고서)"),
        "yellow": (obj["Winner1_Rig"], "character", "노란 꼬마: 1등 단상에서 트로피를 들고 통통 (1위 모델)"),
        "white_second": (obj["Winner2_Rig"], "character", "흰 꼬마: 2등 단상에서 통통 (2위·경쟁 모델)"),
        "red": (obj["Winner3_Rig"], "character", "빨간 꼬마: 3등 단상에서 통통 (3위·뒤처진 모델)"),
    }, FRAMES, "lab3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("lab_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("lab_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
