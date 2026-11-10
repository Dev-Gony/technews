"""9:16 '깃 가지 그래프와 오픈소스 꾸러미' 장면 (오픈소스·깃허브·Git·라이브러리 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 뒤: 공중에 선 깃 그래프. 먹색 본줄기에서 빨간 가지가 위로, 금색 가지가 아래로 갈라졌다 다시 합쳐진다.
  빛 알갱이가 가지를 따라 흐르고, 마지막(합쳐진) 커밋 위에 빨간 깃발이 펄럭인다
- 왼쪽 앞: 뚜껑이 열린 꾸러미 상자(패키지). 코드 블록 하나가 통통 튀어 오른다
- 오른쪽 앞: 받침 위에서 천천히 도는 금색 별(스타), 옆에서 꼬마가 통통
- 앞: 꼬마 3명이 코드 / 문서를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/repo_world.py
    blender -b -P assets3d/scripts/repo_world.py -- --still-only
출력: video/public/assets3d/repo_world.png, repo_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"packets": []}

GY = -1.45  # 그래프가 서는 깊이
MAIN_Z = 1.25


def git_graph():
    """그래프는 rig(원판 뒤쪽) 기준 xz 평면에 그리고, rig 를 돌려 카메라를 정면으로 보게 한다."""
    kit.use_collection("Graph")
    rig = kit.empty("Graph")
    rig.location = (0.1, GY, 0)
    rig.rotation_euler.z = math.radians(-20)
    main = [(2.05, 0, MAIN_Z), (-2.05, 0, MAIN_Z)]
    red = [(1.05, 0, MAIN_Z), (0.62, 0, 2.15), (-0.32, 0, 2.15), (-0.75, 0, MAIN_Z)]
    gold = [(1.65, 0, MAIN_Z), (1.22, 0, 0.5), (-1.22, 0, 0.5), (-1.65, 0, MAIN_Z)]
    for sx in (-1, 1):  # 본줄기를 받치는 기둥
        kit.cylinder(f"Graph_Post{sx}", (sx * 2.12, 0, MAIN_Z / 2), 0.08, MAIN_Z, M["ink"], bevel=0.02, vertices=24, parent=rig)
        kit.cylinder(f"Graph_Foot{sx}", (sx * 2.12, 0, 0.04), 0.28, 0.08, M["ink"], bevel=0.02, vertices=32, parent=rig)
    ck.tube("Graph_Main", main, 0.085, M["ink"], parent=rig)
    ck.tube("Graph_Red", red, 0.08, M["red"], parent=rig)
    ck.tube("Graph_Gold", gold, 0.08, M["gold"], parent=rig)
    commits = [(x, MAIN_Z, M["white"], 0.21) for x in (1.65, 1.05, 0.15)]
    commits += [(x, 2.15, M["red"], 0.19) for x in (0.38, -0.1)]
    commits += [(x, 0.5, M["gold"], 0.19) for x in (0.7, -0.05, -0.8)]
    for k, (x, z, mat, r) in enumerate(commits):
        ck.sphere(f"Commit{k}", (x, 0, z), r, mat, parent=rig)
        ck.torus(f"CommitRing{k}", (x, 0, z), r * 0.97, 0.03, M["ink"], rotation=(math.pi / 2, 0, 0), parent=rig)
    # 두 가지가 합쳐진 커밋 (빨강) + 마지막 커밋 (크게, 금색) + 빨간 깃발
    ck.sphere("Commit_Merge", (-0.75, 0, MAIN_Z), 0.21, M["white"], parent=rig)
    ck.torus("Commit_MergeRing", (-0.75, 0, MAIN_Z), 0.2, 0.03, M["ink"], rotation=(math.pi / 2, 0, 0), parent=rig)
    head = (-1.65, 0, MAIN_Z)
    ck.sphere("Commit_Head", head, 0.29, M["gold"], parent=rig)
    ck.torus("Commit_HeadRing", head, 0.29, 0.04, M["ink"], rotation=(math.pi / 2, 0, 0), parent=rig)
    kit.cylinder("Flag_Pole", (head[0], 0, MAIN_Z + 0.65), 0.03, 0.8, M["ink"], bevel=0.005, vertices=12, parent=rig)
    flag = kit.empty("Flag", parent=rig)
    flag.location = (head[0], 0, MAIN_Z + 0.92)
    ck.extruded("Flag_Cloth", [(0, 0.18), (0, -0.18), (-0.5, -0.05), (-0.5, 0.22)], 0.03, M["red"], center=(0, 0, 0), bevel=0.008, parent=flag)
    ANIM["flag"] = flag
    # 가지를 따라 흐르는 빛 알갱이 (4초에 한 번 끝까지)
    glow = {"main": ck.glow("PacketWhite", "white", 1.6), "red": ck.glow("PacketRed", "red", 3.0), "gold": ck.glow("PacketGold", "gold", 3.0)}
    for path, key, n in ((main, "main", 3), (red, "red", 2), (gold, "gold", 2)):
        for i in range(n):
            p = ck.sphere(f"Packet_{key}{i}", (0, 0, 0), 0.09, glow[key], parent=rig, segments=16)
            ANIM["packets"].append((p, path, i, n))


def package(x, y):
    kit.use_collection("Package")
    card = kit.material("M_Card", "wood", 0.7, 0.2)
    card_in = kit.material("M_CardIn", "#B48D66", 0.75, 0.2)
    w, d, h = 1.15, 0.95, 0.62
    kit.box("Box_Bottom", (x, y, 0.04), (w, d, 0.08), card_in, bevel=0.02)
    for sx in (-1, 1):
        kit.box(f"Box_SideX{sx}", (x + sx * (w / 2 - 0.03), y, h / 2), (0.06, d, h), card, bevel=0.015)
        kit.box(f"Box_SideY{sx}", (x, y + sx * (d / 2 - 0.03), h / 2), (w, 0.06, h), card, bevel=0.015)
        # 바깥으로 젖혀진 뚜껑 (윗모서리를 축으로 돈다)
        hinge = kit.empty(f"Box_HingeY{sx}")
        hinge.location = (x, y + sx * (d / 2), h)
        kit.box(f"Box_FlapY{sx}", (0, sx * 0.21, 0), (w - 0.04, 0.42, 0.04), card, bevel=0.012, parent=hinge)
        hinge.rotation_euler.x = math.radians(-sx * 40)
        hinge = kit.empty(f"Box_HingeX{sx}")
        hinge.location = (x + sx * (w / 2), y, h)
        kit.box(f"Box_FlapX{sx}", (sx * 0.19, 0, 0), (0.38, d - 0.04, 0.04), card, bevel=0.012, parent=hinge)
        hinge.rotation_euler.y = math.radians(sx * 40)
    kit.box("Box_Tape", (x, y + d / 2 + 0.005, h * 0.55), (0.22, 0.012, h * 0.9), kit.material("M_Tape", "#E9D9B8", 0.5, 0.2), bevel=0)
    blocks = []
    for k, (dx, dy, mat) in enumerate(((0.22, -0.15, M["blue"]), (-0.2, -0.1, M["gold"]), (0.0, 0.18, M["red"]))):
        blk = kit.empty(f"Block{k}")
        blk.location = (x + dx, y + dy, h - 0.12)
        kit.box(f"Block{k}_Body", (0, 0, 0.18), (0.36, 0.36, 0.36), mat, bevel=0.05, parent=blk)
        for i, lw in enumerate((0.2, 0.13)):
            kit.box(f"Block{k}_Ln{i}", (-0.03 + lw / 2 - 0.08, 0.183, 0.22 - i * 0.08), (lw, 0.01, 0.035), M["white"], bevel=0, parent=blk)
        blocks.append(blk)
    ANIM["jump"] = blocks[2]
    ANIM["jump_z"] = blocks[2].location.z


def star(x, y):
    kit.use_collection("Star")
    kit.cylinder("Star_Base", (x, y, 0.09), 0.5, 0.18, M["ink"], bevel=0.04, vertices=48)
    kit.cylinder("Star_Stem", (x, y, 0.4), 0.06, 0.5, M["ink"], bevel=0.015, vertices=16)
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        r = 0.6 if i % 2 == 0 else 0.26
        pts.append((r * math.cos(a), r * math.sin(a)))
    rig = kit.empty("Star")
    rig.location = (x, y, 1.15)
    ck.extruded("Star_Body", pts, 0.2, M["gold"], center=(0, 0, 0), bevel=0.05, parent=rig)
    ANIM["star"] = rig


def build_characters():
    walkers = []
    specs = [("Code", M["white"], "code"), ("Doc", M["blue"], "doc"), ("Red", M["red"], None)]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.1), radii=(2.3, 0.68)))
    rig, body, feet = ck.chibi("Fan", M["gold"], None)
    rig.scale = (SIZE * 0.62,) * 3
    rig.location = (-1.35, 0.75, 0)
    rig.rotation_euler.z = math.radians(25)
    return walkers, (rig, body, feet)


def animate(cam_rig, walkers, fan):
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t  # 4초 박자
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        _, body, feet = fan
        ck.hop(f, T, body, feet, hops=8, height=0.06)
        for obj, pts, i, n in ANIM["packets"]:
            u = (i / n + T) % 1.0
            obj.location = ck.sample(pts, u)
            obj.keyframe_insert("location", frame=f)
            s = math.sin(math.pi * u) ** 0.35
            obj.scale = (s, s, s)
            obj.keyframe_insert("scale", frame=f)
        ANIM["flag"].rotation_euler.z = math.radians(12) * math.sin(2 * math.pi * 4 * T)
        ANIM["flag"].keyframe_insert("rotation_euler", index=2, frame=f)
        ANIM["star"].rotation_euler.z = 2 * math.pi * t  # 루프 동안 한 바퀴
        ANIM["star"].keyframe_insert("rotation_euler", index=2, frame=f)
        jump = ANIM["jump"]
        jump.location.z = ANIM["jump_z"] + 0.32 * abs(math.sin(math.pi * 2 * T))
        jump.rotation_euler.z = math.radians(10) * math.sin(2 * math.pi * 2 * T)
        jump.keyframe_insert("location", index=2, frame=f)
        jump.keyframe_insert("rotation_euler", index=2, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    git_graph()
    package(2.15, 0.35)
    star(-2.25, 0.25)
    walkers, fan = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers, fan)

    print("STILL", kit.render_still("repo_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("repo_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
