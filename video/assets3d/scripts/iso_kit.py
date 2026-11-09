"""쇼츠용 3D 장면 공용 틀 (Blender 헤드리스 전용, Blender 5.2 에서 확인).

모든 장면 스크립트가 같이 쓴다:
- 장면 초기화, Eevee 렌더 설정, 투명 배경, PNG 메타데이터 끄기(다시 돌려도 같은 파일)
- 9:16 원근 카메라 + 천천히 도는 카메라 축(CAM_Rig)
- 스튜디오 조명(해 + 주변광), 채널 팔레트 재질
- 둥근 모서리 도형(box, cylinder), 로우폴리 구(ico), 컬렉션 도우미
- 정지 PNG / 루프 WebM(VP9 + 알파, BT.709) 출력

좌표: z 가 위. 도형의 기준점은 만든 자리 그대로 남는다(회전·부모 연결이 자연스럽게 된다).
"""

import math
import os
import shutil
import subprocess
import sys
import tempfile

import bpy
from mathutils import Vector

# ---------------------------------------------------------------- 팔레트
# video/src/Isometric.tsx shades 의 '중간 톤'(left)과 theme.ts ink 테마에서 가져온 색.
# 음영은 조명이 만든다. (윗면/오른쪽 면 색을 따로 칠하지 않는다)
PALETTE = {
    "paper": "#E6E1D4",
    "steel": "#45433D",
    "ink": "#26241F",
    "inkDeep": "#1B1A17",
    "floor": "#2E2D29",
    "red": "#D9483A",
    "gold": "#FFC24B",
    "screen": "#6DB6E8",
    # 장면(paper 테마)용
    "wall": "#EEEBE3",
    "floorTop": "#DAD6CC",
    "ground": "#E6E2D8",
    "white": "#F6F4EE",
    "glass": "#BFD6E4",
    "screenBg": "#1C2530",
    "sage": "#8FB28A",
    "sageDark": "#6F9870",
    "wood": "#C8A27A",
}

REPO_VIDEO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(REPO_VIDEO, "public", "assets3d")


def hex_to_linear(hex_color):
    h = hex_color.lstrip("#")
    srgb = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, 1.0)


# ---------------------------------------------------------------- 장면
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue

    ee = scene.eevee
    ee.taa_render_samples = 64
    for attr, value in (
        ("use_raytracing", True),
        ("use_shadows", True),
        ("use_gtao", True),
        ("gtao_distance", 0.4),
        ("shadow_ray_count", 2),
        ("shadow_step_count", 8),
        ("use_soft_shadows", True),
        ("fast_gi_distance", 0.4),
    ):
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, value)
            except (TypeError, AttributeError):
                pass

    # PNG 에 날짜·렌더 시간 메타데이터를 넣지 않는다 (다시 돌려도 같은 파일이 나오게)
    for attr in dir(scene.render):
        if attr.startswith("use_stamp"):
            try:
                setattr(scene.render, attr, False)
            except (TypeError, AttributeError):
                pass

    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"  # 팔레트 색을 그대로 유지
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.render.fps = 30

    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    bg.inputs["Strength"].default_value = 0.62  # 부드러운 주변광
    return scene


# ---------------------------------------------------------------- 재질
_materials = {}


def material(name, color, roughness=0.55, specular=0.35, emission=None, strength=0.0):
    key = (name, color, roughness, specular, emission, strength)
    if key in _materials and emission is None:
        return _materials[key]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex_to_linear(PALETTE.get(color, color))
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = hex_to_linear(PALETTE.get(color, color))  # 뷰포트 표시 색
    spec = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    spec.default_value = specular
    if emission:
        em = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        em.default_value = hex_to_linear(PALETTE.get(emission, emission))
        bsdf.inputs["Emission Strength"].default_value = strength
    _materials[key] = mat
    return mat


# ---------------------------------------------------------------- 도형
def box(name, center, size, mat, bevel=0.02, segments=3, parent=None):
    """모서리를 둥글린 직육면체. center/size 는 (x, y, z)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)  # 기준점은 제자리
    finish(obj, mat, bevel, segments, parent)
    return obj


def cylinder(name, center, radius, depth, mat, bevel=0.01, segments=2, vertices=48, axis="Z", parent=None):
    rot = {"Z": (0, 0, 0), "X": (0, math.pi / 2, 0), "Y": (math.pi / 2, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=center, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    finish(obj, mat, bevel, segments, parent)
    return obj


def finish(obj, mat, bevel, segments, parent):
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = "ANGLE"
        mod.harden_normals = True
    for poly in obj.data.polygons:
        poly.use_smooth = True
    if parent is not None:
        obj.parent = parent


def cut(target, cutter):
    """target 에서 cutter 를 빼고 cutter 는 지운다. (베벨보다 먼저 적용)"""
    mod = target.modifiers.new("Cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    target.modifiers.move(len(target.modifiers) - 1, 0)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier="Cut")
    bpy.data.objects.remove(cutter, do_unlink=True)


def ico(name, center, radius, mat, subdiv=1, parent=None):
    """로우폴리 구 (나뭇잎, 화분 식물). 면을 각지게 둔다."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=radius, location=center)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    if parent is not None:
        obj.parent = parent
    return obj


