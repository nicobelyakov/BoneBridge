# --- Тестовый запуск ---
if __name__ == "__main__":
    obj = bpy.context.active_object
    selected_bones = bpy.context.selected_pose_bones

    if obj and selected_bones:
        run_create(obj, selected_bones)
        print(f"OK: создано {len(selected_bones)} пустышек")
    else:
        print("Выдели кости в Pose Mode перед запуском!")
