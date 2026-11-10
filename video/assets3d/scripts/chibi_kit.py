"""꼬마 캐릭터 + 장면 공용 소품 (iso_kit 위에 얹는 두 번째 틀).

desk_world.py 의 꼬마(달걀 몸, 쪼꼬만 발, 콩알 팔, 머리 새싹)를 다른 장면에서도 똑같이 쓰려고 뽑아 둔 것이다.
desk_world.py 는 먼저 만들어진 장면이라 자기 안에 같은 코드를 따로 갖고 있다.

- mats(): 장면 공용 재질 (M 에 담긴다)
- chibi(): 꼬마 한 명 (rig 원점 = 발바닥, 앞 = 로컬 +y)
- disc(): 장면 받침 원판 (책상 장면과 같은 크기·색)
- Walker / Hopper: 루프가 끊기지 않는 걷기·통통 애니메이션
- extruded(), ribbon(), label(): 윤곽선 기둥, 휘어진 띠(영수증·케이블), 3D 글자
"""

import math

import bmesh
import bpy
from mathutils import Vector

import iso_kit as kit

M = {}


def mats():
    m = kit.material
    M.update(
        disc=m("M_Disc", "#EAE5D9", 0.65, 0.25),
        discSide=m("M_DiscSide", "ink", 0.55, 0.25),
        steel=m("M_SteelBody", "#3A3833", 0.42, 0.45),
        dark=m("M_LapDark", "inkDeep", 0.5, 0.3),
        white=m("M_White", "white", 0.45, 0.3),
        ink=m("M_Ink", "ink", 0.5, 0.3),
        red=m("M_Red", "red", 0.42, 0.4),
        gold=m("M_Gold", "gold", 0.32, 0.6),
        blue=m("M_Blue", "screen", 0.5, 0.3),
        sage=m("M_Sage", "sage", 0.7, 0.2),
        sageDark=m("M_SageDark", "sageDark", 0.7, 0.2),
        paper=m("M_Paper", "paper", 0.6, 0.2),
        blush=m("M_Blush", "#F3A497", 0.6, 0.2),
        eye=m("M_Eye", "#16150F", 0.25, 0.6),
        screenBg=m("M_ScreenBg", "screenBg", 0.3, 0.3, emission="screenBg", strength=0.7),
    )
    return M


def glow(name, color, strength=1.2):
    return kit.material(f"M_Glow_{name}", color, 0.3, 0.3, emission=color, strength=strength)


