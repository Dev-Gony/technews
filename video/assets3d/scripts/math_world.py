"""9:16 '칠판과 도형, 컴퍼스' 장면 (수학·알고리즘·증명·계산 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 뒤: 초록 칠판. 분필 식 'x+y=1' 과 좌표축 위 곡선이 있고, 곡선 위 빨간 점이 오간다
- 왼쪽 앞: 받침 위에서 천천히 도는 도형들 (정육면체, 원뿔, 구, 고리)
- 오른쪽 앞: 컴퍼스가 한 바퀴 돌며 바닥에 금색 원을 그린다
- 둘레: + − × = 기호가 둥실 떠 있다
- 앞: 꼬마들이 문서를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/math_world.py
    blender -b -P assets3d/scripts/math_world.py -- --still-only
출력: video/public/assets3d/math_world.png, math_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"symbols": [], "solids": []}

BW, BH, BZ = 3.0, 1.75, 0.55


def curve_pts(n=24):
    """칠판 로컬 좌표의 곡선 (화면 왼쪽 +x → 오른쪽 -x 로 오르는 S 곡선)."""
    pts = []
    for i in range(n + 1):
        u = i / n
        x = 0.05 - 1.15 * u
        z = BZ + 0.3 + 1.0 * (0.5 - 0.5 * math.cos(math.pi * u))
        pts.append((x, 0.09, z))
    return pts


def board():
    kit.use_collection("Board")
    rig = kit.empty("Board")
    rig.location = (0.05, -1.6, 0)
    rig.rotation_euler.z = math.radians(-20)
    wood = kit.material("M_BoardWood", "wood", 0.6, 0.2)
    for sx in (-1, 1):
        kit.box(f"Board_Leg{sx}", (sx * (BW / 2 - 0.25), -0.05, BZ / 2), (0.1, 0.1, BZ), M["ink"], bevel=0.02, parent=rig)
        kit.box(f"Board_Foot{sx}", (sx * (BW / 2 - 0.25), -0.05, 0.03), (0.45, 0.5, 0.06), M["ink"], bevel=0.02, parent=rig)
    zc = BZ + BH / 2
    kit.box("Board_Frame", (0, 0, zc), (BW, 0.12, BH), wood, bevel=0.04, parent=rig)
    kit.box("Board_Face", (0, 0.065, zc), (BW - 0.16, 0.01, BH - 0.16), kit.material("M_Chalkboard", "#2F4A3E", 0.8, 0.1), bevel=0.01, parent=rig)
    kit.box("Board_Tray", (0, 0.12, BZ + 0.02), (BW - 0.3, 0.14, 0.04), wood, bevel=0.01, parent=rig)
    chalk = kit.material("M_Chalk", "#F2EFE6", 0.9, 0.1)
    ck.label("Board_Eq", "x+y=1", (0.75, 0.08, BZ + 1.25), 0.36, chalk, depth=0.01, parent=rig)
    # 좌표축 + 곡선
    kit.box("Board_AxisX", (-0.55, 0.08, BZ + 0.28), (1.4, 0.006, 0.025), chalk, bevel=0, parent=rig)
    kit.box("Board_AxisZ", (0.1, 0.08, BZ + 0.85), (0.025, 0.006, 1.2), chalk, bevel=0, parent=rig)
    pts = curve_pts()
    ck.tube("Board_Curve", pts, 0.022, ck.glow("Curve", "gold", 1.4), parent=rig)
    dot = ck.sphere("Board_Dot", (0, 0, 0), 0.07, ck.glow("CurveDot", "red", 2.2), parent=rig, segments=16)
    kit.box("Chalk_Piece", (-1.0, 0.13, BZ + 0.06), (0.22, 0.05, 0.05), chalk, bevel=0.015, parent=rig)
    ANIM.update(dot=dot, curve=pts)


def solids(x, y):
    kit.use_collection("Solids")
    kit.cylinder("Solid_Base", (x, y, 0.08), 0.75, 0.16, M["ink"], bevel=0.04, vertices=48)
    turn = kit.empty("Solids_Turn")
    turn.location = (x, y, 0.16)
    kit.box("Solid_Cube", (0.32, 0.0, 0.2), (0.38, 0.38, 0.38), M["red"], bevel=0.03, parent=turn)
    ck.cone("Solid_Cone", (-0.25, 0.2, 0.27), 0.22, 0.0, 0.54, M["gold"], parent=turn)
    ck.sphere("Solid_Ball", (-0.15, -0.32, 0.18), 0.18, M["blue"], parent=turn)
    ring = ck.torus("Solid_Ring", (0.05, 0.0, 0.85), 0.24, 0.07, M["white"], rotation=(math.pi / 2, 0, 0), parent=turn)
    ANIM.update(turn=turn, ring=ring)


def compass(x, y):
    kit.use_collection("Compass")
    pivot = kit.empty("Compass")
    pivot.location = (x, y, 0.0)
    r = 0.55
    trace = ck.torus("Compass_Circle", (x, y, 0.02), r, 0.025, ck.glow("CircleTrace", "gold", 1.8))
    trace.scale = (1, 1, 0.3)
    spin = kit.empty("Compass_Spin", parent=pivot)
    head = (r / 2, 0, 1.05)
    kit.cylinder("Compass_Head", head, 0.08, 0.14, M["ink"], bevel=0.02, vertices=24, axis="Y", parent=spin)
    kit.cylinder("Compass_Knob", (r / 2, 0, 1.22), 0.04, 0.2, M["red"], bevel=0.01, vertices=16, parent=spin)
    for k, foot in enumerate(((0, 0, 0.0), (r, 0, 0.0))):
        dx, dz = foot[0] - head[0], foot[2] - head[2]
        length = math.hypot(dx, dz)
        leg = kit.empty(f"Compass_LegRig{k}", parent=spin)
        leg.location = head
        leg.rotation_euler.y = math.atan2(dx, dz) + math.pi
        kit.box(f"Compass_Leg{k}", (0, 0, -length / 2), (0.05, 0.05, length), M["steel"] if k == 0 else M["gold"], bevel=0.015, parent=leg)
    ANIM.update(spin=spin)


def symbols():
    kit.use_collection("Symbols")
    specs = [("+", (1.7, -0.6, 1.6), "red"), ("-", (-1.75, -0.8, 1.9), "gold"), ("x", (-2.3, -0.3, 1.25), "blue"), ("=", (2.3, -0.1, 1.95), "white")]
    for k, (ch, pos, c) in enumerate(specs):
        rig = kit.empty(f"Sym{k}")
        rig.location = pos
        rig.rotation_euler.z = math.radians(-20)
        ck.label(f"Sym{k}_Glyph", ch, (0, 0, 0), 0.9, M[c], depth=0.08, parent=rig)
        ANIM["symbols"].append((rig, pos[2], k))


def build_characters():
    walkers = []
    specs = [("Doc", M["white"], "doc"), ("Gold", M["gold"], None), ("Blue", M["blue"], "doc")]
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
        u = 0.5 - 0.5 * math.cos(2 * math.pi * T)  # 곡선 위를 4초에 한 번 왕복
        ANIM["dot"].location = ck.sample(ANIM["curve"], u)
        ANIM["dot"].keyframe_insert("location", frame=f)
        ANIM["turn"].rotation_euler.z = 2 * math.pi * t
        ANIM["turn"].keyframe_insert("rotation_euler", index=2, frame=f)
        ANIM["ring"].rotation_euler.z = 2 * math.pi * 2 * t
        ANIM["ring"].keyframe_insert("rotation_euler", index=2, frame=f)
        ANIM["spin"].rotation_euler.z = 2 * math.pi * 3 * t  # 4초에 한 바퀴
        ANIM["spin"].keyframe_insert("rotation_euler", index=2, frame=f)
        for rig, z, k in ANIM["symbols"]:
            rig.location.z = z + 0.1 * math.sin(2 * math.pi * T + k * 1.6)
            rig.rotation_euler.y = math.radians(10) * math.sin(2 * math.pi * T + k)
            rig.keyframe_insert("location", index=2, frame=f)
            rig.keyframe_insert("rotation_euler", index=1, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    board()
    solids(2.15, 0.4)
    compass(-2.3, 0.35)
    symbols()
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("math_world", {
        "board": (obj["Board"], "object", "'x+y=1' 과 곡선이 그려진 초록 칠판 (수식·증명·알고리즘)"),
        "solids": ([obj["Solids_Turn"], obj["Solid_Base"]], "object", "받침 위에서 도는 정육면체·원뿔·구·고리 (도형·기하·구조)"),
        "compass": ([obj["Compass"], obj["Compass_Circle"]], "object", "돌며 바닥에 금색 원을 그리는 컴퍼스 (계산·정밀함·설계)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 문서를 들고 걸어 다닌다 (연구자·논문)"),
        "yellow": (walkers[1].rig, "character", "노란 꼬마: 빈손으로 걸어 다닌다 (학생·사용자)"),
        "blue": (walkers[2].rig, "character", "파란 꼬마: 문서를 들고 걸어 다닌다 (수학자·풀이)"),
    }, FRAMES, "math3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("math_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("math_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
