"""Blender background pipeline for Meshy -> TaleSpire asset prep.

Usage: blender --background --python core/blender_pipeline.py -- <config.json>
This file is intentionally executed by Blender's bundled Python, not the
ordinary Python interpreter.
"""
import json
import math
import os
import shutil
import sys
import traceback
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix

# Blender uses its own Python runtime: load this sibling from files bundled
# in PyInstaller's _internal/core, not from the Studio process.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from obj_vertex_budget import (inspect_obj_vertex_budget,
                               next_triangle_budget, SAFE_SPLIT_VERTEX_TARGET)


def status(percent, msg):
    print(f"AMF_PROGRESS|{int(percent)}|{msg}", flush=True)


def get_config():
    if "--" not in sys.argv:
        raise ValueError("Falta o arquivo de configuracao apos '--'.")
    file = Path(sys.argv[sys.argv.index("--") + 1])
    return json.loads(file.read_text(encoding="utf-8"))


def deselect():
    bpy.ops.object.select_all(action='DESELECT')


def activate(obj):
    deselect()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def import_model(filepath):
    ext = Path(filepath).suffix.lower()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if ext == ".blend":
        # Use the saved model directly, including packed textures/materials.
        # The Blender process is started with --disable-autoexec.
        bpy.ops.wm.open_mainfile(filepath=filepath, load_ui=False)
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=filepath)
        else:
            bpy.ops.import_scene.obj(filepath=filepath)
    elif ext == ".stl":
        if hasattr(bpy.ops.wm, "stl_import"):
            bpy.ops.wm.stl_import(filepath=filepath)
        else:
            bpy.ops.import_mesh.stl(filepath=filepath)
    else:
        raise ValueError("Formato nao suportado: " + ext)


def prepare_uv_and_materials(obj):
    # Convert modifiers/rig deformation into one static mesh before joining.
    activate(obj)
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.object
    if obj.data.uv_layers:
        original = obj.data.uv_layers.active
        original.name = 'AMF_Original'
    else:
        # Meshes without UVs can still be baked (e.g. STL); use smart unwrap.
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(island_margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')
        if obj.data.uv_layers:
            obj.data.uv_layers.active.name = 'AMF_Original'
    if not obj.data.materials:
        material = bpy.data.materials.new(name='AMF_Default')
        material.use_nodes = True
        material.diffuse_color = (0.72, 0.72, 0.75, 1)
        bsdf = material.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.72, 0.72, 0.75, 1)
        obj.data.materials.append(material)
    return obj


def stabilize_texture_uvs(materials):
    # Meshy's glTF imports commonly use the default (active) UV map.
    # Explicitly pin unconnected image-node vectors to the ORIGINAL UV layer.
    for mat in materials:
        if mat is None:
            continue
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        uv = nodes.new('ShaderNodeUVMap')
        uv.uv_map = 'AMF_Original'
        for n in list(nodes):
            if n.type == 'TEX_IMAGE' and not n.inputs['Vector'].is_linked:
                links.new(uv.outputs['UV'], n.inputs['Vector'])
        # Otherwise the imported material's existing UV wiring is kept intact.


def geometry_as_single_mesh():
    source_meshes = [o for o in list(bpy.context.scene.objects) if o.type == 'MESH']
    if not source_meshes:
        raise ValueError('Nao foram encontradas malhas no arquivo.')
    for obj in source_meshes:
        obj = prepare_uv_and_materials(obj)
        # Vertices in world coordinates, so join doesn't inherit strange origins.
        matrix = obj.matrix_world.copy()
        obj.data = obj.data.copy()  # avoid mutating another object's shared mesh
        obj.data.transform(matrix)
        obj.matrix_world.identity()
    source_meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    deselect()
    for obj in source_meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = source_meshes[0]
    bpy.ops.object.join()
    result = bpy.context.object
    result.name = 'Astronyx_Miniature'
    for mat in set([m for m in result.data.materials if m]):
        stabilize_texture_uvs([mat])
    return result


