"""9:16 '책상 위 꼬마 에이전트들' 장면.

둥근 책상판 위 거대한 노트북 앞을 짜리몽땅한 꼬마들이 종종걸음으로 돈다.
- 걷는 꼬마 4명: 토큰 동전 / 코드 블록 / 문서 / 빈손 (닫힌 길을 따라 돌고, 4초 뒤 정확히 다음 꼬마 자리로 → 끊김 없는 루프)
- 키보드 위에서 통통 뛰며 타이핑하는 꼬마 1명
- 화면 위 모서리에 걸터앉아 다리 흔드는 꼬마 1명
- 금색 토큰 탑, 빨간 머그, 화분, 포스트잇
AI 에이전트 / 코딩 도구 / 토큰·비용 뉴스 공용 배경으로 쓴다.

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/desk_world.py
    blender -b -P assets3d/scripts/desk_world.py -- --still-only
출력: video/public/assets3d/desk_world.png, desk_world_loop.webm (1080x1920, 투명 배경)
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import iso_kit as kit  # noqa: E402

FRAMES = 120  # 4초 루프
STEPS = 12  # 루프 동안 걸음 수 (정수여야 끊김 없음) → 초당 3걸음, 종종걸음
SIZE = 2.1  # 꼬마 크기 배율 (장면의 주인공이 되게 크게)
BASE_TOP = 0.22  # 노트북 본체 윗면 높이
HINGE_Y = -1.75
SCREEN_H, SCREEN_TILT = 2.25, 14
DISC_C, DISC_R = (0.0, 0.5), 3.9

M = {}
WALKERS, HOPPERS, SITTERS, BLINKS = [], [], [], []


def mats():
    m = kit.material
    M.update(
        disc=m("M_Disc", "#EAE5D9", 0.65, 0.25),
        discSide=m("M_DiscSide", "ink", 0.55, 0.25),
        lap=m("M_Laptop", "#3A3833", 0.42, 0.45),
        lapDark=m("M_LapDark", "inkDeep", 0.5, 0.3),
        key=m("M_Key", "white", 0.5, 0.3),
        white=m("M_White", "white", 0.45, 0.3),
        ink=m("M_Ink", "ink", 0.5, 0.3),
        red=m("M_Red", "red", 0.42, 0.4),
        gold=m("M_Gold", "gold", 0.32, 0.6),
        blue=m("M_Blue", "screen", 0.5, 0.3),
        sage=m("M_Sage", "sage", 0.7, 0.2),
        sageDark=m("M_SageDark", "sageDark", 0.7, 0.2),
        paper=m("M_Paper", "paper", 0.6, 0.2),
        blush=m("M_Blush", "#F3A497", 0.6, 0.2),
        eye=m("M_Eye", "#16150F", 0.25, 0.6),
        screenBg=m("M_ScreenBg", "screenBg", 0.3, 0.3, emission="screenBg", strength=0.7),
        noteGold=m("M_NoteGold", "#FFD47A", 0.7, 0.1),
        noteRed=m("M_NoteRed", "#F28B7E", 0.7, 0.1),
    )


def glow(name, color, strength=1.2):
    return kit.material(f"M_Glow_{name}", color, 0.3, 0.3, emission=color, strength=strength)


def sphere(name, center, radius, mat, scale=(1, 1, 1), parent=None, segments=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=segments // 2, radius=radius, location=center)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    if parent is not None:
        obj.parent = parent
    return obj


# ---------------------------------------------------------------- 꼬마
def chibi(name, body_mat, carry=None, sprout=True):
    """짜리몽땅 꼬마: 큰 달걀 몸(=머리) + 쪼꼬만 발 + 콩알 팔. 앞은 로컬 +y.
    rig(원점 발바닥) 아래에 몸 묶음(body)과 발 2개를 둔다."""
    kit.use_collection("Characters")
    rig = kit.empty(f"{name}_Rig")
    body = kit.empty(f"{name}_Body", parent=rig)
    sphere(f"{name}_Egg", (0, 0, 0.27), 0.22, body_mat, scale=(1, 0.92, 1.0), parent=body)
    # 얼굴: 까만 눈 + 하이라이트 + 볼터치
    for sx in (-1, 1):
        sphere(f"{name}_Eye{sx}", (sx * 0.075, 0.185, 0.3), 0.03, M["eye"], scale=(1, 0.6, 1.25), parent=body, segments=16)
        sphere(f"{name}_Hi{sx}", (sx * 0.075 + 0.01, 0.2, 0.315), 0.009, M["white"], parent=body, segments=12)
        sphere(f"{name}_Blush{sx}", (sx * 0.13, 0.165, 0.245), 0.03, M["blush"], scale=(1, 0.4, 0.6), parent=body, segments=16)
    sphere(f"{name}_Mouth", (0, 0.2, 0.25), 0.012, M["eye"], scale=(1.4, 0.6, 0.8), parent=body, segments=12)
    # 콩알 팔
    arms = []
    for sx in (-1, 1):
        arms.append(sphere(f"{name}_Arm{sx}", (sx * 0.215, 0.03, 0.2), 0.05, body_mat, scale=(0.8, 0.9, 1.1), parent=body, segments=16))
    # 머리 새싹
    if sprout:
        kit.cylinder(f"{name}_Stem", (0, 0, 0.5), 0.008, 0.07, M["sageDark"], bevel=0, vertices=8, parent=body)
        for sx in (-1, 1):
            leaf = sphere(f"{name}_Leaf{sx}", (sx * 0.035, 0, 0.54), 0.035, M["sage"], scale=(1.3, 0.45, 0.6), parent=body, segments=12)
            leaf.rotation_euler.y = math.radians(-25 * sx)
    # 들고 가는 것 (머리 위로 번쩍)
    if carry == "coin":
        kit.cylinder(f"{name}_Coin", (0, 0.02, 0.66), 0.13, 0.04, M["gold"], bevel=0.012, vertices=40, axis="Y", parent=body)
        kit.cylinder(f"{name}_CoinIn", (0, 0.045, 0.66), 0.085, 0.01, M["red"], bevel=0.004, vertices=32, axis="Y", parent=body)
    elif carry == "code":
        kit.box(f"{name}_Code", (0, 0.02, 0.66), (0.26, 0.16, 0.18), M["red"], bevel=0.035)
        bpy.context.active_object.parent = body
        for k, w in enumerate((0.14, 0.09)):
            line = kit.box(f"{name}_CodeLn{k}", (-0.04 + w / 2 - 0.03, 0.105, 0.69 - k * 0.05), (w, 0.01, 0.022), M["white"], bevel=0)
            line.parent = body
    elif carry == "doc":
        doc = kit.box(f"{name}_Doc", (0, 0.02, 0.66), (0.24, 0.03, 0.3), M["paper"], bevel=0.01)
        doc.parent = body
        for k in range(3):
            ln = kit.box(f"{name}_DocLn{k}", (0, 0.04, 0.73 - k * 0.06), (0.15, 0.005, 0.018), M["ink"], bevel=0)
            ln.parent = body
    if carry:
        for a, sx in zip(arms, (-1, 1)):  # 두 팔 들기
            a.location = (sx * 0.17, 0.03, 0.47)
    # 쪼꼬만 발
    feet = [sphere(f"{name}_Foot{sx}", (sx * 0.085, 0.02, 0.03), 0.06, M["ink"], scale=(0.9, 1.3, 0.55), parent=rig, segments=16) for sx in (-1, 1)]
    return rig, body, feet


# ---------------------------------------------------------------- 소품
def disc():
    kit.use_collection("Desk")
    kit.cylinder("Disc_Top", (DISC_C[0], DISC_C[1], -0.04), DISC_R, 0.08, M["disc"], bevel=0.03, vertices=128)
    kit.cylinder("Disc_Side", (DISC_C[0], DISC_C[1], -0.3), DISC_R - 0.02, 0.45, M["discSide"], bevel=0.04, vertices=128)


def laptop():
    kit.use_collection("Laptop")
    W, D = 3.5, 2.3
    kit.box("Lap_Base", (0, HINGE_Y + D / 2, BASE_TOP / 2), (W, D, BASE_TOP), M["lap"], bevel=0.06, segments=4)
    kit.box("Lap_Deck", (0, HINGE_Y + D / 2 + 0.05, BASE_TOP - 0.004), (W - 0.2, D - 0.25, 0.01), M["lapDark"], bevel=0.02)
    # 키캡
    rows, cols = 4, 12
    kx0, ky0 = -1.5, HINGE_Y + 0.35
    for r in range(rows):
        for c in range(cols):
            kit.box(f"Key_{r}_{c}", (kx0 + c * 0.272 + 0.12, ky0 + r * 0.27, BASE_TOP + 0.02), (0.22, 0.22, 0.05), M["key"], bevel=0.025, segments=2)
    kit.box("Key_Space", (0, ky0 + 4 * 0.27, BASE_TOP + 0.02), (1.5, 0.22, 0.05), M["key"], bevel=0.025, segments=2)
    kit.box("Lap_Pad", (0, HINGE_Y + D - 0.38, BASE_TOP + 0.002), (0.9, 0.5, 0.01), M["lapDark"], bevel=0.02)

    scr = kit.empty("Lap_ScreenRig")
    scr.location = (0, HINGE_Y, BASE_TOP)
    scr.rotation_euler.x = math.radians(SCREEN_TILT)
    kit.box("Lap_Lid", (0, -0.05, SCREEN_H / 2), (W, 0.1, SCREEN_H), M["lap"], bevel=0.06, segments=4, parent=scr)
    kit.box("Lap_Display", (0, 0.005, SCREEN_H / 2 + 0.04), (W - 0.3, 0.01, SCREEN_H - 0.32), M["screenBg"], bevel=0.01, parent=scr)
    # 화면 내용: 왼쪽 코드 줄 + 오른쪽 말풍선 카드 + 아래 진행 막대
    white, gold, red, blue = glow("W", "paper", 0.9), glow("G", "gold", 1.2), glow("R", "red", 1.2), glow("B", "screen", 1.0)
    lines = [(0.55, blue), (0.9, white), (0.7, white), (0.35, gold), (0.8, white), (0.5, red), (0.65, white)]
    for k, (w, mat) in enumerate(lines):
        indent = 0.12 if k in (2, 3, 5) else 0.0
        kit.box(f"Scr_Ln{k}", (-1.45 + indent + w / 2, 0.012, SCREEN_H - 0.42 - k * 0.2), (w, 0.004, 0.07), mat, bevel=0, parent=scr)
    kit.box("Scr_Card", (0.75, 0.012, SCREEN_H - 0.85), (1.15, 0.004, 0.95), glow("Card", "#2A3644", 1.0), bevel=0.02, parent=scr)
    for k, (w, mat) in enumerate(((0.8, white), (0.6, white), (0.4, gold))):
        kit.box(f"Scr_CardLn{k}", (0.3 + w / 2, 0.016, SCREEN_H - 0.55 - k * 0.18), (w, 0.004, 0.06), mat, bevel=0, parent=scr)
    cursor_mat = glow("Cursor", "gold", 1.5)
    kit.box("Scr_Cursor", (-0.78, 0.014, SCREEN_H - 0.42 - 6 * 0.2), (0.05, 0.004, 0.1), cursor_mat, bevel=0, parent=scr)
    BLINKS.append((cursor_mat, 4, 0.0))
    # 포스트잇 (화면 테두리)
    for k, (x, z, mat, rot) in enumerate(((1.55, SCREEN_H - 0.25, M["noteGold"], 8), (-1.62, 0.5, M["noteRed"], -6))):
        n = kit.box(f"Note{k}", (x, 0.03, z), (0.36, 0.01, 0.36), mat, bevel=0.004, parent=scr)
        n.rotation_euler.y = math.radians(rot)
    return scr


def coin_tower(x, y):
    kit.use_collection("Props")
    for k in range(7):
        c = kit.cylinder(f"Tower_{k}", (x + 0.03 * math.sin(k * 1.7), y + 0.03 * math.cos(k * 2.3), 0.07 + k * 0.125), 0.36, 0.11, M["gold"], bevel=0.025, vertices=48)
        c.rotation_euler.z = k * 0.4
    kit.cylinder("Tower_TopMark", (x, y, 0.07 + 6 * 0.125 + 0.06), 0.22, 0.01, M["red"], bevel=0.003, vertices=40)
    for k, (dx, dy) in enumerate(((0.65, 0.35), (0.45, 0.75))):
        coin = kit.cylinder(f"Loose_{k}", (x + dx, y + dy, 0.05), 0.2, 0.08, M["gold"], bevel=0.02, vertices=40)
        coin.rotation_euler = (math.radians(8), 0, k)


def mug(x, y):
    kit.use_collection("Props")
    kit.cylinder("Mug", (x, y, 0.5), 0.45, 1.0, M["red"], bevel=0.04, vertices=64)
    kit.cylinder("Mug_Coffee", (x, y, 0.94), 0.4, 0.04, M["#3A2A20"] if "#3A2A20" in M else kit.material("M_Coffee", "#3A2A20", 0.2, 0.6), bevel=0, vertices=64)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.27, minor_radius=0.07, location=(x - 0.45, y, 0.5), rotation=(math.radians(90), 0, 0))
    h = bpy.context.active_object
    h.name = "Mug_Handle"
    h.data.materials.append(M["red"])
    for p in h.data.polygons:
        p.use_smooth = True


def plant(x, y):
    kit.use_collection("Props")
    kit.cylinder("Plant_Pot", (x, y, 0.22), 0.26, 0.44, M["white"], bevel=0.03, vertices=32)
    kit.cylinder("Plant_Soil", (x, y, 0.43), 0.23, 0.02, M["ink"], bevel=0, vertices=32)
    for k, (dx, dy, z, r, mat) in enumerate(((0, 0, 0.72, 0.3, M["sage"]), (0.15, -0.1, 1.0, 0.22, M["sageDark"]), (-0.12, 0.08, 1.15, 0.17, M["sage"]))):
        kit.ico(f"Plant_Leaf{k}", (x + dx, y + dy, z), r, mat)


# ---------------------------------------------------------------- 길과 애니메이션
PATH_C, PATH_R = (0.0, 1.75), (2.6, 1.05)


def path_point(u):
    a = 2 * math.pi * u
    x = PATH_C[0] + PATH_R[0] * math.cos(a)
    y = PATH_C[1] + PATH_R[1] * math.sin(a)
    dx = -PATH_R[0] * math.sin(a)
    dy = PATH_R[1] * math.cos(a)
    return x, y, math.atan2(dy, dx) - math.pi / 2


def build_characters():
    specs = [("Red", M["red"], "coin"), ("Paper", M["white"], "code"), ("Gold", M["gold"], "doc"), ("Blue", M["blue"], None)]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        WALKERS.append((rig, body, feet, i / len(specs)))
    # 키보드 위 타자 꼬마 (화면을 보고 = -y 방향)
    rig, body, feet = chibi("Typer", M["white"], None)
    rig.scale = (SIZE * 0.8,) * 3
    rig.location = (-0.6, HINGE_Y + 1.05, BASE_TOP + 0.045)
    rig.rotation_euler.z = math.radians(25)  # 카메라 쪽을 보고 키보드 위에서 통통
    HOPPERS.append((rig, body, feet))
    # 화면 위에 걸터앉은 꼬마 (+y 를 봄, 다리 흔들기)
    rig, body, feet = chibi("Sitter", M["gold"], None)
    rig.scale = (SIZE * 0.8,) * 3
    t = math.radians(SCREEN_TILT)
    top_y = HINGE_Y - SCREEN_H * math.sin(t) - 0.05 * math.cos(t)
    top_z = BASE_TOP + SCREEN_H * math.cos(t) + 0.04
    rig.location = (0.95, top_y + 0.02, top_z - 0.02)
    for f, sx in zip(feet, (-1, 1)):
        f.location = (sx * 0.085, 0.17, 0.0)
        f.rotation_euler.x = math.radians(-50)
    SITTERS.append((rig, body, feet))


def animate(cam_rig):
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)

        step = STEPS * t  # 걸음 진행
        for rig, body, feet, offset in WALKERS:
            u = offset + t / len(WALKERS)  # 루프 끝에 다음 꼬마 자리
            x, y, heading = path_point(u)
            ph = math.pi * step + offset * 7
            rig.location = (x, y, SIZE * 0.035 * abs(math.sin(ph)))
            rig.rotation_euler = (0, math.radians(7) * math.sin(ph), heading)
            rig.keyframe_insert("location", frame=f)
            rig.keyframe_insert("rotation_euler", frame=f)
            for k, foot in enumerate(feet):
                s = math.sin(ph + k * math.pi)
                foot.location.z = 0.03 + 0.045 * max(0.0, s)
                foot.location.y = 0.02 + 0.06 * math.cos(ph + k * math.pi)
                foot.keyframe_insert("location", frame=f)
            body.location.z = 0.012 * math.sin(2 * ph)  # 말랑말랑
            body.scale = (1 + 0.03 * math.sin(2 * ph), 1, 1 - 0.03 * math.sin(2 * ph))
            body.keyframe_insert("location", frame=f)
            body.keyframe_insert("scale", frame=f)

        for rig, body, feet in HOPPERS:  # 통통 타자
            hop = abs(math.sin(math.pi * 16 * t))
            body.location.z = 0.07 * hop
            body.scale = (1 + 0.06 * (1 - hop), 1, 1 - 0.06 * (1 - hop))
            body.keyframe_insert("location", frame=f)
            body.keyframe_insert("scale", frame=f)
            for k, foot in enumerate(feet):
                foot.location.z = 0.03 + 0.05 * hop * (1 if k == (int(16 * t) % 2) else 0.4)
                foot.keyframe_insert("location", frame=f)

        for rig, body, feet in SITTERS:  # 다리 달랑달랑 + 갸웃
            body.rotation_euler.y = math.radians(8) * math.sin(2 * math.pi * 2 * t)
            body.keyframe_insert("rotation_euler", frame=f)
            for k, foot in enumerate(feet):
                foot.rotation_euler.x = math.radians(-50 + 25 * math.sin(2 * math.pi * 4 * t + k * math.pi))
                foot.keyframe_insert("rotation_euler", frame=f)

        for mat, cycles, phase in BLINKS:
            inp = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
            inp.default_value = 1.6 if math.sin(2 * math.pi * cycles * t + phase) > 0 else 0.0
            inp.keyframe_insert("default_value", frame=f)
    for action in bpy.data.actions:
        for fc in getattr(action, "fcurves", []):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    bpy.context.scene.eevee.taa_render_samples = 64
    mats()
    disc()
    laptop()
    coin_tower(2.55, -0.9)
    mug(-2.7, -0.55)
    plant(-2.3, -1.7)  # 꼬마들 길(타원)과 겹치지 않는 머그 뒤쪽
    build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    targets = [o for o in bpy.data.objects if o.type == "MESH" and o.users_collection[0].name in ("Desk", "Laptop", "Props")]
    cam, rig = kit.vertical_camera(targets, lens=50, elevation=38, azimuth=68, margin=0.8)
    # 위는 제목·UI 카드, 아래는 자막 자리. 장면을 살짝 아래로
    cam.data.shift_y = 0.05
    animate(rig)

    print("STILL", kit.render_still("desk_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("desk_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
