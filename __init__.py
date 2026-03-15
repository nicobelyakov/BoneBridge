bl_info = {
    "name":        "Bone Bridge",
    "author":      "BoneBridge",
    "version":     (1, 0, 0),
    "blender":     (4, 0, 0),
    "location":    "View3D > N-Panel > Item > Bone Bridge",
    "description": "reParent, Aim, Manual Pivot, reConstrain — animation retargeting tools",
    "category":    "Animation",
}

import bpy
import bmesh
from mathutils import Matrix
import math
import json

# ══════════════════════════════════════════════════════════════════════════════
#  Bone Bridge — unified addon
#  Три режима: reParent | reParent Aim | Manual Pivot
#  Панель: N-panel > Item > Bone Bridge
# ══════════════════════════════════════════════════════════════════════════════

CTRL_ARM_NAME  = "BoneBridge_Armature_Control"

# Session keys
SCENE_KEY_AIM  = "bb_aim_session"
SCENE_KEY_MP   = "bb_manual_pivot_session"

# Prefixes
MP_PREFIX   = "MPIVOT_"
MPC_PREFIX  = "MPIVOT_CHILD_"

TRACK_AXIS  = 'TRACK_Y'


# ══════════════════════════════════════════════════════════════════════════════
#  Shared utilities — collections, shapes, colors
# ══════════════════════════════════════════════════════════════════════════════

def get_or_create_bb_collection():
    name = "BoneBridge"
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def get_or_create_shapes_collection():
    parent = get_or_create_bb_collection()
    name = "BB_Shapes"
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    parent.children.link(col)
    col.hide_viewport = True
    col.hide_render = True
    return col


def get_or_create_shape_axes():
    name = "BB_Shape_Axes"
    if name in bpy.data.objects:
        return bpy.data.objects[name]
    mesh = bpy.data.meshes.new(name)
    verts = [(-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1)]
    edges = [(0,1),(2,3),(4,5)]
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    get_or_create_shapes_collection().objects.link(obj)
    obj.hide_viewport = True
    obj.hide_render = True
    return obj


def get_or_create_shape_cube():
    name = "BB_Shape_Cube"
    if name in bpy.data.objects:
        return bpy.data.objects[name]
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for f in bm.faces[:]:
        bm.faces.remove(f)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    get_or_create_shapes_collection().objects.link(obj)
    obj.hide_viewport = True
    obj.hide_render = True
    return obj


def get_or_create_shape_sphere():
    name = "BB_Shape_Sphere"
    if name in bpy.data.objects:
        return bpy.data.objects[name]
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    segments = 24
    def make_ring(axis):
        verts = []
        for i in range(segments):
            a = (2 * math.pi * i) / segments
            if axis == 'Z':
                v = bm.verts.new((math.cos(a), math.sin(a), 0))
            elif axis == 'X':
                v = bm.verts.new((0, math.cos(a), math.sin(a)))
            else:
                v = bm.verts.new((math.cos(a), 0, math.sin(a)))
            verts.append(v)
        for i in range(segments):
            bm.edges.new((verts[i], verts[(i+1) % segments]))
    make_ring('Z'); make_ring('X'); make_ring('Y')
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    get_or_create_shapes_collection().objects.link(obj)
    obj.hide_viewport = True
    obj.hide_render = True
    return obj


def get_or_create_shape_aim_loc():
    name = "BB_Shape_AimLoc"
    if name in bpy.data.objects:
        return bpy.data.objects[name]
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    segments = 24
    radius = 1.0
    v_back  = bm.verts.new((0, -radius, 0))
    v_front = bm.verts.new((0,  radius, 0))
    bm.edges.new((v_back, v_front))
    verts = []
    for i in range(segments):
        a = (2 * math.pi * i) / segments
        verts.append(bm.verts.new((math.cos(a) * radius, 0, math.sin(a) * radius)))
    for i in range(segments):
        bm.edges.new((verts[i], verts[(i + 1) % segments]))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    get_or_create_shapes_collection().objects.link(obj)
    obj.hide_viewport = True
    obj.hide_render = True
    return obj


def ensure_all_shapes():
    get_or_create_shape_axes()
    get_or_create_shape_cube()
    get_or_create_shape_sphere()


# Colors

def color_green(pb):
    pb.color.palette = 'CUSTOM'
    pb.color.custom.normal = (0x80/255, 0xFF/255, 0x9E/255)
    pb.color.custom.select = (0xB3/255, 0xFF/255, 0xC6/255)
    pb.color.custom.active = (0xEA/255, 0xFF/255, 0xF0/255)


def color_orange(pb):
    pb.color.palette = 'CUSTOM'
    pb.color.custom.normal = (0xFF/255, 0xA0/255, 0x30/255)
    pb.color.custom.select = (0xFF/255, 0xC8/255, 0x70/255)
    pb.color.custom.active = (0xFF/255, 0xE8/255, 0xB0/255)


def color_blue(pb):
    pb.color.palette = 'CUSTOM'
    pb.color.custom.normal = (0x60/255, 0xC8/255, 0xFF/255)
    pb.color.custom.select = (0x90/255, 0xDA/255, 0xFF/255)
    pb.color.custom.active = (0xC0/255, 0xEE/255, 0xFF/255)


# Shared ctrl armature

def get_or_create_ctrl_armature():
    col = get_or_create_bb_collection()
    if CTRL_ARM_NAME in bpy.data.objects:
        arm_obj = bpy.data.objects[CTRL_ARM_NAME]
        # Убеждаемся что объект есть в коллекции
        if arm_obj.name not in col.objects:
            col.objects.link(arm_obj)
        return arm_obj
    arm_data = bpy.data.armatures.new(CTRL_ARM_NAME)
    arm_obj  = bpy.data.objects.new(CTRL_ARM_NAME, arm_data)
    col.objects.link(arm_obj)
    # Убеждаемся что коллекция слинкована в ViewLayer
    vl_col = bpy.context.view_layer.layer_collection
    def find_layer_col(lc, target_name):
        if lc.collection.name == target_name:
            return lc
        for child in lc.children:
            found = find_layer_col(child, target_name)
            if found:
                return found
        return None
    lc = find_layer_col(vl_col, col.name)
    if lc:
        lc.exclude = False
    bpy.context.view_layer.update()
    return arm_obj


def set_interpolation(arm_obj):
    if arm_obj.animation_data and arm_obj.animation_data.action:
        action = arm_obj.animation_data.action
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    for fcurve in channelbag.fcurves:
                        for kp in fcurve.keyframe_points:
                            kp.interpolation     = 'BEZIER'
                            kp.handle_left_type  = 'AUTO_CLAMPED'
                            kp.handle_right_type = 'AUTO_CLAMPED'
                        fcurve.update()


def finale(source_obj, arm_obj, select_bone_names):
    """Обе арматуры в Pose Mode, выделены указанные кости arm_obj."""
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)

    source_obj.select_set(True)
    bpy.context.view_layer.objects.active = source_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in source_obj.pose.bones:
        pb.select = False
    source_obj.data.bones.active = None

    bpy.ops.object.mode_set(mode='OBJECT')
    arm_obj.select_set(True)
    source_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')

    for pb in arm_obj.pose.bones:
        pb.select = False
    arm_obj.data.bones.active = None

    for bname in select_bone_names:
        if bname in arm_obj.pose.bones:
            arm_obj.pose.bones[bname].select = True
            arm_obj.data.bones.active = arm_obj.data.bones[bname]


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION helpers
# ══════════════════════════════════════════════════════════════════════════════

def save_session(key, data):
    bpy.context.scene[key] = json.dumps(data)

def load_session(key):
    raw = bpy.context.scene.get(key)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}

def clear_session(key):
    if key in bpy.context.scene:
        del bpy.context.scene[key]

def session_active(key):
    session = load_session(key)
    if key == SCENE_KEY_RC:
        return bool(session.get("child_bone"))
    return bool(session.get("bones"))


def tag_bone(arm_obj, bone_name, source_obj, source_bone_name):
    """Записывает custom properties в pose bone — источник и арматура."""
    pb = arm_obj.pose.bones.get(bone_name)
    if pb:
        pb["bb_source_armature"] = source_obj.name
        pb["bb_source_bone"]     = source_bone_name


# ══════════════════════════════════════════════════════════════════════════════
#  AIM_LOC lock helpers
# ══════════════════════════════════════════════════════════════════════════════

def aim_lock_all_except_y(pb):
    """
    Ограничиваем перемещение только по локальному +Y кости.
    lock_location не используем — он работает в глобальных осях.
    Вместо этого Limit Location в LOCAL space: X и Z зажаты в 0, Y >= 0.
    Rotation и Scale блокируем через lock_*.
    """
    # Rotation и Scale — полная блокировка через lock
    pb.lock_rotation[0] = True
    pb.lock_rotation[1] = True
    pb.lock_rotation[2] = True
    pb.lock_rotation_w  = True
    pb.lock_scale[0]    = True
    pb.lock_scale[1]    = True
    pb.lock_scale[2]    = True
    # Location НЕ блокируем через lock — constraint в LOCAL пространстве
    pb.lock_location[0] = False
    pb.lock_location[1] = False
    pb.lock_location[2] = False

    for c in [c for c in list(pb.constraints) if c.name == "BB_AIM_LIMIT_Y"]:
        pb.constraints.remove(c)
    limit = pb.constraints.new(type='LIMIT_LOCATION')
    limit.name        = "BB_AIM_LIMIT_Y"
    limit.owner_space = 'LOCAL'
    # X: зажать в 0
    limit.use_min_x = True;  limit.min_x = 0.0
    limit.use_max_x = True;  limit.max_x = 0.0
    # Y: только положительный
    limit.use_min_y = True;  limit.min_y = 0.0
    limit.use_max_y = False
    # Z: зажать в 0
    limit.use_min_z = True;  limit.min_z = 0.0
    limit.use_max_z = True;  limit.max_z = 0.0


def aim_unlock_all(pb):
    """Снимаем все блокировки после GO."""
    for i in range(3):
        pb.lock_location[i] = False
        pb.lock_rotation[i] = False
        pb.lock_scale[i]    = False
    pb.lock_rotation_w = False
    # Убираем ограничение
    for c in [c for c in list(pb.constraints) if c.name == "BB_AIM_LIMIT_Y"]:
        pb.constraints.remove(c)


# ══════════════════════════════════════════════════════════════════════════════
#  MODE 1 — reParent
# ══════════════════════════════════════════════════════════════════════════════

def rp_ctrl_name(src): return f"BB_{src}"


