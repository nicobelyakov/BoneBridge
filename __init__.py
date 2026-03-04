import bpy
from . import op_reparent
from . import op_bake_and_delete
from . import op_flip_animation
from . import op_playback_speed

bl_info = {
    "name": "Bone Bridge",
    "author": "NicoBelyakov",
    "version": (1, 2, 0),
    "blender": (4, 0, 0),
    "location": "View3D → N-panel → Item",
    "description": "Create and bake Bone Bridge empties for bones",
    "category": "Animation",
}


class BONEBRIDGE_PT_panel(bpy.types.Panel):
    bl_label = "Bone Bridge"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'

    def draw(self, context):
        layout = self.layout
        scene = bpy.data.scenes.get("Scene")

        col = layout.column(align=True)
        col.scale_y = 1.4
        col.operator("bonebridge.create", icon='EMPTY_AXIS')
        col.operator("bonebridge.bake_and_delete", icon='ANIM')
        col.separator()
        col.operator("bonebridge.flip_animation", icon='MOD_MIRROR')

        col.separator()
        col.label(text="Playback Speed:")

        if scene:
            ratio = scene.render.frame_map_new / max(scene.render.frame_map_old, 1)
        else:
            ratio = 1.0

        row = col.row(align=True)
        row.scale_y = 1.2

        op = row.operator("bonebridge.set_playback_speed", text="0.1x",
                          depress=abs(ratio - 0.1) < 0.01)
        op.speed = 0.1

        op = row.operator("bonebridge.set_playback_speed", text="0.3x",
                          depress=abs(ratio - 0.3) < 0.01)
        op.speed = 0.3

        op = row.operator("bonebridge.set_playback_speed", text="0.5x",
                          depress=abs(ratio - 0.5) < 0.01)
        op.speed = 0.5

        op = row.operator("bonebridge.set_playback_speed", text="1x",
                          depress=abs(ratio - 1.0) < 0.01)
        op.speed = 1.0


classes = [
    op_reparent.BONEBRIDGE_OT_create,
    op_bake_and_delete.BONEBRIDGE_OT_bake_and_delete,
    op_flip_animation.BONEBRIDGE_OT_flip_animation,
    op_playback_speed.BONEBRIDGE_OT_set_playback_speed,
    BONEBRIDGE_PT_panel,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
