from util import UIUtil

class SPRITESHEET_PT_MaterialSetPanel():
    """UI Panel for material sets.

    Since this panel is shown multiple times, it is instantiated as multiple sub-types, and this specific class
    is never actually instantiated. Hence, it does not need to extend any classes like the other panels do, since
    those will be mixed in at runtime."""

    bl_label = "" # hidden; see draw_header
    bl_parent_id = "SPRITESHEET_PT_materials"

    index = 0

    @classmethod
    def poll(cls, context):
        props = context.scene.SpritesheetPropertyGroup

        return cls.index < len(props.materialSets)

    @classmethod
    def create_sub_panel(cls, index):
        UIUtil.create_panel_type(cls, index)

    def draw(self, context):
        props = context.scene.SpritesheetPropertyGroup
        material_set = props.materialSets[self.index]

        self.layout.active = props.useMaterials

        row = self.layout.row()
        row.operator("spritesheet.remove_material_set", text = "Remove Set", icon = "REMOVE").index = self.index

        row = self.layout.row()
        row.prop(material_set, "name")

        row = self.layout.row()
        row.prop(material_set, "role")

        row = self.layout.row()
        self.template_list(row,
                           "SPRITESHEET_UL_ObjectMaterialPairPropertyList", # Class name
                           "", # List ID (blank to generate)
                           material_set, # List items property source
                           "objectMaterialPairs", # List items property name
                           material_set, # List index property source
                           "selectedObjectMaterialPair", # List index property name
        )

    def draw_header(self, context):
        props = context.scene.SpritesheetPropertyGroup
        material_set = props.materialSets[self.index]

        set_label = f"Material Set {self.index + 1}"

        if material_set.name:
            set_label = set_label + " - " + material_set.name

        self.layout.label(text = set_label)