def rp_run(source_obj, selected_bones):
    scene = bpy.context.scene
    start = scene.frame_start
    end   = scene.frame_end

    ensure_all_shapes()
    arm_obj = get_or_create_ctrl_armature()

    # Read world matrices and pose data before any mode switch
    bone_matrices = {}
    bone_rotmodes = {}
    bone_lengths  = {}
    for sb in selected_bones:
        bone_matrices[sb.name] = (source_obj.matrix_world @ sb.matrix).copy()
        bone_rotmodes[sb.name] = sb.rotation_mode
        bone_lengths[sb.name]  = sb.length

    # Edit Mode — create BB_ bones
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    arm_data = arm_obj.data
    for sb in selected_bones:
        name = rp_ctrl_name(sb.name)
        if name in arm_data.edit_bones:
            arm_data.edit_bones.remove(arm_data.edit_bones[name])
        eb = arm_data.edit_bones.new(name)
        eb.head       = (0.0, 0.0, 0.0)
        eb.tail       = (0.0, bone_lengths[sb.name], 0.0)
        eb.use_deform = False
        eb.parent     = None

    bpy.ops.object.mode_set(mode='OBJECT')

    # Pose Mode — set matrix + Child Of + Set Inverse
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    arm_imat = arm_obj.matrix_world.inverted()

    for sb in selected_bones:
        cname = rp_ctrl_name(sb.name)
        pb = arm_obj.pose.bones[cname]
        pb.rotation_mode          = bone_rotmodes[sb.name]
        pb.custom_shape           = get_or_create_shape_axes()
        pb.custom_shape_scale_xyz = (1.25, 1.25, 1.25)
        color_green(pb)

        pb.matrix = arm_imat @ bone_matrices[sb.name]
        bpy.context.view_layer.update()

        for c in [c for c in list(pb.constraints) if "BoneBridge" in c.name]:
            pb.constraints.remove(c)
        childof = pb.constraints.new(type='CHILD_OF')
        childof.name      = "BoneBridge_CHILD_OF"
        childof.target    = source_obj
        childof.subtarget = sb.name
        bpy.context.view_layer.update()

        for p in arm_obj.pose.bones:
            p.select = False
        arm_obj.data.bones.active = arm_obj.data.bones[cname]
        pb.select = True
        bpy.ops.constraint.childof_set_inverse(constraint=childof.name, owner='BONE')

    # Bake
    ctrl_names = [rp_ctrl_name(sb.name) for sb in selected_bones]
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.select = False
    arm_obj.data.bones.active = None
    for cname in ctrl_names:
        arm_obj.pose.bones[cname].select = True
        arm_obj.data.bones.active = arm_obj.data.bones[cname]

    if not arm_obj.animation_data:
        arm_obj.animation_data_create()
    if not arm_obj.animation_data.action:
        arm_obj.animation_data.action = bpy.data.actions.new(name=f"{arm_obj.name}_Action")

    bpy.ops.nla.bake(
        frame_start=start, frame_end=end,
        only_selected=True, visual_keying=True,
        clear_constraints=False, use_current_action=True,
        bake_types={'POSE'}
    )
    bpy.context.view_layer.update()
    set_interpolation(arm_obj)

    # Remove Child Of
    bpy.ops.object.mode_set(mode='OBJECT')
    for cname in ctrl_names:
        pb = arm_obj.pose.bones[cname]
        for c in [c for c in list(pb.constraints) if c.name == "BoneBridge_CHILD_OF"]:
            pb.constraints.remove(c)

    # Tag created bones with source info
    for sb in selected_bones:
        tag_bone(arm_obj, rp_ctrl_name(sb.name), source_obj, sb.name)

    # Copy Loc/Rot on source bones
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = source_obj
    source_obj.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    for sb in selected_bones:
        cname = rp_ctrl_name(sb.name)
        for c in [c for c in sb.constraints if "BoneBridge" in c.name]:
            sb.constraints.remove(c)
        cl = sb.constraints.new(type='COPY_LOCATION')
        cl.name = "BoneBridge_COPY_LOCATION"
        cl.target = arm_obj; cl.subtarget = cname
        cl.owner_space = 'WORLD'; cl.target_space = 'WORLD'
        cr = sb.constraints.new(type='COPY_ROTATION')
        cr.name = "BoneBridge_COPY_ROTATION"
        cr.target = arm_obj; cr.subtarget = cname
        cr.owner_space = 'WORLD'; cr.target_space = 'WORLD'

    finale(source_obj, arm_obj, ctrl_names)
    print(f"✅ reParent: {len(selected_bones)} костей")


def rp_run_global(source_obj, selected_bones):
    """Global mode: BB_ gets Copy Location from source. Source gets only Copy Rotation from BB_."""
    scene = bpy.context.scene
    start = scene.frame_start
    end   = scene.frame_end

    ensure_all_shapes()
    arm_obj = get_or_create_ctrl_armature()

    bone_matrices = {}
    bone_rotmodes = {}
    bone_lengths  = {}
    for sb in selected_bones:
        bone_matrices[sb.name] = (source_obj.matrix_world @ sb.matrix).copy()
        bone_rotmodes[sb.name] = sb.rotation_mode
        bone_lengths[sb.name]  = sb.length

    # Edit Mode — create BB_ bones
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    arm_data = arm_obj.data
    for sb in selected_bones:
        name = rp_ctrl_name(sb.name)
        if name in arm_data.edit_bones:
            arm_data.edit_bones.remove(arm_data.edit_bones[name])
        eb = arm_data.edit_bones.new(name)
        eb.head       = (0.0, 0.0, 0.0)
        eb.tail       = (0.0, bone_lengths[sb.name], 0.0)
        eb.use_deform = False
        eb.parent     = None

    bpy.ops.object.mode_set(mode='OBJECT')

    # Pose Mode — set matrix + Child Of + Set Inverse
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    arm_imat = arm_obj.matrix_world.inverted()

    for sb in selected_bones:
        cname = rp_ctrl_name(sb.name)
        pb = arm_obj.pose.bones[cname]
        pb.rotation_mode          = bone_rotmodes[sb.name]
        pb.custom_shape           = get_or_create_shape_axes()
        pb.custom_shape_scale_xyz = (1.25, 1.25, 1.25)
        color_green(pb)

        pb.matrix = arm_imat @ bone_matrices[sb.name]
        bpy.context.view_layer.update()

        for c in [c for c in list(pb.constraints) if "BoneBridge" in c.name]:
            pb.constraints.remove(c)
        childof = pb.constraints.new(type='CHILD_OF')
        childof.name      = "BoneBridge_CHILD_OF"
        childof.target    = source_obj
        childof.subtarget = sb.name
        bpy.context.view_layer.update()

        for p in arm_obj.pose.bones:
            p.select = False
        arm_obj.data.bones.active = arm_obj.data.bones[cname]
        pb.select = True
        bpy.ops.constraint.childof_set_inverse(constraint=childof.name, owner='BONE')

    # Bake
    ctrl_names = [rp_ctrl_name(sb.name) for sb in selected_bones]
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.select = False
    arm_obj.data.bones.active = None
    for cname in ctrl_names:
        arm_obj.pose.bones[cname].select = True
        arm_obj.data.bones.active = arm_obj.data.bones[cname]

    if not arm_obj.animation_data:
        arm_obj.animation_data_create()
    if not arm_obj.animation_data.action:
        arm_obj.animation_data.action = bpy.data.actions.new(name=f"{arm_obj.name}_Action")

    bpy.ops.nla.bake(
        frame_start=start, frame_end=end,
        only_selected=True, visual_keying=True,
        clear_constraints=False, use_current_action=True,
        bake_types={'POSE'}
    )
    bpy.context.view_layer.update()
    set_interpolation(arm_obj)

    # Remove Child Of
    bpy.ops.object.mode_set(mode='OBJECT')
    for cname in ctrl_names:
        pb = arm_obj.pose.bones[cname]
        for c in [c for c in list(pb.constraints) if c.name == "BoneBridge_CHILD_OF"]:
            pb.constraints.remove(c)

    # Tag created bones with source info
    for sb in selected_bones:
        tag_bone(arm_obj, rp_ctrl_name(sb.name), source_obj, sb.name)

    # Global mode constraints:
    # BB_ ctrl bone  → Copy Location from source
    # source bone    → Copy Rotation from BB_ only
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for sb in selected_bones:
        cname = rp_ctrl_name(sb.name)
        pb = arm_obj.pose.bones[cname]
        for c in [c for c in list(pb.constraints) if "BoneBridge" in c.name]:
            pb.constraints.remove(c)
        cl = pb.constraints.new(type='COPY_LOCATION')
        cl.name         = "BoneBridge_COPY_LOCATION"
        cl.target       = source_obj
        cl.subtarget    = sb.name
        cl.owner_space  = 'WORLD'
        cl.target_space = 'WORLD'

    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = source_obj
    source_obj.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    for sb in selected_bones:
        cname = rp_ctrl_name(sb.name)
        for c in [c for c in sb.constraints if "BoneBridge" in c.name]:
            sb.constraints.remove(c)
        cr = sb.constraints.new(type='COPY_ROTATION')
        cr.name         = "BoneBridge_COPY_ROTATION"
        cr.target       = arm_obj
        cr.subtarget    = cname
        cr.owner_space  = 'WORLD'
        cr.target_space = 'WORLD'

    finale(source_obj, arm_obj, ctrl_names)
    print(f"✅ Global reParent: {len(selected_bones)} костей")


# ══════════════════════════════════════════════════════════════════════════════
#  MODE 2 — reParent Aim  (упрощённый)
#
#  Step 1: создаём AIM_LOC_<name> на позиции source кости + 125% длины по Y
#          (world space). Кость повторяет rotation_mode source кости.
#          Все трансформы заблокированы кроме Location Y (только +).
#
#  GO:     снимаем блокировки → бейкаем AIM_LOC → вешаем Damped Track:
#            source → AIM_LOC  (TRACK_Y)
#            AIM_LOC → source  (TRACK_Y)
#          AIM_LOC остаётся свободной после GO (блокировки не восстанавливаются).
# ══════════════════════════════════════════════════════════════════════════════

def aim_loc_name(src): return f"AIM_LOC_{src}"


