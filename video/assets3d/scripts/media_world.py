"""9:16 '이젤 그림과 슬레이트, 캠코더' 장면 (이미지·영상 생성 AI, 사진, 동영상, 디자인 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 가운데 뒤: 이젤 위 큰 캔버스 (산·해·구름 그림). 해가 숨 쉬듯 빛나고, 붓이 캔버스 앞에서 오간다
- 캔버스 둘레에 사진 3장이 떠서 오르내린다
- 왼쪽 앞: 4초에 한 번 '딱' 닫히는 슬레이트(클래퍼보드)
- 오른쪽 앞: 릴 두 개가 도는 캠코더와 빨간 녹화등
- 앞: 꼬마들이 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/media_world.py
    blender -b -P assets3d/scripts/media_world.py -- --still-only
출력: video/public/assets3d/media_world.png, media_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"frames": [], "reels": []}  # frames = 떠 있는 사진

CANVAS_W, CANVAS_H = 2.2, 1.55
CANVAS_Z = 0.75  # 캔버스 아래 끝


def easel():
    kit.use_collection("Easel")
    rig = kit.empty("Easel")
    rig.location = (0.1, -1.45, 0)
    rig.rotation_euler.z = math.radians(-20)
    wood = kit.material("M_EaselWood", "wood", 0.6, 0.2)
    for sx in (-1, 1):
        leg = kit.box(f"Easel_Leg{sx}", (sx * 0.75, -0.02, 1.15), (0.09, 0.09, 2.35), wood, bevel=0.02, parent=rig)
        leg.rotation_euler.y = math.radians(sx * 9)
    back = kit.box("Easel_Back", (0, -0.45, 1.05), (0.08, 0.08, 2.2), wood, bevel=0.02, parent=rig)
    back.rotation_euler.x = math.radians(-22)
    kit.box("Easel_Shelf", (0, 0.2, CANVAS_Z - 0.06), (1.9, 0.26, 0.08), wood, bevel=0.02, parent=rig)
    c = kit.empty("Canvas", parent=rig)
    c.location = (0, 0.12, CANVAS_Z)
    c.rotation_euler.x = math.radians(6)
    zc = CANVAS_H / 2
    kit.box("Canvas_Frame", (0, 0, zc), (CANVAS_W, 0.1, CANVAS_H), M["ink"], bevel=0.04, parent=c)
    kit.box("Canvas_Sky", (0, 0.052, zc), (CANVAS_W - 0.16, 0.01, CANVAS_H - 0.16), kit.material("M_Sky", "#BFD9EA", 0.6, 0.2), bevel=0.01, parent=c)
    # 산 두 개 (빨강, 먹색) + 땅
    ck.extruded("Canvas_Hill1", [(-1.02, 0.08), (0.2, 0.08), (-0.35, 0.95)], 0.02, M["sage"], center=(0, 0.065, 0), bevel=0.004, parent=c)
    ck.extruded("Canvas_Hill2", [(-0.3, 0.08), (1.02, 0.08), (1.02, 0.3), (0.45, 1.12)], 0.02, M["red"], center=(0, 0.075, 0), bevel=0.004, parent=c)
    kit.box("Canvas_Ground", (0, 0.085, 0.16), (CANVAS_W - 0.16, 0.01, 0.16), M["sageDark"], bevel=0, parent=c)
    sun = ck.glow("Sun", "gold", 1.4)
    kit.cylinder("Canvas_Sun", (-0.62, 0.075, 1.15), 0.2, 0.02, sun, bevel=0.005, vertices=40, axis="Y", parent=c)
    for k, (dx, dz, r) in enumerate(((0.25, 1.22, 0.12), (0.4, 1.25, 0.15), (0.56, 1.21, 0.11))):
        kit.cylinder(f"Canvas_Cloud{k}", (dx, 0.08, dz), r, 0.02, M["white"], bevel=0.005, vertices=24, axis="Y", parent=c)
    ANIM["sun"] = sun
    brush = kit.empty("Brush", parent=c)
    brush.location = (0.2, 0.32, 0.7)
    b = kit.empty("Brush_Tilt", parent=brush)
    b.rotation_euler = (math.radians(-35), math.radians(35), 0)
    kit.cylinder("Brush_Handle", (0, 0, 0.35), 0.035, 0.6, M["red"], bevel=0.01, vertices=16, parent=b)
    kit.cylinder("Brush_Ferrule", (0, 0, 0.02), 0.045, 0.1, M["steel"], bevel=0.01, vertices=16, parent=b)
    ck.cone("Brush_Tip", (0, 0, -0.1), 0.0, 0.05, 0.16, M["gold"], vertices=16, parent=b)
    ANIM["brush"] = brush


def photos():
    """캔버스 둘레에 떠 있는 사진 3장 (흰 테두리 + 색 그림). 천천히 오르내리며 흔들린다."""
    kit.use_collection("Photos")
    specs = [((1.55, -1.0, 1.55), 14, M["blue"], M["gold"]), ((-1.45, -1.25, 1.85), -12, M["red"], M["white"]), ((-1.75, -0.35, 0.95), 8, M["gold"], M["red"])]
    for k, (pos, tilt, img, dot) in enumerate(specs):
        rig = kit.empty(f"Photo{k}")
        rig.location = pos
        rig.rotation_euler = (0, math.radians(tilt), math.radians(-20))
        kit.box(f"Photo{k}_Card", (0, 0, 0), (0.62, 0.04, 0.72), M["white"], bevel=0.02, parent=rig)
        kit.box(f"Photo{k}_Img", (0, 0.022, 0.06), (0.5, 0.01, 0.48), img, bevel=0.01, parent=rig)
        kit.cylinder(f"Photo{k}_Dot", (0.12, 0.03, 0.16), 0.08, 0.01, dot, bevel=0, vertices=24, axis="Y", parent=rig)
        ANIM["frames"].append((rig, k, pos[2], tilt))


def clapper(x, y):
    kit.use_collection("Clapper")
    rig = kit.empty("Clapper")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-25)
    kit.box("Clap_Board", (0, 0, 0.42), (1.05, 0.1, 0.8), M["ink"], bevel=0.04, parent=rig)
    for k in range(3):
        kit.box(f"Clap_Ln{k}", (0, 0.052, 0.62 - k * 0.2), (0.85, 0.01, 0.03), M["white"], bevel=0, parent=rig)
    arm_rig = kit.empty("Clap_Hinge", parent=rig)
    arm_rig.location = (0.5, 0, 0.86)
    arm = kit.empty("Clap_Arm", parent=arm_rig)
    kit.box("Clap_ArmBody", (-0.52, 0, 0.07), (1.05, 0.1, 0.14), M["white"], bevel=0.03, parent=arm)
    for k in range(4):
        st = kit.box(f"Clap_Stripe{k}", (-0.15 - k * 0.24, 0.052, 0.07), (0.1, 0.01, 0.2), M["ink"], bevel=0, parent=arm)
        st.rotation_euler.y = math.radians(30)
    kit.box("Clap_Base", (-0.0, 0, 0.9), (1.05, 0.1, 0.1), M["white"], bevel=0.02, parent=rig)
    for k in range(4):
        st = kit.box(f"Clap_BStripe{k}", (0.35 - k * 0.24, 0.052, 0.9), (0.1, 0.01, 0.14), M["ink"], bevel=0, parent=rig)
        st.rotation_euler.y = math.radians(-30)
    ANIM["clap"] = arm_rig
    arm_rig.location.z = 0.96


def camcorder(x, y):
    kit.use_collection("Camera")
    rig = kit.empty("Cam")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-55)
    for k in range(3):
        leg = kit.box(f"Cam_Leg{k}", (0.22 * math.cos(k * 2.1), 0.22 * math.sin(k * 2.1), 0.32), (0.05, 0.05, 0.7), M["ink"], bevel=0.01, parent=rig)
        leg.rotation_euler = (math.radians(14) * math.sin(k * 2.1), -math.radians(14) * math.cos(k * 2.1), 0)
    body_z = 0.85
    kit.box("Cam_Body", (0, 0, body_z), (0.55, 0.9, 0.5), M["steel"], bevel=0.06, parent=rig)
    kit.cylinder("Cam_Lens", (0, 0.58, body_z), 0.18, 0.3, M["ink"], bevel=0.03, vertices=32, axis="Y", parent=rig)
    kit.cylinder("Cam_Glass", (0, 0.74, body_z), 0.13, 0.03, kit.material("M_LensGlass", "#4B6E8E", 0.1, 0.8), bevel=0.01, vertices=32, axis="Y", parent=rig)
    rec = ck.glow("Rec", "red", 2.0)
    ck.sphere("Cam_Rec", (0.2, 0.3, body_z + 0.27), 0.05, rec, segments=16, parent=rig)
    ANIM["rec"] = rec
    for k, dy in enumerate((-0.22, 0.2)):
        reel = kit.empty(f"Reel{k}", parent=rig)
        reel.location = (0, dy, body_z + 0.5)
        kit.cylinder(f"Reel{k}_Disc", (0, 0, 0), 0.25, 0.06, M["ink"], bevel=0.015, vertices=40, axis="X", parent=reel)
        for h in range(3):
            a = h * 2 * math.pi / 3
            kit.cylinder(f"Reel{k}_Hole{h}", (0.032, 0.12 * math.cos(a), 0.12 * math.sin(a)), 0.05, 0.01, M["paper"], bevel=0, vertices=16, axis="X", parent=reel)
        kit.cylinder(f"Reel{k}_Hub", (0.035, 0, 0), 0.04, 0.01, M["gold"], bevel=0, vertices=16, axis="X", parent=reel)
        ANIM["reels"].append(reel)


def build_characters():
    walkers = []
    specs = [("White", M["white"], None), ("Red", M["red"], "doc"), ("Blue", M["blue"], None)]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.2), radii=(2.3, 0.62)))
    return walkers


def animate(cam_rig, walkers):
    bx = ANIM["brush"].location.x
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        ck.pulse(f, T, ANIM["sun"], 1.0, 2.6, 2)
        br = ANIM["brush"]
        br.location.x = bx + 0.3 * math.sin(2 * math.pi * 2 * T)
        br.location.z = 0.7 + 0.12 * math.sin(2 * math.pi * 4 * T)
        br.keyframe_insert("location", frame=f)
        for rig, k, z, tilt in ANIM["frames"]:
            rig.location.z = z + 0.08 * math.sin(2 * math.pi * T + k * 2.1)
            rig.rotation_euler.y = math.radians(tilt + 4 * math.sin(2 * math.pi * 2 * T + k))
            rig.keyframe_insert("location", index=2, frame=f)
            rig.keyframe_insert("rotation_euler", index=1, frame=f)
        # 슬레이트: 4초에 한 번 열렸다가 딱
        ph = T % 1.0
        if ph < 0.6:
            o = math.sin(math.pi / 2 * ph / 0.6)
        elif ph < 0.68:
            o = 1 - ((ph - 0.6) / 0.08) ** 2
        else:
            o = 0.0
        ANIM["clap"].rotation_euler.y = -math.radians(32) * o
        ANIM["clap"].keyframe_insert("rotation_euler", index=1, frame=f)
        ck.pulse(f, T, ANIM["rec"], 0.2, 3.0, 4, square=True)
        for reel in ANIM["reels"]:
            reel.rotation_euler.x = 2 * math.pi * 3 * t
            reel.keyframe_insert("rotation_euler", index=0, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    easel()
    photos()
    clapper(2.2, 0.35)
    camcorder(-2.15, 0.35)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("media_world", {
        "canvas": (obj["Canvas"], "object", "이젤 위 큰 캔버스에 산·해 그림, 붓이 오간다 (생성된 이미지·작품)"),
        "photo": (obj["Photo0"], "object", "공중에 떠 오르내리는 사진 한 장 (사진·생성 결과물)"),
        "clapper": (obj["Clapper"], "object", "4초마다 딱 닫히는 슬레이트 (영상 촬영·영상 생성 시작)"),
        "camcorder": (obj["Cam"], "object", "릴이 돌고 빨간 녹화등이 켜진 캠코더 (동영상·녹화)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 빈손으로 걸어 다닌다 (사용자·크리에이터)"),
        "red": (walkers[1].rig, "character", "빨간 꼬마: 문서를 들고 걸어 다닌다 (프롬프트·기획안)"),
        "blue": (walkers[2].rig, "character", "파란 꼬마: 빈손으로 걸어 다닌다 (사용자·디자이너)"),
    }, FRAMES, "media3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("media_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("media_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