def metrics(mesh_obj):
    vertices = mesh_obj.data.vertices
    if not vertices:
        raise ValueError('O arquivo 3D nao contem vertices.')
    xs = [v.co.x for v in vertices]
    ys = [v.co.y for v in vertices]
    zs = [v.co.z for v in vertices]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

def enforce_footprint(obj, limit=1.30):
    """Limit visual footprint of export, not TaleSpire's gameplay collider."""
    lowx, highx, lowy, highy, _, _ = metrics(obj)
    footprint = max(highx-lowx, highy-lowy)
    if footprint <= limit:
        return 1.0
    factor = limit / footprint
    for vert in obj.data.vertices:
        vert.co *= factor
    obj.data.update()
    print(f'AMF_WARNING|Base muito larga, reduzindo {factor:.3f}x. '
          'Asas e armas podem diminuir o tamanho aparente.', flush=True)
    return factor


def normalize_model(obj, cfg):
    angle = math.radians(cfg['rotation'])
    rot = Matrix.Rotation(angle, 4, 'Z')
    obj.data.transform(rot)
    lowx, highx, lowy, highy, lowz, highz = metrics(obj)
    height = highz - lowz
    if height < 1e-6:
        raise ValueError('Altura da miniatura e praticamente zero; revise a orientacao.')
    scale = cfg['height'] / height
    cx, cy = (lowx + highx) / 2, (lowy + highy) / 2
    for vert in obj.data.vertices:
        vert.co.x = (vert.co.x - cx) * scale
        vert.co.y = (vert.co.y - cy) * scale
        vert.co.z = (vert.co.z - lowz) * scale
    obj.data.update()
    return {'height_scale': scale, 'footprint_scale': enforce_footprint(obj)}


def optimize(obj, desired_faces):
    activate(obj)
    source_faces = len(obj.data.polygons)
    source_vertices = len(obj.data.vertices)
    # We triangulate explicitly. TaleWeaverLite requires one triangle mesh.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    faces = len(obj.data.polygons)
    initial_triangles = faces
    if faces > desired_faces:
        dec = obj.modifiers.new('Astronyx_LowPoly', 'DECIMATE')
        dec.ratio = max(0.001, desired_faces / faces)
        bpy.ops.object.modifier_apply(modifier=dec.name)
    while len(obj.data.vertices) > 55000 and len(obj.data.polygons) > 600:
        old = len(obj.data.polygons)
        mod = obj.modifiers.new('Astronyx_SafetyLimit', 'DECIMATE')
        mod.ratio = 0.75
        bpy.ops.object.modifier_apply(modifier=mod.name)
        if len(obj.data.polygons) >= old:
            break
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for face in bm.faces:
        face.smooth = True
    for edge in bm.edges:
        if len(edge.link_faces) == 2 and edge.calc_face_angle(0.0) > math.radians(55):
            edge.smooth = False
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    if len(obj.data.vertices) > 60000:
        raise ValueError('O modelo ainda excede 60.000 vertices. Reduza o limite de triangulos.')
    if source_faces and len(obj.data.polygons) < source_faces * 0.55:
        print('AMF_WARNING|Malha reduzida mais de 45 por cento; detalhes finos podem mudar.', flush=True)
    retained = (min(100., 100. * len(obj.data.polygons) / initial_triangles)
                if initial_triangles else 100.)
    return {'vertices': len(obj.data.vertices), 'triangles': len(obj.data.polygons),
            'original_vertices': source_vertices, 'original_faces': source_faces,
            'initial_triangles': initial_triangles,
            'triangle_retention_percent': round(retained, 1)}


