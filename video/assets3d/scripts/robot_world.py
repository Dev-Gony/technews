"""9:16 '손 흔드는 로봇, 자율주행차, 드론' 장면 (로봇·휴머노이드·자율주행·드론·물리 AI 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 가운데 뒤: 네모 머리 로봇 (금색 눈이 깜빡이고, 안테나 끝이 빛나고, 한 팔을 흔든다)
- 로봇 둘레: 원판 위 둥근 길을 자율주행차가 한 바퀴 돈다 (지붕 라이다가 돌며 빛난다)
- 오른쪽 위: 프로펠러 4개가 도는 드론이 둥실, 왼쪽 앞: 주황 고깔
- 앞: 꼬마들이 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/robot_world.py
    blender -b -P assets3d/scripts/robot_world.py -- --still-only
출력: video/public/assets3d/robot_world.png, robot_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"props": []}

BOT = (0.1, -1.35)
ROAD_C, ROAD_R = (0.1, -1.1), (2.35, 1.05)


def robot():
    kit.use_collection("Robot")
    rig = kit.empty("Robot")
    rig.location = (BOT[0], BOT[1], 0)
    rig.rotation_euler.z = math.radians(-20)
    rig.scale = (1.1,) * 3
    metal = kit.material("M_RobotBody", "#D8D4CA", 0.35, 0.5)
    for sx in (-1, 1):
        kit.box(f"Bot_Leg{sx}", (sx * 0.22, 0, 0.3), (0.2, 0.24, 0.6), M["steel"], bevel=0.05, parent=rig)
        kit.box(f"Bot_Foot{sx}", (sx * 0.22, 0.06, 0.06), (0.3, 0.4, 0.12), M["ink"], bevel=0.04, parent=rig)
    body = kit.empty("Bot_Body", parent=rig)
    body.location = (0, 0, 0.6)
    kit.box("Bot_Torso", (0, 0, 0.42), (0.85, 0.55, 0.85), metal, bevel=0.1, segments=4, parent=body)
    kit.box("Bot_Chest", (0, 0.28, 0.48), (0.42, 0.02, 0.3), M["screenBg"], bevel=0.04, parent=body)
    heart = ck.glow("BotHeart", "red", 2.0)
    ck.sphere("Bot_Heart", (0, 0.3, 0.48), 0.07, heart, segments=16, parent=body)
    kit.cylinder("Bot_Neck", (0, 0, 0.9), 0.1, 0.12, M["steel"], bevel=0.02, vertices=24, parent=body)
    head = kit.empty("Bot_Head", parent=body)
    head.location = (0, 0, 1.25)
    kit.box("Bot_Skull", (0, 0, 0), (0.75, 0.6, 0.55), metal, bevel=0.12, segments=4, parent=head)
    kit.box("Bot_Face", (0, 0.3, 0), (0.58, 0.02, 0.36), M["screenBg"], bevel=0.06, parent=head)
    eye = ck.glow("BotEye", "gold", 2.2)
    eyes = [kit.box(f"Bot_Eye{sx}", (sx * 0.14, 0.315, 0.02), (0.1, 0.01, 0.12), eye, bevel=0.03, parent=head) for sx in (-1, 1)]
    for sx in (-1, 1):
        kit.cylinder(f"Bot_Ear{sx}", (sx * 0.4, 0, 0), 0.1, 0.08, M["red"], bevel=0.02, vertices=24, axis="X", parent=head)
    kit.cylinder("Bot_Antenna", (0, 0, 0.4), 0.02, 0.25, M["ink"], bevel=0, vertices=12, parent=head)
    tip = ck.glow("BotTip", "red", 2.5)
    ck.sphere("Bot_AntTip", (0, 0, 0.55), 0.06, tip, segments=16, parent=head)
    arms = []
    for sx in (-1, 1):
        sh = kit.empty(f"Bot_Shoulder{sx}", parent=body)
        sh.location = (sx * 0.5, 0, 0.72)
        kit.box(f"Bot_Arm{sx}", (sx * 0.05, 0, -0.28), (0.16, 0.18, 0.55), M["steel"], bevel=0.05, parent=sh)
        ck.sphere(f"Bot_Hand{sx}", (sx * 0.05, 0, -0.6), 0.11, M["red"], parent=sh, segments=20)
        arms.append(sh)
    ANIM.update(eyes=eyes, tip=tip, heart=heart, wave=arms[1], head=head)


def road():
    kit.use_collection("Road")
    cx, cy = ROAD_C
    rx, ry = ROAD_R
    asphalt = kit.material("M_Road", "#4A4842", 0.8, 0.1)
    n = 96
    outer = [(cx + (rx + 0.28) * math.cos(2 * math.pi * i / n), cy + (ry + 0.28) * math.sin(2 * math.pi * i / n), 0.012) for i in range(n + 1)]
    # 길: 타원 둘레를 따라 가는 띠 (옆 방향 = 바깥쪽)
    import bmesh

    me = bpy.data.meshes.new("Road")
    bm = bmesh.new()
    rows = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rows.append((bm.verts.new((cx + (rx - 0.28) * math.cos(a), cy + (ry - 0.28) * math.sin(a), 0.01)),
                     bm.verts.new((cx + (rx + 0.28) * math.cos(a), cy + (ry + 0.28) * math.sin(a), 0.01))))
    for i in range(n):
        a0, b0 = rows[i]
        a1, b1 = rows[(i + 1) % n]
        bm.faces.new((a0, b0, b1, a1))
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("Road", me)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(asphalt)
    sol = obj.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.02
    for k in range(24):  # 가운데 점선
        a = 2 * math.pi * (k + 0.5) / 24
        d = kit.box(f"Road_Dash{k}", (cx + rx * math.cos(a), cy + ry * math.sin(a), 0.03), (0.2, 0.05, 0.01), M["white"], bevel=0)
        d.rotation_euler.z = math.atan2(ry * math.cos(a), -rx * math.sin(a))
    del outer


def car():
    kit.use_collection("Car")
    rig = kit.empty("Car")
    body = kit.empty("Car_Body", parent=rig)
    kit.box("Car_Lower", (0, 0, 0.2), (0.48, 0.85, 0.24), M["white"], bevel=0.08, segments=4, parent=body)
    kit.box("Car_Cabin", (0, -0.05, 0.4), (0.42, 0.5, 0.22), M["white"], bevel=0.08, segments=4, parent=body)
    glass = kit.material("M_CarGlass", "#3E5568", 0.15, 0.7)
    kit.box("Car_Glass", (0, -0.05, 0.41), (0.44, 0.44, 0.15), glass, bevel=0.05, parent=body)
    kit.box("Car_Stripe", (0, 0, 0.24), (0.49, 0.86, 0.05), M["red"], bevel=0.02, parent=body)
    for sx in (-1, 1):
        for sy in (-1, 1):
            kit.cylinder(f"Car_Wheel{sx}{sy}", (sx * 0.24, sy * 0.27, 0.1), 0.1, 0.08, M["ink"], bevel=0.02, vertices=24, axis="X", parent=body)
        kit.box(f"Car_Light{sx}", (sx * 0.15, 0.43, 0.22), (0.08, 0.02, 0.05), M["gold"], bevel=0.01, parent=body)
    lidar = kit.empty("Car_Lidar", parent=body)
    lidar.location = (0, -0.05, 0.56)
    kit.cylinder("Lidar_Base", (0, 0, 0), 0.09, 0.08, M["ink"], bevel=0.02, vertices=24, parent=lidar)
    beam = ck.glow("Lidar", "red", 2.5)
    kit.box("Lidar_Eye", (0, 0.085, 0.01), (0.07, 0.02, 0.03), beam, bevel=0, parent=lidar)
    rig.scale = (1.15,) * 3
    ANIM.update(car=rig, lidar=lidar)


def drone(x, y, z):
    kit.use_collection("Drone")
    rig = kit.empty("Drone")
    rig.location = (x, y, z)
    rig.rotation_euler.z = math.radians(-20)
    rig.scale = (1.7,) * 3
    kit.box("Drone_Body", (0, 0, 0), (0.42, 0.42, 0.14), M["ink"], bevel=0.05, parent=rig)
    kit.cylinder("Drone_Cam", (0, 0.1, -0.1), 0.07, 0.08, M["gold"], bevel=0.02, vertices=24, parent=rig)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        ax, ay = 0.42 * math.cos(a), 0.42 * math.sin(a)
        arm = kit.box(f"Drone_Arm{k}", (ax / 2, ay / 2, 0), (0.6, 0.06, 0.04), M["steel"], bevel=0.01, parent=rig)
        arm.rotation_euler.z = a
        kit.cylinder(f"Drone_Motor{k}", (ax, ay, 0.04), 0.05, 0.08, M["red"], bevel=0.01, vertices=16, parent=rig)
        prop = kit.empty(f"Drone_Prop{k}", parent=rig)
        prop.location = (ax, ay, 0.09)
        kit.box(f"Drone_Blade{k}", (0, 0, 0), (0.38, 0.05, 0.01), M["white"], bevel=0.005, parent=prop)
        ANIM["props"].append((prop, 1 if k % 2 else -1))
    ANIM["drone"] = (rig, z)


def cone(x, y):
    kit.use_collection("Cone")
    orange = kit.material("M_Cone", "#E8743B", 0.5, 0.3)
    kit.box("Cone_Base", (x, y, 0.03), (0.5, 0.5, 0.06), M["ink"], bevel=0.02)
    ck.cone("Cone_Body", (x, y, 0.34), 0.2, 0.04, 0.6, orange)
    kit.cylinder("Cone_Stripe", (x, y, 0.36), 0.115, 0.08, M["white"], bevel=0, vertices=32)


def build_characters():
    walkers = []
    specs = [("White", M["white"], None), ("Gold", M["gold"], "key"), ("Blue", M["blue"], None)]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.4), radii=(2.2, 0.5)))
    return walkers


def animate(cam_rig, walkers):
    cx, cy = ROAD_C
    rx, ry = ROAD_R
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        # 로봇: 오른팔 흔들기, 눈 깜빡 (4초에 한 번), 고개 까딱
        ANIM["wave"].rotation_euler.y = -math.radians(145) + math.radians(25) * math.sin(2 * math.pi * 4 * T)
        ANIM["wave"].keyframe_insert("rotation_euler", index=1, frame=f)
        ph = T % 1.0
        blink = 0.15 if 0.5 < ph < 0.55 else 1.0
        for e in ANIM["eyes"]:
            e.scale.z = blink
            e.keyframe_insert("scale", index=2, frame=f)
        ANIM["head"].rotation_euler.y = math.radians(6) * math.sin(2 * math.pi * T)
        ANIM["head"].keyframe_insert("rotation_euler", index=1, frame=f)
        ck.pulse(f, T, ANIM["tip"], 0.5, 3.0, 2, square=True)
        ck.pulse(f, T, ANIM["heart"], 1.0, 2.6, 3)
        # 차: 루프 동안 길을 한 바퀴
        a = 2 * math.pi * t + 0.6
        c = ANIM["car"]
        c.location = (cx + rx * math.cos(a), cy + ry * math.sin(a), 0.02)
        c.rotation_euler.z = math.atan2(ry * math.cos(a), -rx * math.sin(a)) - math.pi / 2
        c.keyframe_insert("location", frame=f)
        c.keyframe_insert("rotation_euler", index=2, frame=f)
        ANIM["lidar"].rotation_euler.z = 2 * math.pi * 12 * t
        ANIM["lidar"].keyframe_insert("rotation_euler", index=2, frame=f)
        rig, z = ANIM["drone"]
        rig.location.z = z + 0.12 * math.sin(2 * math.pi * T)
        rig.rotation_euler.x = math.radians(5) * math.sin(2 * math.pi * T + 1)
        rig.keyframe_insert("location", index=2, frame=f)
        rig.keyframe_insert("rotation_euler", index=0, frame=f)
        for prop, d in ANIM["props"]:
            prop.rotation_euler.z = d * 2 * math.pi * 30 * t
            prop.keyframe_insert("rotation_euler", index=2, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    road()
    robot()
    car()
    drone(-1.85, -1.2, 2.0)
    cone(2.4, 0.6)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)

    print("STILL", kit.render_still("robot_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("robot_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
