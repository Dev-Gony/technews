"""9:16 '발사대 위 로켓' 장면 (새 모델·제품 출시, 공개, 베타, 정식 출시 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 가운데 뒤: 발사대 위에 떠오른 흰 로켓(빨간 코·날개, 금색 창). 아래 불꽃이 일렁이고 연기 뭉치가 퍼진다
- 로켓 옆: 먹색 발사탑과 로켓을 잡은 금색 팔
- 왼쪽 앞: 카운트다운 화면 (3 → 2 → 1 이 4초에 한 번)
- 오른쪽 앞: 뚜껑이 들썩이는 선물 상자, 금색 반짝이가 튀어나온다
- 앞: 꼬마들이 문서 / 코드를 들고 돌고, 한 명은 발사대 앞에서 통통

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/launch_world.py
    blender -b -P assets3d/scripts/launch_world.py -- --still-only
출력: video/public/assets3d/launch_world.png, launch_world_loop.webm (1080x1920, 투명 배경)
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import chibi_kit as ck  # noqa: E402
import iso_kit as kit  # noqa: E402

FRAMES = 360  # 12초 루프
STEPS = 36
SIZE = 2.1
M = ck.M
ANIM = {"puffs": [], "digits": []}

PAD = (-0.1, -1.15)
BODY_R = 0.42
BODY_Z0, BODY_Z1 = 0.62, 1.72


def rocket():
    kit.use_collection("Rocket")
    x, y = PAD
    kit.cylinder("Pad", (x, y, 0.09), 1.0, 0.18, M["ink"], bevel=0.05, vertices=64)
    kit.cylinder("Pad_Ring", (x, y, 0.19), 0.8, 0.03, M["gold"], bevel=0.01, vertices=64)
    rig = kit.empty("Rocket")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-20)
    h = BODY_Z1 - BODY_Z0
    kit.cylinder("Rocket_Body", (0, 0, BODY_Z0 + h / 2), BODY_R, h, M["white"], bevel=0.04, vertices=64, parent=rig)
    ck.cone("Rocket_Nose", (0, 0, BODY_Z1 + 0.33), BODY_R, 0.0, 0.66, M["red"], parent=rig)
    kit.cylinder("Rocket_Band", (0, 0, BODY_Z1 - 0.02), BODY_R + 0.015, 0.08, M["red"], bevel=0.015, vertices=64, parent=rig)
    kit.cylinder("Rocket_Skirt", (0, 0, BODY_Z0 + 0.05), BODY_R + 0.02, 0.1, M["ink"], bevel=0.02, vertices=64, parent=rig)
    # 창: 카메라 쪽(+y)으로 금테 + 하늘색 유리
    win = (0, BODY_R - 0.01, BODY_Z0 + h * 0.62)
    ck.torus("Rocket_WinRing", win, 0.15, 0.035, M["gold"], rotation=(math.pi / 2, 0, 0), parent=rig)
    kit.cylinder("Rocket_Win", win, 0.14, 0.04, kit.material("M_RocketGlass", "glass", 0.15, 0.6), bevel=0.01, vertices=32, axis="Y", parent=rig)
    # 날개 3장: xz 윤곽(x = 바깥쪽, z = 위)을 y 로 얇게 밀고, 몸통 둘레로 돌려 꽂는다
    for k in range(3):
        fin = kit.empty(f"Rocket_FinRig{k}", parent=rig)
        fin.rotation_euler.z = math.radians(30 + k * 120)  # 하나는 뒤, 둘은 양옆 (창을 가리지 않게)
        ck.extruded(f"Rocket_Fin{k}", [(0.0, -0.05), (0.34, -0.28), (0.34, -0.06), (0.0, 0.55)], 0.06, M["red"],
                    center=(BODY_R - 0.04, 0, BODY_Z0 + 0.05), bevel=0.015, parent=fin)
    kit.cylinder("Rocket_Nozzle", (0, 0, BODY_Z0 - 0.08), 0.2, 0.16, M["steel"], bevel=0.02, vertices=32, parent=rig)
    flame = kit.empty("Flame", parent=rig)
    flame.location = (0, 0, BODY_Z0 - 0.16)
    ck.cone("Flame_Out", (0, 0, -0.22), 0.0, 0.2, 0.44, ck.glow("FlameGold", "gold", 3.2), parent=flame)
    ck.cone("Flame_In", (0, 0, -0.14), 0.0, 0.11, 0.28, ck.glow("FlameRed", "red", 3.0), parent=flame)
    ANIM["rocket"], ANIM["flame"] = rig, flame
    # 연기 뭉치 (바깥으로 퍼지며 커졌다 사라진다)
    smoke = kit.material("M_Smoke", "#F1EEE6", 0.9, 0.1)
    for i in range(9):
        p = ck.sphere(f"Puff{i}", (0, 0, 0), 0.26, smoke, segments=20)
        ANIM["puffs"].append((p, i, 9))


def tower():
    kit.use_collection("Tower")
    x, y = PAD[0] + 1.3, PAD[1] - 0.15
    for sx in (-1, 1):
        kit.box(f"Tower_Post{sx}", (x + sx * 0.2, y, 1.1), (0.08, 0.08, 2.2), M["ink"], bevel=0.02)
    for k in range(6):
        z = 0.25 + k * 0.36
        kit.box(f"Tower_Bar{k}", (x, y, z), (0.48, 0.06, 0.05), M["ink"], bevel=0.015)
        brace = kit.box(f"Tower_Brace{k}", (x, y, z + 0.18), (0.5, 0.04, 0.04), M["steel"], bevel=0.01)
        brace.rotation_euler.y = math.radians(40 if k % 2 else -40)
    kit.box("Tower_Top", (x, y, 2.24), (0.6, 0.2, 0.08), M["red"], bevel=0.02)
    lamp = ck.glow("TowerLamp", "red", 2.0)
    ck.sphere("Tower_Lamp", (x, y, 2.36), 0.07, lamp, segments=16)
    ANIM["lamp"] = lamp
    kit.box("Tower_Arm", ((x + PAD[0]) / 2 + 0.25, y + 0.07, 1.3), (abs(x - PAD[0]) - 0.75, 0.1, 0.08), M["gold"], bevel=0.02)


def countdown(x, y):
    kit.use_collection("Countdown")
    rig = kit.empty("Countdown")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-25)
    kit.box("Cd_Leg", (0, 0, 0.35), (0.1, 0.1, 0.7), M["ink"], bevel=0.02, parent=rig)
    kit.box("Cd_Foot", (0, 0, 0.03), (0.6, 0.45, 0.06), M["ink"], bevel=0.02, parent=rig)
    kit.box("Cd_Frame", (0, 0, 1.1), (0.95, 0.14, 0.85), M["steel"], bevel=0.05, parent=rig)
    kit.box("Cd_Screen", (0, 0.075, 1.1), (0.8, 0.01, 0.7), M["screenBg"], bevel=0.01, parent=rig)
    gold = ck.glow("Digit", "gold", 2.0)
    for k, d in enumerate("321"):
        lab = ck.label(f"Cd_Digit{d}", d, (0, 0.09, 1.1), 0.62, gold if d != "1" else ck.glow("DigitRed", "red", 2.2), depth=0.02, parent=rig)
        ANIM["digits"].append((lab, k))


def gift(x, y):
    kit.use_collection("Gift")
    s = 0.85
    kit.box("Gift_Box", (x, y, s * 0.42), (s, s, s * 0.84), M["red"], bevel=0.04)
    for k, size in enumerate(((0.16, s + 0.01, s * 0.84 + 0.005), (s + 0.01, 0.16, s * 0.84 + 0.005))):
        kit.box(f"Gift_Ribbon{k}", (x, y, s * 0.42), size, M["gold"], bevel=0.01)
    lid = kit.empty("Gift_Lid")
    lid.location = (x, y, s * 0.84)
    kit.box("Gift_LidBox", (0, 0, 0.09), (s + 0.08, s + 0.08, 0.18), M["red"], bevel=0.04, parent=lid)
    for k, size in enumerate(((0.17, s + 0.09, 0.185), (s + 0.09, 0.17, 0.185))):
        kit.box(f"Gift_LidRibbon{k}", (0, 0, 0.09), size, M["gold"], bevel=0.01, parent=lid)
    for sx in (-1, 1):
        loop = ck.torus(f"Gift_Bow{sx}", (sx * 0.14, 0, 0.27), 0.12, 0.04, M["gold"], rotation=(math.pi / 2, 0, 0), parent=lid)
        loop.scale = (1, 1, 0.75)
    ANIM["lid"], ANIM["lid_z"] = lid, lid.location.z
    sparks = []
    for k in range(4):
        sp = ck.sphere(f"Spark{k}", (0, 0, 0), 0.07, ck.glow("Spark", "gold", 3.0), segments=12)
        sparks.append((sp, k))
    ANIM["sparks"] = (sparks, (x, y, s * 0.84))


def build_characters():
    walkers = []
    specs = [("Doc", M["white"], "doc"), ("Code", M["blue"], "code"), ("Gold", M["gold"], None)]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.15), radii=(2.3, 0.66)))
    rig, body, feet = ck.chibi("Cheer", M["red"], None)
    rig.scale = (SIZE * 0.6,) * 3
    rig.location = (PAD[0] - 1.0, PAD[1] + 1.15, 0)
    rig.rotation_euler.z = math.radians(200)
    return walkers, (rig, body, feet)


def animate(cam_rig, walkers, cheer):
    x, y = PAD
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        _, body, feet = cheer
        ck.hop(f, T, body, feet, hops=8, height=0.07)
        # 로켓: 살짝 떠서 오르내림, 불꽃 일렁임
        r = ANIM["rocket"]
        r.location.z = 0.06 + 0.05 * math.sin(2 * math.pi * 2 * T)
        r.keyframe_insert("location", index=2, frame=f)
        fl = ANIM["flame"]
        k = 1 + 0.18 * math.sin(2 * math.pi * 12 * T) + 0.08 * math.sin(2 * math.pi * 20 * T + 1)
        fl.scale = (1 - 0.06 * (k - 1), 1 - 0.06 * (k - 1), k)
        fl.keyframe_insert("scale", frame=f)
        for p, i, n in ANIM["puffs"]:
            u = (i / n + T) % 1.0
            a = 2 * math.pi * i / n + 0.7
            rad = 0.55 + 0.75 * u
            p.location = (x + rad * math.cos(a), y + rad * math.sin(a), 0.22 + 0.18 * u)
            p.keyframe_insert("location", frame=f)
            s = 1.2 * math.sin(math.pi * u) ** 0.6
            p.scale = (s, s, s * 0.85)
            p.keyframe_insert("scale", frame=f)
        ck.pulse(f, T, ANIM["lamp"], 0.2, 2.6, 6, square=True)
        # 카운트다운: 4초에 한 번 3 → 2 → 1
        step = int((T % 1.0) * 3)
        for lab, k2 in ANIM["digits"]:
            ck.show(lab, f, step == k2)
        # 선물 상자: 4초에 두 번 뚜껑이 들썩, 반짝이가 튀어나온다
        lid = ANIM["lid"]
        pop = abs(math.sin(math.pi * 2 * T))
        lid.location.z = ANIM["lid_z"] + 0.22 * pop ** 3
        lid.rotation_euler.x = math.radians(8) * pop ** 3
        lid.keyframe_insert("location", index=2, frame=f)
        lid.keyframe_insert("rotation_euler", index=0, frame=f)
        sparks, (gx, gy, gz) = ANIM["sparks"]
        for sp, k2 in sparks:
            u = (T * 2 + k2 / 4) % 1.0
            a = 2 * math.pi * k2 / 4 + 0.4
            sp.location = (gx + 0.45 * u * math.cos(a), gy + 0.45 * u * math.sin(a), gz + 0.2 + 0.9 * u - 0.5 * u * u)
            sp.keyframe_insert("location", frame=f)
            s = math.sin(math.pi * u) ** 0.5
            sp.scale = (s, s, s)
            sp.keyframe_insert("scale", frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    rocket()
    tower()
    countdown(2.35, 0.3)
    gift(-2.2, 0.25)
    walkers, cheer = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers, cheer)

    print("STILL", kit.render_still("launch_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("launch_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
