import bpy


def create_bonebridge_for_bone(obj, bone):
    target_name = f"{obj.name}_{bone.name}_BoneBridge"
    empty = bpy.data.objects.new(target_name, None)
    bpy.context.scene.collection.objects.link(empty)  # корневая коллекция сцены
    empty.location = (0, 0, 0)
    empty.rotation_euler = (0, 0, 0)
    empty.rotation_mode = bone.rotation_mode
    empty["bonebridge_rig"] = obj.name
    empty["bonebridge_bone"] = bone.name
    childof = empty.constraints.new(type='CHILD_OF')
    childof.name = "BoneBridge_CHILD_OF"
    childof.target = obj
    childof.subtarget = bone.name
    bpy.context.view_layer.update()
    childof.inverse_matrix.identity()
    return empty


def run_create(obj, selected_bones):
    scene = bpy.context.scene
    start = scene.frame_start
    end = scene.frame_end

    empties = []
    for bone in selected_bones:
        empty = create_bonebridge_for_bone(obj, bone)
        empties.append((bone, empty))

    bpy.ops.object.mode_set(mode='OBJECT')

    for o in bpy.context.selected_objects:
        o.select_set(False)
    for bone, empty in empties:
        empty.select_set(True)
    bpy.context.view_layer.objects.active = empties[0][1]

    bpy.ops.nla.bake(
        frame_start=start,
        frame_end=end,
        only_selected=True,
        visual_keying=True,
        clear_constraints=False,
        use_current_action=False,
        bake_types={'OBJECT'}
    )

    for bone, empty in empties:
        for c in list(empty.constraints):
            empty.constraints.remove(c)

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')

    for bone, empty in empties:
        copy_loc = bone.constraints.new(type='COPY_LOCATION')
        copy_loc.name = "BoneBridge_COPY_LOCATION"
        copy_loc.target = empty
        copy_loc.owner_space = 'WORLD'
        copy_loc.target_space = 'WORLD'

        copy_rot = bone.constraints.new(type='COPY_ROTATION')
        copy_rot.name = "BoneBridge_COPY_ROTATION"
        copy_rot.target = empty
        copy_rot.owner_space = 'WORLD'
        copy_rot.target_space = 'WORLD'

    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for bone, empty in empties:
        empty.select_set(True)
    bpy.context.view_layer.objects.active = empties[0][1]


class BONEBRIDGE_OT_create(bpy.types.Operator):
    bl_idname = "bonebridge.create"
    bl_label = "reParent"
    bl_description = "Создать BoneBridge Empty для выделенных костей"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'POSE' and
            context.active_pose_bone is not None and
            len(context.selected_pose_bones) > 0
        )

    def execute(self, context):
        obj = context.active_object
        selected_bones = context.selected_pose_bones
        run_create(obj, selected_bones)
        self.report({'INFO'}, f"BoneBridge создан для {len(selected_bones)} костей")
        return {'FINISHED'}