def aim_step1(source_obj, selected_bones):
    ensure_all_shapes()
    arm_obj = get_or_create_ctrl_armature()

    bone_data = []
    for sb in selected_bones:
        world_mat = (source_obj.matrix_world @ sb.matrix).copy()
        bone_data.append({
            "name":          sb.name,
            "rotation_mode": sb.rotation_mode,
            "length":        sb.length,
            "matrix":        [list(r) for r in world_mat],
        })

    # ── Edit Mode: создаём одну кость AIM_LOC_ на каждую выделенную ──────────
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    arm_imat = arm_obj.matrix_world.inverted()
    arm_data = arm_obj.data

    # Считаем позиции в пространстве арматуры и сразу ставим в Edit Mode
    bone_aim_data = {}
    for bd in bone_data:
        src_mat    = Matrix([bd["matrix"][i] for i in range(4)])
        src_origin = src_mat.translation
        y_world    = src_mat.to_3x3().col[1].normalized()
        aim_world  = src_origin + y_world * bd["length"] * 1.25
        tail_world = aim_world  + y_world * bd["length"]
        bone_aim_data[bd["name"]] = {
            "head": (arm_imat @ aim_world.to_4d()).to_3d(),
            "tail": (arm_imat @ tail_world.to_4d()).to_3d(),
        }

    for bd in bone_data:
        lname = aim_loc_name(bd["name"])
        if lname in arm_data.edit_bones:
            arm_data.edit_bones.remove(arm_data.edit_bones[lname])
        ex            = bone_aim_data[bd["name"]]
        eb            = arm_data.edit_bones.new(lname)
        eb.head       = ex["head"]
        eb.tail       = ex["tail"]
        eb.use_deform = False
        eb.parent     = None

    bpy.ops.object.mode_set(mode='OBJECT')

    # ── Pose Mode: внешний вид и блокировки ──────────────────────────────────
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    for bd in bone_data:
        lname = aim_loc_name(bd["name"])
        pb    = arm_obj.pose.bones[lname]
        pb.rotation_mode          = bd["rotation_mode"]
        pb.custom_shape           = get_or_create_shape_sphere()
        pb.custom_shape_scale_xyz = (0.25, 0.25, 0.25)
        color_green(pb)
        aim_lock_all_except_y(pb)

    save_session(SCENE_KEY_AIM, {
        "source_obj": source_obj.name,
        "arm_obj":    arm_obj.name,
        "bones":      bone_data,
    })

    # ── Финал Step 1: обе арматуры в Pose, выделены AIM_LOC_ кости ───────────
    for o in bpy.context.selected_objects:
        o.select_set(False)
    source_obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.select = False
    arm_obj.data.bones.active = None
    for pb in source_obj.pose.bones:
        pb.select = False
    source_obj.data.bones.active = None
    for bd in bone_data:
        lname = aim_loc_name(bd["name"])
        if lname in arm_obj.pose.bones:
            arm_obj.pose.bones[lname].select = True
            arm_obj.data.bones.active = arm_obj.data.bones[lname]

    print("✅ Aim: AIM_LOC локаторы созданы. Переместите их по Y, затем нажмите GO.")


def aim_step2_go():
    session = load_session(SCENE_KEY_AIM)
    if not session:
        print("❌ Нет активной Aim сессии.")
        return

    source_obj = bpy.data.objects.get(session["source_obj"])
    arm_obj    = bpy.data.objects.get(session["arm_obj"])
    bone_data  = session["bones"]

    if not source_obj or not arm_obj:
        clear_session(SCENE_KEY_AIM)
        return

    scene = bpy.context.scene
    start = scene.frame_start
    end   = scene.frame_end

    # ── Шаг 1: снимаем блокировки с AIM_LOC_ костей ──────────────────────────
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    for bd in bone_data:
        lname = aim_loc_name(bd["name"])
        pb    = arm_obj.pose.bones.get(lname)
        if pb:
            aim_unlock_all(pb)
            # Сбрасываем X и Z в нули — пользователь мог случайно сдвинуть
            pb.location[0] = 0.0
            pb.location[2] = 0.0
    bpy.context.view_layer.update()

    # ── Шаг 2: Child Of AIM_LOC_ → source кость → Set Inverse ───────────────
    for bd in bone_data:
        lname  = aim_loc_name(bd["name"])
        pb_loc = arm_obj.pose.bones[lname]
        for c in list(pb_loc.constraints):
            pb_loc.constraints.remove(c)
        childof          = pb_loc.constraints.new(type='CHILD_OF')
        childof.name     = "BoneBridge_CHILD_OF"
        childof.target   = source_obj
        childof.subtarget = bd["name"]
        bpy.context.view_layer.update()
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='POSE')
        for p in arm_obj.pose.bones:
            p.select = False
        arm_obj.data.bones.active = arm_obj.data.bones[lname]
        pb_loc.select = True
        bpy.ops.constraint.childof_set_inverse(constraint=childof.name, owner='BONE')
        bpy.ops.object.mode_set(mode='OBJECT')

    # ── Шаг 3: Bake AIM_LOC_ костей ──────────────────────────────────────────
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.select = False
    arm_obj.data.bones.active = None
    for bd in bone_data:
        lname = aim_loc_name(bd["name"])
        arm_obj.pose.bones[lname].select = True
        arm_obj.data.bones.active = arm_obj.data.bones[lname]

    if not arm_obj.animation_data:
        arm_obj.animation_data_create()
    if not arm_obj.animation_data.action:
        arm_obj.animation_data.action = bpy.data.actions.new(f"{arm_obj.name}_Action")

    bpy.ops.nla.bake(
        frame_start=start, frame_end=end,
        only_selected=True, visual_keying=True,
        clear_constraints=False, use_current_action=True,
        bake_types={'POSE'}
    )
    bpy.context.view_layer.update()
    set_interpolation(arm_obj)

    # ── Шаг 4: убираем Child Of ───────────────────────────────────────────────
    bpy.ops.object.mode_set(mode='OBJECT')
    for bd in bone_data:
        lname = aim_loc_name(bd["name"])
        pb    = arm_obj.pose.bones[lname]
        for c in [c for c in list(pb.constraints) if c.name == "BoneBridge_CHILD_OF"]:
            pb.constraints.remove(c)

    # ── Шаг 4б: удаляем fcurves вращения/scale AIM_LOC_, обнуляем pose ────────
    lnames = {aim_loc_name(bd["name"]) for bd in bone_data}
    if arm_obj.animation_data and arm_obj.animation_data.action:
        action = arm_obj.animation_data.action
        # Новый API (Blender 4.x — layered actions)
        if hasattr(action, 'layers'):
            for layer in action.layers:
                for strip in layer.strips:
                    if hasattr(strip, 'channelbags'):
                        for cb in strip.channelbags:
                            to_remove = [
                                fc for fc in cb.fcurves
                                if any(f'"{ln}"' in fc.data_path or f"'{ln}'" in fc.data_path
                                       for ln in lnames)
                                and any(k in fc.data_path for k in ("rotation", "scale"))
                            ]
                            for fc in to_remove:
                                cb.fcurves.remove(fc)
        # Старый API
        elif hasattr(action, 'fcurves'):
            to_remove = [
                fc for fc in action.fcurves
                if any(f'"{ln}"' in fc.data_path or f"'{ln}'" in fc.data_path
                       for ln in lnames)
                and any(k in fc.data_path for k in ("rotation", "scale"))
            ]
            for fc in to_remove:
                action.fcurves.remove(fc)

    # Обнуляем rotation/scale в pose напрямую
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for bd in bone_data:
        lname = aim_loc_name(bd["name"])
        pb    = arm_obj.pose.bones.get(lname)
        if pb:
            if pb.rotation_mode == 'QUATERNION':
                pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            elif pb.rotation_mode == 'AXIS_ANGLE':
                pb.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
            else:
                pb.rotation_euler = (0.0, 0.0, 0.0)
            pb.scale = (1.0, 1.0, 1.0)
    bpy.ops.object.mode_set(mode='OBJECT')

    # ── Шаг 5: тегируем AIM_LOC_ кости ───────────────────────────────────────
    for bd in bone_data:
        tag_bone(arm_obj, aim_loc_name(bd["name"]), source_obj, bd["name"])

    # ── Шаг 6: Damped Track — source → AIM_LOC_ ──────────────────────────────
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = source_obj
    source_obj.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    for bd in bone_data:
        lname = aim_loc_name(bd["name"])
        sb    = source_obj.pose.bones[bd["name"]]
        for c in [c for c in sb.constraints if "BoneBridge" in c.name]:
            sb.constraints.remove(c)
        dt            = sb.constraints.new(type='DAMPED_TRACK')
        dt.name       = "BoneBridge_DAMPED_TRACK"
        dt.target     = arm_obj
        dt.subtarget  = lname
        dt.track_axis = TRACK_AXIS

    # ── Шаг 7: убираем все оставшиеся констрейнты с AIM_LOC_ ─────────────────
    # AIM_LOC_ — просто точка в пространстве, никуда не смотрит.
    # Взаимный Damped Track создавал цикличную зависимость и задержку.
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    for bd in bone_data:
        lname  = aim_loc_name(bd["name"])
        pb_loc = arm_obj.pose.bones[lname]
        for c in list(pb_loc.constraints):
            pb_loc.constraints.remove(c)

    bpy.ops.object.mode_set(mode='OBJECT')
    clear_session(SCENE_KEY_AIM)

    finale(source_obj, arm_obj, [aim_loc_name(bd["name"]) for bd in bone_data])
    print("✅ Aim: готово.")


def aim_cancel():
    session = load_session(SCENE_KEY_AIM)
    if not session:
        return
    arm_obj   = bpy.data.objects.get(session["arm_obj"])
    bone_data = session["bones"]
    clear_session(SCENE_KEY_AIM)
    if not arm_obj:
        return
    bones_to_remove = [aim_loc_name(bd["name"]) for bd in bone_data]
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    for bname in bones_to_remove:
        if bname in arm_obj.data.edit_bones:
            arm_obj.data.edit_bones.remove(arm_obj.data.edit_bones[bname])
    bpy.ops.object.mode_set(mode='OBJECT')
    print("✅ Aim отменён.")


# ══════════════════════════════════════════════════════════════════════════════
#  MODE 3 — Manual Pivot
# ══════════════════════════════════════════════════════════════════════════════

def mp_loc_name(src):   return f"{MP_PREFIX}{src}"
def mp_child_name(src): return f"{MPC_PREFIX}{src}"


def mp_step1(source_obj, selected_bones):
    ensure_all_shapes()
    arm_obj = get_or_create_ctrl_armature()

    bone_data = []
    for sb in selected_bones:
        mat = (source_obj.matrix_world @ sb.matrix).copy()
        bone_data.append({
            "name":          sb.name,
            "rotation_mode": sb.rotation_mode,
            "length":        sb.length,
            "matrix":        [list(r) for r in mat],
        })

    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    arm_data = arm_obj.data
    for bd in bone_data:
        lname = mp_loc_name(bd["name"])
        cname = mp_child_name(bd["name"])
        for n in (lname, cname):
            if n in arm_data.edit_bones:
                arm_data.edit_bones.remove(arm_data.edit_bones[n])
        eb = arm_data.edit_bones.new(lname)
        eb.head = (0.0, 0.0, 0.0)
        eb.tail = (0.0, bd["length"], 0.0)
        eb.use_deform = False
        eb.parent = None

    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    for bd in bone_data:
        lname = mp_loc_name(bd["name"])
        pb = arm_obj.pose.bones[lname]
        pb.rotation_mode          = bd["rotation_mode"]
        pb.custom_shape           = get_or_create_shape_axes()
        pb.custom_shape_scale_xyz = (1.3, 1.3, 1.3)
        color_orange(pb)
        mat = Matrix([bd["matrix"][i] for i in range(4)])
        pb.matrix = arm_obj.matrix_world.inverted() @ mat

    bpy.context.view_layer.update()

    save_session(SCENE_KEY_MP, {
        "source_obj": source_obj.name,
        "arm_obj":    arm_obj.name,
        "bones":      bone_data,
    })

    for o in bpy.context.selected_objects:
        o.select_set(False)
    source_obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.select = False
    arm_obj.data.bones.active = None
    for pb in source_obj.pose.bones:
        pb.select = False
    source_obj.data.bones.active = None
    for bd in bone_data:
        lname = mp_loc_name(bd["name"])
        if lname in arm_obj.pose.bones:
            arm_obj.pose.bones[lname].select = True
            arm_obj.data.bones.active = arm_obj.data.bones[lname]

    print("✅ Manual Pivot: локаторы созданы.")


