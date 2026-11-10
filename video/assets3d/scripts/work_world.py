"""9:16 '칸반 보드와 시계, 커피' 장면 (일하는 방식·조직·커리어·생산성·업무 자동화 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 뒤: 세 칸(할 일 / 하는 중 / 끝) 칸반 보드. 메모지가 4초에 한 칸씩 오른쪽으로 옮겨 가고, 끝 칸에 금색 체크
- 왼쪽 앞: 받침 위 큰 벽시계, 분침이 돌아간다
- 오른쪽 앞: 김이 오르는 빨간 커피 잔과 달력
- 앞: 꼬마들이 문서 / 코드를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/work_world.py
    blender -b -P assets3d/scripts/work_world.py -- --still-only
출력: video/public/assets3d/work_world.png, work_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"steam": []}

BW, BH, BZ = 3.1, 1.8, 0.55
COLS = [0.98, 0.0, -0.98]  # 보드 로컬 x (+x 가 화면 왼쪽): 할 일 → 하는 중 → 끝


def board():
    kit.use_collection("Board")
    rig = kit.empty("Board")
    rig.location = (0.05, -1.6, 0)
    rig.rotation_euler.z = math.radians(-20)
    for sx in (-1, 1):
        kit.box(f"Board_Leg{sx}", (sx * (BW / 2 - 0.3), -0.05, BZ / 2), (0.1, 0.1, BZ), M["ink"], bevel=0.02, parent=rig)
        kit.box(f"Board_Foot{sx}", (sx * (BW / 2 - 0.3), -0.05, 0.03), (0.45, 0.5, 0.06), M["ink"], bevel=0.02, parent=rig)
    zc = BZ + BH / 2
    kit.box("Board_Frame", (0, 0, zc), (BW, 0.12, BH), M["ink"], bevel=0.05, parent=rig)
    kit.box("Board_Face", (0, 0.065, zc), (BW - 0.14, 0.01, BH - 0.14), M["white"], bevel=0.02, parent=rig)
    heads = [M["red"], M["gold"], M["sage"]]
    for k, x in enumerate(COLS):
        kit.box(f"Board_Head{k}", (x, 0.075, BZ + BH - 0.2), (0.86, 0.012, 0.16), heads[k], bevel=0.02, parent=rig)
        if k < 2:
            kit.box(f"Board_Div{k}", ((x + COLS[k + 1]) / 2, 0.075, zc - 0.08), (0.02, 0.012, BH - 0.4), M["paper"], bevel=0, parent=rig)
    # 고정 메모지 (칸마다)
    fixed = [(0, 0.95, M["gold"]), (0, 0.55, M["blue"]), (1, 0.95, M["blue"]), (2, 0.55, M["gold"])]
    for k, (c, z, mat) in enumerate(fixed):
        kit.box(f"Note{k}", (COLS[c], 0.08, BZ + z), (0.6, 0.02, 0.32), mat, bevel=0.02, parent=rig)
        kit.box(f"Note{k}_Ln", (COLS[c], 0.092, BZ + z + 0.04), (0.38, 0.005, 0.04), M["ink"], bevel=0, parent=rig)
    # 움직이는 메모지 (빨강) + 끝 칸 체크
    mover = kit.empty("Mover", parent=rig)
    kit.box("Mover_Body", (0, 0, 0), (0.6, 0.03, 0.32), M["red"], bevel=0.02, parent=mover)
    kit.box("Mover_Ln", (0, 0.017, 0.04), (0.38, 0.005, 0.04), M["white"], bevel=0, parent=mover)
    check = [(-0.05, 0.0), (-0.15, 0.1), (-0.25, 0.0), (-0.45, 0.2), (-0.55, 0.1), (-0.25, -0.2)]
    chk = ck.extruded("Check", [(px + 0.3, pz) for px, pz in check], 0.04, ck.glow("Check", "gold", 1.8), center=(COLS[2] + 0.42, 0.1, BZ + 1.2), bevel=0.01, parent=rig)
    ANIM.update(mover=mover, check=chk)


def clock(x, y):
    kit.use_collection("Clock")
    kit.cylinder("Clock_Base", (x, y, 0.06), 0.42, 0.12, M["ink"], bevel=0.04, vertices=40)
    kit.cylinder("Clock_Post", (x, y, 0.45), 0.05, 0.75, M["ink"], bevel=0.01, vertices=16)
    rig = kit.empty("Clock")
    rig.location = (x, y, 1.3)
    rig.rotation_euler.z = math.radians(-20)
    kit.cylinder("Clock_Rim", (0, 0, 0), 0.62, 0.16, M["red"], bevel=0.05, vertices=64, axis="Y", parent=rig)
    kit.cylinder("Clock_Face", (0, 0.07, 0), 0.53, 0.04, M["white"], bevel=0.01, vertices=64, axis="Y", parent=rig)
    for k in range(12):
        a = 2 * math.pi * k / 12
        size = (0.05, 0.01, 0.12) if k % 3 == 0 else (0.03, 0.01, 0.06)
        tick = kit.box(f"Clock_Tick{k}", (0.43 * math.sin(a), 0.095, 0.43 * math.cos(a)), size, M["ink"], bevel=0, parent=rig)
        tick.rotation_euler.y = a
    hour = kit.empty("Clock_Hour", parent=rig)
    hour.location = (0, 0.1, 0)
    kit.box("Clock_HourHand", (0, 0, 0.13), (0.06, 0.012, 0.26), M["ink"], bevel=0.01, parent=hour)
    minute = kit.empty("Clock_Minute", parent=rig)
    minute.location = (0, 0.11, 0)
    kit.box("Clock_MinHand", (0, 0, 0.2), (0.04, 0.012, 0.4), M["red"], bevel=0.01, parent=minute)
    kit.cylinder("Clock_Pin", (0, 0.12, 0), 0.04, 0.03, M["gold"], bevel=0.005, vertices=16, axis="Y", parent=rig)
    hour.rotation_euler.y = math.radians(-60)
    ANIM.update(minute=minute, hour=hour)


def coffee(x, y):
    kit.use_collection("Coffee")
    kit.cylinder("Saucer", (x, y, 0.03), 0.48, 0.06, M["white"], bevel=0.02, vertices=48)
    kit.cylinder("Cup", (x, y, 0.36), 0.32, 0.6, M["red"], bevel=0.05, vertices=48)
    kit.cylinder("Cup_Coffee", (x, y, 0.64), 0.27, 0.04, kit.material("M_Coffee", "#4A2F22", 0.3, 0.4), bevel=0.005, vertices=48)
    ck.torus("Cup_Handle", (x - 0.34, y + 0.1, 0.38), 0.14, 0.045, M["red"], rotation=(math.pi / 2, 0, math.radians(70)))
    smoke = kit.material("M_Steam", "#F1EEE6", 0.9, 0.1)
    for k in range(5):
        p = ck.sphere(f"Steam{k}", (0, 0, 0), 0.12, smoke, segments=16)
        ANIM["steam"].append((p, k, (x, y)))
    cal = kit.empty("Calendar")
    cal.location = (x + 0.15, y - 0.75, 0)
    cal.rotation_euler.z = math.radians(-20)
    kit.box("Cal_Back", (0, 0, 0.42), (0.75, 0.08, 0.8), M["white"], bevel=0.03, parent=cal)
    kit.box("Cal_Top", (0, 0.03, 0.74), (0.75, 0.1, 0.18), M["red"], bevel=0.03, parent=cal)
    for r in range(3):
        for c in range(4):
            kit.box(f"Cal_Day{r}{c}", (0.24 - c * 0.16, 0.045, 0.52 - r * 0.15), (0.1, 0.01, 0.1), M["gold"] if (r, c) == (1, 2) else M["paper"], bevel=0.01, parent=cal)


def build_characters():
    walkers = []
    specs = [("Doc", M["white"], "doc"), ("Code", M["blue"], "code"), ("Gold", M["gold"], "doc")]
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
        # 빨간 메모지: 12초 동안 할 일 → 하는 중 → 끝 (칸마다 4초, 옮길 때 살짝 들린다)
        stage = t * 3
        k = int(stage)
        u = stage - k
        move = 0.0 if u < 0.7 else (u - 0.7) / 0.3
        move = move * move * (3 - 2 * move)
        if k < 2:
            x = COLS[k] + (COLS[k + 1] - COLS[k]) * move
        else:
            x = COLS[2] + (COLS[0] - COLS[2]) * move  # 끝에서 다시 처음으로 (뒤로 돌아간다)
        lift = math.sin(math.pi * move)
        m = ANIM["mover"]
        m.location = (x, 0.1 + 0.25 * lift, BZ + 0.15 + 0.12 * lift)
        m.keyframe_insert("location", frame=f)
        ck.show(ANIM["check"], f, k == 2 and u < 0.7)
        ANIM["minute"].rotation_euler.y = 2 * math.pi * 3 * t
        ANIM["minute"].keyframe_insert("rotation_euler", index=1, frame=f)
        for p, k2, (cx, cy) in ANIM["steam"]:
            v = (T + k2 / 5) % 1.0
            p.location = (cx + 0.08 * math.sin(2 * math.pi * v + k2), cy, 0.75 + 0.9 * v)
            s = 1.1 * math.sin(math.pi * v) ** 0.7
            p.scale = (s, s, s)
            p.keyframe_insert("location", frame=f)
            p.keyframe_insert("scale", frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    board()
    clock(2.25, 0.3)
    coffee(-2.1, 0.55)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("work_world", {
        "board": (obj["Board"], "object", "세 칸 칸반 보드, 빨간 메모지가 끝 칸으로 옮겨 간다 (업무·프로젝트·진행 상황)"),
        "note": (obj["Mover"], "object", "칸반 보드 위를 옮겨 다니는 빨간 메모지 (할 일·작업 하나)"),
        "clock": ([obj["Clock"], obj["Clock_Base"], obj["Clock_Post"]], "object", "분침이 도는 큰 빨간 시계 (시간·마감·근무 시간)"),
        "coffee": ([obj["Saucer"], obj["Cup"], obj["Cup_Coffee"], obj["Cup_Handle"]], "object", "김이 오르는 빨간 커피 잔 (휴식·직장 생활)"),
        "calendar": (obj["Calendar"], "object", "금색 날짜 하나가 표시된 달력 (일정·기한·주 4일제)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 문서를 들고 걸어 다닌다 (직원·보고서)"),
        "blue": (walkers[1].rig, "character", "파란 꼬마: 코드를 들고 걸어 다닌다 (개발자·자동화)"),
        "yellow": (walkers[2].rig, "character", "노란 꼬마: 문서를 들고 걸어 다닌다 (관리자·회사)"),
    }, FRAMES, "work3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("work_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("work_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
