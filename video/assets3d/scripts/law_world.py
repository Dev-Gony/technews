"""9:16 '법원 건물과 의사봉, 도장' 장면 (법·규제·소송·저작권·정책 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 뒤: 기둥 4개가 선 법원 건물 (계단, 삼각 지붕에 금색 원 문장)
- 왼쪽 앞: 의사봉이 받침을 4초에 두 번 땅땅 내려치고, 칠 때마다 금색 물결이 퍼진다
- 오른쪽 앞: 서류 더미 위로 빨간 도장이 쾅 찍히고 빨간 도장 자국이 남는다
- 앞: 꼬마들이 문서를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/law_world.py
    blender -b -P assets3d/scripts/law_world.py -- --still-only
출력: video/public/assets3d/law_world.png, law_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {}


def courthouse():
    kit.use_collection("Court")
    rig = kit.empty("Court")
    rig.location = (0.05, -1.55, 0)
    rig.rotation_euler.z = math.radians(-20)
    w = 2.7
    for k in range(3):  # 계단
        kit.box(f"Court_Step{k}", (0, 0.12 - k * 0.08, 0.06 + k * 0.12), (w + 0.4 - k * 0.2, 1.3 - k * 0.16, 0.12), M["paper"] if k % 2 == 0 else M["white"], bevel=0.02, parent=rig)
    base_z = 0.36
    col_h = 1.25
    kit.box("Court_Wall", (0, -0.35, base_z + col_h / 2), (w - 0.3, 0.3, col_h), M["paper"], bevel=0.02, parent=rig)
    kit.box("Court_Door", (0, -0.19, base_z + 0.42), (0.5, 0.04, 0.84), M["ink"], bevel=0.04, parent=rig)
    for k in range(4):
        x = -w / 2 + 0.38 + k * (w - 0.76) / 3
        kit.cylinder(f"Court_Col{k}", (x, 0.12, base_z + col_h / 2), 0.13, col_h, M["white"], bevel=0.02, vertices=32, parent=rig)
        kit.box(f"Court_ColCap{k}", (x, 0.12, base_z + col_h - 0.03), (0.36, 0.36, 0.08), M["white"], bevel=0.015, parent=rig)
        kit.box(f"Court_ColFoot{k}", (x, 0.12, base_z + 0.04), (0.34, 0.34, 0.08), M["white"], bevel=0.015, parent=rig)
    top = base_z + col_h
    kit.box("Court_Beam", (0, -0.05, top + 0.11), (w + 0.1, 0.85, 0.22), M["white"], bevel=0.03, parent=rig)
    kit.box("Court_BeamLine", (0, 0.38, top + 0.11), (w - 0.1, 0.01, 0.05), M["red"], bevel=0, parent=rig)
    ck.extruded("Court_Roof", [(-(w + 0.2) / 2, 0), ((w + 0.2) / 2, 0), (0, 0.6)], 0.85, M["paper"], center=(0, -0.05, top + 0.22), bevel=0.03, parent=rig)
    ck.extruded("Court_RoofIn", [(-(w - 0.4) / 2, 0.06), ((w - 0.4) / 2, 0.06), (0, 0.48)], 0.05, M["ink"], center=(0, 0.39, top + 0.22), bevel=0.01, parent=rig)
    kit.cylinder("Court_Emblem", (0, 0.43, top + 0.43), 0.14, 0.05, M["gold"], bevel=0.015, vertices=32, axis="Y", parent=rig)


def group(name, x, y, scale):
    """소품 묶음: (x, y) 바닥에 두고 통째로 키운다. 안의 좌표는 묶음 기준."""
    rig = kit.empty(name)
    rig.location = (x, y, 0)
    rig.scale = (scale,) * 3
    return rig


def gavel(x, y):
    kit.use_collection("Gavel")
    grp = group("GavelSet", x, y, 1.45)
    wood = kit.material("M_GavelWood", "#8A5A3C", 0.45, 0.35)
    kit.cylinder("Block_Base", (0, 0, 0.05), 0.55, 0.1, M["ink"], bevel=0.03, vertices=48, parent=grp)
    kit.cylinder("Block", (0, 0, 0.19), 0.42, 0.18, wood, bevel=0.04, vertices=48, parent=grp)
    kit.cylinder("Block_Ring", (0, 0, 0.2), 0.43, 0.04, M["gold"], bevel=0.01, vertices=48, parent=grp)
    pivot = kit.empty("Gavel", parent=grp)
    pivot.location = (0.95, -0.35, 0.42)
    pivot.rotation_euler.z = math.atan2(0.35, -0.95)  # 손잡이 끝에서 받침 쪽을 본다
    reach = math.hypot(0.95, 0.35)
    kit.cylinder("Gavel_Handle", (reach / 2, 0, 0), 0.05, reach, wood, bevel=0.01, vertices=16, axis="X", parent=pivot)
    head = kit.empty("Gavel_Head", parent=pivot)
    head.location = (reach, 0, 0.05)
    kit.cylinder("Gavel_HeadBody", (0, 0, 0), 0.17, 0.62, wood, bevel=0.03, vertices=32, axis="Y", parent=head)
    for sy in (-1, 1):
        kit.cylinder(f"Gavel_Band{sy}", (0, sy * 0.2, 0), 0.18, 0.06, M["gold"], bevel=0.01, vertices=32, axis="Y", parent=head)
    ANIM["gavel"] = pivot
    ANIM["ripple"] = ck.torus("Gavel_Ripple", (0, 0, 0.29), 0.45, 0.03, ck.glow("Ripple", "gold", 2.0), parent=grp)


def stamp(x, y):
    kit.use_collection("Stamp")
    grp = group("StampSet", x, y, 1.35)
    for k in range(5):
        p = kit.box(f"Doc{k}", (0.03 * math.sin(k * 2.1), 0.03 * math.cos(k * 1.7), 0.03 + k * 0.05), (0.85, 1.05, 0.045), M["white"] if k % 2 else M["paper"], bevel=0.01, parent=grp)
        p.rotation_euler.z = math.radians(-14 + 6 * math.sin(k * 1.4))
    top = 0.03 + 4 * 0.05 + 0.025
    for k in range(3):
        kit.box(f"Doc_Ln{k}", (0.05, -0.32 + k * 0.13, top), (0.5 - 0.1 * k, 0.04, 0.004), M["ink"], bevel=0, parent=grp).rotation_euler.z = math.radians(-14 + 6 * math.sin(4 * 1.4))
    mark = kit.cylinder("Stamp_Mark", (-0.08, 0.22, top + 0.003), 0.2, 0.006, M["red"], bevel=0, vertices=48, parent=grp)
    ck.torus("Stamp_MarkIn", (0, 0, 0.004), 0.13, 0.018, M["paper"], parent=mark)
    ANIM["mark"] = mark
    rig = kit.empty("Stamp", parent=grp)
    rig.location = (-0.08, 0.22, top + 0.02)
    kit.cylinder("Stamp_Face", (0, 0, 0.06), 0.22, 0.12, M["red"], bevel=0.02, vertices=48, parent=rig)
    kit.cylinder("Stamp_Neck", (0, 0, 0.3), 0.08, 0.36, M["ink"], bevel=0.02, vertices=24, parent=rig)
    ck.sphere("Stamp_Knob", (0, 0, 0.56), 0.17, M["red"], parent=rig)
    kit.cylinder("Stamp_Collar", (0, 0, 0.14), 0.18, 0.05, M["gold"], bevel=0.01, vertices=48, parent=rig)
    ANIM["stamp"], ANIM["stamp_z"] = rig, rig.location.z


def build_characters():
    walkers = []
    specs = [("Doc", M["white"], "doc"), ("Key", M["blue"], "key"), ("Gold", M["gold"], "doc")]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.15), radii=(2.3, 0.66)))
    return walkers


def animate(cam_rig, walkers):
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        # 의사봉: 4초에 두 번 들었다 땅 (내려칠 때 빠르게)
        u = (2 * T) % 1.0
        if u < 0.7:  # 천천히 든다
            lift = math.sin(math.pi / 2 * u / 0.7)
        elif u < 0.8:  # 빠르게 내려친다
            lift = 1 - ((u - 0.7) / 0.1) ** 2
        else:
            lift = 0.0
        g = ANIM["gavel"]
        g.rotation_euler.y = -math.radians(38) * lift
        g.keyframe_insert("rotation_euler", index=1, frame=f)
        r = ANIM["ripple"]
        v = (u - 0.8) % 1.0  # 내려친 직후부터 퍼진다
        s = 1 + 1.6 * v if v < 0.45 else 0.0
        r.scale = (s, s, 1 if s else 0)
        r.keyframe_insert("scale", frame=f)
        # 도장: 4초에 한 번 쾅. 찍은 뒤 자국이 남았다가 다음에 들 때 사라진다
        ph = T % 1.0
        press = max(0.0, math.sin(math.pi * (ph - 0.15) / 0.3)) if 0.15 < ph < 0.45 else 0.0
        st = ANIM["stamp"]
        st.location.z = ANIM["stamp_z"] + 0.55 * (1 - press)
        st.keyframe_insert("location", index=2, frame=f)
        ck.show(ANIM["mark"], f, 0.32 < ph < 0.95)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    courthouse()
    gavel(2.05, 0.35)
    stamp(-2.15, 0.2)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("law_world", {
        "court": (obj["Court"], "object", "기둥 4개 선 법원 건물, 지붕에 금색 문장 (법원·정부·규제 당국)"),
        "gavel": ([obj["Block_Base"], obj["Block"], obj["Block_Ring"], ANIM["gavel"]], "object", "받침을 땅땅 내려치는 의사봉 (판결·결정·제재)"),
        "stamp": (obj["StampSet"], "object", "서류 더미에 쾅 찍히는 빨간 도장 (승인·법안 통과·허가)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 문서를 들고 걸어 다닌다 (소송 서류·원고)"),
        "blue": (walkers[1].rig, "character", "파란 꼬마: 열쇠를 들고 걸어 다닌다 (권리·저작권 가진 쪽)"),
        "yellow": (walkers[2].rig, "character", "노란 꼬마: 문서를 들고 걸어 다닌다 (기업·피고·신청인)"),
    }, FRAMES, "law3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("law_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("law_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