def mp_step2_go():
    session = load_session(SCENE_KEY_MP)
    if not session:
        print("❌ Нет активной Manual Pivot сессии.")
        return

    source_obj = bpy.data.objects.get(session["source_obj"])
    arm_obj    = bpy.data.objects.get(session["arm_obj"])
    bone_data  = session["bones"]

    if not source_obj or not arm_obj:
        clear_session(SCENE_KEY_MP)
        return

    scene = bpy.context.scene
    start = scene.frame_start
    end   = scene.frame_end

    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    arm_imat = arm_obj.matrix_world.inverted()

    src_bone_world_mats = {}
    for bd in bone_data:
        src_bone_world_mats[bd["name"]] = Matrix([bd["matrix"][i] for i in range(4)])

    # Child Of on MPIVOT_ → source bone → Set Inverse → bake
    for bd in bone_data:
        lname = mp_loc_name(bd["name"])
        pb = arm_obj.pose.bones[lname]
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        childof = pb.constraints.new(type='CHILD_OF')
        childof.name = "MP_CHILD_OF"
        childof.target = source_obj; childof.subtarget = bd["name"]
        bpy.context.view_layer.update()
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='POSE')
        for p in arm_obj.pose.bones:
            p.select = False
        arm_obj.data.bones.active = arm_obj.data.bones[lname]
        pb.select = True
        bpy.ops.constraint.childof_set_inverse(constraint=childof.name, owner='BONE')
        bpy.ops.object.mode_set(mode='OBJECT')

    # Bake MPIVOT_ bones
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.select = False
    arm_obj.data.bones.active = None
    for bd in bone_data:
        lname = mp_loc_name(bd["name"])
        arm_obj.pose.bones[lname].select = True
        arm_obj.data.bones.active = arm_obj.data.bones[lname]

    if not arm_obj.animation_data:
        arm_obj.animation_data_create()
    if not arm_obj.animation_data.action:
        arm_obj.animation_data.action = bpy.data.actions.new(f"{arm_obj.name}_Action")

    bpy.ops.nla.bake(
        frame_start=start, frame_end=end,
        only_selected=True, visual_keying=True,
        clear_constraints=False, use_current_action=True,
        bake_types={'POSE'}
    )
    bpy.context.view_layer.update()
    set_interpolation(arm_obj)

    # Remove Child Of
    bpy.ops.object.mode_set(mode='OBJECT')
    for bd in bone_data:
        lname = mp_loc_name(bd["name"])
        pb = arm_obj.pose.bones[lname]
        for c in [c for c in list(pb.constraints) if c.name == "MP_CHILD_OF"]:
            pb.constraints.remove(c)

    # Edit Mode — create MPIVOT_CHILD_ without parent
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    arm_data = arm_obj.data
    for bd in bone_data:
        lname    = mp_loc_name(bd["name"])
        cname    = mp_child_name(bd["name"])
        src_mat  = src_bone_world_mats[bd["name"]]
        bone_len = bd["length"]

        src_arm_mat = arm_imat @ src_mat
        child_head  = src_arm_mat.translation.copy()
        y_local     = src_arm_mat.to_3x3().col[1].normalized()
        child_tail  = child_head + y_local * bone_len

        if cname in arm_data.edit_bones:
            arm_data.edit_bones.remove(arm_data.edit_bones[cname])

        child_eb             = arm_data.edit_bones.new(cname)
        child_eb.head        = child_head
        child_eb.tail        = child_tail
        child_eb.use_deform  = False
        child_eb.hide        = True
        child_eb.parent      = None
        child_eb.use_connect = False

    bpy.ops.object.mode_set(mode='OBJECT')

    # Set parent in edit mode
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    arm_data = arm_obj.data
    for bd in bone_data:
        lname = mp_loc_name(bd["name"])
        cname = mp_child_name(bd["name"])
        arm_data.edit_bones[cname].parent      = arm_data.edit_bones[lname]
        arm_data.edit_bones[cname].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')

    # Pose Mode — fix matrix so child lands on source bone position
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    for bd in bone_data:
        cname    = mp_child_name(bd["name"])
        pb_child = arm_obj.pose.bones[cname]
        target_world = src_bone_world_mats[bd["name"]]
        pb_child.matrix = arm_obj.matrix_world.inverted() @ target_world
        bpy.context.view_layer.update()
        pb_child.rotation_mode          = bd["rotation_mode"]
        pb_child.custom_shape           = get_or_create_shape_axes()
        pb_child.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
        color_blue(pb_child)
        pb_child.hide = True

    # Tag all created bones with source info
    for bd in bone_data:
        tag_bone(arm_obj, mp_loc_name(bd["name"]),   source_obj, bd["name"])
        tag_bone(arm_obj, mp_child_name(bd["name"]), source_obj, bd["name"])

    # Copy Loc/Rot on source → MPIVOT_CHILD_
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = source_obj
    source_obj.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    for bd in bone_data:
        cname = mp_child_name(bd["name"])
        sb    = source_obj.pose.bones[bd["name"]]
        for c in [c for c in sb.constraints if "BoneBridge" in c.name]:
            sb.constraints.remove(c)
        cl = sb.constraints.new(type='COPY_LOCATION')
        cl.name = "BoneBridge_COPY_LOCATION"
        cl.target = arm_obj; cl.subtarget = cname
        cl.owner_space = 'WORLD'; cl.target_space = 'WORLD'
        cr = sb.constraints.new(type='COPY_ROTATION')
        cr.name = "BoneBridge_COPY_ROTATION"
        cr.target = arm_obj; cr.subtarget = cname
        cr.owner_space = 'WORLD'; cr.target_space = 'WORLD'

    clear_session(SCENE_KEY_MP)
    finale(source_obj, arm_obj, [mp_loc_name(bd["name"]) for bd in bone_data])
    print("✅ Manual Pivot: готово.")


def mp_cancel():
    session = load_session(SCENE_KEY_MP)
    if not session:
        return
    arm_obj   = bpy.data.objects.get(session["arm_obj"])
    bone_data = session["bones"]
    clear_session(SCENE_KEY_MP)
    if not arm_obj:
        return
    bones_to_remove = []
    for bd in bone_data:
        bones_to_remove += [mp_loc_name(bd["name"]), mp_child_name(bd["name"])]
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    for bname in bones_to_remove:
        if bname in arm_obj.data.edit_bones:
            arm_obj.data.edit_bones.remove(arm_obj.data.edit_bones[bname])
    bpy.ops.object.mode_set(mode='OBJECT')
    print("✅ Manual Pivot отменён.")


# ══════════════════════════════════════════════════════════════════════════════
#  MODE 4 — reConstrain  (+optional Manual Pivot)
#
#  Базовый:
#    Выбраны 2 кости из одной арматуры.
#    active = child, non-active = parent.
#    RC_<child> создаётся в ctrl_arm в позиции/ориентации child кости.
#    Бейкается с Child Of parent → Set Inverse (анимация child в пространстве parent).
#    Child Of убирается. На child вешается Copy Loc + Copy Rot от RC_.
#
#  + Manual Pivot (Step1/GO):
#    Step1: создаётся RCPIVOT_<child> — локатор pivot (как в Manual Pivot).
#           Пользователь его перемещает.
#    GO:    RC_ создаётся дочерней к RCPIVOT_, бейкается,
#           затем аналогично базовому.
# ══════════════════════════════════════════════════════════════════════════════

SCENE_KEY_RC   = "bb_reconstrain_session"
RCPIVOT_PREFIX = "RCPIVOT_"
RC_PREFIX      = "RC_"


def rc_parent_name(parent): return f"RC_PARENT_{parent}"
def rc_ctrl_name(child):    return f"{RC_PREFIX}{child}"


