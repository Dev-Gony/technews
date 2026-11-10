"""9:16 '떠 있는 브라우저 창과 지구본' 장면 (웹·브라우저·사이트·프런트엔드 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 뒤: 공중에 뜬 큰 브라우저 창(빨강·금·초록 점 3개, 주소창, 탭). 주소창 아래 금색 로딩 막대가 4초에 한 번 차고,
  본문 카드 3장이 차례로 톡 튀어나온다. 뒤에 먹색 창 하나가 겹쳐 있다
- 왼쪽 앞: 받침 위에서 도는 파란 지구본 (먹색 경선, 금색 적도)
- 오른쪽 앞: 큰 마우스 화살표가 빨간 버튼을 누르고, 바닥에 물결이 퍼진다
- 앞: 꼬마들이 문서 / 코드를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/web_world.py
    blender -b -P assets3d/scripts/web_world.py -- --still-only
출력: video/public/assets3d/web_world.png, web_world_loop.webm (1080x1920, 투명 배경)
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

WIN = (0.05, -1.45)
WIN_W, WIN_H = 3.1, 1.95
WIN_Z = 0.5  # 창 아래 끝 높이


def browser():
    kit.use_collection("Browser")
    base = kit.empty("BrowserRig")
    base.location = (WIN[0], WIN[1], 0)
    base.rotation_euler.z = math.radians(-20)
    # 바닥 그림자 자리 (먹색 얇은 판) — 창이 떠 있다는 느낌
    kit.cylinder("Browser_Shadow", (0, 0.1, 0.006), 1.0, 0.012, kit.material("M_Shadow", "#D9D4C8", 0.8, 0.1), bevel=0, vertices=64, parent=base).scale = (1.3, 0.3, 1)
    rig = kit.empty("Browser", parent=base)
    # 뒤에 겹친 먹색 창
    kit.box("Back_Win", (-0.45, -0.35, WIN_Z + WIN_H / 2 + 0.25), (WIN_W * 0.85, 0.1, WIN_H * 0.85), M["steel"], bevel=0.08, segments=4, parent=rig)
    kit.box("Back_Bar", (-0.45, -0.29, WIN_Z + WIN_H * 0.85 + 0.25 + WIN_H * 0.075 - 0.2), (WIN_W * 0.85, 0.02, 0.22), M["ink"], bevel=0.01, parent=rig)
    zc = WIN_Z + WIN_H / 2
    top = WIN_Z + WIN_H
    kit.box("Win_Frame", (0, 0, zc), (WIN_W, 0.12, WIN_H), M["white"], bevel=0.08, segments=4, parent=rig)
    kit.box("Win_Bar", (0, 0.03, top - 0.2), (WIN_W - 0.02, 0.08, 0.38), M["ink"], bevel=0.06, segments=3, parent=rig)
    kit.box("Win_Tab", (0.75, 0.0, top + 0.06), (0.95, 0.09, 0.26), M["ink"], bevel=0.06, segments=3, parent=rig)
    kit.box("Win_Tab2", (-0.3, -0.02, top + 0.03), (0.95, 0.07, 0.2), M["steel"], bevel=0.05, segments=3, parent=rig)
    for k, color in enumerate(("red", "gold", "sage")):
        kit.cylinder(f"Win_Dot{k}", (WIN_W / 2 - 0.22 - k * 0.17, 0.08, top - 0.2), 0.055, 0.03, M[color], bevel=0.01, vertices=24, axis="Y", parent=rig)
    kit.box("Win_Address", (-0.32, 0.075, top - 0.2), (2.0, 0.02, 0.2), M["paper"], bevel=0.05, segments=4, parent=rig)
    for k, w in enumerate((0.7, 0.35)):
        kit.box(f"Win_AddrText{k}", (0.45 - k * 0.6 - w / 2, 0.088, top - 0.2), (w, 0.005, 0.04), M["steel"], bevel=0, parent=rig)
    # 로딩 막대 (원점 = 왼쪽 끝, x 방향으로 늘어난다; 창 로컬에서 +x 가 화면 왼쪽)
    bar = kit.box("Win_Load", (0, 0.08, top - 0.39), (1.0, 0.012, 0.035), ck.glow("LoadBar", "gold", 2.0), bevel=0, parent=rig)
    for v in bar.data.vertices:
        v.co.x -= 0.5
    bar.location.x = WIN_W / 2 - 0.08
    ANIM["load"] = bar
    # 본문: 빨간 큰 배너 + 글줄 + 카드 3장
    kit.box("Win_Hero", (0, 0.075, top - 0.75), (WIN_W - 0.4, 0.03, 0.5), M["red"], bevel=0.04, parent=rig)
    for k, w in enumerate((1.2, 0.8)):
        kit.box(f"Win_HeroLn{k}", (WIN_W / 2 - 0.4 - w / 2, 0.095, top - 0.66 - k * 0.14), (w, 0.01, 0.07), M["white"], bevel=0, parent=rig)
    for k, color in enumerate(("blue", "gold", "paper")):
        card = kit.empty(f"Card{k}", parent=rig)
        card.location = (0.92 - k * 0.92, 0.06, WIN_Z + 0.42)
        kit.box(f"Card{k}_Body", (0, 0.03, 0), (0.78, 0.06, 0.62), M[color], bevel=0.05, parent=card)
        kit.box(f"Card{k}_Ln", (0.08, 0.065, -0.17), (0.45, 0.01, 0.05), M["ink"], bevel=0, parent=card)
        ANIM["cards"].append((card, k))
    ANIM["browser"] = rig


def globe(x, y):
    kit.use_collection("Globe")
    kit.cylinder("Globe_Base", (x, y, 0.07), 0.42, 0.14, M["ink"], bevel=0.04, vertices=48)
    kit.cylinder("Globe_Stem", (x, y, 0.3), 0.05, 0.36, M["ink"], bevel=0.01, vertices=16)
    tilt = kit.empty("Globe_Tilt")
    tilt.location = (x, y, 1.05)
    tilt.rotation_euler.x = math.radians(20)
    ck.torus("Globe_Arc", (0, 0, 0), 0.66, 0.035, M["gold"], rotation=(0, math.pi / 2, 0), parent=tilt)
    spin = kit.empty("Globe_Spin", parent=tilt)
    ck.sphere("Globe_Ball", (0, 0, 0), 0.58, M["blue"], parent=spin, segments=48)
    ck.torus("Globe_Equator", (0, 0, 0), 0.585, 0.025, M["gold"], parent=spin)
    for k in range(3):
        ck.torus(f"Globe_Meridian{k}", (0, 0, 0), 0.585, 0.018, M["ink"], rotation=(math.pi / 2, 0, k * math.pi / 3), parent=spin)
    for k, (z, r) in enumerate(((0.3, 0.5), (-0.3, 0.5))):
        ck.torus(f"Globe_Lat{k}", (0, 0, z), r + 0.005, 0.015, M["ink"], parent=spin)
    ANIM["globe"] = spin


ARROW = [(0.0, 0.0), (0.0, 0.78), (0.2, 0.6), (0.36, 0.95), (0.5, 0.89), (0.33, 0.55), (0.58, 0.55)]


def cursor(x, y):
    kit.use_collection("Cursor")
    kit.cylinder("Button_Base", (x, y, 0.06), 0.5, 0.12, M["ink"], bevel=0.04, vertices=48)
    btn = kit.cylinder("Button_Top", (x, y, 0.17), 0.36, 0.14, M["red"], bevel=0.05, vertices=48)
    ANIM["button"], ANIM["button_z"] = btn, btn.location.z
    ring_mat = ck.glow("Ripple", "red", 1.4)
    rings = [(ck.torus(f"Ripple{k}", (x, y, 0.03), 0.5, 0.03, ring_mat), k) for k in range(2)]
    ANIM["ripples"] = rings
    rig = kit.empty("Cursor")
    rig.location = (x + 0.05, y + 0.05, 0.34)
    rig.rotation_euler = (0, 0, math.radians(-20))  # 카메라 정면
    arrow = kit.empty("Arrow", parent=rig)
    arrow.scale = (1.5, 1.5, 1.5)
    ck.extruded("Arrow_Body", ARROW, 0.1, M["white"], center=(0, 0.02, 0), bevel=0.02, parent=arrow)
    cx, cz = 0.25, 0.5
    outline = [(cx + (px - cx) * 1.13, cz + (pz - cz) * 1.1) for px, pz in ARROW]
    ck.extruded("Arrow_Edge", outline, 0.08, M["ink"], center=(-0.0, -0.04, -0.03), bevel=0.02, parent=arrow)
    ANIM["cursor"], ANIM["cursor_z"] = rig, rig.location.z


def build_characters():
    walkers = []
    specs = [("Doc", M["white"], "doc"), ("Code", M["red"], "code"), ("Gold", M["gold"], None)]
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
        b = ANIM["browser"]
        b.location.z = 0.05 * math.sin(2 * math.pi * T)
        b.keyframe_insert("location", index=2, frame=f)
        ph = T % 1.0
        load = ANIM["load"]
        load.scale.x = max(0.001, min(1.0, ph / 0.55) * (WIN_W - 0.16))
        load.keyframe_insert("scale", index=0, frame=f)
        for card, k in ANIM["cards"]:
            # 로딩이 끝나면 카드가 차례로 톡 (0.55 ~ 0.85 사이), 다음 박자 시작 전에 가라앉는다
            u = (ph - 0.55 - k * 0.1) / 0.18
            pop = math.sin(math.pi * min(max(u, 0.0), 1.0))
            card.location.y = 0.06 + 0.18 * pop
            card.scale = (1 + 0.08 * pop,) * 3
            card.keyframe_insert("location", index=1, frame=f)
            card.keyframe_insert("scale", frame=f)
        ANIM["globe"].rotation_euler.z = 2 * math.pi * t
        ANIM["globe"].keyframe_insert("rotation_euler", index=2, frame=f)
        # 화살표: 4초에 두 번 누른다
        press = max(0.0, math.sin(2 * math.pi * 2 * T)) ** 4
        ANIM["cursor"].location.z = ANIM["cursor_z"] + 0.25 - 0.25 * press
        ANIM["cursor"].keyframe_insert("location", index=2, frame=f)
        ANIM["button"].location.z = ANIM["button_z"] - 0.05 * press
        ANIM["button"].keyframe_insert("location", index=2, frame=f)
        for ring, k in ANIM["ripples"]:
            u = (2 * T - 0.25 + k * 0.5) % 1.0
            s = 0.8 + 1.4 * u
            ring.scale = (s, s, 1)
            ring.location.z = 0.03 if u < 0.9 else -0.2  # 다 퍼지면 원판 밑으로 숨긴다
            ring.keyframe_insert("scale", frame=f)
            ring.keyframe_insert("location", index=2, frame=f)
        ck.pulse(f, T, ANIM["ripples"][0][0].data.materials[0], 0.6, 1.8, 2)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    browser()
    globe(2.25, 0.3)
    cursor(-2.2, 0.35)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("web_world", {
        "browser": (obj["Browser"], "object", "공중에 뜬 큰 브라우저 창, 로딩 막대와 카드가 뜬다 (웹사이트·브라우저)"),
        "globe": (obj["Globe_Tilt"], "object", "받침 위에서 도는 파란 지구본 (인터넷·전 세계)"),
        "cursor": ([obj["Cursor"], obj["Button_Base"], obj["Button_Top"]], "object", "큰 마우스 화살표가 빨간 버튼을 누른다 (클릭·사용자 조작)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 문서를 들고 걷는다 (웹 문서·콘텐츠)"),
        "red": (walkers[1].rig, "character", "빨간 꼬마: 빨간 코드 블록을 들고 걷는다 (프런트엔드 코드)"),
        "yellow": (walkers[2].rig, "character", "노란 꼬마: 빈손으로 걸어 다닌다 (방문자·사용자)"),
    }, FRAMES, "web3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("web_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("web_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
