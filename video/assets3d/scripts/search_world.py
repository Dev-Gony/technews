"""9:16 '큰 돋보기와 검색창, 결과 카드' 장면 (검색·검색엔진·RAG·색인·추천 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 뒤: 공중에 뜬 큰 검색창(흰 알약 모양 + 빨간 검색 버튼). 입력 막대가 4초에 한 번 쳐진다
- 가운데: 바닥에 깔린 결과 카드 5장 위로 금색 테 돋보기가 미끄러지며 훑고,
  돋보기 밑 카드가 빨갛게 골라져 살짝 떠오른다
- 오른쪽 앞: 쌓인 책(색인), 맨 위 책갈피
- 앞: 꼬마들이 문서를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/search_world.py
    blender -b -P assets3d/scripts/search_world.py -- --still-only
출력: video/public/assets3d/search_world.png, search_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"cards": []}

N_CARD = 5


def search_bar():
    kit.use_collection("Bar")
    base = kit.empty("BarRig")
    base.location = (0.0, -1.75, 0)
    base.rotation_euler.z = math.radians(-20)
    base.scale = (1.2,) * 3
    rig = kit.empty("Bar", parent=base)
    z = 1.6
    kit.box("Bar_Pill", (0, 0, z), (3.2, 0.2, 0.55), M["white"], bevel=0.27, segments=8, parent=rig)
    kit.box("Bar_Edge", (0, -0.03, z), (3.28, 0.16, 0.63), M["ink"], bevel=0.31, segments=8, parent=rig)
    kit.cylinder("Bar_Btn", (-1.3, 0.1, z), 0.24, 0.08, M["red"], bevel=0.03, vertices=40, axis="Y", parent=rig)
    ck.torus("Bar_BtnGlass", (-1.3, 0.15, z + 0.03), 0.08, 0.022, M["white"], rotation=(math.pi / 2, 0, 0), parent=rig)
    h = kit.box("Bar_BtnHandle", (-1.235, 0.15, z - 0.04), (0.1, 0.02, 0.03), M["white"], bevel=0, parent=rig)
    h.rotation_euler.y = math.radians(45)
    typed = kit.box("Bar_Typed", (0, 0.11, z), (1.0, 0.012, 0.11), M["ink"], bevel=0, parent=rig)
    for v in typed.data.vertices:
        v.co.x -= 0.5
    typed.location.x = 1.3
    caret = kit.box("Bar_Caret", (0, 0.11, z), (0.03, 0.012, 0.26), M["red"], bevel=0, parent=rig)
    ANIM["typed"], ANIM["caret"], ANIM["bar"] = typed, caret, rig
    # 기둥 (바닥에서 받친다)
    kit.box("Bar_Post", (0, -0.1, z / 2 - 0.15), (0.12, 0.1, z - 0.3), M["ink"], bevel=0.02, parent=base)
    kit.cylinder("Bar_Foot", (0, -0.1, 0.05), 0.4, 0.1, M["ink"], bevel=0.03, vertices=40, parent=base)


def results():
    kit.use_collection("Results")
    rig = kit.empty("Results")
    rig.location = (0.05, -0.35, 0)
    rig.rotation_euler.z = math.radians(-20)
    rig.scale = (1.2,) * 3
    colors = ["blue", "gold", "paper", "sage", "white"]
    for k in range(N_CARD):
        x = 1.6 - k * 0.8
        lift = kit.empty(f"CardLift{k}", parent=rig)
        lift.location = (x, 0, 0.3)
        lift.rotation_euler.x = math.radians(-38)  # 뒤쪽이 들린 카드 (카메라에서 잘 보이게)
        card = kit.empty(f"Card{k}", parent=lift)
        kit.box(f"Card{k}_Body", (0, 0, 0.05), (0.66, 0.9, 0.08), M["white"] if k % 2 else M["paper"], bevel=0.03, parent=card)
        kit.box(f"Card{k}_Img", (0, 0.2, 0.095), (0.5, 0.32, 0.01), M[colors[k]], bevel=0.01, parent=card)
        for i in range(2):
            kit.box(f"Card{k}_Ln{i}", (-0.05 * i, -0.12 - i * 0.14, 0.095), (0.48 - 0.12 * i, 0.06, 0.01), M["ink"], bevel=0, parent=card)
        hit = kit.box(f"Card{k}_Hit", (0, 0, 0.1), (0.8, 1.04, 0.012), M["red"], bevel=0.02, parent=card)
        hit.location.z = -0.035  # 카드 밑에 깔려 테두리만 보인다
        ANIM["cards"].append((card, hit, x))
    lens_rig = kit.empty("Lens", parent=rig)
    lens_rig.location = (0, 0.45, 0.95)
    tilt = kit.empty("LensTilt", parent=lens_rig)
    tilt.rotation_euler.x = math.radians(-55)  # 렌즈가 카메라 쪽 아래를 본다
    ck.torus("Lens_Rim", (0, 0, 0), 0.55, 0.075, M["gold"], parent=tilt)
    kit.cylinder("Lens_Glass", (0, 0, 0), 0.5, 0.03, kit.material("M_Lens", "#CFE3EE", 0.05, 0.9), bevel=0.01, vertices=48, parent=tilt)
    handle = kit.empty("Lens_HandleRig", parent=tilt)
    handle.rotation_euler.z = math.radians(-35)
    kit.cylinder("Lens_Neck", (0.68, 0, 0), 0.06, 0.2, M["gold"], bevel=0.01, vertices=16, axis="X", parent=handle)
    kit.cylinder("Lens_Handle", (1.05, 0, 0), 0.1, 0.6, M["ink"], bevel=0.04, vertices=24, axis="X", parent=handle)
    ANIM["lens"] = lens_rig


def books(x, y):
    kit.use_collection("Books")
    rig = kit.empty("Books")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-10)
    specs = [(0.95, 0.7, 0.2, "red", 4), (0.85, 0.66, 0.18, "blue", -8), (0.9, 0.62, 0.22, "gold", 6), (0.8, 0.6, 0.16, "sage", -3)]
    z = 0.0
    for k, (w, d, h, color, rot) in enumerate(specs):
        b = kit.empty(f"Book{k}", parent=rig)
        b.location = (0, 0, z)
        b.rotation_euler.z = math.radians(rot)
        kit.box(f"Book{k}_Cover", (0, 0, h / 2), (w, d, h), M[color], bevel=0.025, parent=b)
        kit.box(f"Book{k}_Pages", (0.02, 0.0, h / 2), (w - 0.04, d + 0.005, h - 0.05), M["white"], bevel=0.005, parent=b)
        z += h
    mark = kit.box("Bookmark", (0.2, 0.36, z - 0.12), (0.1, 0.02, 0.3), M["red"], bevel=0.005, parent=rig)
    mark.rotation_euler.x = math.radians(8)


def build_characters():
    walkers = []
    specs = [("Doc", M["white"], "doc"), ("Gold", M["gold"], None), ("Red", M["red"], "doc")]
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
        ph = T % 1.0
        typed = ANIM["typed"]
        u = min(ph / 0.45, 1.0) if ph < 0.9 else 0.0
        typed.scale.x = max(0.001, 2.1 * u)
        typed.keyframe_insert("scale", index=0, frame=f)
        ANIM["caret"].location.x = 1.3 - 2.1 * u - 0.05
        ANIM["caret"].keyframe_insert("location", index=0, frame=f)
        ANIM["bar"].location.z = 0.04 * math.sin(2 * math.pi * T)
        ANIM["bar"].keyframe_insert("location", index=2, frame=f)
        # 돋보기: 카드 줄 위를 좌우로 한 번 왕복 (4초), 밑에 온 카드가 골라진다
        lx = 1.6 * math.cos(2 * math.pi * T)
        lens = ANIM["lens"]
        lens.location.x = lx
        lens.location.z = 0.95 + 0.06 * math.sin(2 * math.pi * 4 * T)
        lens.keyframe_insert("location", frame=f)
        for card, hit, x in ANIM["cards"]:
            near = max(0.0, 1 - abs(lx - x) / 0.45)
            card.location.z = 0.12 * near
            card.keyframe_insert("location", index=2, frame=f)
            ck.show(hit, f, near > 0.35)  # 돋보기 밑 카드만 빨간 테두리
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    search_bar()
    results()
    books(-2.35, 0.55)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)

    print("STILL", kit.render_still("search_world", resolution=1080, height=1920, frame=20))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("search_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