def sphere(name, center, radius, mat, scale=(1, 1, 1), parent=None, segments=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=segments // 2, radius=radius, location=center)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    if parent is not None:
        obj.parent = parent
    return obj


def torus(name, center, major, minor, mat, rotation=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=center, rotation=rotation, major_segments=48, minor_segments=16)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    if parent is not None:
        obj.parent = parent
    return obj


# ---------------------------------------------------------------- 꼬마
def chibi(name, body_mat, carry=None, sprout=True, collection="Characters"):
    """짜리몽땅 꼬마: 큰 달걀 몸(=머리) + 쪼꼬만 발 + 콩알 팔. 앞은 로컬 +y.
    carry: None / coin / code / doc / key / trophy / flask (머리 위로 번쩍 든다)"""
    kit.use_collection(collection)
    rig = kit.empty(f"{name}_Rig")
    body = kit.empty(f"{name}_Body", parent=rig)
    sphere(f"{name}_Egg", (0, 0, 0.27), 0.22, body_mat, scale=(1, 0.92, 1.0), parent=body)
    for sx in (-1, 1):
        sphere(f"{name}_Eye{sx}", (sx * 0.075, 0.185, 0.3), 0.03, M["eye"], scale=(1, 0.6, 1.25), parent=body, segments=16)
        sphere(f"{name}_Hi{sx}", (sx * 0.075 + 0.01, 0.2, 0.315), 0.009, M["white"], parent=body, segments=12)
        sphere(f"{name}_Blush{sx}", (sx * 0.13, 0.165, 0.245), 0.03, M["blush"], scale=(1, 0.4, 0.6), parent=body, segments=16)
    sphere(f"{name}_Mouth", (0, 0.2, 0.25), 0.012, M["eye"], scale=(1.4, 0.6, 0.8), parent=body, segments=12)
    arms = [sphere(f"{name}_Arm{sx}", (sx * 0.215, 0.03, 0.2), 0.05, body_mat, scale=(0.8, 0.9, 1.1), parent=body, segments=16) for sx in (-1, 1)]
    if sprout:
        kit.cylinder(f"{name}_Stem", (0, 0, 0.5), 0.008, 0.07, M["sageDark"], bevel=0, vertices=8, parent=body)
        for sx in (-1, 1):
            leaf = sphere(f"{name}_Leaf{sx}", (sx * 0.035, 0, 0.54), 0.035, M["sage"], scale=(1.3, 0.45, 0.6), parent=body, segments=12)
            leaf.rotation_euler.y = math.radians(-25 * sx)

    def part(obj):
        obj.parent = body
        return obj

    if carry == "coin":
        kit.cylinder(f"{name}_Coin", (0, 0.02, 0.66), 0.13, 0.04, M["gold"], bevel=0.012, vertices=40, axis="Y", parent=body)
        kit.cylinder(f"{name}_CoinIn", (0, 0.045, 0.66), 0.085, 0.01, M["red"], bevel=0.004, vertices=32, axis="Y", parent=body)
    elif carry == "code":
        part(kit.box(f"{name}_Code", (0, 0.02, 0.66), (0.26, 0.16, 0.18), M["red"], bevel=0.035))
        for k, w in enumerate((0.14, 0.09)):
            part(kit.box(f"{name}_CodeLn{k}", (-0.04 + w / 2 - 0.03, 0.105, 0.69 - k * 0.05), (w, 0.01, 0.022), M["white"], bevel=0))
    elif carry == "doc":
        part(kit.box(f"{name}_Doc", (0, 0.02, 0.66), (0.24, 0.03, 0.3), M["paper"], bevel=0.01))
        for k in range(3):
            part(kit.box(f"{name}_DocLn{k}", (0, 0.04, 0.73 - k * 0.06), (0.15, 0.005, 0.018), M["ink"], bevel=0))
    elif carry == "key":
        torus(f"{name}_KeyRing", (-0.09, 0.02, 0.66), 0.075, 0.025, M["gold"], rotation=(math.pi / 2, 0, 0), parent=body)
        part(kit.box(f"{name}_KeyShaft", (0.06, 0.02, 0.66), (0.2, 0.04, 0.045), M["gold"], bevel=0.012))
        for k, dx in enumerate((0.1, 0.145)):
            part(kit.box(f"{name}_KeyTooth{k}", (dx, 0.02, 0.62), (0.03, 0.04, 0.06), M["gold"], bevel=0.008))
    elif carry == "trophy":
        kit.cylinder(f"{name}_TrBase", (0, 0.02, 0.56), 0.09, 0.05, M["ink"], bevel=0.012, vertices=32, parent=body)
        kit.cylinder(f"{name}_TrStem", (0, 0.02, 0.62), 0.025, 0.08, M["gold"], bevel=0.005, vertices=16, parent=body)
        sphere(f"{name}_TrCup", (0, 0.02, 0.74), 0.11, M["gold"], scale=(1, 1, 0.9), parent=body)
        for sx in (-1, 1):
            torus(f"{name}_TrHandle{sx}", (sx * 0.11, 0.02, 0.76), 0.045, 0.014, M["gold"], rotation=(math.pi / 2, 0, 0), parent=body)
    elif carry == "flask":
        sphere(f"{name}_Flask", (0, 0.02, 0.64), 0.1, glow("FlaskLiquid", "red", 0.9), parent=body)
        kit.cylinder(f"{name}_FlaskNeck", (0, 0.02, 0.77), 0.035, 0.12, M["white"], bevel=0.008, vertices=16, parent=body)
    if carry:
        for a, sx in zip(arms, (-1, 1)):
            a.location = (sx * 0.17, 0.03, 0.47)
    feet = [sphere(f"{name}_Foot{sx}", (sx * 0.085, 0.02, 0.03), 0.06, M["ink"], scale=(0.9, 1.3, 0.55), parent=rig, segments=16) for sx in (-1, 1)]
    return rig, body, feet


class Walker:
    """닫힌 길(타원)을 도는 꼬마. 루프 동안 laps 바퀴(정수)를 돌아 제자리로 → 끊김이 없다.
    (1/n 바퀴만 돌면 루프 이음새에서 서로 다른 꼬마가 옆자리로 순간 이동한다)"""

    def __init__(self, rig, body, feet, offset, size, center, radii, laps=1):
        self.rig, self.body, self.feet = rig, body, feet
        self.offset, self.size, self.center, self.radii, self.laps = offset, size, center, radii, laps

    def point(self, u):
        a = 2 * math.pi * u
        x = self.center[0] + self.radii[0] * math.cos(a)
        y = self.center[1] + self.radii[1] * math.sin(a)
        dx, dy = -self.radii[0] * math.sin(a), self.radii[1] * math.cos(a)
        return x, y, math.atan2(dy, dx) - math.pi / 2

    def key(self, f, t, steps, z0=0.0):
        x, y, heading = self.point(self.offset + t * self.laps)
        ph = math.pi * steps * t + self.offset * 7
        self.rig.location = (x, y, z0 + self.size * 0.035 * abs(math.sin(ph)))
        self.rig.rotation_euler = (0, math.radians(7) * math.sin(ph), heading)
        self.rig.keyframe_insert("location", frame=f)
        self.rig.keyframe_insert("rotation_euler", frame=f)
        for k, foot in enumerate(self.feet):
            s = math.sin(ph + k * math.pi)
            foot.location.z = 0.03 + 0.045 * max(0.0, s)
            foot.location.y = 0.02 + 0.06 * math.cos(ph + k * math.pi)
            foot.keyframe_insert("location", frame=f)
        self.body.location.z = 0.012 * math.sin(2 * ph)
        self.body.scale = (1 + 0.03 * math.sin(2 * ph), 1, 1 - 0.03 * math.sin(2 * ph))
        self.body.keyframe_insert("location", frame=f)
        self.body.keyframe_insert("scale", frame=f)


def hop(f, t, body, feet, hops=8, height=0.07, phase=0.0):
    """제자리 통통 (hops 는 정수: 루프 끝에서 처음과 같아진다)."""
    h = abs(math.sin(math.pi * hops * t + phase))
    body.location.z = height * h
    body.scale = (1 + 0.06 * (1 - h), 1, 1 - 0.06 * (1 - h))
    body.keyframe_insert("location", frame=f)
    body.keyframe_insert("scale", frame=f)
    for k, foot in enumerate(feet):
        foot.location.z = 0.03 + 0.4 * height * h * (1 if k == int(hops * t + phase / math.pi) % 2 else 0.4)
        foot.keyframe_insert("location", frame=f)


def sway(f, t, body, degrees=8, cycles=2, phase=0.0):
    body.rotation_euler.y = math.radians(degrees) * math.sin(2 * math.pi * cycles * t + phase)
    body.keyframe_insert("rotation_euler", frame=f)


def pulse(f, t, mat, low, high, cycles, phase=0.0, square=False):
    inp = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    s = math.sin(2 * math.pi * cycles * t + phase)
    inp.default_value = (high if s > 0 else low) if square else low + (high - low) * (0.5 + 0.5 * s)
    inp.keyframe_insert("default_value", frame=f)


def linear_keys():
    for action in bpy.data.actions:
        for fc in getattr(action, "fcurves", []):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    # Blender 5 의 레이어드 액션: 채널백 안의 fcurve 도 직선으로
    for action in bpy.data.actions:
        for layer in getattr(action, "layers", []):
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", []):
                    for fc in bag.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "LINEAR"


# ---------------------------------------------------------------- 받침, 도형
DISC_C, DISC_R = (0.0, 0.5), 3.9


def disc():
    kit.use_collection("Stage")
    kit.cylinder("Disc_Top", (DISC_C[0], DISC_C[1], -0.04), DISC_R, 0.08, M["disc"], bevel=0.03, vertices=128)
    kit.cylinder("Disc_Side", (DISC_C[0], DISC_C[1], -0.3), DISC_R - 0.02, 0.45, M["discSide"], bevel=0.04, vertices=128)


def extruded(name, outline_xz, depth, mat, center=(0, 0, 0), bevel=0.02, parent=None):
    """xz 평면 윤곽선(시계 반대 방향 점들)을 y 로 depth 만큼 밀어 낸 기둥. 방패·자물쇠 고리 같은 모양."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((x, depth / 2, z)) for x, z in outline_xz]
    face = bm.faces.new(verts)
    bmesh.ops.recalc_face_normals(bm, faces=[face])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    moved = [v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=moved, vec=(0, -depth, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    obj.location = center
    kit.finish(obj, mat, bevel, 3, parent)
    for p in obj.data.polygons:  # 평평한 앞뒷면은 각지게 (매끈하게 두면 얼룩이 생긴다)
        p.use_smooth = False
    return obj


def ribbon(name, points, width, mat, axis=(1, 0, 0), thickness=0.012):
    """점들을 따라 가는 얇은 띠 (영수증 종이, 바닥 케이블). axis 방향으로 width 만큼 넓다."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    half = Vector(axis).normalized() * (width / 2)
    rows = [(bm.verts.new(Vector(p) - half), bm.verts.new(Vector(p) + half)) for p in points]
    for (a0, b0), (a1, b1) in zip(rows, rows[1:]):
        bm.faces.new((a0, b0, b1, a1))
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    sol = obj.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = thickness
    sol.offset = 0
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def label(name, text, center, size, mat, depth=0.02, rotation=(math.pi / 2, 0, math.pi), parent=None):
    """3D 글자 (숫자·기호만 쓴다. 한글 글꼴 의존을 피한다). 기본은 +y(카메라)를 보고 선다."""
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = text
    curve.size = size
    curve.extrude = depth
    curve.bevel_depth = depth * 0.3
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.location = center
    obj.rotation_euler = rotation
    obj.data.materials.append(mat)
    if parent is not None:
        obj.parent = parent
    return obj


def bezier_points(p0, p1, p2, n=12):
    """2차 베지어 (점들은 튜플)."""
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(tuple((1 - t) ** 2 * a + 2 * (1 - t) * t * b + t * t * c for a, b, c in zip(p0, p1, p2)))
    return out


def frame_camera(lens=50, elevation=38, azimuth=68, margin=0.8, shift_y=0.05):
    """책상 장면과 똑같은 카메라. 책상 장면이 맞춘 범위(원판 + 노트북 화면 꼭대기 z≈2.4)를
    보이지 않는 상자로 흉내 내서 거리를 맞춘다 → 장면마다 원판 크기·자리가 같다."""
    proxy = kit.box("CamProxy", (DISC_C[0], DISC_C[1], (-0.525 + 2.43) / 2), (2 * DISC_R, 2 * DISC_R, 0.525 + 2.43), M["ink"], bevel=0)
    cam, rig = kit.vertical_camera([proxy], lens=lens, elevation=elevation, azimuth=azimuth, margin=margin)
    bpy.data.objects.remove(proxy, do_unlink=True)
    cam.data.shift_y = shift_y
    return cam, rig


# ---------------------------------------------------------------- 두 번째 묶음 장면들이 같이 쓰는 도형·움직임
def tube(name, points, radius, mat, parent=None):
    """점들을 지나는 둥근 관 (케이블, 깃 가지, 빛 줄기)."""
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
    if parent is not None:
        obj.parent = parent
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


def cone(name, center, r1, r2, depth, mat, vertices=48, rotation=(0, 0, 0), parent=None):
    """원뿔(로켓 코, 깔때기, 불꽃). r1 = 아래 반지름, r2 = 위 반지름."""
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2, depth=depth, location=center, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    if parent is not None:
        obj.parent = parent
    return obj


def wedge(name, radius, height, a0, a1, mat, center=(0, 0, 0), steps=24, parent=None):
    """원기둥 부채꼴 조각 (원그래프). 각도는 도(degree), 원점 = 부채꼴 꼭짓점 바닥."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    ring = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        ring.append((radius * math.cos(a), radius * math.sin(a)))
    pts = [(0.0, 0.0)] + ring
    bottom = [bm.verts.new((x, y, 0)) for x, y in pts]
    top = [bm.verts.new((x, y, height)) for x, y in pts]
    bm.faces.new(list(reversed(bottom)))
    bm.faces.new(top)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    obj.location = center
    kit.finish(obj, mat, 0.015, 2, parent)
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj


def show(obj, f, visible):
    """보였다 안 보였다 (매 프레임 키를 넣으므로 크기 0/1 로 끊어서 바꾼다)."""
    s = 1.0 if visible else 0.0
    obj.scale = (s, s, s)
    obj.keyframe_insert("scale", frame=f)
