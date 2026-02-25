import bpy


def find_bonebridge_empty(armature, bone_name):
    for obj in bpy.data.objects:
        if (obj.type == 'EMPTY'
                and obj.get("bonebridge_rig") == armature.name
                and obj.get("bonebridge_bone") == bone_name):
            return obj
    return None


def collect_tasks(context):
    tasks = []
    seen_empties = set()
    active = context.active_object

    if context.mode == 'OBJECT':
        for obj in context.selected_objects:
            if obj.type != 'EMPTY':
                continue
            rig_name = obj.get("bonebridge_rig")
            bone_name = obj.get("bonebridge_bone")
            if not rig_name or not bone_name:
                continue
            armature = bpy.data.objects.get(rig_name)
            if not armature or armature.type != 'ARMATURE':
                continue
            if id(obj) not in seen_empties:
                tasks.append((obj, armature, bone_name))
                seen_empties.add(id(obj))

    elif context.mode == 'POSE':
        armature = active
        for pose_bone in context.selected_pose_bones:
            empty = find_bonebridge_empty(armature, pose_bone.name)
            if not empty:
                continue
            if id(empty) not in seen_empties:
                tasks.append((empty, armature, pose_bone.name))
                seen_empties.add(id(empty))

    return tasks


def run_bake_and_delete(tasks):
    by_armature = {}
    for empty, armature, bone_name in tasks:
        key = armature.name
        if key not in by_armature:
            by_armature[key] = {'armature': armature, 'items': []}
        by_armature[key]['items'].append((empty, bone_name))

    for o in bpy.context.selected_objects:
        o.select_set(False)

    for rig_name, data in by_armature.items():
        armature = data['armature']
        items = data['items']

        bpy.context.view_layer.objects.active = armature
        armature.select_set(True)
        bpy.ops.object.mode_set(mode='POSE')

        for pb in armature.pose.bones:
            pb.select = False
        armature.data.bones.active = None

        found_bones = []
        for empty, bone_name in items:
            if bone_name in armature.pose.bones:
                armature.pose.bones[bone_name].select = True
                armature.data.bones.active = armature.data.bones[bone_name]
                found_bones.append(bone_name)

        if not found_bones:
            bpy.ops.object.mode_set(mode='OBJECT')
            continue

        scene = bpy.context.scene
        bpy.ops.nla.bake(
            frame_start=scene.frame_start,
            frame_end=scene.frame_end,
            only_selected=True,
            visual_keying=True,
            clear_constraints=False,
            clear_parents=False,
            use_current_action=True,
            clean_curves=False,
            bake_types={'POSE'}
        )

        for bone_name in found_bones:
            pose_bone = armature.pose.bones[bone_name]
            to_remove = [c for c in pose_bone.constraints if 'BoneBridge' in c.name]
            for c in to_remove:
                pose_bone.constraints.remove(c)

        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')
    for empty, armature, bone_name in tasks:
        empty.select_set(True)
    bpy.ops.object.delete()

    last_armature = tasks[-1][1]
    bpy.context.view_layer.objects.active = last_armature
    last_armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    for pb in last_armature.pose.bones:
        pb.select = False
    for empty, armature, bone_name in tasks:
        if armature == last_armature and bone_name in armature.pose.bones:
            armature.pose.bones[bone_name].select = True
            armature.data.bones.active = armature.data.bones[bone_name]


class BONEBRIDGE_OT_bake_and_delete(bpy.types.Operator):
    bl_idname = "bonebridge.bake_and_delete"
    bl_label = "Bake and Delete"
    bl_description = (
        "Bake костей и удалить BoneBridge Empty. "
        "Object Mode: выделить пустышки. Pose Mode: выделить кости"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return any(
                o.type == 'EMPTY' and o.get("bonebridge_rig")
                for o in context.selected_objects
            )
        elif context.mode == 'POSE':
            if not context.selected_pose_bones:
                return False
            armature = context.active_object
            return any(
                find_bonebridge_empty(armature, pb.name)
                for pb in context.selected_pose_bones
            )
        return False

    def execute(self, context):
        tasks = collect_tasks(context)
        if not tasks:
            self.report({'WARNING'}, "Нет валидных объектов для обработки")
            return {'CANCELLED'}
        run_bake_and_delete(tasks)
        self.report({'INFO'}, f"Bake завершён: {len(tasks)} костей")
        return {'FINISHED'}
