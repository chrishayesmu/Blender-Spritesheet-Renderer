import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class SPRITESHEET_PT_AnimationsPanel(BaseAddonPanel, bpy.types.Panel):
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
        self.template_list(row,
                           "SPRITESHEET_UL_AnimationSelectionPropertyList", # Class name
                           "", # List ID (blank to generate)
                           props, # List items property source
                           "animationSelections", # List items property name
                           props, # List index property source
                           "activeAnimationSelectionIndex" # List index property name
        )