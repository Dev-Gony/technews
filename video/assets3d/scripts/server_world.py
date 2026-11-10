"""9:16 '작은 서버실' 장면 (인프라·성능 뉴스 배경).

책상 장면과 같은 받침 원판 위:
- 뒤: 서버 랙 3대가 반원으로 선다. 앞판의 LED 가 제각각 깜빡인다
- 랙마다 바닥 케이블이 가운데 허브로 모이고, 그 위로 빛 알갱이(금·빨강)가 흘러간다
- 가운데 랙 위: 작은 구름이 둥실, 구름과 랙 사이로 빛 알갱이가 오르내린다
- 왼쪽 앞: 큰 메모리(RAM) 막대, 오른쪽 앞: 속도계 바늘이 끝까지 올라갔다 떨린다
- 앞: 꼬마 3명이 데이터 블록 / 문서 / 빈손으로 돈다
서버, 클라우드, EC2, 메모리, 지연, 성능 n배 뉴스에 쓴다.

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/server_world.py
    blender -b -P assets3d/scripts/server_world.py -- --still-only
출력: video/public/assets3d/server_world.png, server_world_loop.webm (1080x1920, 투명 배경)
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import chibi_kit as ck  # noqa: E402
import iso_kit as kit  # noqa: E402

FRAMES = 360  # 12초 루프: 꼬마가 정확히 한 바퀴 돌아 제자리로 (끊김 없음)
STEPS = 36  # 초당 3걸음 (짝수여야 끊김 없음)
SIZE = 2.1
M = ck.M
ANIM = {"leds": [], "packets": [], "cloud": None}

RACK_W, RACK_D, RACK_H = 1.15, 1.0, 2.3
RACKS = [(1.8, -0.95, 22), (0.0, -1.45, 0), (-1.8, -0.95, -22)]  # x, y, 회전(도). 반원으로 가운데를 본다
HUB = (0.0, 0.55)


def rack(k, x, y, rot):
    kit.use_collection("Racks")
    rig = kit.empty(f"Rack{k}")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(rot)
    kit.box(f"Rack{k}_Body", (0, 0, RACK_H / 2 + 0.06), (RACK_W, RACK_D, RACK_H), M["steel"], bevel=0.06, segments=4, parent=rig)
    for sx in (-1, 1):
        for sy in (-1, 1):
            kit.box(f"Rack{k}_Foot{sx}{sy}", (sx * 0.45, sy * 0.38, 0.03), (0.14, 0.14, 0.06), M["ink"], bevel=0.02, parent=rig)
    units = 6
    unit_h = (RACK_H - 0.3) / units
    for u in range(units):
        z = 0.24 + unit_h * (u + 0.5)
        kit.box(f"Rack{k}_Unit{u}", (0, RACK_D / 2 + 0.01, z), (RACK_W - 0.18, 0.04, unit_h - 0.07), M["dark"], bevel=0.015, parent=rig)
        for g in range(3):  # 통풍 줄
            kit.box(f"Rack{k}_Vent{u}_{g}", (0.12 + g * 0.11, RACK_D / 2 + 0.035, z), (0.05, 0.01, unit_h - 0.16), M["ink"], bevel=0, parent=rig)
        for d in range(3):  # LED 3개: 색과 깜빡이는 박자를 칸마다 다르게
            color = ("gold", "screen", "red")[(u + d + k) % 3]
            idx = (u * 3 + d + k * 5) % 7
            mat = ck.glow(f"Led_{color}_{idx}", color, 2.0)
            if mat not in [m for m, _, _ in ANIM["leds"]]:
                ANIM["leds"].append((mat, 2 + idx % 4, idx * 0.9))
            kit.cylinder(f"Rack{k}_Led{u}_{d}", (-0.38 + d * 0.11, RACK_D / 2 + 0.04, z), 0.03, 0.02, mat, bevel=0, vertices=16, axis="Y", parent=rig)
    # 위 덮개 (금색 띠)
    kit.box(f"Rack{k}_Cap", (0, 0, RACK_H + 0.07), (RACK_W + 0.04, RACK_D + 0.04, 0.06), M["ink"], bevel=0.02, parent=rig)
    bpy.context.view_layer.update()
    return rig


def tube(name, points, radius, mat):
    """점들을 지나는 둥근 관 (케이블, 빛 줄기)."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 4
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def sample(points, u):
    """꺾은선 위 길이 비율 u(0~1) 자리."""
    seg = [(Vector(a), Vector(b)) for a, b in zip(points, points[1:])]
    lengths = [(b - a).length for a, b in seg]
    target = u * sum(lengths)
    for (a, b), length in zip(seg, lengths):
        if target <= length:
            return a.lerp(b, target / length if length else 0)
        target -= length
    return Vector(points[-1])


