import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class AnimationsPanel(BaseAddonPanel, bpy.types.Panel):
    """UI Panel for animations"""
    bl_idname = "SPRITESHEET_PT_animations"
    bl_label = "Control Animations"

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.prop(props, "useAnimations", text = "")

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        self.layout.active = props.useAnimations

        row = self.layout.row()
        row.prop(props, "outputFrameRate")

        row = self.layout.row()
        row.template_list("UI_UL_AnimationSelectionPropertyList", # Class name
                        "", # List ID (blank to generate)
                        props, # List items property source
                        "animationSelections", # List items property name
                        props, # List index property source
                        "activeAnimationSelectionIndex", # List index property name
                        rows = min(5, len(props.animationSelections)),
                        maxrows = 5
        )