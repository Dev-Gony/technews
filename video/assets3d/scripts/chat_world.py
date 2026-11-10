"""9:16 '큰 편지 봉투와 말풍선, 종이비행기' 장면 (메일·메신저·채팅·슬랙·알림·소통 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 가운데 뒤: 비스듬히 선 큰 편지 봉투. 4초에 한 번 뚜껑이 열리고 편지가 쏙 올라왔다 들어간다 (빨간 봉인)
- 봉투 위: 말풍선 3개가 둥실 떠 있고, 가운데 말풍선의 점 3개가 차례로 통통 (입력 중)
- 둘레: 종이비행기가 원판 위를 크게 한 바퀴 돈다
- 앞: 꼬마들이 문서 / 편지를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/chat_world.py
    blender -b -P assets3d/scripts/chat_world.py -- --still-only
출력: video/public/assets3d/chat_world.png, chat_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"bubbles": [], "dots": []}

ENV_W, ENV_H = 2.3, 1.45
ENV_Z = 0.25


def envelope():
    kit.use_collection("Envelope")
    rig = kit.empty("Envelope")
    rig.location = (0.1, -1.2, 0)
    rig.rotation_euler.z = math.radians(-20)
    kit.box("Env_Stand", (0, 0.1, 0.1), (1.6, 0.6, 0.2), M["ink"], bevel=0.05, parent=rig)
    body = kit.empty("Env_Body", parent=rig)
    body.location = (0, 0, ENV_Z)
    body.rotation_euler.x = math.radians(10)
    zc = ENV_H / 2
    kit.box("Env_Back", (0, -0.06, zc), (ENV_W, 0.06, ENV_H), M["paper"], bevel=0.03, parent=body)
    # 안의 편지 (위로 올라온다)
    letter = kit.empty("Letter", parent=body)
    letter.location = (0, -0.01, 0.15)
    kit.box("Letter_Paper", (0, 0, 0.6), (ENV_W - 0.3, 0.02, 1.2), M["white"], bevel=0.01, parent=letter)
    for k in range(3):
        kit.box(f"Letter_Ln{k}", (0, 0.012, 1.05 - k * 0.14), (1.3 - 0.25 * k, 0.005, 0.05), M["ink"] if k else M["red"], bevel=0, parent=letter)
    ANIM["letter"] = letter
    # 앞면: 양옆 삼각 + 아래 삼각 (봉투 모양)
    w2 = ENV_W / 2
    ck.extruded("Env_FrontL", [(-w2, 0), (0, ENV_H * 0.42), (-w2, ENV_H)], 0.05, M["white"], center=(0, 0.02, 0), bevel=0.01, parent=body)
    ck.extruded("Env_FrontR", [(w2, 0), (w2, ENV_H), (0, ENV_H * 0.42)], 0.05, M["white"], center=(0, 0.02, 0), bevel=0.01, parent=body)
    ck.extruded("Env_FrontB", [(-w2, 0), (w2, 0), (0, ENV_H * 0.5)], 0.05, M["paper"], center=(0, 0.06, 0), bevel=0.01, parent=body)
    # 뚜껑 (윗모서리 축으로 열린다)
    hinge = kit.empty("Env_Hinge", parent=body)
    hinge.location = (0, -0.03, ENV_H)
    ck.extruded("Env_Flap", [(-w2, 0), (w2, 0), (0, -ENV_H * 0.55)], 0.05, M["white"], center=(0, 0.0, 0), bevel=0.01, parent=hinge)
    kit.cylinder("Env_Seal", (0, 0.05, -ENV_H * 0.44), 0.17, 0.05, M["red"], bevel=0.02, vertices=32, axis="Y", parent=hinge)
    ANIM["flap"] = hinge


def bubbles():
    kit.use_collection("Bubbles")
    specs = [((1.7, -0.55, 2.0), 0.95, 0.55, M["white"], 1), ((-0.15, -0.6, 2.55), 1.1, 0.6, M["gold"], 0), ((-1.9, -0.6, 1.75), 0.9, 0.5, M["red"], -1)]
    for k, (pos, w, h, mat, tail) in enumerate(specs):
        rig = kit.empty(f"Bubble{k}")
        rig.location = pos
        rig.rotation_euler.z = math.radians(-20)
        kit.box(f"Bubble{k}_Body", (0, 0, 0), (w, 0.16, h), mat, bevel=min(w, h) * 0.45, segments=8, parent=rig)
        ck.extruded(f"Bubble{k}_Tail", [(tail * 0.1, -h / 2 + 0.05), (tail * 0.35 + 0.0, -h / 2 + 0.05), (tail * 0.4 + (0.12 if tail == 0 else 0), -h / 2 - 0.25)], 0.12, mat, center=(0, 0, 0), bevel=0.02, parent=rig)
        if k == 1:
            for d in range(3):
                dot = ck.sphere(f"Dot{d}", (-0.3 + d * 0.3, 0.09, 0), 0.08, M["ink"], parent=rig, segments=16)
                ANIM["dots"].append((dot, d))
        else:
            for i, lw in enumerate((w * 0.55, w * 0.35)):
                kit.box(f"Bubble{k}_Ln{i}", (0, 0.085, 0.07 - i * 0.15), (lw, 0.01, 0.06), M["ink"] if mat is not M["red"] else M["white"], bevel=0, parent=rig)
        ANIM["bubbles"].append((rig, pos[2], k))


def plane():
    kit.use_collection("Plane")
    rig = kit.empty("Plane")
    body = kit.empty("Plane_Body", parent=rig)
    body.location = (0, 0, 0)
    # 종이비행기: 앞 = +y. 두 날개 + 가운데 접힌 몸
    ck.extruded("Plane_WingL", [(0.0, 0.0), (0.42, -0.05), (0.0, 0.6)], 0.01, M["white"], center=(0, 0, 0), bevel=0.003, parent=body).rotation_euler = (math.radians(90), 0, 0)
    ck.extruded("Plane_WingR", [(0.0, 0.0), (0.0, 0.6), (-0.42, -0.05)], 0.01, M["white"], center=(0, 0, 0), bevel=0.003, parent=body).rotation_euler = (math.radians(90), 0, 0)
    ck.extruded("Plane_Keel", [(0.0, 0.0), (0.0, 0.6), (-0.12, -0.05)], 0.01, M["paper"], center=(0, 0, 0), bevel=0.003, parent=body).rotation_euler = (math.radians(90), 0, math.radians(90))
    body.scale = (1.3,) * 3
    ANIM["plane"] = rig


def build_characters():
    walkers = []
    specs = [("Doc", M["white"], "doc"), ("Blue", M["blue"], "doc"), ("Red", M["red"], None)]
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
        ph = T % 1.0
        # 뚜껑: 0.05~0.25 열림, 0.75~0.95 닫힘. 편지: 열린 동안 올라온다
        if ph < 0.05:
            o = 0.0
        elif ph < 0.25:
            o = math.sin(math.pi / 2 * (ph - 0.05) / 0.2)
        elif ph < 0.75:
            o = 1.0
        elif ph < 0.95:
            o = math.cos(math.pi / 2 * (ph - 0.75) / 0.2)
        else:
            o = 0.0
        ANIM["flap"].rotation_euler.x = -math.radians(170) * o
        ANIM["flap"].keyframe_insert("rotation_euler", index=0, frame=f)
        up = max(0.0, min(1.0, (ph - 0.25) / 0.15)) if ph < 0.6 else max(0.0, 1 - (ph - 0.6) / 0.15)
        ANIM["letter"].location.z = 0.15 + 0.5 * math.sin(math.pi / 2 * up)
        ANIM["letter"].keyframe_insert("location", index=2, frame=f)
        for rig, z, k in ANIM["bubbles"]:
            rig.location.z = z + 0.08 * math.sin(2 * math.pi * T + k * 2.1)
            rig.keyframe_insert("location", index=2, frame=f)
        for dot, d in ANIM["dots"]:
            dot.location.z = 0.07 * max(0.0, math.sin(2 * math.pi * 3 * T - d * 0.9))
            dot.keyframe_insert("location", index=2, frame=f)
        # 종이비행기: 루프 동안 원판 위를 한 바퀴 (기울어 돈다)
        a = 2 * math.pi * t
        p = ANIM["plane"]
        p.location = (2.6 * math.cos(a), 0.3 + 1.7 * math.sin(a), 1.3 + 0.25 * math.sin(2 * a))
        dx, dy = -2.6 * math.sin(a), 1.7 * math.cos(a)
        p.rotation_euler = (math.radians(6) * math.cos(2 * a), math.radians(-18), math.atan2(dy, dx) - math.pi / 2)
        p.keyframe_insert("location", frame=f)
        p.keyframe_insert("rotation_euler", frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    envelope()
    bubbles()
    plane()
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)

    print("STILL", kit.render_still("chat_world", resolution=1080, height=1920, frame=60))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("chat_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