def use_collection(name):
    """이후 만드는 오브젝트를 name 컬렉션에 넣는다."""
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    layer = bpy.context.view_layer.layer_collection.children[name]
    bpy.context.view_layer.active_layer_collection = layer
    return coll


def studio_lights(sun_dir=(0.55, 0.35, 1.0), sun=1.0, sun_angle=12, world=0.55):
    """밝은 스튜디오 톤: 부드러운 해 + 하늘빛 주변광."""
    scene = bpy.context.scene
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = world
    data = bpy.data.lights.new("L_Sun", "SUN")
    data.energy = sun
    data.angle = math.radians(sun_angle)
    obj = bpy.data.objects.new("L_Sun", data)
    scene.collection.objects.link(obj)
    obj.rotation_euler = Vector(sun_dir).normalized().to_track_quat("Z", "Y").to_euler()
    return obj


def area_light(name, center, size, energy, color=(1.0, 0.97, 0.92)):
    """아래를 비추는 사각 면광 (층 천장 조명)."""
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = size
    data.energy = energy
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = center
    return obj


def vertical_camera(objects, lens=60, elevation=30, azimuth=45, margin=1.06, shift_y=0.0):
    """9:16 원근 카메라. objects 가 화면에 꽉 차게 거리를 맞추고, 가운데 축(Rig)에 매단다.
    Rig 의 z 회전을 키프레임하면 건물 주위를 천천히 돈다."""
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objects if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (lo + hi) / 2

    data = bpy.data.cameras.new("CAM_Main")
    data.lens = lens
    data.sensor_fit = "AUTO"
    data.clip_end = 500
    data.shift_y = shift_y
    cam = bpy.data.objects.new("CAM_Main", data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    el, az = math.radians(elevation), math.radians(azimuth)
    direction = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    cam.location = center + direction * 50
    bpy.context.view_layer.update()
    flat = [v for p in pts for v in p]
    loc, _ = cam.camera_fit_coords(bpy.context.evaluated_depsgraph_get(), flat)
    cam.location = center + (Vector(loc) - center) * margin

    rig = bpy.data.objects.new("CAM_Rig", None)
    scene.collection.objects.link(rig)
    rig.location = center
    bpy.context.view_layer.update()
    world = cam.matrix_world.copy()
    cam.parent = rig
    cam.matrix_world = world
    return cam, rig


def empty(name, parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


# ---------------------------------------------------------------- 출력
def _png(scene, resolution, height=None):
    r = scene.render
    r.resolution_x = resolution
    r.resolution_y = height or resolution
    r.resolution_percentage = 100
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.image_settings.color_depth = "8"
    r.image_settings.compression = 90


def render_still(name, resolution=1200, frame=1, height=None):
    scene = bpy.context.scene
    _png(scene, resolution, height)
    scene.frame_set(frame)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def find_ffmpeg():
    local = os.path.join(REPO_VIDEO, "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe")
    # 워크트리에는 node_modules 가 없을 수 있어 본 저장소 위치도 본다
    main = os.path.abspath(os.path.join(REPO_VIDEO, "..", "..", "..", "..", "video", "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe"))
    for candidate in (os.environ.get("FFMPEG"), local, main, shutil.which("ffmpeg")):
        if candidate and os.path.exists(candidate):
            return candidate
    raise RuntimeError("ffmpeg 를 찾지 못했습니다. FFMPEG 환경변수로 경로를 지정하세요.")


def render_loop(name, frames=60, resolution=720, crf=34, height=None):
    """PNG 시퀀스를 임시 폴더에 뽑고 VP9 + 알파 WebM 으로 묶는다. 시퀀스는 저장소에 남기지 않는다."""
    scene = bpy.context.scene
    _png(scene, resolution, height)
    scene.render.image_settings.compression = 15
    scene.frame_start = 1
    scene.frame_end = frames
    tmp = tempfile.mkdtemp(prefix=f"{name}_")
    scene.render.filepath = os.path.join(tmp, "f_")
    bpy.ops.render.render(animation=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{name}.webm")
    cmd = [
        find_ffmpeg(), "-y", "-loglevel", "error",
        "-framerate", str(scene.render.fps),
        "-start_number", "1",
        "-i", os.path.join(tmp, "f_%04d.png"),
        # 색공간을 BT.709 로 명시 (안 하면 브라우저에서 빨강이 주황으로 틀어진다)
        "-vf", "scale=out_color_matrix=bt709:out_range=tv",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
        "-b:v", "0", "-crf", str(crf), "-row-mt", "1", "-auto-alt-ref", "0",
        out,
    ]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def args():
    """blender -b -P script.py -- [--still-only] [--no-plate] 의 '--' 뒤 인자."""
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
