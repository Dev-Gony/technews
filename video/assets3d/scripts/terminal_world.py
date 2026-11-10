"""9:16 '터미널 창과 톱니바퀴, 폴더' 장면 (터미널·CLI·리눅스·macOS·윈도우·운영체제·셸 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 가운데 뒤: 공중에 뜬 먹색 터미널 창. 금색 '>_' 프롬프트와 커서가 깜빡이고,
  명령 줄이 4초에 한 번 한 줄씩 쳐진다(늘어난다)
- 왼쪽 앞: 맞물려 도는 톱니바퀴 두 개 (설정)
- 오른쪽 앞: 금색 폴더 두 개, 앞 폴더에서 서류가 들락날락
- 앞: 꼬마들이 코드 / 문서를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/terminal_world.py
    blender -b -P assets3d/scripts/terminal_world.py -- --still-only
출력: video/public/assets3d/terminal_world.png, terminal_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"lines": [], "gears": []}

WIN_W, WIN_H = 2.9, 1.85
WIN_Z = 0.55


def terminal():
    kit.use_collection("Terminal")
    base = kit.empty("TermRig")
    base.location = (0.05, -1.45, 0)
    base.rotation_euler.z = math.radians(-20)
    rig = kit.empty("Terminal", parent=base)
    zc = WIN_Z + WIN_H / 2
    top = WIN_Z + WIN_H
    # 테두리는 밝은 회색으로 (영상 배경이 먹색이라 창 윤곽이 묻히지 않게)
    kit.box("Term_Frame", (0, 0, zc), (WIN_W, 0.14, WIN_H), kit.material("M_TermEdge", "#8C877C", 0.5, 0.3), bevel=0.09, segments=4, parent=rig)
    kit.box("Term_Screen", (0, 0.065, zc - 0.1), (WIN_W - 0.14, 0.02, WIN_H - 0.34), M["dark"], bevel=0.05, parent=rig)
    kit.box("Term_Bar", (0, 0.02, top - 0.17), (WIN_W - 0.02, 0.12, 0.32), M["steel"], bevel=0.07, segments=3, parent=rig)
    for k, color in enumerate(("red", "gold", "sage")):
        kit.cylinder(f"Term_Dot{k}", (WIN_W / 2 - 0.22 - k * 0.17, 0.085, top - 0.17), 0.055, 0.03, M[color], bevel=0.01, vertices=24, axis="Y", parent=rig)
    kit.box("Term_Title", (-0.2, 0.085, top - 0.17), (0.7, 0.01, 0.05), M["paper"], bevel=0, parent=rig)
    gold = ck.glow("Prompt", "gold", 1.8)
    text = ck.glow("TermText", "paper", 0.7)
    sage = ck.glow("TermOk", "sage", 1.2)
    # 줄들: 프롬프트(>) + 명령 막대. 막대는 원점 = 왼쪽 끝(창 로컬 +x 가 화면 왼쪽)
    rows = [(0.95, gold, text), (0.55, None, sage), (1.2, gold, text), (0.75, None, text)]
    x0 = WIN_W / 2 - 0.3
    for r, (w, prompt, mat) in enumerate(rows):
        z = top - 0.6 - r * 0.28
        if prompt is not None:
            ck.label(f"Term_Gt{r}", ">", (x0, 0.08, z), 0.26, prompt, depth=0.012, parent=rig)
        bar = kit.box(f"Term_Line{r}", (0, 0.078, z), (1.0, 0.012, 0.075), mat, bevel=0, parent=rig)
        for v in bar.data.vertices:
            v.co.x -= 0.5
        bar.location.x = x0 - 0.2 if prompt is not None else x0
        ANIM["lines"].append((bar, w, r))
    cursor = kit.box("Term_Cursor", (0, 0.08, top - 0.6 - 4 * 0.28), (0.14, 0.012, 0.2), gold, bevel=0, parent=rig)
    ck.label("Term_GtLast", ">", (x0, 0.08, top - 0.6 - 4 * 0.28), 0.26, gold, depth=0.012, parent=rig)
    cursor.location.x = x0 - 0.3
    ANIM["cursor"] = cursor
    ANIM["term"] = rig


def gear(name, x, y, z, r_out, teeth, mat, thick=0.18, parent=None):
    rig = kit.empty(name, parent=parent)
    rig.location = (x, y, z)
    pts = []
    for i in range(teeth * 2):
        a = math.pi * i / teeth
        r = r_out if i % 2 == 0 else r_out * 0.78
        for da in (-0.32 * math.pi / teeth, 0.32 * math.pi / teeth):
            pts.append((r * math.cos(a + da), r * math.sin(a + da)))
    ck.extruded(f"{name}_Body", pts, thick, mat, center=(0, 0, 0), bevel=0.02, parent=rig)
    kit.cylinder(f"{name}_Hub", (0, 0, 0), r_out * 0.32, thick + 0.06, M["white"], bevel=0.02, vertices=32, axis="Y", parent=rig)
    return rig


def gears(x, y):
    kit.use_collection("Gears")
    stand = kit.empty("GearStand")
    stand.location = (x, y, 0)
    stand.rotation_euler.z = math.radians(-20)
    kit.box("Gear_Base", (0, 0, 0.06), (1.5, 0.5, 0.12), M["ink"], bevel=0.04, parent=stand)
    for k, (gx, gz) in enumerate(((0.32, 0.9), (-0.42, 0.62))):
        kit.box(f"Gear_Post{k}", (gx, -0.12, gz / 2), (0.08, 0.08, gz), M["ink"], bevel=0.02, parent=stand)
    big = gear("GearBig", 0.32, 0.0, 0.9, 0.55, 12, M["red"], parent=stand)
    small = gear("GearSmall", -0.42, 0.0, 0.62, 0.36, 8, M["gold"], parent=stand)
    small.rotation_euler.y = math.pi / 8  # 톱니가 맞물리게
    ANIM["gears"] = [(big, 1.0, 0.0), (small, -12 / 8, math.pi / 8)]


def folders(x, y):
    kit.use_collection("Folders")
    rig = kit.empty("Folders")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-25)
    folder_mat = kit.material("M_Folder", "gold", 0.45, 0.4)
    folder_back = kit.material("M_FolderBack", "#E0A93D", 0.5, 0.3)
    for k, (dx, dy, s) in enumerate(((0.25, -0.35, 0.85), (-0.1, 0.15, 1.0))):
        f = kit.empty(f"Folder{k}", parent=rig)
        f.location = (dx, dy, 0)
        f.scale = (s,) * 3
        kit.box(f"Folder{k}_Back", (0, -0.06, 0.5), (1.0, 0.06, 0.95), folder_back, bevel=0.03, parent=f)
        kit.box(f"Folder{k}_Tab", (0.25, -0.06, 1.0), (0.4, 0.06, 0.16), folder_back, bevel=0.03, parent=f)
        front = kit.box(f"Folder{k}_Front", (0, 0.06, 0.4), (1.0, 0.06, 0.8), folder_mat, bevel=0.03, parent=f)
        front.rotation_euler.x = math.radians(-8)
        if k == 1:
            paper = kit.empty("Folder_Paper", parent=f)
            paper.location = (0.05, 0.0, 0.45)
            kit.box("Folder_PaperBody", (0, 0, 0.3), (0.8, 0.03, 0.75), M["white"], bevel=0.01, parent=paper)
            for i in range(3):
                kit.box(f"Folder_PaperLn{i}", (0, 0.017, 0.55 - i * 0.12), (0.5, 0.005, 0.035), M["ink"], bevel=0, parent=paper)
            ANIM["paper"] = paper


def build_characters():
    walkers = []
    specs = [("Code", M["white"], "code"), ("Doc", M["blue"], "doc"), ("Red", M["red"], None)]
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
        term = ANIM["term"]
        term.location.z = 0.05 * math.sin(2 * math.pi * T)
        term.keyframe_insert("location", index=2, frame=f)
        ph = T % 1.0
        for bar, w, r in ANIM["lines"]:  # 4초 동안 위에서부터 한 줄씩 쳐진다, 끝에서 잠깐 비운다
            u = min(max((ph - r * 0.2) / 0.16, 0.0), 1.0)
            if ph > 0.93:
                u = 0.0
            bar.scale.x = max(0.001, w * u)
            bar.keyframe_insert("scale", index=0, frame=f)
        ck.show(ANIM["cursor"], f, int(T * 6) % 2 == 0)  # 커서 깜빡 (초당 1.5번)
        for g, ratio, phase in ANIM["gears"]:
            g.rotation_euler.y = phase + ratio * 2 * math.pi * t
            g.keyframe_insert("rotation_euler", index=1, frame=f)
        p = ANIM["paper"]
        p.location.z = 0.45 + 0.3 * max(0.0, math.sin(2 * math.pi * 2 * T)) ** 2
        p.keyframe_insert("location", index=2, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    terminal()
    gears(2.15, 0.35)
    folders(-2.15, 0.25)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("terminal_world", {
        "terminal": (obj["Terminal"], "object", "공중에 뜬 먹색 터미널 창, 명령 줄이 쳐진다 (CLI·셸·명령 실행)"),
        "gears": (obj["GearStand"], "object", "맞물려 도는 빨강·금색 톱니바퀴 (설정·시스템·자동화)"),
        "folders": (obj["Folders"], "object", "금색 폴더 두 개, 서류가 들락날락 (파일·디렉터리·저장소)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 코드 조각을 들고 걸어 다닌다 (개발자·스크립트)"),
        "blue": (walkers[1].rig, "character", "파란 꼬마: 문서를 들고 걸어 다닌다 (문서·설정 파일)"),
        "red": (walkers[2].rig, "character", "빨간 꼬마: 빈손으로 걸어 다닌다 (사용자·관리자)"),
    }, FRAMES, "terminal3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("terminal_world", resolution=1080, height=1920, frame=100))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("terminal_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