def cables():
    kit.use_collection("Cables")
    kit.cylinder("Hub", (HUB[0], HUB[1], 0.12), 0.42, 0.24, M["ink"], bevel=0.05, vertices=48)
    hub_ring = ck.glow("HubRing", "gold", 1.6)
    ck.torus("Hub_Ring", (HUB[0], HUB[1], 0.24), 0.36, 0.035, hub_ring)
    ANIM["hub"] = hub_ring
    cable = kit.material("M_Cable", "#33312C", 0.5, 0.3)
    gold, red = ck.glow("PacketGold", "gold", 3.0), ck.glow("PacketRed", "red", 3.0)
    for k, (x, y, rot) in enumerate(RACKS):
        a = math.radians(rot)
        fx, fy = x - math.sin(a) * (RACK_D / 2 - 0.1), y + math.cos(a) * (RACK_D / 2 - 0.1)
        start = (fx, fy, 0.07)
        mid = (fx - math.sin(a) * 0.6, fy + math.cos(a) * 0.6, 0.07)
        pts = ck.bezier_points(start, mid, (HUB[0], HUB[1], 0.07), 16)
        tube(f"Cable{k}", pts, 0.06, cable)
        for i in range(3):  # 빛 알갱이: 루프 동안 한 칸씩 앞으로 → 끝(허브 안)에서 다음 알갱이 자리로
            p = ck.sphere(f"Packet{k}_{i}", (0, 0, 0), 0.075, gold if (i + k) % 2 else red, segments=16)
            ANIM["packets"].append((p, pts, i, 3, 0.03))
    # 가운데 랙 위 구름 + 빛 기둥
    x, y, _ = RACKS[1]
    cloud = kit.empty("Cloud")
    cloud.location = (x, y, RACK_H + 0.85)
    for k, (dx, dz, r) in enumerate(((0, 0.08, 0.36), (-0.36, -0.04, 0.26), (0.38, -0.02, 0.28), (0.18, 0.22, 0.24), (-0.2, 0.2, 0.2))):
        ck.sphere(f"Cloud_{k}", (dx, 0, dz), r, M["white"], scale=(1, 0.8, 0.9), parent=cloud)
    ANIM["cloud"] = cloud
    beam = [(x, y, RACK_H + 0.12), (x, y, RACK_H + 0.65)]
    tube("Beam", beam, 0.03, ck.glow("Beam", "gold", 1.2))
    for i in range(2):
        p = ck.sphere(f"BeamPacket{i}", (0, 0, 0), 0.06, red, segments=16)
        ANIM["packets"].append((p, beam, i, 2, 0.0))


def ram_stick(x, y):
    kit.use_collection("Props")
    rig = kit.empty("Ram")
    rig.location = (x, y, 0)
    rig.rotation_euler = (math.radians(-14), 0, math.radians(-18))
    board = kit.material("M_Board", "#2F4A3A", 0.55, 0.3)
    kit.box("Ram_Board", (0, 0, 0.36), (1.7, 0.07, 0.6), board, bevel=0.02, parent=rig)
    for k in range(4):
        kit.box(f"Ram_Chip{k}", (-0.6 + k * 0.4, 0.05, 0.4), (0.3, 0.04, 0.3), M["ink"], bevel=0.015, parent=rig)
    for k in range(16):
        kit.box(f"Ram_Pin{k}", (-0.75 + k * 0.1, 0.04, 0.1), (0.05, 0.01, 0.1), M["gold"], bevel=0, parent=rig)
    kit.box("Ram_Label", (0.62, 0.05, 0.62), (0.32, 0.02, 0.12), M["red"], bevel=0.01, parent=rig)
    kit.box("Ram_Stand", (0, -0.22, 0.12), (1.2, 0.4, 0.06), M["ink"], bevel=0.02, parent=rig)


def gauge(x, y):
    kit.use_collection("Props")
    rig = kit.empty("Gauge")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-20)
    kit.box("Gauge_Stand", (0, -0.05, 0.3), (0.16, 0.16, 0.6), M["ink"], bevel=0.04, parent=rig)
    kit.cylinder("Gauge_Base", (0, -0.05, 0.04), 0.32, 0.08, M["ink"], bevel=0.02, vertices=40, parent=rig)
    face = kit.empty("Gauge_Face", parent=rig)
    face.location = (0, 0.06, 1.05)
    face.rotation_euler.x = math.radians(-12)
    kit.cylinder("Gauge_Rim", (0, 0, 0), 0.55, 0.12, M["steel"], bevel=0.03, vertices=64, axis="Y", parent=face)
    kit.cylinder("Gauge_Dial", (0, 0.04, 0), 0.47, 0.06, M["white"], bevel=0.01, vertices=64, axis="Y", parent=face)
    for k in range(9):  # 눈금: 왼쪽 아래 → 오른쪽 아래, 마지막 두 칸은 빨강
        a = math.radians(-120 + k * 30)
        tick = kit.empty(f"Gauge_Tick{k}", parent=face)
        tick.rotation_euler.y = a
        kit.box(f"Gauge_TickBar{k}", (0, 0.075, 0.36), (0.035, 0.01, 0.12), M["red"] if k >= 7 else M["ink"], bevel=0, parent=tick)
    needle = kit.empty("Gauge_Needle", parent=face)
    needle.location = (0, 0.09, 0)
    kit.box("Gauge_NeedleBar", (0, 0, 0.18), (0.04, 0.02, 0.38), M["red"], bevel=0.008, parent=needle)
    kit.cylinder("Gauge_Hub", (0, 0.01, 0), 0.06, 0.04, M["ink"], bevel=0.01, vertices=24, axis="Y", parent=needle)
    ANIM["needle"] = needle


