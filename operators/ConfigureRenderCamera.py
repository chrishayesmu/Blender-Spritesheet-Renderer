import bpy

class SPRITESHEET_OT_ConfigureRenderCameraOperator(bpy.types.Operator):
    bl_idname = "spritesheet.configure_render_camera"
    bl_label = "Configure Render Camera"

    def execute(self, context):
        props = context.scene.SpritesheetPropertyGroup

        if props.renderCamera:
            props.renderCamera.data.type = "ORTHO"
            return {"FINISHED"}

        return {"CANCELLED"}