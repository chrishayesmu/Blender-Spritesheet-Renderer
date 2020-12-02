import bpy

from ui.BaseAddonPanel import BaseAddonPanel

class AnimationsPanel(BaseAddonPanel, bpy.types.Panel):
    """UI Panel for animations"""
    bl_idname = "SPRITESHEET_PT_animations"
    bl_label = "Animation Data"

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup

        row = self.layout.row()
        row.prop(props, "useAnimations")

        if (props.useAnimations):
            if len(props.animationSelections) > 0:
                row = self.layout.row()
                row.prop(props, "outputFrameRate")

                self.layout.separator()
                row = self.layout.row()
                split = row.split(factor = 0.075)
                split.scale_y = 0.4
                col1, col2 = (split.column(), split.column())
                
                split = col2.split(factor = 0.75)
                col2, col3 = (split.column(), split.column())

                col1.label(text = "Use")
                col2.label(text = "Action")
                col3.label(text = "Length")
                
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

            else:
                row = self.layout.row()
                box = row.box()
                box.label(text = "There are no animations in the file to render.", icon = "ERROR")