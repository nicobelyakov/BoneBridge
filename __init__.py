import bpy
from . import op_reparent
from . import op_bake_and_delete
from . import op_flip_animation

bl_info = {
    "name": "BoneBridge",
    "author": "NicoBelyakov",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D → N-panel → Item",
    "description": "Create and bake BoneBridge empties for bones",
    "category": "Animation",
}


class BONEBRIDGE_PT_panel(bpy.types.Panel):
    bl_label = "BoneBridge"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.scale_y = 1.4
        col.operator("bonebridge.create", icon='EMPTY_AXIS')
        col.operator("bonebridge.bake_and_delete", icon='ANIM')
        col.separator()
        col.operator("bonebridge.flip_animation", icon='MOD_MIRROR')


classes = [
    op_reparent.BONEBRIDGE_OT_create,
    op_bake_and_delete.BONEBRIDGE_OT_bake_and_delete,
    op_flip_animation.BONEBRIDGE_OT_flip_animation,
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
