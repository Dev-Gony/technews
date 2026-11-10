"""9:16 '빌딩 숲과 치솟는 화살표, 돈 자루' 장면 (투자·스타트업·상장·인수·기업가치·매출 뉴스 그림).

책상 장면과 같은 받침 원판 위:
- 뒤: 높이가 다른 회사 빌딩 3채 (창문이 차례로 켜진다). 그 앞으로 빨간 지그재그 화살표가 위로 치솟고
  빛 알갱이가 화살표를 타고 오른다
- 왼쪽 앞: 통통 튀는 금색 돈 자루 ($ 글자)
- 오른쪽 앞: 금색 띠를 두른 지폐 다발, 맨 위 지폐가 팔랑인다
- 앞: 꼬마들이 동전 / 문서를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/invest_world.py
    blender -b -P assets3d/scripts/invest_world.py -- --still-only
출력: video/public/assets3d/invest_world.png, invest_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"windows": [], "packets": []}


def towers():
    kit.use_collection("City")
    rig = kit.empty("City")
    rig.location = (0.0, -1.8, 0)
    rig.rotation_euler.z = math.radians(-20)
    glass = kit.material("M_TowerGlass", "#9FC3DA", 0.2, 0.6)
    specs = [(-1.15, 1.35, 0.95, M["white"]), (0.0, 2.25, 1.05, M["paper"]), (1.15, 1.75, 0.9, M["white"])]
    for k, (x, h, w, mat) in enumerate(specs):
        kit.box(f"Tower{k}", (x, 0, h / 2), (w, 0.9, h), mat, bevel=0.04, parent=rig)
        kit.box(f"Tower{k}_Roof", (x, 0, h + 0.04), (w - 0.1, 0.8, 0.08), M["ink"], bevel=0.02, parent=rig)
        rows = int((h - 0.3) / 0.28)
        for r in range(rows):
            for c in range(3):
                lit = ck.glow(f"Win{k}_{r}_{c}", "gold", 0.0) if (r + c + k) % 3 == 0 else glass
                kit.box(f"Tower{k}_Win{r}_{c}", (x - w / 3 + c * w / 3, 0.455, 0.3 + r * 0.28), (w / 3 - 0.1, 0.01, 0.18), lit, bevel=0, parent=rig)
                if lit is not glass:
                    ANIM["windows"].append((lit, r * 0.37 + c * 0.6 + k))
    kit.box("Tower1_Door", (0, 0.456, 0.15), (0.3, 0.012, 0.3), M["ink"], bevel=0.01, parent=rig)


def arrow():
    kit.use_collection("Arrow")
    pts = [(1.95, -0.6, 0.25), (1.0, -0.75, 0.95), (0.35, -0.8, 0.7), (-0.6, -0.9, 1.7), (-1.55, -1.0, 2.25)]
    ck.tube("Arrow_Line", pts, 0.11, M["red"])
    for k, p in enumerate(pts[1:-1]):
        ck.sphere(f"Arrow_Joint{k}", p, 0.11, M["red"], segments=20)
    a, b = pts[-2], pts[-1]
    d = [b[i] - a[i] for i in range(3)]
    head = kit.empty("Arrow_Head")
    head.location = b
    from mathutils import Vector

    head.rotation_euler = Vector(d).normalized().to_track_quat("Z", "Y").to_euler()
    ck.cone("Arrow_Cone", (0, 0, 0.12), 0.27, 0.0, 0.42, M["red"], parent=head)
    glow = ck.glow("ArrowPacket", "gold", 3.0)
    for i in range(3):
        p = ck.sphere(f"ArrowPacket{i}", (0, 0, 0), 0.085, glow, segments=16)
        ANIM["packets"].append((p, pts, i, 3))


def money_bag(x, y):
    kit.use_collection("Bag")
    rig = kit.empty("Bag")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-25)
    body = kit.empty("Bag_Body", parent=rig)
    sack = kit.material("M_Sack", "gold", 0.55, 0.3)
    ck.sphere("Bag_Sack", (0, 0, 0.5), 0.5, sack, scale=(1, 0.9, 0.95), parent=body)
    kit.cylinder("Bag_Neck", (0, 0, 0.98), 0.17, 0.14, sack, bevel=0.04, vertices=32, parent=body)
    ck.torus("Bag_Tie", (0, 0, 0.98), 0.17, 0.035, M["red"], parent=body)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        ck.sphere(f"Bag_Frill{k}", (0.12 * math.cos(a), 0.12 * math.sin(a), 1.1), 0.09, sack, parent=body, segments=16)
    ck.label("Bag_Dollar", "$", (0, 0.44, 0.48), 0.5, M["red"], depth=0.03, parent=body)
    ANIM["bag"] = body


def bills(x, y):
    kit.use_collection("Bills")
    rig = kit.empty("Bills")
    rig.location = (x, y, 0)
    rig.rotation_euler.z = math.radians(-15)
    bill = kit.material("M_Bill", "#A9C9A0", 0.6, 0.2)
    dark = kit.material("M_BillInk", "#5F8A5C", 0.6, 0.2)
    for k in range(7):
        b = kit.box(f"Bill{k}", (0.02 * math.sin(k * 2.3), 0.02 * math.cos(k * 1.9), 0.035 + k * 0.05), (1.05, 0.55, 0.045), bill, bevel=0.008, parent=rig)
        b.rotation_euler.z = math.radians(3 * math.sin(k * 1.7))
    kit.box("Bill_Band", (0, 0, 0.2), (0.22, 0.57, 0.37), M["gold"], bevel=0.01, parent=rig)
    flap = kit.empty("Bill_FlapHinge", parent=rig)
    flap.location = (0.52, 0, 0.4)
    kit.box("Bill_Top", (-0.52, 0, 0.0), (1.05, 0.55, 0.02), bill, bevel=0.005, parent=flap)
    kit.cylinder("Bill_TopSeal", (-0.52, 0, 0.012), 0.12, 0.006, dark, bevel=0, vertices=24, parent=flap)
    ANIM["flap"] = flap


def build_characters():
    walkers = []
    specs = [("Coin", M["white"], "coin"), ("Doc", M["blue"], "doc"), ("Red", M["red"], "coin")]
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
        for mat, phase in ANIM["windows"]:
            ck.pulse(f, T, mat, 0.0, 1.6, 1, phase=phase, square=True)
        for obj, pts, i, n in ANIM["packets"]:
            u = (i / n + T) % 1.0
            obj.location = ck.sample(pts, u)
            obj.keyframe_insert("location", frame=f)
            s = math.sin(math.pi * u) ** 0.35
            obj.scale = (s, s, s)
            obj.keyframe_insert("scale", frame=f)
        bag = ANIM["bag"]
        h = abs(math.sin(math.pi * 4 * T))
        bag.location.z = 0.18 * h
        bag.scale = (1 + 0.05 * (1 - h), 1 + 0.05 * (1 - h), 1 - 0.06 * (1 - h))
        bag.keyframe_insert("location", index=2, frame=f)
        bag.keyframe_insert("scale", frame=f)
        ANIM["flap"].rotation_euler.y = math.radians(25) * max(0.0, math.sin(2 * math.pi * 2 * T)) ** 2
        ANIM["flap"].keyframe_insert("rotation_euler", index=1, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    towers()
    arrow()
    money_bag(2.2, 0.35)
    bills(-2.15, 0.35)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    # 관(커브)은 경계 상자가 커서 빼고, 꺾임 구슬과 화살촉으로 화살표 자리를 잡는다
    arrow_parts = [obj["Arrow_Head"]] + [o for o in obj if o.name.startswith("Arrow_Joint")]
    print("ANCHORS", ck.export_anchors("invest_world", {
        "towers": (obj["City"], "object", "창문이 차례로 켜지는 회사 빌딩 3채 (기업·스타트업·시장)"),
        "arrow": (arrow_parts, "object", "위로 치솟는 빨간 지그재그 화살표 (성장·주가·기업가치 상승)"),
        "bag": (obj["Bag"], "object", "통통 튀는 금색 $ 돈 자루 (투자금·자금 조달)"),
        "bills": (obj["Bills"], "object", "금색 띠를 두른 지폐 다발 (매출·현금·인수 대금)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 동전을 들고 걸어 다닌다 (투자자·돈을 대는 쪽)"),
        "blue": (walkers[1].rig, "character", "파란 꼬마: 문서를 들고 걸어 다닌다 (계약서·사업계획·창업자)"),
        "red": (walkers[2].rig, "character", "빨간 꼬마: 동전을 들고 걸어 다닌다 (투자자·인수하는 쪽)"),
    }, FRAMES, "invest3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("invest_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("invest_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