def rc_run(source_obj, parent_bone, child_bone):
    """Базовый reConstrain без pivot.

    RC_PARENT_<parent> — в месте non-active кости, Copy Loc+Rot от non-active.
    RC_<child>         — дочерняя к RC_PARENT_, без connect, в месте active,
                         Copy Loc+Rot от active.
    Бейкаем только RC_<child>.
    Убираем все констрейнты с обеих RC_ костей.
    На active вешаем Copy Loc+Rot от RC_<child>.
    """
    scene = bpy.context.scene
    start = scene.frame_start
    end   = scene.frame_end

    ensure_all_shapes()
    arm_obj = get_or_create_ctrl_armature()

    parent_world = (source_obj.matrix_world @ parent_bone.matrix).copy()
    child_world  = (source_obj.matrix_world @ child_bone.matrix).copy()
    parent_name  = parent_bone.name
    child_name   = child_bone.name
    p_len        = parent_bone.length
    c_len        = child_bone.length
    p_rot        = parent_bone.rotation_mode
    c_rot        = child_bone.rotation_mode
    arm_imat     = arm_obj.matrix_world.inverted()

    pname = rc_parent_name(parent_name)
    cname = rc_ctrl_name(child_name)

    def world_head_tail(world_mat, bone_len):
        y   = world_mat.to_3x3().col[1].normalized()
        h   = (arm_imat @ world_mat.translation.to_4d()).to_3d()
        t   = (arm_imat @ (world_mat.translation + y * bone_len).to_4d()).to_3d()
        return h, t

    # ── Edit Mode: создаём обе кости ─────────────────────────────────────────
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    arm_data = arm_obj.data
    for n in (pname, cname):
        if n in arm_data.edit_bones:
            arm_data.edit_bones.remove(arm_data.edit_bones[n])

    ph, pt = world_head_tail(parent_world, p_len)
    pe            = arm_data.edit_bones.new(pname)
    pe.head       = ph
    pe.tail       = pt
    pe.use_deform = False
    pe.parent     = None

    ch, ct = world_head_tail(child_world, c_len)
    ce             = arm_data.edit_bones.new(cname)
    ce.head        = ch
    ce.tail        = ct
    ce.use_deform  = False
    ce.parent      = arm_data.edit_bones[pname]
    ce.use_connect = False

    bpy.ops.object.mode_set(mode='OBJECT')

    # ── Pose Mode: Copy Loc+Rot на обе кости ─────────────────────────────────
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    def setup_copy_constraints(pb, src_name, rot_mode, color_fn, scale):
        pb.rotation_mode          = rot_mode
        pb.custom_shape           = get_or_create_shape_axes()
        pb.custom_shape_scale_xyz = (scale, scale, scale)
        color_fn(pb)
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        cl = pb.constraints.new(type='COPY_LOCATION')
        cl.name = "BB_RC_COPY_LOC"
        cl.target = source_obj; cl.subtarget = src_name
        cl.owner_space = 'WORLD'; cl.target_space = 'WORLD'
        cr = pb.constraints.new(type='COPY_ROTATION')
        cr.name = "BB_RC_COPY_ROT"
        cr.target = source_obj; cr.subtarget = src_name
        cr.owner_space = 'WORLD'; cr.target_space = 'WORLD'

    setup_copy_constraints(arm_obj.pose.bones[pname], parent_name, p_rot, color_orange, 1.25)
    setup_copy_constraints(arm_obj.pose.bones[cname], child_name,  c_rot, color_green,  1.25)
    arm_obj.pose.bones[pname].hide = True

    # ── Bake только RC_<child> ────────────────────────────────────────────────
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.select = False
    arm_obj.data.bones.active = None
    arm_obj.pose.bones[cname].select = True
    arm_obj.data.bones.active = arm_obj.data.bones[cname]

    if not arm_obj.animation_data:
        arm_obj.animation_data_create()
    if not arm_obj.animation_data.action:
        arm_obj.animation_data.action = bpy.data.actions.new(f"{arm_obj.name}_Action")

    bpy.ops.nla.bake(
        frame_start=start, frame_end=end,
        only_selected=True, visual_keying=True,
        clear_constraints=False, use_current_action=True,
        bake_types={'POSE'}
    )
    bpy.context.view_layer.update()
    set_interpolation(arm_obj)

    # ── Убираем констрейнты только с RC_<child> ──────────────────────────────
    bpy.ops.object.mode_set(mode='OBJECT')
    pb_rc = arm_obj.pose.bones[cname]
    for c in list(pb_rc.constraints):
        pb_rc.constraints.remove(c)

    # Тегируем — RC_PARENT_ помечаем флагом bb_skip_bake
    tag_bone(arm_obj, pname, source_obj, parent_name)
    arm_obj.pose.bones[pname]["bb_skip_bake"] = True
    tag_bone(arm_obj, cname, source_obj, child_name)

    # ── Copy Loc+Rot на active (child) → RC_<child> ───────────────────────────
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = source_obj
    source_obj.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    cb = source_obj.pose.bones[child_name]
    for c in [c for c in cb.constraints if "BoneBridge" in c.name]:
        cb.constraints.remove(c)
    cl = cb.constraints.new(type='COPY_LOCATION')
    cl.name         = "BoneBridge_COPY_LOCATION"
    cl.target       = arm_obj; cl.subtarget = cname
    cl.owner_space  = 'WORLD'; cl.target_space = 'WORLD'
    cr = cb.constraints.new(type='COPY_ROTATION')
    cr.name         = "BoneBridge_COPY_ROTATION"
    cr.target       = arm_obj; cr.subtarget = cname
    cr.owner_space  = 'WORLD'; cr.target_space = 'WORLD'

    finale(source_obj, arm_obj, [cname])
    print(f"✅ reConstrain: {child_name} привязан к {parent_name}")


# ── reConstrain + Manual Pivot name helpers ───────────────────────────────────
def rc_pivot_name(child):   return f"PIVOT_{child}"
def cm_parent_name(parent): return f"CM_PARENT_{parent}"
def cm_ctrl_name(child):    return f"CM_CONTROL_{child}"
def cm_child_name(child):   return f"CM_CHILD_{child}"


def rc_step1(source_obj, parent_bone, child_bone):
    """reConstrain + Manual Pivot — Step1.
    Создаём PIVOT_<child> в позиции active кости — пользователь её двигает.
    """
    ensure_all_shapes()
    arm_obj = get_or_create_ctrl_armature()
    bpy.context.view_layer.update()

    child_world = (source_obj.matrix_world @ child_bone.matrix).copy()
    child_name  = child_bone.name
    parent_name = parent_bone.name
    c_len       = child_bone.length
    c_rot       = child_bone.rotation_mode
    arm_imat    = arm_obj.matrix_world.inverted()

    piv_name = rc_pivot_name(child_name)

    # ── Edit Mode: создаём PIVOT_ в позиции active ───────────────────────────
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    arm_data = arm_obj.data
    if piv_name in arm_data.edit_bones:
        arm_data.edit_bones.remove(arm_data.edit_bones[piv_name])

    y_w    = child_world.to_3x3().col[1].normalized()
    ch     = (arm_imat @ child_world.translation.to_4d()).to_3d()
    ct     = (arm_imat @ (child_world.translation + y_w * c_len).to_4d()).to_3d()

    eb            = arm_data.edit_bones.new(piv_name)
    eb.head       = ch
    eb.tail       = ct
    eb.use_deform = False
    eb.parent     = None

    bpy.ops.object.mode_set(mode='OBJECT')

    # ── Pose Mode: внешний вид ────────────────────────────────────────────────
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    pb_piv = arm_obj.pose.bones[piv_name]
    pb_piv.rotation_mode          = c_rot
    pb_piv.custom_shape           = get_or_create_shape_axes()
    pb_piv.custom_shape_scale_xyz = (1.25, 1.25, 1.25)
    color_orange(pb_piv)

    save_session(SCENE_KEY_RC, {
        "source_obj":   source_obj.name,
        "arm_obj":      arm_obj.name,
        "parent_bone":  parent_name,
        "child_bone":   child_name,
        "child_len":    c_len,
        "child_rot":    c_rot,
        "child_matrix": [list(r) for r in child_world],
        "piv_name":     piv_name,
    })

    # ── Финал: Pose, выделена PIVOT_ кость ───────────────────────────────────
    for o in bpy.context.selected_objects:
        o.select_set(False)
    source_obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.select = False
    arm_obj.data.bones.active = None
    for pb in source_obj.pose.bones:
        pb.select = False
    source_obj.data.bones.active = None
    pb_piv.select = True
    arm_obj.data.bones.active = arm_obj.data.bones[piv_name]

    print("✅ reConstrain+Pivot: переместите PIVOT_ кость, затем нажмите GO.")


