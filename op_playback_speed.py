import bpy


class BONEBRIDGE_OT_set_playback_speed(bpy.types.Operator):
    """Установить скорость воспроизведения через Time Remapping"""
    bl_idname = "bonebridge.set_playback_speed"
    bl_label = "Set Playback Speed"
    bl_options = {'REGISTER', 'UNDO'}

    speed: bpy.props.FloatProperty(name="Speed", default=1.0)

    def execute(self, context):
        scene = bpy.data.scenes["Scene"]

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