def build_characters():
    walkers = []
    specs = [("Code", M["white"], "code"), ("Doc", M["gold"], "doc"), ("Red", M["red"], None)]
    for i, (n, mat, carry) in enumerate(specs):
        rig, body, feet = ck.chibi(f"Walker{n}", mat, carry)
        rig.scale = (SIZE,) * 3
        walkers.append(ck.Walker(rig, body, feet, i / len(specs), SIZE, center=(0.0, 2.1), radii=(2.3, 0.68)))
    # 케이블이 모이는 허브 위에서 통통 뛰는 파란 꼬마 (서버 지기)
    rig, body, feet = ck.chibi("Keeper", M["blue"], None)
    rig.scale = (SIZE * 0.7,) * 3
    rig.location = (HUB[0], HUB[1] - 0.05, 0.25)
    rig.rotation_euler.z = math.radians(20)
    return walkers, (rig, body, feet)


def animate(cam_rig, walkers, keeper):
    cloud_z = ANIM["cloud"].location.z
    for f in range(1, FRAMES + 1):
        t = (f - 1) / FRAMES
        T = 3 * t  # 4초 박자 (깜빡임·흔들림은 4초에 정수 번)
        cam_rig.rotation_euler.z = math.radians(3) * math.sin(2 * math.pi * t)
        cam_rig.keyframe_insert("rotation_euler", index=2, frame=f)
        for w in walkers:
            w.key(f, t, STEPS)
        _, body, feet = keeper
        ck.hop(f, T, body, feet, hops=8, height=0.06)
        for obj, pts, i, n, lift in ANIM["packets"]:
            u = (i / n + T) % 1.0  # 4초에 한 번 끝까지 → 루프 끝에서 제자리
            p = sample(pts, u)
            obj.location = (p.x, p.y, p.z + lift)
            obj.keyframe_insert("location", frame=f)
            s = math.sin(math.pi * u) ** 0.35  # 양 끝(랙·허브 안)에서 작아져 사라진다
            obj.scale = (s, s, s)
            obj.keyframe_insert("scale", frame=f)
        for mat, cycles, phase in ANIM["leds"]:
            ck.pulse(f, T, mat, 0.3, 2.6, cycles, phase, square=True)
        ck.pulse(f, T, ANIM["hub"], 0.8, 2.4, 4)
        ANIM["cloud"].location.z = cloud_z + 0.07 * math.sin(2 * math.pi * t)
        ANIM["cloud"].keyframe_insert("location", index=2, frame=f)
        # 속도계: 끝까지 올라가 빨간 칸에서 파르르 (2번 오르내림)
        swing = 0.5 - 0.5 * math.cos(2 * math.pi * 2 * T)
        ANIM["needle"].rotation_euler.y = math.radians(-60 + 160 * swing + 4 * math.sin(2 * math.pi * 12 * T) * swing)
        ANIM["needle"].keyframe_insert("rotation_euler", index=1, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    for k, (x, y, rot) in enumerate(RACKS):
        rack(k, x, y, rot)
    cables()
    ram_stick(2.45, 0.85)
    gauge(-2.55, 0.65)
    walkers, keeper = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers, keeper)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("server_world", {
        "racks": ([obj["Rack0"], obj["Rack1"], obj["Rack2"]], "object", "반원으로 선 서버 랙 3대, LED 가 깜빡인다 (서버·데이터센터)"),
        "cloud": (ANIM["cloud"], "object", "가운데 랙 위에 둥실 뜬 흰 구름 (클라우드·호스팅)"),
        "hub": ([obj["Hub"], obj["Hub_Ring"]], "object", "랙 케이블이 모이는 빛나는 허브 (네트워크·트래픽)"),
        "ram": (obj["Ram"], "object", "큰 초록 메모리(RAM) 막대 (메모리·용량)"),
        "gauge": (obj["Gauge"], "object", "바늘이 빨간 칸까지 치솟는 속도계 (성능·속도·지연)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 빨간 코드 블록을 들고 걷는다 (코드·워크로드)"),
        "yellow": (walkers[1].rig, "character", "노란 꼬마: 문서를 들고 걷는다 (요청·문서)"),
        "red": (walkers[2].rig, "character", "빨간 꼬마: 빈손으로 걸어 다닌다 (사용자·트래픽)"),
        "blue": (keeper[0], "character", "파란 꼬마: 허브 위에서 통통 뛴다 (서버 관리자·운영자)"),
    }, FRAMES, "server3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("server_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("server_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