def rc_step2_go():
    session = load_session(SCENE_KEY_RC)
    if not session:
        print("❌ Нет активной reConstrain сессии.")
        return

    source_obj  = bpy.data.objects.get(session["source_obj"])
    arm_obj     = bpy.data.objects.get(session["arm_obj"])
    parent_name = session["parent_bone"]
    child_name  = session["child_bone"]
    c_len       = session.get("child_len", 0.1)
    c_rot       = session.get("child_rot", "XYZ")
    child_world = Matrix([session["child_matrix"][i] for i in range(4)])
    piv_name    = session.get("piv_name", rc_pivot_name(child_name))

    if not source_obj or not arm_obj:
        clear_session(SCENE_KEY_RC)
        return

    scene    = bpy.context.scene
    start    = scene.frame_start
    end      = scene.frame_end
    arm_imat = arm_obj.matrix_world.inverted()

    pname  = cm_parent_name(parent_name)
    cname  = cm_ctrl_name(child_name)
    chname = cm_child_name(child_name)

    # ── Шаг 1: Child Of active → Set Inverse на PIVOT_ ───────────────────────
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    pb_piv = arm_obj.pose.bones[piv_name]
    for c in list(pb_piv.constraints):
        pb_piv.constraints.remove(c)
    co          = pb_piv.constraints.new(type='CHILD_OF')
    co.name     = "BB_PIVOT_CHILD_OF"
    co.target   = source_obj
    co.subtarget = child_name
    bpy.context.view_layer.update()
    for p in arm_obj.pose.bones:
        p.select = False
    arm_obj.data.bones.active = arm_obj.data.bones[piv_name]
    pb_piv.select = True
    bpy.ops.constraint.childof_set_inverse(constraint=co.name, owner='BONE')

    # ── Шаг 2: Edit Mode — создаём CM_PARENT_, CM_CONTROL_, CM_CHILD_ ────────
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    arm_data = arm_obj.data
    for n in (pname, cname, chname):
        if n in arm_data.edit_bones:
            arm_data.edit_bones.remove(arm_data.edit_bones[n])

    def arm_ht(world_mat, bone_len):
        y = world_mat.to_3x3().col[1].normalized()
        h = (arm_imat @ world_mat.translation.to_4d()).to_3d()
        t = (arm_imat @ (world_mat.translation + y * bone_len).to_4d()).to_3d()
        return h, t

    # CM_PARENT_ в позиции non-active кости
    par_bone   = source_obj.pose.bones[parent_name]
    par_world  = (source_obj.matrix_world @ par_bone.matrix).copy()
    par_len    = par_bone.length
    par_rot    = par_bone.rotation_mode
    ph, pt     = arm_ht(par_world, par_len)

    pe            = arm_data.edit_bones.new(pname)
    pe.head       = ph
    pe.tail       = pt
    pe.use_deform = False
    pe.parent     = None

    # CM_CONTROL_ в позиции PIVOT_ кости (где пользователь поставил)
    # Читаем из pose bones чтобы учесть перемещение пользователя
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    pb_piv_pose  = arm_obj.pose.bones[piv_name]
    piv_head_w   = arm_obj.matrix_world @ pb_piv_pose.head
    piv_tail_w   = arm_obj.matrix_world @ pb_piv_pose.tail
    piv_y        = (piv_tail_w - piv_head_w).normalized()
    piv_rot      = pb_piv_pose.rotation_mode

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    arm_data = arm_obj.data

    ctrl_h = (arm_imat @ piv_head_w.to_4d()).to_3d()
    ctrl_t = (arm_imat @ (piv_head_w + piv_y * c_len).to_4d()).to_3d()

    ce             = arm_data.edit_bones.new(cname)
    ce.head        = ctrl_h
    ce.tail        = ctrl_t
    ce.use_deform  = False
    ce.parent      = arm_data.edit_bones[pname]
    ce.use_connect = False

    # CM_CHILD_ в позиции active кости
    ch_h, ch_t = arm_ht(child_world, c_len)

    che             = arm_data.edit_bones.new(chname)
    che.head        = ch_h
    che.tail        = ch_t
    che.use_deform  = False
    che.hide        = True
    che.parent      = arm_data.edit_bones[cname]
    che.use_connect = False

    bpy.ops.object.mode_set(mode='OBJECT')

    # ── Шаг 3: Pose Mode — назначаем констрейнты ─────────────────────────────
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()

    # CM_PARENT_: Copy Loc+Rot от non-active, скрытая
    pb_par = arm_obj.pose.bones[pname]
    pb_par.rotation_mode          = par_rot
    pb_par.custom_shape           = get_or_create_shape_axes()
    pb_par.custom_shape_scale_xyz = (1.25, 1.25, 1.25)
    color_orange(pb_par)
    pb_par.hide = True
    for c in list(pb_par.constraints):
        pb_par.constraints.remove(c)
    cl = pb_par.constraints.new(type='COPY_LOCATION')
    cl.name = "BB_CM_COPY_LOC"; cl.target = source_obj; cl.subtarget = parent_name
    cl.owner_space = 'WORLD'; cl.target_space = 'WORLD'
    cr = pb_par.constraints.new(type='COPY_ROTATION')
    cr.name = "BB_CM_COPY_ROT"; cr.target = source_obj; cr.subtarget = parent_name
    cr.owner_space = 'WORLD'; cr.target_space = 'WORLD'

    # CM_CONTROL_: Copy Loc+Rot от PIVOT_, берём rotation_mode от PIVOT_
    pb_ctrl = arm_obj.pose.bones[cname]
    pb_ctrl.rotation_mode          = piv_rot
    pb_ctrl.custom_shape           = get_or_create_shape_axes()
    pb_ctrl.custom_shape_scale_xyz = (1.25, 1.25, 1.25)
    color_green(pb_ctrl)
    for c in list(pb_ctrl.constraints):
        pb_ctrl.constraints.remove(c)
    cl = pb_ctrl.constraints.new(type='COPY_LOCATION')
    cl.name = "BB_CM_COPY_LOC"; cl.target = arm_obj; cl.subtarget = piv_name
    cl.owner_space = 'WORLD'; cl.target_space = 'WORLD'
    cr = pb_ctrl.constraints.new(type='COPY_ROTATION')
    cr.name = "BB_CM_COPY_ROT"; cr.target = arm_obj; cr.subtarget = piv_name
    cr.owner_space = 'WORLD'; cr.target_space = 'WORLD'

    # CM_CHILD_: без констрейнтов, rotation_mode = active
    pb_ch = arm_obj.pose.bones[chname]
    pb_ch.rotation_mode          = c_rot
    pb_ch.custom_shape           = get_or_create_shape_axes()
    pb_ch.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
    color_blue(pb_ch)
    pb_ch.hide = True

    # ── Шаг 4: Bake CM_CONTROL_ ──────────────────────────────────────────────
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.select = False
    arm_obj.data.bones.active = None
    arm_obj.pose.bones[cname].select = True
    arm_obj.data.bones.active = arm_obj.data.bones[cname]

    if not arm_obj.animation_data:
        arm_obj.animation_data_create()
    if not arm_obj.animation_data.action:
        arm_obj.animation_data.action = bpy.data.actions.new(f"{arm_obj.name}_Action")

    bpy.ops.nla.bake(
        frame_start=start, frame_end=end,
        only_selected=True, visual_keying=True,
        clear_constraints=False, use_current_action=True,
        bake_types={'POSE'}
    )
    bpy.context.view_layer.update()
    set_interpolation(arm_obj)

    # ── Шаг 5: убираем констрейнты с CM_CONTROL_ ─────────────────────────────
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for c in list(arm_obj.pose.bones[cname].constraints):
        arm_obj.pose.bones[cname].constraints.remove(c)

    # ── Шаг 6: удаляем PIVOT_ кость ──────────────────────────────────────────
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    if piv_name in arm_obj.data.edit_bones:
        arm_obj.data.edit_bones.remove(arm_obj.data.edit_bones[piv_name])
    bpy.ops.object.mode_set(mode='OBJECT')

    # ── Шаг 7: тегируем кости ────────────────────────────────────────────────
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    tag_bone(arm_obj, chname, source_obj, child_name)
    tag_bone(arm_obj, pname,  source_obj, parent_name)
    tag_bone(arm_obj, cname,  source_obj, child_name)
    arm_obj.pose.bones[pname]["bb_skip_bake"] = True
    arm_obj.pose.bones[cname]["bb_skip_bake"] = True

    # ── Шаг 8: Copy Loc+Rot на active → CM_CHILD_ ────────────────────────────
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = source_obj
    source_obj.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    cb = source_obj.pose.bones[child_name]
    for c in [c for c in cb.constraints if "BoneBridge" in c.name]:
        cb.constraints.remove(c)
    cl = cb.constraints.new(type='COPY_LOCATION')
    cl.name         = "BoneBridge_COPY_LOCATION"
    cl.target       = arm_obj; cl.subtarget = chname
    cl.owner_space  = 'WORLD'; cl.target_space = 'WORLD'
    cr = cb.constraints.new(type='COPY_ROTATION')
    cr.name         = "BoneBridge_COPY_ROTATION"
    cr.target       = arm_obj; cr.subtarget = chname
    cr.owner_space  = 'WORLD'; cr.target_space = 'WORLD'

    clear_session(SCENE_KEY_RC)
    finale(source_obj, arm_obj, [cname])
    print(f"✅ reConstrain+Pivot: {child_name} готово.")


def rc_cancel():
    session = load_session(SCENE_KEY_RC)
    if not session:
        return
    arm_obj     = bpy.data.objects.get(session.get("arm_obj", ""))
    child_name  = session.get("child_bone", "")
    parent_name = session.get("parent_bone", "")
    piv_name    = session.get("piv_name", rc_pivot_name(child_name))
    clear_session(SCENE_KEY_RC)
    if not arm_obj or not child_name:
        return
    to_remove = [
        piv_name,
        cm_parent_name(parent_name),
        cm_ctrl_name(child_name),
        cm_child_name(child_name),
    ]
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    for bname in to_remove:
        if bname in arm_obj.data.edit_bones:
            arm_obj.data.edit_bones.remove(arm_obj.data.edit_bones[bname])
    bpy.ops.object.mode_set(mode='OBJECT')
    print("✅ reConstrain отменён.")



def on_aim_toggle(self, context):
    if self.bb_mode_aim:
        self.bb_mode_manual_pivot = False
        self.bb_mode_global       = False
        self.bb_mode_reconstrain  = False

def on_mp_toggle(self, context):
    if self.bb_mode_manual_pivot:
        self.bb_mode_aim    = False
        self.bb_mode_global = False
        # reConstrain совместим с Manual Pivot — не сбрасываем

def on_global_toggle(self, context):
    if self.bb_mode_global:
        self.bb_mode_aim          = False
        self.bb_mode_manual_pivot = False
        self.bb_mode_reconstrain  = False

def on_rc_toggle(self, context):
    if self.bb_mode_reconstrain:
        self.bb_mode_aim    = False
        self.bb_mode_global = False
        # Manual Pivot совместим с reConstrain — не сбрасываем


def register_props():
    bpy.types.Scene.bb_mode_aim = bpy.props.BoolProperty(
        name="Aim",
        description="Режим Aim: создать локатор-цель, кость будет смотреть на него через Damped Track",
        default=False,
        update=on_aim_toggle,
    )
    bpy.types.Scene.bb_mode_manual_pivot = bpy.props.BoolProperty(
        name="Manual Pivot",
        description=(
            "Режим Manual Pivot: вручную задать точку вращения для кости. "
            "Совместим с reConstrain"
        ),
        default=False,
        update=on_mp_toggle,
    )
    bpy.types.Scene.bb_mode_global = bpy.props.BoolProperty(
        name="Global",
        description="Режим Global: контрол следует за костью по локации, кость берёт только вращение от контрола",
        default=False,
        update=on_global_toggle,
    )
    bpy.types.Scene.bb_mode_reconstrain = bpy.props.BoolProperty(
        name="reConstrain",
        description=(
            "Режим reConstrain: привязать active кость к non-active с сохранением анимации. "
            "Выделите ровно 2 кости. Совместим с Manual Pivot"
        ),
        default=False,
        update=on_rc_toggle,
    )

def unregister_props():
    for p in ("bb_mode_aim", "bb_mode_manual_pivot", "bb_mode_global", "bb_mode_reconstrain"):
        if hasattr(bpy.types.Scene, p):
            try:
                delattr(bpy.types.Scene, p)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
#  BAKE AND DELETE helpers
# ══════════════════════════════════════════════════════════════════════════════

BB_COLLECTIONS = ("BoneBridge", "BB_Shapes")
BB_SHAPE_NAMES = ("BB_Shape_Axes", "BB_Shape_Cube", "BB_Shape_Sphere", "BB_Shape_AimLoc")


def get_ctrl_arm():
    return bpy.data.objects.get(CTRL_ARM_NAME)


def bb_scene_has_leftovers():
    if get_ctrl_arm():
        return True
    for name in BB_COLLECTIONS:
        if name in bpy.data.collections:
            return True
    for name in BB_SHAPE_NAMES:
        if name in bpy.data.objects:
            return True
    return False


def collect_tagged_bones(ctrl_arm):
    result = {}
    for pb in ctrl_arm.pose.bones:
        if pb.get("bb_skip_bake"):
            continue
        src_arm  = pb.get("bb_source_armature")
        src_bone = pb.get("bb_source_bone")
        if src_arm and src_bone:
            result.setdefault(src_arm, set()).add(src_bone)
    return result


def ctrl_bones_for_source(ctrl_arm, source_arm_name, source_bone_names):
    result = []
    for pb in ctrl_arm.pose.bones:
        if pb.get("bb_skip_bake"):
            continue
        if (pb.get("bb_source_armature") == source_arm_name and
                pb.get("bb_source_bone") in source_bone_names):
            result.append(pb.name)
    return result


