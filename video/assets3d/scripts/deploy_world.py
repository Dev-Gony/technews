"""9:16 '빌드 → 테스트 → 배포 컨베이어' 장면 (배포·CI/CD·데브옵스·테스트·릴리스 파이프라인 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 뒤: 긴 컨베이어 벨트. 화면 왼쪽 끝 톱니바퀴(빌드)가 돌고, 상자가 벨트를 따라 흐른다
  가운데 검사 문(테스트)을 지날 때마다 문 위 등이 금색으로 반짝이고, 오른쪽 끝 체크 깃발(배포)로 들어간다
- 오른쪽 앞: 신호등 (빨강 → 금색 → 초록이 4초에 한 번)
- 앞: 꼬마들이 상자 / 코드를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/deploy_world.py
    blender -b -P assets3d/scripts/deploy_world.py -- --still-only
출력: video/public/assets3d/deploy_world.png, deploy_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"boxes": [], "rollers": []}

BELT_Y = -1.05
BELT_Z = 0.62  # 벨트 윗면
BELT_X0, BELT_X1 = 1.75, -1.75  # 상자가 들어오는 곳(화면 왼쪽) → 나가는 곳(화면 오른쪽)
N_BOX = 4


def conveyor():
    kit.use_collection("Belt")
    rig = kit.empty("Belt")
    rig.location = (0, BELT_Y, 0)
    rig.rotation_euler.z = math.radians(-15)
    rig.scale = (1.08,) * 3
    length = 4.3
    kit.box("Belt_Frame", (0, 0, BELT_Z - 0.12), (length, 0.95, 0.2), M["steel"], bevel=0.05, parent=rig)
    kit.box("Belt_Top", (0, 0, BELT_Z - 0.01), (length - 0.1, 0.8, 0.03), M["ink"], bevel=0.01, parent=rig)
    for sx in (-1, 1):
        for sy in (-1, 1):
            kit.box(f"Belt_Leg{sx}{sy}", (sx * (length / 2 - 0.3), sy * 0.35, (BELT_Z - 0.2) / 2), (0.1, 0.1, BELT_Z - 0.2), M["ink"], bevel=0.02, parent=rig)
    for k in range(9):  # 벨트 옆 롤러 무늬 (돌아간다)
        roller = kit.empty(f"Roller{k}", parent=rig)
        roller.location = (-length / 2 + 0.25 + k * (length - 0.5) / 8, 0.48, BELT_Z - 0.12)
        kit.cylinder(f"Roller{k}_Body", (0, 0, 0), 0.08, 0.04, M["gold"], bevel=0.01, vertices=6, axis="Y", parent=roller)
        ANIM["rollers"].append(roller)
    # 검사 터널 (가운데): 상자가 들어갔다 나온다. 앞벽의 빨간 띠가 깜빡이고 지붕 등이 반짝인다
    for sy in (-1, 1):
        kit.box(f"Gate_Wall{sy}", (0, sy * 0.47, BELT_Z + 0.38), (0.8, 0.1, 0.76), M["ink"], bevel=0.04, parent=rig)
    kit.box("Gate_Roof", (0, 0, BELT_Z + 0.8), (0.9, 1.1, 0.14), M["ink"], bevel=0.05, parent=rig)
    lamp = ck.glow("GateLamp", "gold", 0.4)
    ck.sphere("Gate_Lamp", (0, 0, BELT_Z + 0.95), 0.13, lamp, segments=20, parent=rig)
    scan = ck.glow("GateScan", "red", 1.0)
    for k in range(2):
        kit.box(f"Gate_Scan{k}", (0, 0.53, BELT_Z + 0.3 + k * 0.2), (0.62, 0.02, 0.05), scan, bevel=0, parent=rig)
    ANIM["lamp"], ANIM["scan"] = lamp, scan
    # 들어오는 쪽: 빌드 톱니바퀴, 나가는 쪽: 체크 깃발
    gear = kit.empty("Gear", parent=rig)
    gear.location = (length / 2 + 0.05, 0, BELT_Z + 0.55)
    teeth = []
    for i in range(20):
        a = 2 * math.pi * i / 20
        r = 0.55 if i % 2 == 0 else 0.42
        for da in (-0.07, 0.07):
            teeth.append((r * math.cos(a + da), r * math.sin(a + da)))
    ck.extruded("Gear_Body", teeth, 0.16, M["red"], center=(0, 0, 0), bevel=0.02, parent=gear)
    kit.cylinder("Gear_Hub", (0, 0, 0), 0.16, 0.22, M["white"], bevel=0.03, vertices=32, axis="Y", parent=gear)
    kit.box("Gear_Post", (length / 2 + 0.05, -0.2, (BELT_Z + 0.55) / 2), (0.1, 0.1, BELT_Z + 0.55), M["ink"], bevel=0.02, parent=rig)
    ANIM["gear"] = gear
    end = -length / 2 - 0.15
    kit.cylinder("Flag_Pole", (end, 0, (BELT_Z + 1.5) / 2), 0.035, BELT_Z + 1.5, M["ink"], bevel=0.008, vertices=12, parent=rig)
    flag = kit.empty("Flag", parent=rig)
    flag.location = (end, 0, BELT_Z + 1.3)
    ck.extruded("Flag_Cloth", [(0, 0.22), (0, -0.22), (-0.62, -0.18), (-0.62, 0.26)], 0.03, M["gold"], center=(0, 0, 0), bevel=0.008, parent=flag)
    # 체크 표시 (흰색)
    check = [(-0.12, 0.02), (-0.2, 0.1), (-0.3, 0.0), (-0.48, 0.18), (-0.56, 0.1), (-0.3, -0.15)]
    ck.extruded("Flag_Check", check, 0.05, M["white"], center=(0, 0.02, 0), bevel=0.01, parent=flag)
    ANIM["flag"] = flag
    kit.box("Bin", (end - 0.1, 0, 0.25), (0.75, 0.95, 0.5), M["sage"], bevel=0.05, parent=rig)
    return rig, length


def boxes(rig, length):
    kit.use_collection("Boxes")
    mats = [kit.material("M_Card", "wood", 0.7, 0.2), M["blue"], M["white"], M["red"]]
    for k in range(N_BOX):
        b = kit.empty(f"Box{k}", parent=rig)
        kit.box(f"Box{k}_Body", (0, 0, 0.22), (0.44, 0.44, 0.44), mats[k], bevel=0.04, parent=b)
        kit.box(f"Box{k}_Tape", (0, 0, 0.441), (0.1, 0.45, 0.01), M["gold"] if k != 1 else M["white"], bevel=0, parent=b)
        ANIM["boxes"].append((b, k))
    ANIM["span"] = (length / 2 - 0.2, -length / 2 + 0.15)


def traffic_light(x, y):
    kit.use_collection("Light")
    rig = kit.empty("Signal")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-20)
    kit.cylinder("Sig_Base", (0, 0, 0.06), 0.38, 0.12, M["ink"], bevel=0.04, vertices=40, parent=rig)
    kit.cylinder("Sig_Pole", (0, 0, 0.5), 0.05, 0.85, M["ink"], bevel=0.01, vertices=16, parent=rig)
    kit.box("Sig_Box", (0, 0, 1.45), (0.5, 0.36, 1.2), M["ink"], bevel=0.08, segments=4, parent=rig)
    lights = []
    for k, color in enumerate(("red", "gold", "sage")):
        mat = ck.glow(f"Sig{k}", color, 0.2)
        kit.cylinder(f"Sig_Lamp{k}", (0, 0.17, 1.82 - k * 0.37), 0.14, 0.06, mat, bevel=0.02, vertices=32, axis="Y", parent=rig)
        kit.box(f"Sig_Hood{k}", (0, 0.22, 1.95 - k * 0.37), (0.34, 0.12, 0.03), M["ink"], bevel=0.01, parent=rig)
        lights.append((mat, k))
    ANIM["signal"] = lights


def build_characters():
    walkers = []
    specs = [("Code", M["white"], "code"), ("Doc", M["gold"], "doc"), ("Blue", M["blue"], None)]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.15), radii=(2.3, 0.66)))
    return walkers


def animate(cam_rig, walkers):
    x0, x1 = ANIM["span"]
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        # 상자: 4초에 끝까지 한 번, 4개가 1초 간격 → 검사 문(가운데)을 1초에 한 번 지난다
        for b, k in ANIM["boxes"]:
            u = (T + k / N_BOX) % 1.0
            b.location = (x0 + (x1 - x0) * u, 0, BELT_Z)
            grow = min(1.0, u / 0.08, (1 - u) / 0.08)  # 양 끝에서 커지고 작아진다
            b.scale = (grow,) * 3
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("scale", frame=f)
        # 상자 하나가 문 아래(u = 0.5)에 올 때마다 등이 반짝
        near = (T * N_BOX) % 1.0
        flash = max(0.0, 1 - abs(near - 0.5) / 0.18)
        inp = ANIM["lamp"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        inp.default_value = 0.4 + 3.0 * flash
        inp.keyframe_insert("default_value", frame=f)
        ck.pulse(f, T, ANIM["scan"], 0.6, 2.4, 4)
        for roller in ANIM["rollers"]:
            roller.rotation_euler.y = -2 * math.pi * 6 * t
            roller.keyframe_insert("rotation_euler", index=1, frame=f)
        ANIM["gear"].rotation_euler.y = 2 * math.pi * 2 * t  # 루프 동안 두 바퀴
        ANIM["gear"].keyframe_insert("rotation_euler", index=1, frame=f)
        ANIM["flag"].rotation_euler.z = math.radians(10) * math.sin(2 * math.pi * 4 * T)
        ANIM["flag"].keyframe_insert("rotation_euler", index=2, frame=f)
        step = int((T % 1.0) * 3)  # 빨강 → 금색 → 초록
        for mat, k in ANIM["signal"]:
            inp = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
            inp.default_value = 2.6 if k == step else 0.15
            inp.keyframe_insert("default_value", frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    rig, length = conveyor()
    boxes(rig, length)
    traffic_light(-2.4, 0.55)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("deploy_world", {
        "belt": ([o for o in obj if o.name.startswith(("Belt_", "Roller"))], "object", "상자가 줄지어 흐르는 긴 컨베이어 벨트 (파이프라인·자동화)"),
        "gear": ([ANIM["gear"], obj["Gear_Post"]], "object", "벨트 끝에서 도는 빨간 톱니바퀴 (빌드·컴파일)"),
        "gate": ([o for o in obj if o.name.startswith("Gate_")], "object", "벨트 가운데 검사 터널, 지붕 등이 반짝 (테스트·검증·CI)"),
        "flag": (ANIM["flag"], "object", "벨트 끝 높이 걸린 흰 체크 표시 금색 깃발 (배포 완료·릴리스)"),
        "signal": (obj["Signal"], "object", "빨강→금색→초록으로 바뀌는 신호등 (승인·대기·배포 상태)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 코드를 들고 걸어 다닌다 (개발자·커밋)"),
        "yellow": (walkers[1].rig, "character", "노란 꼬마: 문서를 들고 걸어 다닌다 (릴리스 노트·리뷰어)"),
        "blue": (walkers[2].rig, "character", "파란 꼬마: 빈손으로 걸어 다닌다 (운영자·사용자)"),
    }, FRAMES, "deploy3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("deploy_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("deploy_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
