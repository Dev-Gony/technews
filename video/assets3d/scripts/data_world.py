"""9:16 '데이터베이스 원통과 원그래프' 장면 (데이터·DB·SQL·분석·지표 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 가운데 뒤: 데이터베이스 아이콘 그대로의 3단 원통 (먹색 몸, 단 사이 금색 빛 띠가 차례로 켜진다)
- 오른쪽: 표(격자 칸)에서 행이 하나씩 빨갛게 골라지고(쿼리), 빛 알갱이가 관을 따라 DB 로 들어간다
- 왼쪽: 원그래프. 빨간 조각 하나가 바깥으로 빠졌다 들어간다. DB 에서 원그래프로도 알갱이가 흐른다
- 앞: 꼬마들이 문서 / 동전을 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/data_world.py
    blender -b -P assets3d/scripts/data_world.py -- --still-only
출력: video/public/assets3d/data_world.png, data_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"bands": [], "packets": [], "rows": []}

DB = (0.1, -1.35)
DB_R = 0.85
LAYER_H = 0.52


def database():
    kit.use_collection("DB")
    x, y = DB
    for k in range(3):
        z0 = 0.05 + k * (LAYER_H + 0.1)
        kit.cylinder(f"DB_Layer{k}", (x, y, z0 + LAYER_H / 2), DB_R, LAYER_H, M["ink"], bevel=0.07, segments=4, vertices=96)
        # 단 사이 빛 띠
        band = ck.glow(f"Band{k}", "gold", 1.0)
        kit.cylinder(f"DB_Band{k}", (x, y, z0 + LAYER_H + 0.05), DB_R - 0.05, 0.07, band, bevel=0.01, vertices=96)
        ANIM["bands"].append((band, k))
        # 앞쪽 작은 LED 두 개
        for d in range(2):
            ang = math.radians(70 + d * 9)
            kit.cylinder(f"DB_Led{k}{d}", (x + (DB_R + 0.005) * math.cos(ang), y + (DB_R + 0.005) * math.sin(ang), z0 + LAYER_H / 2), 0.045, 0.03,
                         M["red"] if d == 0 else M["white"], bevel=0.005, vertices=16, axis="Y")
    top = 0.05 + 3 * (LAYER_H + 0.1)
    kit.cylinder("DB_Lid", (x, y, top), DB_R, 0.1, M["paper"], bevel=0.04, vertices=96)
    ck.torus("DB_LidRing", (x, y, top + 0.05), DB_R * 0.62, 0.03, M["red"])
    return top


def table(x, y):
    """바닥에 기운 표: 5행 × 4열 칸. 4초에 한 번 위에서부터 한 행씩 빨갛게 골라진다."""
    kit.use_collection("Table")
    rig = kit.empty("Table")
    rig.location = (x, y, 0.0)
    rig.rotation_euler = (0, 0, math.radians(-15))
    kit.box("Table_Base", (0, 0, 0.06), (1.55, 1.85, 0.12), M["ink"], bevel=0.04, parent=rig)
    hdr = kit.box("Table_Head", (0, -0.72, 0.16), (1.4, 0.26, 0.08), M["gold"], bevel=0.02, parent=rig)
    hdr.name = "Table_Head"
    for r in range(5):
        hit = ck.glow(f"Row{r}", "red", 0.0)
        cells = []
        for c in range(4):
            cell = kit.box(f"Cell{r}{c}", (-0.525 + c * 0.35, -0.42 + r * 0.3, 0.15), (0.3, 0.24, 0.06), M["white"] if r % 2 else M["paper"], bevel=0.015, parent=rig)
            cells.append(cell)
        # 고를 때 칸 위에 빨간 띠가 덮인다
        cover = kit.box(f"RowHit{r}", (0, -0.42 + r * 0.3, 0.2), (1.38, 0.26, 0.03), hit, bevel=0.01, parent=rig)
        ANIM["rows"].append((cover, hit, r))
    return rig


def pie(x, y):
    kit.use_collection("Pie")
    kit.cylinder("Pie_Base", (x, y, 0.05), 1.0, 0.1, M["ink"], bevel=0.03, vertices=64)
    slices = [(0, 150, "paper"), (150, 250, "gold"), (250, 310, "blue"), (310, 360, "red")]
    for k, (a0, a1, color) in enumerate(slices):
        rig = kit.empty(f"PieRig{k}")
        rig.location = (x, y, 0.1)
        ck.wedge(f"Pie{k}", 0.85, 0.32 if color != "red" else 0.42, a0 + 1, a1 - 1, M[color], parent=rig)
        if color == "red":
            mid = math.radians((a0 + a1) / 2)
            ANIM["slice"] = (rig, (math.cos(mid), math.sin(mid)), (x, y))


def flows(top):
    kit.use_collection("Flows")
    pipe = kit.material("M_Pipe", "#33312C", 0.5, 0.3)
    red, gold = ck.glow("PacketRed", "red", 3.0), ck.glow("PacketGold", "gold", 3.0)
    x, y = DB
    # 표 → DB 윗면 (호를 그리며)
    a = ck.bezier_points((-2.0, -0.2, 0.3), (-1.4, -1.2, 2.6), (x - 0.25, y, top + 0.12), 18)
    # DB 윗면 → 원그래프
    b = ck.bezier_points((x + 0.25, y, top + 0.12), (1.6, -1.2, 2.6), (2.1, 0.0, 0.6), 18)
    ck.tube("Flow_In", a, 0.035, pipe)
    ck.tube("Flow_Out", b, 0.035, pipe)
    for path, mat, name in ((a, red, "In"), (b, gold, "Out")):
        for i in range(3):
            p = ck.sphere(f"Packet{name}{i}", (0, 0, 0), 0.08, mat, segments=16)
            ANIM["packets"].append((p, path, i, 3))


def build_characters():
    walkers = []
    specs = [("Doc", M["white"], "doc"), ("Coin", M["blue"], "coin"), ("Red", M["red"], None)]
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
        for mat, k in ANIM["bands"]:  # 아래에서 위로 차례로 켜진다 (4초에 두 번)
            ck.pulse(f, T, mat, 0.4, 2.8, 2, phase=-k * 1.1)
        for obj, pts, i, n in ANIM["packets"]:
            u = (i / n + T) % 1.0
            obj.location = ck.sample(pts, u)
            obj.keyframe_insert("location", frame=f)
            s = math.sin(math.pi * u) ** 0.35
            obj.scale = (s, s, s)
            obj.keyframe_insert("scale", frame=f)
        row = int((T % 1.0) * 5)
        for cover, mat, r in ANIM["rows"]:
            on = r == row
            ck.show(cover, f, on)
            inp = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
            inp.default_value = 1.2 if on else 0.0
            inp.keyframe_insert("default_value", frame=f)
        rig, (dx, dy), (px, py) = ANIM["slice"]
        out = 0.12 + 0.12 * (0.5 - 0.5 * math.cos(2 * math.pi * 2 * T))
        rig.location = (px + dx * out, py + dy * out, 0.1 + out * 0.6)
        rig.keyframe_insert("location", frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    top = database()
    table(-2.15, 0.2)
    pie(2.2, 0.3)
    flows(top)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("data_world", {
        "db": ([o for o in obj if o.name.startswith("DB_")], "object", "3단 원통 데이터베이스, 단 사이 금색 띠가 켜진다 (DB·저장소)"),
        "table": (obj["Table"], "object", "격자 표, 행이 하나씩 빨갛게 골라진다 (쿼리·SQL·레코드)"),
        "pie": ([obj["Pie_Base"]] + [obj[f"PieRig{k}"] for k in range(4)], "object", "원그래프, 빨간 조각이 빠졌다 들어간다 (지표·점유율·분석)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 문서를 들고 걷는다 (보고서·데이터 문서)"),
        "blue": (walkers[1].rig, "character", "파란 꼬마: 금색 동전을 들고 걷는다 (비용·가치)"),
        "red": (walkers[2].rig, "character", "빨간 꼬마: 빈손으로 걸어 다닌다 (사용자·분석가)"),
    }, FRAMES, "data3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("data_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("data_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
