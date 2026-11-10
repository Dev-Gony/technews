"""9:16 '신경망 조형물과 반짝이, AI 말풍선' 장면 (AI 모델·LLM·챗봇·추론·프롬프트 일반 뉴스 그림).

다른 장면이 맞지 않는 AI 일반 주제의 마지막 선택지다.
책상 장면과 같은 받침 원판 위:
- 뒤: 세 겹 신경망 조형물 (마디 3-4-3개, 마디 사이 연결선). 빛 알갱이가 왼쪽 겹에서 오른쪽 겹으로 흐르고
  마디가 차례로 밝아진다
- 왼쪽 앞: 천천히 도는 큰 금색 네 갈래 반짝이 + 작은 반짝이 2개
- 오른쪽 앞: 'AI' 라고 쓴 빨간 말풍선, 아래 점 3개가 통통 (답을 쓰는 중)
- 앞: 꼬마들이 문서 / 코드를 들고 돈다

실행 (저장소 video 폴더에서):
    blender -b -P assets3d/scripts/ai_world.py
    blender -b -P assets3d/scripts/ai_world.py -- --still-only
출력: video/public/assets3d/ai_world.png, ai_world_loop.webm (1080x1920, 투명 배경)
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
ANIM = {"nodes": [], "packets": [], "dots": [], "sparks": []}


def network():
    kit.use_collection("Net")
    rig = kit.empty("Net")
    rig.location = (0.1, -1.5, 0)
    rig.rotation_euler.z = math.radians(-20)
    layers = [(1.5, [0.75, 1.35, 1.95]), (0.0, [0.55, 1.1, 1.65, 2.2]), (-1.5, [0.75, 1.35, 1.95])]
    for k, (x, _) in enumerate(layers):
        kit.box(f"Net_Post{k}", (x, -0.15, 1.15), (0.08, 0.08, 2.3), M["ink"], bevel=0.02, parent=rig)
        kit.cylinder(f"Net_Foot{k}", (x, -0.15, 0.04), 0.28, 0.08, M["ink"], bevel=0.02, vertices=32, parent=rig)
    wire = kit.material("M_Wire", "#8C877C", 0.5, 0.3)
    paths = []
    for (xa, za), (xb, zb) in ((layers[0], layers[1]), (layers[1], layers[2])):
        for z1 in za:
            for z2 in zb:
                pts = [(xa, 0, z1), (xb, 0, z2)]
                ck.tube("Net_Wire", pts, 0.012, wire, parent=rig)
                paths.append(pts)
    colors = [M["white"], M["gold"], M["red"]]
    for k, (x, zs) in enumerate(layers):
        for i, z in enumerate(zs):
            glow = ck.glow(f"Node{k}{i}", ["white", "gold", "red"][k], 0.3)
            ck.sphere(f"Node{k}{i}", (x, 0, z), 0.19, glow, parent=rig)
            ck.torus(f"NodeRing{k}{i}", (x, 0, z), 0.19, 0.03, M["ink"], rotation=(math.pi / 2, 0, 0), parent=rig)
            ANIM["nodes"].append((glow, k, i))
    del colors
    gold = ck.glow("NetPacket", "gold", 3.0)
    for j, pts in enumerate(paths[::3]):
        p = ck.sphere(f"NetPacket{j}", (0, 0, 0), 0.06, gold, parent=rig, segments=12)
        ANIM["packets"].append((p, pts, j))


def sparkle(name, x, y, z, size, mat):
    rig = kit.empty(name)
    rig.location = (x, y, z)
    pts = []
    for i in range(8):
        a = math.pi / 2 + i * math.pi / 4
        r = size if i % 2 == 0 else size * 0.28
        pts.append((r * math.cos(a), r * math.sin(a)))
    ck.extruded(f"{name}_Body", pts, size * 0.25, mat, center=(0, 0, 0), bevel=size * 0.05, parent=rig)
    return rig


def sparkles(x, y):
    kit.use_collection("Sparkles")
    kit.cylinder("Spark_Base", (x, y, 0.08), 0.45, 0.16, M["ink"], bevel=0.04, vertices=40)
    kit.cylinder("Spark_Stem", (x, y, 0.35), 0.05, 0.4, M["ink"], bevel=0.01, vertices=16)
    big = sparkle("SparkBig", x, y, 1.15, 0.62, M["gold"])
    ANIM["spark_big"] = big
    for k, (dx, dz, s) in enumerate(((0.65, 1.85, 0.22), (-0.55, 1.75, 0.16))):
        sp = sparkle(f"SparkSmall{k}", x + dx, y, dz, s, ck.glow(f"SparkGlow{k}", "gold", 1.5))
        ANIM["sparks"].append((sp, dz, k))


def answer_bubble(x, y):
    kit.use_collection("Bubble")
    rig = kit.empty("Bubble")
    rig.location = (x, y, 1.2)
    rig.rotation_euler.z = math.radians(-20)
    kit.box("Bubble_Body", (0, 0, 0), (1.15, 0.2, 0.8), M["red"], bevel=0.3, segments=8, parent=rig)
    ck.extruded("Bubble_Tail", [(0.15, -0.3), (0.42, -0.3), (0.5, -0.68)], 0.16, M["red"], center=(0, 0, 0), bevel=0.02, parent=rig)
    ck.label("Bubble_AI", "AI", (0, 0.11, 0.08), 0.42, M["white"], depth=0.03, parent=rig)
    for d in range(3):
        dot = ck.sphere(f"Bubble_Dot{d}", (0.2 - d * 0.2, 0.11, -0.22), 0.05, M["white"], parent=rig, segments=12)
        ANIM["dots"].append((dot, d))
    kit.cylinder("Bubble_Post", (x, y - 0.05, 0.4), 0.04, 0.8, M["ink"], bevel=0.01, vertices=12)
    kit.cylinder("Bubble_Foot", (x, y - 0.05, 0.05), 0.32, 0.1, M["ink"], bevel=0.03, vertices=32)
    ANIM["bubble"] = rig


def build_characters():
    walkers = []
    specs = [("Doc", M["white"], "doc"), ("Code", M["blue"], "code"), ("Gold", M["gold"], None)]
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
        ph = T % 1.0
        for p, pts, j in ANIM["packets"]:
            u = (ph * 2 + j * 0.13) % 1.0  # 4초에 두 번 건너간다
            p.location = ck.sample(pts, u)
            p.keyframe_insert("location", frame=f)
            s = math.sin(math.pi * u) ** 0.4
            p.scale = (s, s, s)
            p.keyframe_insert("scale", frame=f)
        for mat, k, i in ANIM["nodes"]:  # 겹마다 차례로 밝아진다 (왼쪽 → 오른쪽)
            lit = max(0.0, 1 - abs(((ph * 2 - k * 0.3 - i * 0.04) % 1.0) - 0.2) / 0.15)
            inp = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
            inp.default_value = 0.3 + 2.4 * lit
            inp.keyframe_insert("default_value", frame=f)
        big = ANIM["spark_big"]
        big.rotation_euler.z = 2 * math.pi * t
        s = 1 + 0.06 * math.sin(2 * math.pi * 2 * T)
        big.scale = (s, s, s)
        big.keyframe_insert("rotation_euler", index=2, frame=f)
        big.keyframe_insert("scale", frame=f)
        for sp, z, k in ANIM["sparks"]:
            sp.location.z = z + 0.1 * math.sin(2 * math.pi * T + k * 2)
            sp.rotation_euler.z = -2 * math.pi * t * (k + 1)
            q = 0.7 + 0.3 * abs(math.sin(2 * math.pi * T + k))
            sp.scale = (q, q, q)
            sp.keyframe_insert("location", index=2, frame=f)
            sp.keyframe_insert("rotation_euler", index=2, frame=f)
            sp.keyframe_insert("scale", frame=f)
        for dot, d in ANIM["dots"]:
            dot.location.z = -0.22 + 0.06 * max(0.0, math.sin(2 * math.pi * 3 * T - d * 0.9))
            dot.keyframe_insert("location", index=2, frame=f)
        b = ANIM["bubble"]
        b.location.z = 1.2 + 0.06 * math.sin(2 * math.pi * T + 1)
        b.keyframe_insert("location", index=2, frame=f)
    ck.linear_keys()
    bpy.context.scene.frame_set(1)


def main():
    opts = kit.args()
    kit.reset_scene()
    ck.mats()
    ck.disc()
    network()
    sparkles(2.25, 0.35)
    answer_bubble(-2.2, 0.35)
    walkers = build_characters()
    kit.studio_lights(sun_dir=(-0.75, 0.55, 0.8), sun=1.15, sun_angle=8, world=0.42)
    _, cam_rig = ck.frame_camera()
    animate(cam_rig, walkers)
    obj = bpy.data.objects
    print("ANCHORS", ck.export_anchors("ai_world", {
        "network": ([o for o in obj if o.name.startswith(("Net_Post", "Net_Foot", "Node"))], "object", "세 겹 신경망 조형물, 빛 알갱이가 마디를 따라 흐른다 (AI 모델·추론·학습)"),
        "sparkle": ([obj["SparkBig"], obj["SparkSmall0"], obj["SparkSmall1"], obj["Spark_Base"], obj["Spark_Stem"]], "object",
                    "천천히 도는 큰 금색 반짝이 (생성 AI·새 기능·마법 같은 결과)"),
        "bubble": ([obj["Bubble"], obj["Bubble_Post"], obj["Bubble_Foot"]], "object", "'AI' 라고 쓴 빨간 말풍선, 점 3개가 통통 (챗봇·답변 생성 중)"),
        "white": (walkers[0].rig, "character", "흰 꼬마: 문서를 들고 걸어 다닌다 (사용자·프롬프트·데이터)"),
        "blue": (walkers[1].rig, "character", "파란 꼬마: 코드를 들고 걸어 다닌다 (개발자·API·에이전트)"),
        "yellow": (walkers[2].rig, "character", "노란 꼬마: 빈손으로 걸어 다닌다 (사용자·기업)"),
    }, FRAMES, "ai3d"))
    if "--anchors-only" in opts:
        return

    print("STILL", kit.render_still("ai_world", resolution=1080, height=1920, frame=1))
    if "--still-only" not in opts:
        print("LOOP", kit.render_loop("ai_world_loop", frames=FRAMES, resolution=1080, height=1920, crf=36))


main()
