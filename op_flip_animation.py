import bpy


def get_selected_bone_names():
    return [pb.name for pb in (bpy.context.selected_pose_bones or [])]


def select_bones_by_name(obj, bone_names):
    """Выделяем кости через PoseBone.select (Blender 5)."""
    for pb in obj.pose.bones:
        pb.select = False
    obj.data.bones.active = None
    for name in bone_names:
        if name in obj.pose.bones:
            obj.pose.bones[name].select = True
            obj.data.bones.active = obj.data.bones[name]


def get_all_fcurves(action):
    """Blender 5: action.layers[].strips[].channelbags[].fcurves"""
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
    scene = bpy.context.scene
    frame_start = scene.frame_start
    frame_end = scene.frame_end
    half_range = (frame_end - frame_start) / 2.0

    action = obj.animation_data.action if obj.animation_data else None
    if not action:
        return False, "No action found on armature"

    all_fcurves = get_all_fcurves(action)

    # Удаляем все ключи у зеркальных костей
    for fc in all_fcurves:
        if any(bone_in_path(bn, fc.data_path) for bn in mirror_bone_names):
            fc.keyframe_points.clear()
            fc.update()

    # Для каждого кадра: Copy Pose -> Paste Flipped -> вставить ключи
    for frame in range(frame_start, frame_end + 1):
        scene.frame_set(frame)

        select_bones_by_name(obj, original_bone_names)
        bpy.ops.pose.copy()

        select_bones_by_name(obj, mirror_bone_names)
        bpy.ops.pose.paste(flipped=True)

        # После paste выделены исходные — явно выделяем зеркальные для вставки ключей
        select_bones_by_name(obj, mirror_bone_names)
        bpy.ops.anim.keyframe_insert(type='WholeCharacterSelected')

    # Сдвигаем ключи зеркальных костей на half_range
    all_fcurves = get_all_fcurves(action)  # перечитываем после вставки ключей
    for fc in all_fcurves:
        if not any(bone_in_path(bn, fc.data_path) for bn in mirror_bone_names):
            continue
        for kp in fc.keyframe_points:
            kp.co.x += half_range
            kp.handle_left.x += half_range
            kp.handle_right.x += half_range
        fc.update()

    # Make Cyclic для всех задействованных костей
    all_bone_names = set(original_bone_names) | set(mirror_bone_names)
    for fc in all_fcurves:
        if not any(bone_in_path(bn, fc.data_path) for bn in all_bone_names):
            continue
        for mod in list(fc.modifiers):
            if mod.type == 'CYCLES':
                fc.modifiers.remove(mod)
        cycles_mod = fc.modifiers.new(type='CYCLES')
        cycles_mod.mode_before = 'REPEAT_OFFSET'
        cycles_mod.mode_after = 'REPEAT_OFFSET'

    return True, f"Done: {len(original_bone_names)} original + {len(mirror_bone_names)} mirror bones"


class BONEBRIDGE_OT_flip_animation(bpy.types.Operator):
    bl_idname = "bonebridge.flip_animation"
    bl_label = "Flip Anim to Mirror"
    bl_description = (
        "Зеркалит анимацию на противоположные кости со сдвигом на пол-цикла. "
        "Выдели исходные кости в Pose Mode и запусти"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'POSE' and
            context.active_object is not None and
            context.active_object.type == 'ARMATURE' and
            len(context.selected_pose_bones or []) > 0
        )

    def execute(self, context):
        obj = context.active_object

        # Запоминаем исходные кости
        original_bone_names = get_selected_bone_names()
        if not original_bone_names:
            self.report({'WARNING'}, "No bones selected")
            return {'CANCELLED'}

        # Получаем зеркальные кости через Selected Mirror
        bpy.ops.pose.select_mirror(only_active=False, extend=False)
        mirror_bone_names = get_selected_bone_names()

        if not mirror_bone_names:
            self.report({'WARNING'}, "No mirror bones found")
            return {'CANCELLED'}

        # Возвращаемся к исходным
        bpy.ops.pose.select_mirror(only_active=False, extend=False)

        ok, msg = run_flip_animation(obj, original_bone_names, mirror_bone_names)

        if ok:
            # В конце выделяем исходные кости
            select_bones_by_name(obj, original_bone_names)
            self.report({'INFO'}, msg)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