def resolve_target_bones(context):
    ctrl_arm = get_ctrl_arm()

    selected_pose_bones = context.selected_pose_bones or []
    active_obj = context.active_object

    selected_by_obj = {}
    if context.mode == 'POSE' and active_obj and active_obj.type == 'ARMATURE':
        for pb in selected_pose_bones:
            selected_by_obj.setdefault(active_obj.name, []).append(pb.name)

    for obj in context.selected_objects:
        if obj.type == 'ARMATURE' and obj != active_obj:
            for pb in obj.pose.bones:
                if pb.select:
                    selected_by_obj.setdefault(obj.name, []).append(pb.name)

    if not selected_by_obj or not ctrl_arm:
        return None

    result = []

    for obj_name, bone_names in selected_by_obj.items():
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            continue

        if obj_name == ctrl_arm.name:
            by_src = {}
            for bname in bone_names:
                pb = ctrl_arm.pose.bones.get(bname)
                if pb:
                    src_arm  = pb.get("bb_source_armature")
                    src_bone = pb.get("bb_source_bone")
                    if src_arm and src_bone:
                        by_src.setdefault(src_arm, {"ctrl_bones": [], "source_bones": []})
                        by_src[src_arm]["ctrl_bones"].append(bname)
                        by_src[src_arm]["source_bones"].append(src_bone)
            for src_arm_name, data in by_src.items():
                src_obj = bpy.data.objects.get(src_arm_name)
                if src_obj:
                    result.append({
                        "source_obj":   src_obj,
                        "source_bones": data["source_bones"],
                        "ctrl_bones":   data["ctrl_bones"],
                    })

        else:
            if not ctrl_arm:
                continue
            controlled = []
            for bname in bone_names:
                for pb in ctrl_arm.pose.bones:
                    if (pb.get("bb_source_armature") == obj_name and
                            pb.get("bb_source_bone") == bname):
                        controlled.append(bname)
                        break
            if controlled:
                ctrl_bones = ctrl_bones_for_source(ctrl_arm, obj_name, controlled)
                result.append({
                    "source_obj":   obj,
                    "source_bones": controlled,
                    "ctrl_bones":   ctrl_bones,
                })

    return result if result else None


def cleanup_bb_objects():
    for name in BB_SHAPE_NAMES:
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    for col_name in ("BB_Shapes", "BoneBridge"):
        if col_name in bpy.data.collections:
            col = bpy.data.collections[col_name]
            bpy.data.collections.remove(col)


def bake_and_delete_run(context):
    scene    = context.scene
    start    = scene.frame_start
    end      = scene.frame_end
    ctrl_arm = get_ctrl_arm()

    prev_mode         = context.mode
    prev_active_name  = context.active_object.name if context.active_object else None
    prev_selected_names = [o.name for o in context.selected_objects]

    prev_pose_bones = {}
    if prev_mode == 'POSE':
        for obj in context.selected_objects:
            if obj.type == 'ARMATURE':
                selected = [pb.name for pb in obj.pose.bones if pb.select]
                if selected:
                    prev_pose_bones[obj.name] = selected

    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

    if not ctrl_arm:
        cleanup_bb_objects()
        _restore_state(prev_active_name, prev_selected_names, prev_mode, prev_pose_bones)
        print("✅ Bake and Delete: BB объекты удалены (ctrl_arm не найден).")
        return

    targets = resolve_target_bones(context)
    was_relevant = targets is not None

    if not targets:
        all_tagged = collect_tagged_bones(ctrl_arm)
        targets = []
        for src_arm_name, src_bone_set in all_tagged.items():
            src_obj = bpy.data.objects.get(src_arm_name)
            if src_obj:
                ctrl_bones = ctrl_bones_for_source(ctrl_arm, src_arm_name, src_bone_set)
                targets.append({
                    "source_obj":   src_obj,
                    "source_bones": list(src_bone_set),
                    "ctrl_bones":   ctrl_bones,
                })

    if not targets:
        _remove_ctrl_arm_if_empty(ctrl_arm)
        cleanup_bb_objects()
        _restore_state(prev_active_name, prev_selected_names, prev_mode, prev_pose_bones)
        print("✅ Bake and Delete: нет тегированных костей, BB объекты удалены.")
        return

    baked_sources = {}
    for target in targets:
        src_obj      = target["source_obj"]
        source_bones = target["source_bones"]

        for o in bpy.context.selected_objects:
            o.select_set(False)
        src_obj.select_set(True)
        bpy.context.view_layer.objects.active = src_obj
        bpy.ops.object.mode_set(mode='POSE')
        bpy.context.view_layer.update()

        for pb in src_obj.pose.bones:
            pb.select = False
        src_obj.data.bones.active = None

        valid_bones = []
        for bname in source_bones:
            if bname in src_obj.pose.bones:
                src_obj.pose.bones[bname].select = True
                src_obj.data.bones.active = src_obj.data.bones[bname]
                valid_bones.append(bname)

        if not valid_bones:
            bpy.ops.object.mode_set(mode='OBJECT')
            continue

        if not src_obj.animation_data:
            src_obj.animation_data_create()
        if not src_obj.animation_data.action:
            src_obj.animation_data.action = bpy.data.actions.new(
                name=f"{src_obj.name}_Action"
            )

        bpy.ops.nla.bake(
            frame_start=start, frame_end=end,
            only_selected=True, visual_keying=True,
            clear_constraints=True,
            use_current_action=True,
            bake_types={'POSE'}
        )
        bpy.context.view_layer.update()
        set_interpolation(src_obj)
        bpy.ops.object.mode_set(mode='OBJECT')

        baked_sources[src_obj.name] = valid_bones
        print(f"✅ Baked: {src_obj.name} → {valid_bones}")

    all_ctrl_to_remove = []
    for target in targets:
        all_ctrl_to_remove.extend(target["ctrl_bones"])

    # Дополнительно удаляем кости с bb_skip_bake (CM_PARENT_, RC_ и т.п.),
    # которые принадлежат тем же source арматурам что и удаляемые ctrl кости
    if ctrl_arm:
        src_arms_being_removed = {target["source_obj"].name for target in targets}
        for pb in ctrl_arm.pose.bones:
            if (pb.get("bb_skip_bake") and
                    pb.get("bb_source_armature") in src_arms_being_removed and
                    pb.name not in all_ctrl_to_remove):
                all_ctrl_to_remove.append(pb.name)

    if all_ctrl_to_remove:
        for o in bpy.context.selected_objects:
            o.select_set(False)
        bpy.context.view_layer.objects.active = ctrl_arm
        bpy.ops.object.mode_set(mode='EDIT')
        arm_data = ctrl_arm.data
        for bname in all_ctrl_to_remove:
            if bname in arm_data.edit_bones:
                arm_data.edit_bones.remove(arm_data.edit_bones[bname])
        bpy.ops.object.mode_set(mode='OBJECT')

    _remove_ctrl_arm_if_empty(ctrl_arm)

    if was_relevant and baked_sources:
        for o in bpy.context.selected_objects:
            o.select_set(False)

        first = True
        for src_arm_name, bone_names in baked_sources.items():
            src_obj = bpy.data.objects.get(src_arm_name)
            if not src_obj:
                continue
            src_obj.select_set(True)
            if first:
                bpy.context.view_layer.objects.active = src_obj
                first = False

        bpy.ops.object.mode_set(mode='POSE')
        bpy.context.view_layer.update()

        for src_arm_name, bone_names in baked_sources.items():
            src_obj = bpy.data.objects.get(src_arm_name)
            if not src_obj:
                continue
            for pb in src_obj.pose.bones:
                pb.select = False
            src_obj.data.bones.active = None
            for bname in bone_names:
                if bname in src_obj.pose.bones:
                    src_obj.pose.bones[bname].select = True
                    src_obj.data.bones.active = src_obj.data.bones[bname]
    else:
        _restore_state(prev_active_name, prev_selected_names, prev_mode, prev_pose_bones)

    print("✅ Bake and Delete: готово.")


def _restore_state(prev_active_name, prev_selected_names, prev_mode, prev_pose_bones):
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

    for o in bpy.context.selected_objects:
        o.select_set(False)

    still_exists = [bpy.data.objects[n] for n in prev_selected_names if n in bpy.data.objects]
    for o in still_exists:
        o.select_set(True)

    active = bpy.data.objects.get(prev_active_name) if prev_active_name else None
    if not active and still_exists:
        active = still_exists[0]
    if active:
        bpy.context.view_layer.objects.active = active

    if active:
        try:
            if prev_mode == 'POSE':
                bpy.ops.object.mode_set(mode='POSE')
                bpy.context.view_layer.update()
                for obj in still_exists:
                    if obj.type == 'ARMATURE' and obj.name in prev_pose_bones:
                        for pb in obj.pose.bones:
                            pb.select = False
                        obj.data.bones.active = None
                        for bname in prev_pose_bones[obj.name]:
                            if bname in obj.pose.bones:
                                obj.pose.bones[bname].select = True
                                obj.data.bones.active = obj.data.bones[bname]
            elif prev_mode == 'EDIT':
                bpy.ops.object.mode_set(mode='EDIT')
        except Exception:
            pass


def _remove_ctrl_arm_if_empty(ctrl_arm):
    if ctrl_arm and len(ctrl_arm.data.bones) == 0:
        bpy.data.objects.remove(ctrl_arm, do_unlink=True)
        cleanup_bb_objects()
        print("✅ BoneBridge_Armature_Control удалён (пустой), BB объекты очищены.")


# ══════════════════════════════════════════════════════════════════════════════
#  Operators
# ══════════════════════════════════════════════════════════════════════════════

class BB_OT_bake_and_delete(bpy.types.Operator):
    bl_idname      = "bb.bake_and_delete"
    bl_label       = "Bake and Delete"
    bl_description = "Запечь анимацию в source-кости и удалить контролы BoneBridge"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bb_scene_has_leftovers()

    def execute(self, context):
        bake_and_delete_run(context)
        return {'FINISHED'}