def make_uv_atlas(obj):
    """Retain original UVs for a single material; otherwise build an atlas.

    Repacking a valid single-material Meshy UV into tiny islands can blur faces,
    ornaments and armor even with a 2048px texture.
    """
    activate(obj)
    used_materials = [m for m in obj.data.materials if m]
    original = obj.data.uv_layers.get('AMF_Original')
    if original is not None and len(used_materials) <= 1:
        obj.data.uv_layers.active = original
        original.active_render = True
        print('AMF_PROGRESS|53|UV original do Meshy preservado', flush=True)
        return original.name
    print('AMF_WARNING|UVs requerem atlas (multiplos materiais ou sem UV); reveja detalhes finos.', flush=True)
    if obj.data.uv_layers.get('AMF_Atlas') is None:
        obj.data.uv_layers.new(name='AMF_Atlas')
    layer = obj.data.uv_layers['AMF_Atlas']
    obj.data.uv_layers.active = layer
    layer.active_render = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # Keep space for an 8-12px bake bleed while improving atlas utilization.
    bpy.ops.uv.smart_project(island_margin=0.008)
    bpy.ops.object.mode_set(mode='OBJECT')
    return layer.name


def new_image(name, size, *, is_data=False):
    image = bpy.data.images.new(name, width=size, height=size, alpha=True, float_buffer=False)
    if is_data:
        image.colorspace_settings.name = 'Non-Color'
    return image


def add_image_target(material, image):
    material.use_nodes = True
    nodes = material.node_tree.nodes
    for node in nodes:
        node.select = False
    target = nodes.new('ShaderNodeTexImage')
    target.name = 'AMF_Bake_Target'
    target.image = image
    nodes.active = target
    target.select = True
    return target


def save_image(image, filepath):
    image.filepath_raw = str(filepath)
    image.file_format = 'PNG'
    image.alpha_mode = 'STRAIGHT'
    image.save()


