"""9:16 '큰 스마트폰과 앱 아이콘' 장면 (모바일·앱·iOS·Android·스마트폰 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 가운데 뒤: 받침에 선 큰 스마트폰. 화면에 색색 앱 아이콘 격자, 아이콘이 차례로 톡 튀고
  위쪽에 알림 말풍선이 4초에 한 번 내려온다
- 왼쪽 앞: 거치대에 놓인 태블릿 (화면에 카드 2장)
- 오른쪽 앞: 흔들리는 금색 알림 종과 빨간 숫자 배지
- 앞: 꼬마들이 코드 / 문서를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/phone_world.py
    blender -b -P assets3d/scripts/phone_world.py -- --still-only
출력: video/public/assets3d/phone_world.png, phone_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"icons": []}

PH_W, PH_H = 1.3, 2.15
PH_Z = 0.28  # 폰 아래 끝 높이


def phone():
    kit.use_collection("Phone")
    rig = kit.empty("Phone")
    rig.location = (0.0, -1.3, 0)
    rig.rotation_euler.z = math.radians(-20)
    rig.scale = (1.12,) * 3
    kit.box("Phone_Stand", (0, 0.05, 0.08), (1.0, 0.75, 0.16), M["ink"], bevel=0.05, parent=rig)
    body = kit.empty("Phone_Body", parent=rig)
    body.location = (0, 0, PH_Z)
    body.rotation_euler.x = math.radians(8)  # 살짝 뒤로 기댄다 (+x 회전 = 윗부분이 -y 로)
    zc = PH_H / 2
    kit.box("Phone_Shell", (0, 0, zc), (PH_W, 0.14, PH_H), M["ink"], bevel=0.16, segments=6, parent=body)
    kit.box("Phone_Screen", (0, 0.07, zc), (PH_W - 0.12, 0.01, PH_H - 0.12), M["screenBg"], bevel=0.11, segments=6, parent=body)
    kit.box("Phone_Notch", (0, 0.08, PH_H - 0.16), (0.36, 0.01, 0.08), M["ink"], bevel=0.035, parent=body)
    kit.box("Phone_HomeBar", (0, 0.08, 0.13), (0.42, 0.01, 0.035), M["white"], bevel=0.015, parent=body)
    colors = ["red", "gold", "blue", "sage", "white", "paper", "gold", "red", "blue", "white", "sage", "red"]
    for k, color in enumerate(colors):
        c, r = k % 3, k // 3
        icon = kit.empty(f"Icon{k}", parent=body)
        icon.location = (0.36 - c * 0.36, 0.08, PH_H - 0.58 - r * 0.38)
        kit.box(f"Icon{k}_Body", (0, 0.025, 0), (0.27, 0.05, 0.27), M[color], bevel=0.07, segments=4, parent=icon)
        ANIM["icons"].append((icon, k))
    # 알림 말풍선 (화면 위쪽에서 내려온다)
    note = kit.empty("Note", parent=body)
    note.location = (0, 0.16, PH_H - 0.3)
    kit.box("Note_Card", (0, 0, 0), (1.25, 0.06, 0.3), M["white"], bevel=0.1, segments=4, parent=note)
    kit.box("Note_Icon", (0.45, 0.035, 0), (0.18, 0.02, 0.18), M["red"], bevel=0.05, parent=note)
    for k, w in enumerate((0.6, 0.4)):
        kit.box(f"Note_Ln{k}", (0.28 - w / 2, 0.035, 0.05 - k * 0.1), (w, 0.01, 0.045), M["ink"] if k == 0 else M["steel"], bevel=0, parent=note)
    ANIM["note"] = note


def tablet(x, y):
    kit.use_collection("Tablet")
    rig = kit.empty("Tablet")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-25)
    rig.scale = (1.25,) * 3
    kit.box("Tab_Foot", (0, 0.1, 0.04), (1.1, 0.55, 0.08), M["ink"], bevel=0.03, parent=rig)
    kit.box("Tab_Lip", (0, 0.32, 0.12), (1.1, 0.08, 0.14), M["ink"], bevel=0.02, parent=rig)
    body = kit.empty("Tab_Body", parent=rig)
    body.location = (0, 0.22, 0.1)
    body.rotation_euler.x = math.radians(18)
    kit.box("Tab_Shell", (0, 0, 0.45), (1.25, 0.07, 0.9), M["white"], bevel=0.08, segments=4, parent=body)
    kit.box("Tab_Screen", (0, 0.036, 0.45), (1.12, 0.01, 0.78), M["screenBg"], bevel=0.05, parent=body)
    kit.box("Tab_Card1", (0.25, 0.045, 0.52), (0.48, 0.01, 0.48), M["blue"], bevel=0.04, parent=body)
    kit.box("Tab_Card2", (-0.25, 0.045, 0.6), (0.42, 0.01, 0.3), M["gold"], bevel=0.04, parent=body)
    kit.box("Tab_Card3", (-0.25, 0.045, 0.32), (0.42, 0.01, 0.16), M["red"], bevel=0.04, parent=body)


def bell(x, y):
    kit.use_collection("Bell")
    kit.cylinder("Bell_Base", (x, y, 0.06), 0.42, 0.12, M["ink"], bevel=0.04, vertices=48)
    kit.cylinder("Bell_Post", (x, y, 0.55), 0.04, 0.9, M["ink"], bevel=0.01, vertices=16)
    pivot = kit.empty("Bell")
    pivot.location = (x, y, 1.48)
    ck.torus("Bell_Loop", (0, 0, 0.02), 0.07, 0.025, M["gold"], rotation=(math.pi / 2, 0, 0), parent=pivot)
    ck.cone("Bell_Body", (0, 0, -0.28), 0.42, 0.16, 0.5, M["gold"], parent=pivot)
    ck.sphere("Bell_Top", (0, 0, -0.03), 0.17, M["gold"], scale=(1, 1, 0.6), parent=pivot)
    ck.torus("Bell_Lip", (0, 0, -0.53), 0.41, 0.045, M["gold"], parent=pivot)
    ck.sphere("Bell_Clapper", (0, 0, -0.6), 0.09, M["ink"], parent=pivot)
    badge = kit.empty("Badge")
    badge.location = (x - 0.35, y + 0.1, 1.55)
    badge.rotation_euler.z = math.radians(-20)
    kit.cylinder("Badge_Disc", (0, 0, 0), 0.2, 0.08, M["red"], bevel=0.03, vertices=40, axis="Y", parent=badge)
    ck.label("Badge_Num", "3", (0, 0.05, 0), 0.24, M["white"], depth=0.012, parent=badge)
    ANIM["bell"], ANIM["badge"] = pivot, badge


def build_characters():
    walkers = []
    specs = [("Code", M["white"], "code"), ("Doc", M["red"], "doc"), ("Blue", M["blue"], None)]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.15), radii=(2.3, 0.66)))
    return walkers


def animate(cam_rig, walkers):
    note_z = ANIM["note"].location.z
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        ph = T % 1.0
        for icon, k in ANIM["icons"]:  # 4초에 한 바퀴 차례로 톡
            u = (ph * 12 - k) % 12
            pop = math.sin(math.pi * u / 1.6) if u < 1.6 else 0.0
            icon.location.y = 0.08 + 0.1 * pop
            icon.scale = (1 + 0.25 * pop,) * 3
            icon.keyframe_insert("location", index=1, frame=f)
            icon.keyframe_insert("scale", frame=f)
        # 알림: 0.1~0.2 사이 내려와 0.75 까지 머물고 0.85 까지 사라진다
        if ph < 0.1:
            a = 0.0
        elif ph < 0.2:
            a = math.sin(math.pi / 2 * (ph - 0.1) / 0.1)
        elif ph < 0.75:
            a = 1.0
        elif ph < 0.85:
            a = 1 - (ph - 0.75) / 0.1
        else:
            a = 0.0
        n = ANIM["note"]
        n.location.z = note_z + 0.25 * (1 - a)
        n.scale = (a, a, a)
        n.keyframe_insert("location", index=2, frame=f)
        n.keyframe_insert("scale", frame=f)
        # 종: 알림이 올 때 크게 흔들리고 잦아든다
        ring = math.exp(-4 * ((ph - 0.1) % 1.0)) * math.sin(2 * math.pi * 6 * (ph - 0.1))
        ANIM["bell"].rotation_euler.x = math.radians(22) * ring
        ANIM["bell"].keyframe_insert("rotation_euler", index=0, frame=f)
        b = 1 + 0.15 * max(0.0, math.sin(2 * math.pi * 2 * T))
        ANIM["badge"].scale = (b, b, b)
        ANIM["badge"].keyframe_insert("scale", frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    phone()
    tablet(2.2, 0.3)
    bell(-2.15, 0.25)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)

    print("STILL", kit.render_still("phone_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("phone_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
