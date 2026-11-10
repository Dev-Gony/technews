"""9:16 '</> 조형물과 컴파일러 기계' 장면 (프로그래밍 언어·컴파일러·런타임·타입 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 뒤: 받침 위에 선 큰 '</>' 글자 조형물 (빨강 꺾쇠, 금색 빗금)
- 가운데: 컴파일러 기계. 위 깔때기로 색색 코드 블록이 떨어져 들어가고, 옆 배출구로 0·1 조각이 톡톡 나온다.
  기계 옆 톱니가 돌고 램프가 깜빡인다
- 오른쪽 앞: 줄마다 들여쓰기가 다른 코드 블록 탑 (위 블록이 들썩)
- 앞: 꼬마들이 코드 / 문서를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/lang_world.py
    blender -b -P assets3d/scripts/lang_world.py -- --still-only
출력: video/public/assets3d/lang_world.png, lang_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"drops": [], "bits": []}


def sign():
    kit.use_collection("Sign")
    rig = kit.empty("Sign")
    rig.location = (-0.9, -1.75, 0)
    rig.rotation_euler.z = math.radians(-20)
    kit.box("Sign_Base", (0, 0, 0.2), (2.1, 0.5, 0.4), M["ink"], bevel=0.05, parent=rig)
    t = kit.empty("Sign_Text", parent=rig)
    t.location = (0, 0, 0.98)
    ck.label("Sign_Lt", "<", (0.7, 0, 0), 1.6, M["red"], depth=0.12, parent=t)
    ck.label("Sign_Slash", "/", (0, 0, 0), 1.6, M["gold"], depth=0.12, parent=t)
    ck.label("Sign_Gt", ">", (-0.7, 0, 0), 1.6, M["red"], depth=0.12, parent=t)
    ANIM["sign"] = t


def compiler(x, y):
    kit.use_collection("Compiler")
    rig = kit.empty("Compiler")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-20)
    kit.box("Cmp_Body", (0, 0, 0.55), (1.2, 0.95, 1.1), M["steel"], bevel=0.08, segments=4, parent=rig)
    kit.box("Cmp_Panel", (0, 0.48, 0.62), (0.8, 0.02, 0.5), M["screenBg"], bevel=0.04, parent=rig)
    lamp = ck.glow("CmpLamp", "gold", 1.0)
    for k in range(3):
        kit.box(f"Cmp_Bar{k}", (0.2 - k * 0.2, 0.495, 0.62), (0.12, 0.01, 0.3), lamp if k == 1 else ck.glow(f"CmpBar{k}", "sage", 1.2), bevel=0, parent=rig)
    ck.cone("Cmp_Funnel", (0, 0, 1.38), 0.22, 0.55, 0.55, M["gold"], parent=rig)
    kit.box("Cmp_Chute", (-0.68, 0.15, 0.35), (0.35, 0.4, 0.22), M["ink"], bevel=0.05, parent=rig)
    gear = kit.empty("Cmp_Gear", parent=rig)
    gear.location = (0.62, 0.0, 0.85)
    pts = []
    for i in range(20):
        a = math.pi * i / 10
        r = 0.32 if i % 2 == 0 else 0.24
        for da in (-0.08, 0.08):
            pts.append((r * math.cos(a + da), r * math.sin(a + da)))
    g = ck.extruded("Cmp_GearBody", pts, 0.1, M["red"], center=(0, 0, 0), bevel=0.015, parent=gear)
    g.rotation_euler.z = math.pi / 2  # 기계 옆면(+x)에 붙는다
    ANIM["gear"], ANIM["lamp"] = gear, lamp
    colors = [M["red"], M["blue"], M["white"], M["gold"]]
    for k in range(4):
        b = kit.empty(f"Drop{k}", parent=rig)
        kit.box(f"Drop{k}_Body", (0, 0, 0), (0.24, 0.24, 0.16), colors[k], bevel=0.04, parent=b)
        kit.box(f"Drop{k}_Ln", (0, 0.122, 0.0), (0.14, 0.005, 0.03), M["ink"] if k != 0 else M["white"], bevel=0, parent=b)
        ANIM["drops"].append((b, k))
    for k in range(4):
        d = "01"[k % 2]
        b = kit.empty(f"Bit{k}", parent=rig)
        ck.label(f"Bit{k}_Num", d, (0, 0, 0), 0.32, ck.glow(f"Bit{k}", "gold" if d == "1" else "white", 1.4), depth=0.05, parent=b)
        b.rotation_euler.z = math.radians(-70)
        ANIM["bits"].append((b, k))


def code_tower(x, y):
    kit.use_collection("Tower")
    rig = kit.empty("CodeTower")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-20)
    specs = [(0.0, 1.1, M["ink"]), (0.18, 0.85, M["blue"]), (0.36, 0.7, M["red"]), (0.18, 0.8, M["white"]), (0.0, 1.0, M["gold"])]
    z = 0.0
    for k, (indent, w, mat) in enumerate(specs):
        blk = kit.empty(f"Code{k}", parent=rig)
        blk.location = (indent - 0.2, 0, z)
        kit.box(f"Code{k}_Body", (-w / 2 + 0.55, 0, 0.11), (w, 0.55, 0.22), mat, bevel=0.04, parent=blk)
        z += 0.24
        if k == len(specs) - 1:
            ANIM["top"], ANIM["top_z"] = blk, blk.location.z


def build_characters():
    walkers = []
    specs = [("Code", M["white"], "code"), ("Doc", M["blue"], "doc"), ("Red", M["red"], "code")]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.2), radii=(2.3, 0.62)))
    return walkers


def animate(cam_rig, walkers):
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        s = ANIM["sign"]
        s.location.z = 0.98 + 0.06 * math.sin(2 * math.pi * T)
        s.keyframe_insert("location", index=2, frame=f)
        # 코드 블록: 4초에 4개가 차례로 깔때기 위에서 떨어져 들어간다
        for b, k in ANIM["drops"]:
            u = (T + k / 4) % 1.0
            b.location = (0.06 * math.sin(k * 2), 0, 2.1 - 1.0 * u * u)
            b.rotation_euler.z = 2 * math.pi * u * (1 if k % 2 else -1) * 0.5
            sc = min(1.0, (1 - u) / 0.15)
            b.scale = (sc, sc, sc)
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("rotation_euler", index=2, frame=f)
            b.keyframe_insert("scale", frame=f)
        # 0·1 조각: 배출구에서 톡 튀어나와 바닥으로
        for b, k in ANIM["bits"]:
            u = (T + k / 4 + 0.5) % 1.0
            b.location = (-0.85 - 0.6 * u, 0.15 + 0.2 * u, 0.45 + 0.7 * u - 0.75 * u * u)
            sc = min(1.0, u / 0.1, (1 - u) / 0.15)
            b.scale = (sc, sc, sc)
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("scale", frame=f)
        ANIM["gear"].rotation_euler.x = 2 * math.pi * 2 * t
        ANIM["gear"].keyframe_insert("rotation_euler", index=0, frame=f)
        ck.pulse(f, T, ANIM["lamp"], 0.3, 2.6, 4, square=True)
        top = ANIM["top"]
        h = max(0.0, math.sin(2 * math.pi * 2 * T)) ** 2
        top.location.z = ANIM["top_z"] + 0.15 * h
        top.rotation_euler.z = math.radians(8) * h
        top.keyframe_insert("location", index=2, frame=f)
        top.keyframe_insert("rotation_euler", index=2, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    sign()
    compiler(1.35, -0.75)
    code_tower(-2.0, 0.35)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("lang_world", {
        "sign": (obj["Sign"], "object", "받침 위 큰 '</>' 글자 조형물 (프로그래밍 언어·코드)"),
        "compiler": ([o for o in obj if o.name.startswith("Cmp_")], "object",
                     "컴파일러 기계: 코드 블록을 삼켜 0·1 조각을 뱉는다 (컴파일러·런타임·빌드)"),
        "tower": (obj["CodeTower"], "object", "들여쓰기가 다른 색색 코드 블록 탑 (코드베이스·라이브러리·스택)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 코드를 들고 걸어 다닌다 (개발자·새 언어)"),
        "blue": (walkers[1].rig, "character", "파란 꼬마: 문서를 들고 걸어 다닌다 (문서·명세·사용자)"),
        "red": (walkers[2].rig, "character", "빨간 꼬마: 코드를 들고 걸어 다닌다 (개발자·버그·경쟁 언어)"),
    }, FRAMES, "lang3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("lang_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("lang_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