class BB_OT_reparent(bpy.types.Operator):
    bl_idname      = "bb.reparent"
    bl_label       = "reParent"
    bl_description = (
        "Создать контрол-кость и перенести на неё анимацию выделенных костей. "
        "Режим зависит от активных галочек: Aim, Manual Pivot, Global, reConstrain"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if session_active(SCENE_KEY_AIM) or session_active(SCENE_KEY_MP) or session_active(SCENE_KEY_RC):
            return False
        if not (context.mode == 'POSE' and
                context.active_object and
                context.active_object.type == 'ARMATURE' and
                context.selected_pose_bones):
            return False
        scene = context.scene
        # reConstrain требует ровно 2 выделенные кости
        if scene.bb_mode_reconstrain:
            return len(context.selected_pose_bones) == 2
        return True

    def execute(self, context):
        scene      = context.scene
        use_aim    = scene.bb_mode_aim
        use_mp     = scene.bb_mode_manual_pivot
        use_global = scene.bb_mode_global
        use_rc     = scene.bb_mode_reconstrain

        if use_rc:
            bones = context.selected_pose_bones
            # active = child, non-active = parent
            active_bone = context.active_pose_bone
            other_bones = [b for b in bones if b != active_bone]
            if not active_bone or not other_bones:
                self.report({'WARNING'}, "Нужно выделить ровно 2 кости, active = child")
                return {'CANCELLED'}
            parent_bone = other_bones[0]
            child_bone  = active_bone
            if use_mp:
                rc_step1(context.active_object, parent_bone, child_bone)
            else:
                rc_run(context.active_object, parent_bone, child_bone)
        elif use_aim:
            aim_step1(context.active_object, list(context.selected_pose_bones))
        elif use_mp:
            mp_step1(context.active_object, list(context.selected_pose_bones))
        elif use_global:
            rp_run_global(context.active_object, list(context.selected_pose_bones))
        else:
            rp_run(context.active_object, list(context.selected_pose_bones))
        return {'FINISHED'}


class BB_OT_go(bpy.types.Operator):
    bl_idname      = "bb.go"
    bl_label       = "GO"
    bl_description = "Завершить текущую сессию: запечь и применить настроенные контролы"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return session_active(SCENE_KEY_AIM) or session_active(SCENE_KEY_MP) or session_active(SCENE_KEY_RC)

    def execute(self, context):
        if session_active(SCENE_KEY_AIM):
            aim_step2_go()
        elif session_active(SCENE_KEY_MP):
            mp_step2_go()
        elif session_active(SCENE_KEY_RC):
            rc_step2_go()
        return {'FINISHED'}


class BB_OT_cancel(bpy.types.Operator):
    bl_idname      = "bb.cancel"
    bl_label       = "Cancel"
    bl_description = "Отменить текущую сессию и удалить созданные временные кости"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return session_active(SCENE_KEY_AIM) or session_active(SCENE_KEY_MP) or session_active(SCENE_KEY_RC)

    def execute(self, context):
        if session_active(SCENE_KEY_AIM):
            aim_cancel()
        elif session_active(SCENE_KEY_MP):
            mp_cancel()
        elif session_active(SCENE_KEY_RC):
            rc_cancel()
        return {'FINISHED'}


# ══════════════════════════════════════════════════════════════════════════════
#  Panel
# ══════════════════════════════════════════════════════════════════════════════

class BB_PT_panel(bpy.types.Panel):
    bl_label       = "Bone Bridge"
    bl_idname      = "BB_PT_panel"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = 'Item'

    def draw(self, context):
        layout = self.layout
        scene  = context.scene
        col    = layout.column(align=True)
        col.scale_y = 1.4

        aim_active = session_active(SCENE_KEY_AIM)
        mp_active  = session_active(SCENE_KEY_MP)
        rc_active  = session_active(SCENE_KEY_RC)
        any_active = aim_active or mp_active or rc_active

        is_aim  = scene.bb_mode_aim
        is_mp   = scene.bb_mode_manual_pivot
        is_glob = scene.bb_mode_global
        is_rc   = scene.bb_mode_reconstrain

        # ── Строка 1: Aim | Manual Pivot | Global ─────────────────────────────
        row = col.row(align=True)

        sub = row.row(align=True)
        sub.enabled = not any_active and not (is_mp or is_glob or is_rc)
        sub.prop(scene, "bb_mode_aim")

        sub = row.row(align=True)
        sub.enabled = not any_active and not (is_aim or is_glob)
        sub.prop(scene, "bb_mode_manual_pivot")

        sub = row.row(align=True)
        sub.enabled = not any_active and not (is_aim or is_mp or is_rc)
        sub.prop(scene, "bb_mode_global")

        # ── Строка 2: reConstrain ─────────────────────────────────────────────
        row2 = col.row(align=True)
        sub = row2.row(align=True)
        sub.enabled = not any_active and not (is_aim or is_glob)
        sub.prop(scene, "bb_mode_reconstrain")

        col.separator(factor=0.5)

        sub = col.column(align=True)
        sub.enabled = not any_active
        sub.operator("bb.reparent",        icon='BONE_DATA')
        sub.operator("bb.bake_and_delete", icon='TRASH')

        if any_active:
            col.separator(factor=0.5)
            row3 = col.row(align=True)
            row3.scale_y = 1.4
            row3.operator("bb.go",     icon='PLAY')
            row3.operator("bb.cancel", icon='X')

        col.separator()
        col.operator("bb_util.flip_animation", icon='MOD_MIRROR')

        col.separator(factor=0.5)
        col.label(text="Playback Speed:")
        ratio = context.scene.render.frame_map_old / max(context.scene.render.frame_map_new, 1)
        row4 = col.row(align=True)
        row4.scale_y = 1.2
        for spd, label in ((0.1, "0.1x"), (0.3, "0.3x"), (0.5, "0.5x"), (1.0, "1x")):
            op = row4.operator("bb_util.set_playback_speed", text=label,
                               depress=abs(ratio - spd) < 0.01)
            op.speed = spd


# ══════════════════════════════════════════════════════════════════════════════
#  UTILITIES — Flip Animation + Playback Speed
# ══════════════════════════════════════════════════════════════════════════════

def get_selected_bone_names():
    return [pb.name for pb in (bpy.context.selected_pose_bones or [])]


def select_bones_by_name(obj, bone_names):
    for pb in obj.pose.bones:
        pb.select = False
    obj.data.bones.active = None
    for name in bone_names:
        if name in obj.pose.bones:
            obj.pose.bones[name].select = True
            obj.data.bones.active = obj.data.bones[name]


def get_all_fcurves(action):
    fcurves = []
    if hasattr(action, 'layers'):
        for layer in action.layers:
            for strip in layer.strips:
                if hasattr(strip, 'channelbags'):
                    for cb in strip.channelbags:
                        fcurves.extend(cb.fcurves)
    elif hasattr(action, 'fcurves'):
        fcurves.extend(action.fcurves)
    return fcurves


def bone_in_path(bone_name, data_path):
    return f'"{bone_name}"' in data_path or f"'{bone_name}'" in data_path


def run_flip_animation(obj, original_bone_names, mirror_bone_names):
    scene       = bpy.context.scene
    frame_start = scene.frame_start
    frame_end   = scene.frame_end
    half_range  = (frame_end - frame_start) / 2.0

    action = obj.animation_data.action if obj.animation_data else None
    if not action:
        return False, "No action found on armature"

    all_fcurves = get_all_fcurves(action)

    for orig_name, mirror_name in zip(original_bone_names, mirror_bone_names):
        if orig_name in obj.pose.bones and mirror_name in obj.pose.bones:
            obj.pose.bones[mirror_name].rotation_mode = obj.pose.bones[orig_name].rotation_mode

    for fc in all_fcurves:
        if any(bone_in_path(bn, fc.data_path) for bn in mirror_bone_names):
            fc.keyframe_points.clear()
            fc.update()

    for frame in range(frame_start, frame_end + 1):
        scene.frame_set(frame)
        select_bones_by_name(obj, original_bone_names)
        bpy.ops.pose.copy()
        select_bones_by_name(obj, mirror_bone_names)
        bpy.ops.pose.paste(flipped=True)
        select_bones_by_name(obj, mirror_bone_names)
        bpy.ops.anim.keyframe_insert(type='WholeCharacterSelected')

    all_fcurves = get_all_fcurves(action)
    for fc in all_fcurves:
        if not any(bone_in_path(bn, fc.data_path) for bn in mirror_bone_names):
            continue
        for kp in fc.keyframe_points:
            kp.co.x           += half_range
            kp.handle_left.x  += half_range
            kp.handle_right.x += half_range
        fc.update()

    all_bone_names = set(original_bone_names) | set(mirror_bone_names)
    for fc in all_fcurves:
        if not any(bone_in_path(bn, fc.data_path) for bn in all_bone_names):
            continue
        for mod in list(fc.modifiers):
            if mod.type == 'CYCLES':
                fc.modifiers.remove(mod)
        cyc = fc.modifiers.new(type='CYCLES')
        cyc.mode_before = 'REPEAT_OFFSET'
        cyc.mode_after  = 'REPEAT_OFFSET'

    return True, f"Done: {len(original_bone_names)} orig + {len(mirror_bone_names)} mirror bones"


class BB_OT_flip_animation(bpy.types.Operator):
    bl_idname      = "bb_util.flip_animation"
    bl_label       = "Flip Anim to Mirror"
    bl_description = (
        "Зеркалить анимацию на противоположные кости со сдвигом на пол-цикла. "
        "Работает только с костями у которых есть зеркальный аналог"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.mode == 'POSE' and
                context.active_object and
                context.active_object.type == 'ARMATURE' and
                bool(context.selected_pose_bones))

    def execute(self, context):
        obj         = context.active_object
        saved_frame = context.scene.frame_current

        original = get_selected_bone_names()
        if not original:
            self.report({'WARNING'}, "No bones selected")
            return {'CANCELLED'}

        bpy.ops.pose.select_mirror(only_active=False, extend=False)
        mirror = get_selected_bone_names()

        # Если select_mirror вернул те же кости — зеркальных костей нет
        if not mirror or set(mirror) == set(original):
            # Восстанавливаем исходное выделение
            select_bones_by_name(obj, original)
            self.report({'WARNING'}, "No mirror bones found — кости без зеркального аналога")
            return {'CANCELLED'}

        # Убираем из mirror кости которые совпадают с original
        # (select_mirror может вернуть микс если только часть костей имеет зеркало)
        mirror_only = [b for b in mirror if b not in original]
        if not mirror_only:
            select_bones_by_name(obj, original)
            self.report({'WARNING'}, "No mirror bones found — кости без зеркального аналога")
            return {'CANCELLED'}

        bpy.ops.pose.select_mirror(only_active=False, extend=False)

        ok, msg = run_flip_animation(obj, original, mirror_only)
        context.scene.frame_set(saved_frame)

        if ok:
            select_bones_by_name(obj, original)
            self.report({'INFO'}, msg)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}


class BB_OT_set_playback_speed(bpy.types.Operator):
    bl_idname      = "bb_util.set_playback_speed"
    bl_label       = "Set Playback Speed"
    bl_description = "Изменить скорость воспроизведения через frame_map. При возврате на 1x восстанавливает исходный frame_end"
    bl_options     = {'REGISTER', 'UNDO'}

    speed: bpy.props.FloatProperty(name="Speed", default=1.0)

    def execute(self, context):
        scene = context.scene
        scene.render.frame_map_old = 100
        scene.render.frame_map_new = round(100 / self.speed)

        if self.speed == 1.0:
            if "_original_frame_end" in scene:
                scene.frame_end = scene["_original_frame_end"]
                del scene["_original_frame_end"]
        else:
            if "_original_frame_end" not in scene:
                scene["_original_frame_end"] = scene.frame_end
            scene.frame_end = round(scene["_original_frame_end"] / self.speed)

        return {'FINISHED'}


# ══════════════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════════════

classes = (
    BB_OT_bake_and_delete,
    BB_OT_reparent,
    BB_OT_go,
    BB_OT_cancel,
    BB_PT_panel,
    BB_OT_flip_animation,
    BB_OT_set_playback_speed,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_props()
    print("✅ Bone Bridge зарегистрирован → N-панель > Item > Bone Bridge + BB Utilities")


def unregister():
    unregister_props()
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


# Если запущен напрямую через Text Editor — регистрируемся сразу.
# Если загружен как аддон — Blender сам вызовет register(), этот блок не нужен.
# Определяем: аддон импортируется как пакет (есть __package__) или напрямую.
if not __package__:
    try:
        unregister()
    except Exception:
        pass
    register()