def run_bake(obj, kind, image, *, pass_filter=None):
    for material in obj.data.materials:
        if material:
            add_image_target(material, image)
    activate(obj)
    bpy.context.scene.render.engine = 'CYCLES'
    # More robust antialiasing at UV seams with limited additional CPU cost.
    bpy.context.scene.cycles.samples = 4
    bpy.context.scene.render.bake.use_selected_to_active = False
    margin = max(8, min(12, image.size[0] // 256))
    opts = {'type': kind, 'margin': margin, 'use_clear': True}
    if pass_filter is not None:
        opts['pass_filter'] = pass_filter
    bpy.ops.object.bake(**opts)


def swapped_material_bake(obj, property_name, img, default_value):
    """Bake a Principled PBR numeric property into a grayscale texture."""
    originals = list(obj.data.materials)
    temps = []
    try:
        for idx, old in enumerate(originals):
            tmp = old.copy() if old else bpy.data.materials.new(name='AMF_Bake_Default')
            tmp.name = f'AMF_Bake_{property_name}_{idx}'
            tmp.use_nodes = True
            nodes = tmp.node_tree.nodes
            links = tmp.node_tree.links
            principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
            surf = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
            if surf is None:
                surf = nodes.new('ShaderNodeOutputMaterial')
            emitter = nodes.new('ShaderNodeEmission')
            emitter.inputs['Strength'].default_value = 1.0
            socket = principled.inputs.get(property_name) if principled else None
            if socket:
                if socket.is_linked:
                    previous = socket.links[0]
                    links.new(previous.from_socket, emitter.inputs['Color'])
                else:
                    n = float(socket.default_value)
                    emitter.inputs['Color'].default_value = (n, n, n, 1)
            else:
                emitter.inputs['Color'].default_value = (default_value,) * 3 + (1,)
            links.new(emitter.outputs['Emission'], surf.inputs['Surface'])
            tmp_target = add_image_target(tmp, img)
            tmp.node_tree.nodes.active = tmp_target
            obj.data.materials[idx] = tmp
            temps.append(tmp)
        activate(obj)
        bpy.ops.object.bake(type='EMIT', margin=6, use_clear=True)
    finally:
        for i, material in enumerate(originals):
            obj.data.materials[i] = material
        for mat in temps:
            if mat.users == 0:
                bpy.data.materials.remove(mat)


def blank_normal(size):
    normal = new_image('AMF_Normal', size, is_data=True)
    pixels = np.empty(size * size * 4, dtype=np.float32)
    pixels[0::4] = 0.5
    pixels[1::4] = 0.5
    pixels[2::4] = 1
    pixels[3::4] = 1
    normal.pixels.foreach_set(pixels)
    normal.update()
    return normal



def try_preserve_png_albedo(obj, uv_name, output):
    """Keep exact PNG pixels when the source shader is a direct UV-to-color PNG.

    Avoid unnecessary Cycles baking of Meshy's original face/hair/armor albedo.
    Complex or multi-material graphs still go through the regular bake path;
    no assumption is made about non-PNG packed files or transformed UVs.
    """
    if uv_name != 'AMF_Original' or len(obj.data.materials) != 1:
        return None
    material = obj.data.materials[0]
    if material is None or not material.use_nodes:
        return None
    nodes = material.node_tree.nodes
    principled = next((node for node in nodes if node.type == 'BSDF_PRINCIPLED'), None)
    if principled is None:
        return None
    base = principled.inputs.get('Base Color')
    if base is None or not base.is_linked:
        return None
    link = base.links[0]
    texture = link.from_node
    if texture.type != 'TEX_IMAGE' or link.from_socket.name != 'Color':
        return None
    image = texture.image
    if image is None or image.source != 'FILE':
        return None
    if image.colorspace_settings.name != 'sRGB':
        return None
    if not (0 < image.size[0] <= 2048 and 0 < image.size[1] <= 2048):
        return None
    # In case the source material deliberately uses UV transforms, bake the
    # shading instead; a bare texture copy would otherwise have wrong mapping.
    vector = texture.inputs.get('Vector')
    if vector is not None and vector.is_linked:
        uv_link = vector.links[0]
        if (uv_link.from_node.type != 'UVMAP'
                or uv_link.from_node.uv_map != uv_name):
            return None

    png_sig = b'\x89PNG\r\n\x1a\n'
    try:
        if image.packed_file is not None:
            payload = bytes(image.packed_file.data)
            if not payload.startswith(png_sig):
                return None
            output.write_bytes(payload)
        else:
            source = Path(bpy.path.abspath(image.filepath, library=image.library))
            if not source.is_file():
                return None
            with source.open('rb') as stream:
                if stream.read(8) != png_sig:
                    return None
            shutil.copy2(source, output)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print('AMF_WARNING|Nao foi possivel copiar PNG original: ' + str(exc), flush=True)
        return None
    print('AMF_PROGRESS|58|PNG albedo original preservado sem recompressao', flush=True)
    return image


def bake_textures(obj, folder, size):
    status(52, 'Criando atlas de UV e texturas')
    uv_name = make_uv_atlas(obj)
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'CPU'
    albedo = try_preserve_png_albedo(obj, uv_name, folder / 'Albedo.png')
    kept_original_png = albedo is not None
    if not kept_original_png:
        albedo = new_image('AMF_Albedo', size)
        status(58, 'Renderizando albedo')
        run_bake(obj, 'DIFFUSE', albedo, pass_filter={'COLOR'})
        save_image(albedo, folder / 'Albedo.png')
    status(66, 'Renderizando normal map')
    normal = new_image('AMF_Normal_Baked', size, is_data=True)
    try:
        run_bake(obj, 'NORMAL', normal)
    except Exception as exc:
        print('AMF_WARNING|Normal map simplificado: ' + str(exc), flush=True)
        normal = blank_normal(size)
    save_image(normal, folder / 'Normal.png')
    status(73, 'Renderizando acabamento metalico')
    metallic = new_image('AMF_Metallic', size, is_data=True)
    swapped_material_bake(obj, 'Metallic', metallic, 0)
    status(79, 'Renderizando acabamento fosco/brilhante')
    roughness = new_image('AMF_Roughness', size, is_data=True)
    swapped_material_bake(obj, 'Roughness', roughness, 0.75)
    status(84, 'Preparando textura MAES')
    a = np.empty(size * size * 4, dtype=np.float32)
    metal = np.empty(size * size * 4, dtype=np.float32)
    rough = np.empty(size * size * 4, dtype=np.float32)
    metallic.pixels.foreach_get(metal)
    roughness.pixels.foreach_get(rough)
    a[0::4] = np.clip(metal[0::4], 0, 1)
    a[1::4] = 1.0  # Neutral ambient occlusion (does not darken materials)
    a[2::4] = 0.0  # Neutral emissive by default
    a[3::4] = 1.0 - np.clip(rough[0::4], 0, 1)
    packed = new_image('AMF_MAES', size, is_data=True)
    packed.pixels.foreach_set(a)
    packed.update()
    save_image(packed, folder / 'MAES.png')
    return albedo, normal, uv_name, kept_original_png


def assign_final_material(obj, albedo_image, uv_name):
    mat = bpy.data.materials.new(name='AstronyxMini')
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = albedo_image
    uv = mat.node_tree.nodes.new('ShaderNodeUVMap')
    uv.uv_map = uv_name
    mat.node_tree.links.new(uv.outputs['UV'], tex.inputs['Vector'])
    mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.data.uv_layers.active = obj.data.uv_layers[uv_name]
    obj.data.uv_layers[uv_name].active_render = True


def export_fbx(obj, folder, name):
    activate(obj)
    bpy.ops.export_scene.fbx(filepath=str(folder / (name + '.fbx')),
                             use_selection=True, object_types={'MESH'},
                             bake_anim=False, add_leaf_bones=False,
                             axis_forward='-Z', axis_up='Y',
                             path_mode='RELATIVE', embed_textures=False)


def export_plugin_obj(obj, folder, name, albedo_file):
    folder.mkdir(parents=True, exist_ok=True)
    activate(obj)
    filepath = folder / (name + '.obj')
    if hasattr(bpy.ops.wm, 'obj_export'):
        bpy.ops.wm.obj_export(filepath=str(filepath), export_selected_objects=True,
                              export_materials=True, forward_axis='NEGATIVE_Z',
                              up_axis='Y')
    else:
        bpy.ops.export_scene.obj(filepath=str(filepath), use_selection=True,
                                 use_materials=True, axis_forward='-Z', axis_up='Y')
    shutil.copy2(str(albedo_file), str(folder / (name + '.png')))
    # Simple and predictable MTL for CustomMiniPlugin, no absolute paths.
    mtl_name = name + '.mtl'
    (folder / mtl_name).write_text(
        'newmtl AstronyxMini\nKa 0.2 0.2 0.2\nKd 1.0 1.0 1.0\nKs 0.0 0.0 0.0\nd 1.0\nillum 2\n'
        f'map_Kd {name}.png\n', encoding='utf-8')
    body = filepath.read_text(encoding='utf-8', errors='replace').splitlines()
    has_mtllib = False
    has_usemtl = False
    for i, line in enumerate(body):
        if line.startswith('mtllib '):
            body[i] = 'mtllib ' + mtl_name
            has_mtllib = True
        elif line.startswith('usemtl '):
            body[i] = 'usemtl AstronyxMini'
            has_usemtl = True
    if not has_mtllib:
        body.insert(0, 'mtllib ' + mtl_name)
    if not has_usemtl:
        at = next((i for i, ln in enumerate(body) if ln.startswith('f ')), len(body))
        body.insert(at, 'usemtl AstronyxMini')
    filepath.write_text('\n'.join(body) + '\n', encoding='utf-8')


def enforce_taleweaver_vertex_budget(obj, cmd_dir, name, albedo_file):
    """Decimate and re-export the *actual* OBJ until UV/normal splits fit safely.

    Blender object vertex counts alone miss splits created by seams and sharp
    normals. Work on the baked output mesh, leaving source Meshy files intact.
    Unity has the final word; TaleWeaverCmd errors remain actionable.
    """
    for attempt in range(7):
        export_plugin_obj(obj, cmd_dir, name, albedo_file)
        budget = inspect_obj_vertex_budget(cmd_dir / (name + '.obj'))
        if not budget.faces:
            raise ValueError('OBJ exportado não contém faces triangulares.')
        status(91, f'Vertices Blender: {len(obj.data.vertices)} | '
               f'OBJ com UV/normais: {budget.split_vertices} '
               f'(alvo de seguranca: {SAFE_SPLIT_VERTEX_TARGET})')
        if budget.split_vertices <= SAFE_SPLIT_VERTEX_TARGET:
            return budget, attempt
        faces = len(obj.data.polygons)
        if faces <= 600:
            break
        target = next_triangle_budget(faces, budget.split_vertices)
        ratio = max(.02, min(.85, target / faces))
        previous = len(obj.data.polygons)
        activate(obj)
        mod = obj.modifiers.new('Astronyx_TaleWeaver_VertexBudget', 'DECIMATE')
        mod.ratio = ratio
        bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.data.update()
        if len(obj.data.polygons) >= previous:
            break
        print('AMF_WARNING|Reduzindo geometria para respeitar o limite '
              'de vertices reais do TaleWeaverCmd. '
              f'Passagem {attempt + 1}: {previous} -> '
              f'{len(obj.data.polygons)} triangulos.', flush=True)
    raise ValueError(
        'A malha exportada ainda possui vertices UV/normal demais para '
        'TaleWeaverCmd. Selecione 45.000 triangulos e converta novamente '
        'o GLB original do Meshy.'
    )


def render_thumbnail(obj, output, height):
    """Create TaleWeaverCmd-required 512x512 character portrait using Blender."""
    from mathutils import Vector
    scene = bpy.context.scene
    # Imported camera and lighting are unpredictable; create a simple studio setup.
    for old in list(scene.objects):
        if old.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(old, do_unlink=True)
    cam_data = bpy.data.cameras.new('AMF_Thumbnail_Camera')
    cam = bpy.data.objects.new('AMF_Thumbnail_Camera', cam_data)
    scene.collection.objects.link(cam)
    look = Vector((0.0, 0.0, height * .53))
    cam.location = (height * 2.15, -height * 2.75, height * 1.55)
    direction = look - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'
    bbox = metrics(obj)
    width = max(bbox[1] - bbox[0], bbox[3] - bbox[2])
    cam.data.ortho_scale = max(height * 1.6, width * 1.75)
    scene.camera = cam
    for name, loc, power, size in (
        ('AMF_Key', (height * 1.7, -height * 2.2, height * 2.75), 350, 3),
        ('AMF_Fill', (-height * 1.6, -height * 1.1, height * 1.3), 160, 3),
    ):
        lamp_data = bpy.data.lights.new(name, type='AREA')
        lamp_data.energy = power
        lamp_data.shape = 'DISK'
        lamp_data.size = size
        lamp = bpy.data.objects.new(name, lamp_data)
        scene.collection.objects.link(lamp)
        lamp.location = loc
        lamp.rotation_euler = (look - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    world = bpy.data.worlds.new('AMF_Thumbnail_Studio')
    world.use_nodes = True
    background = world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (0.28, 0.25, 0.38, 1)
    background.inputs['Strength'].default_value = 0.7
    scene.world = world
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 8
    scene.render.film_transparent = True
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = str(output)
    scene.render.film_transparent = True
    scene.render.image_settings.color_depth = '8'
    bpy.ops.render.render(write_still=True)
    if not output.is_file() or output.stat().st_size < 100:
        raise RuntimeError('Blender nao criou thumbnail.png corretamente')


def main():
    cfg = get_config()
    source = Path(cfg['source'])
    out = Path(cfg['output_root']) / cfg['name']
    tw = out / 'TaleWeaverLite'
    tw.mkdir(parents=True, exist_ok=True)
    status(3, 'Abrindo modelo no Blender')
    import_model(str(source))
    status(15, 'Unindo malhas e preservando materiais')
    obj = geometry_as_single_mesh()
    status(25, 'Centralizando, girando e ajustando escala')
    norm = normalize_model(obj, cfg)
    status(35, 'Reduzindo triangulos e verificando limites')
    stats = optimize(obj, cfg['tris'])
    bounds = metrics(obj)
    stats['height'] = bounds[5] - bounds[4]
    stats['requested_height'] = cfg['height']
    stats['width'] = bounds[1] - bounds[0]
    stats['depth'] = bounds[3] - bounds[2]
    stats['height_scale_applied'] = norm['height_scale']
    stats['footprint_scale_applied'] = norm['footprint_scale']
    if max(stats['width'], stats['depth']) > cfg['height'] * 1.8:
        print('AMF_WARNING|Modelo muito largo ou profundo; a base pode ser maior por causa de asas e acessorios.', flush=True)
    status(45, f"Malha pronta: {stats['vertices']} vertices / {stats['triangles']} triangulos")
    albedo, _, used_uv, original_png = bake_textures(obj, tw, cfg['texture_size'])
    stats['uv_mode'] = 'original' if used_uv == 'AMF_Original' else 'repacked'
    stats['albedo_method'] = 'png_original' if original_png else 'cycles_baked'
    stats['bake_samples'] = 4
    stats['bake_margin_px'] = max(8, min(12, cfg['texture_size'] // 256))
    stats['texture_bake_size'] = cfg['texture_size']
    stats['taleweaver_texture_max_side'] = min(2048, cfg['texture_size'])
    assign_final_material(obj, albedo, used_uv)
    if cfg.get('create_taleweavercmd', False):
        status(90, 'Exportando e verificando limite de vertices do TaleWeaverCmd')
        cmd_dir = out / 'TaleWeaverCmd_Source'
        budget, reductions = enforce_taleweaver_vertex_budget(
            obj, cmd_dir, cfg['name'], tw / 'Albedo.png')
        stats['taleweavercmd_obj_split_vertices'] = budget.split_vertices
        stats['taleweavercmd_obj_positions'] = budget.positions
        stats['taleweavercmd_vertex_reductions'] = reductions
        stats['vertices'] = len(obj.data.vertices)
        stats['triangles'] = len(obj.data.polygons)
        original_tris = stats.get('initial_triangles', len(obj.data.polygons))
        stats['triangle_retention_percent'] = round(
            100 * stats['triangles'] / max(1, original_tris), 1)
        for tex in ('Albedo.png', 'Normal.png', 'MAES.png'):
            shutil.copy2(tw / tex, cmd_dir / tex)
        # The OBJ and FBX must describe the same final low-poly mesh.
    status(93, 'Exportando FBX final para TaleWeaverLite')
    export_fbx(obj, tw, cfg['name'])
    if cfg.get('create_taleweavercmd', False):
        status(94, 'Criando imagem da miniatura para TaleWeaverCmd')
        try:
            # Center camera on effective mesh height after footprint corrections.
            render_thumbnail(obj, cmd_dir / 'thumbnail.png', stats['height'])
        except Exception as ex:
            print('AMF_WARNING|Imagem 3D de miniatura falhou; usando albedo como reserva: ' + str(ex), flush=True)
            shutil.copy2(tw / 'Albedo.png', cmd_dir / 'thumbnail.png')
    if cfg.get('create_plugin', True):
        status(95, 'Exportando opcao para CustomMiniPlugin')
        export_plugin_obj(obj, out / 'CustomMiniPlugin' / cfg['name'], cfg['name'], tw / 'Albedo.png')
    (out / 'blender_stats.json').write_text(json.dumps(stats, indent=2), encoding='utf-8')
    status(100, 'Conversao concluida! Veja LEIA_PRIMEIRO.txt')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('AMF_ERROR|' + str(error), flush=True)
        traceback.print_exc()
        sys.exit(1)
