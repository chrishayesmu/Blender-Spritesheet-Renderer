import bpy

import utils

def _get_camera_control_mode_options(self, context: bpy.types.Context):
    #pylint: disable=unused-argument
    props = context.scene.SpritesheetPropertyGroup

    items = [
        ("move_once", "Fit All Frames", "The camera will be adjusted once before any rendering is done, so that the entire spritesheet is rendered from the same camera perspective.", 0),
        ("move_each_frame", "Fit Each Frame", "The camera will be adjusted before every render frame to fit the Target Object. Note that this will prevent the appearance of movement in the spritesheet.", 1)
    ]

    if props.control_animations:
        items.append(("move_each_animation", "Fit Each Animation", "The camera will be adjusted at the start of each animation, so that the entire animation is rendered without subsequently moving the camera.", 2))

    if props.control_rotation:
        items.append(("move_each_rotation", "Fit Each Rotation", "The camera will be adjusted every time the Target Object is rotated, so that all frames for the rotation (including animations if enabled) " +
                                                                 "are rendered without subsequently moving the camera.", 3))

    return items

def _get_camera_control_mode(self) -> int:
    val = self.get("camera_control_mode")

    if val is None:
        val = 0
    else:
        # Make sure the chosen value is still an option based on latest configuration
        items = _get_camera_control_mode_options(self, bpy.context)
        is_valid = any(item[3] == val for item in items)

        if not is_valid:
            val = 0 # default to moving once

    return val

def _set_camera_control_mode(self, value):
    self["camera_control_mode"] = value

class AnimationSelectionPropertyGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name = "Action Name",
        default = ""
    )

    is_selected_for_export: bpy.props.BoolProperty(default = True)

    num_frames: bpy.props.IntProperty()

class RenderTargetMaterialPropertyGroup(bpy.types.PropertyGroup):
    # You can only make CollectionProperties out of PropertyGroups, so this class just wraps bpy.types.Material

    material: bpy.props.PointerProperty(
        name = "Material",
        type = bpy.types.Material
    )

    def set_material_from_mesh(self, context: bpy.types.Context, mesh_index: int):
        props = context.scene.SpritesheetPropertyGroup

        target = props.render_targets[mesh_index]

        if not target.mesh or len(target.mesh.materials) == 0:
            return

        self.material = target.mesh.materials[0]

class MaterialSetPropertyGroup(bpy.types.PropertyGroup):

    def _get_name(self) -> str:
        name = self.get("name")

        return name if name and not name.isspace() else utils.enum_display_name_from_identifier(self, "role", self.role)

    def _set_name(self, value: str):
        self["name"] = value

    mode: bpy.props.EnumProperty(
        name = "Mode",
        description = "How materials should be assigned within this set",
        items = [
            ("individual", "Material Per Target", "Each Render Target is manually assigned a material in this set."),
            ("shared", "Shared Material", "A single material is chosen which will be applied to every Render Target when this set is being rendered. This is mostly useful for certain effects, such as rendering object normals from the camera.")
        ],
        default = "individual"
    )

    name: bpy.props.StringProperty(
        name = "Set Name",
        description = "(Optional) A user-friendly name you can supply to help you keep track of your material sets. If not provided, the material set's role will be displayed instead",
        get = _get_name,
        set = _set_name
    )

    materials: bpy.props.CollectionProperty(type = RenderTargetMaterialPropertyGroup)

    role: bpy.props.EnumProperty(
        name = "Role",
        description = "How the output from this material set will be used. Does not impact the rendered images, but is included in output metadata for import to other programs",
        items = [
            ("albedo", "Albedo/Base Color", "This material set provides the albedo, or base color, of the object."),
            ("mask_unity", "Mask (Unity)", "This material set creates a Unity mask texture, where the red channel is metallic, green is occlusion, blue is the detail mask, and alpha is smoothness."),
            ("normal_unity", "Normal (Unity)", "This material set creates a normal map for use in Unity (tangent space, Y+)."),
            ("other", "Other", "Any use not fitting the options above.")
        ]
    )

    selected_material_index: bpy.props.IntProperty(
        get = lambda self: -1 # dummy getter and no setter means items in the list can't be selected
    )

    shared_material: bpy.props.PointerProperty(
        name = "Material",
        description = "The material to use for all Render Targets while rendering this material set",
        type = bpy.types.Material
    )

class RenderTargetPropertyGroup(bpy.types.PropertyGroup):

    def _on_target_mesh_updated(self, context):
        #pylint: disable=invalid-name

        # Sync up the mesh_object property for convenience
        self.mesh_object = None if self.mesh is None else utils.find_object_data_for_mesh(self.mesh)

        # When selecting an object for the first time, auto-detect its associated material and assign it
        # in all of the material sets, for convenience; also set its rotation root to itself
        if self.previous_mesh is None and self.mesh is not None and hasattr(self.mesh, "materials") and len(self.mesh.materials) > 0:
            props = context.scene.SpritesheetPropertyGroup

            self.rotation_root = self.mesh_object

            # Figure out which index this object is, because it's the same in the material sets
            index = list(props.render_targets).index(self)

            for material_set in props.material_sets:
                material_set.materials[index].set_material_from_mesh(context, index)

        self.previous_mesh = self.mesh

    mesh: bpy.props.PointerProperty(
        name = "Render Target",
        description = "A mesh to be rendered into the spritesheet",
        type = bpy.types.Mesh,
        update = _on_target_mesh_updated
    )

    # Just stores the object linked to the mesh so we don't have to look it up constantly
    mesh_object: bpy.props.PointerProperty(type = bpy.types.Object)

    previous_mesh: bpy.props.PointerProperty(type = bpy.types.Mesh)

    rotation_root: bpy.props.PointerProperty(
        name = "Rotation Root",
        description = "If 'Control Rotation' is set, this object will be rotated instead of the Render Target. This is useful for parent objects or armatures. If not set, the Render Target is rotated",
        type = bpy.types.Object
    )

class ReportingPropertyGroup(bpy.types.PropertyGroup):
    current_frame_num: bpy.props.IntProperty() # which frame we are currently rendering

    elapsed_time: bpy.props.FloatProperty() # how much time has elapsed in the current job, in seconds

    has_any_job_started: bpy.props.BoolProperty() # whether any job has started in the current session

    job_in_progress: bpy.props.BoolProperty() # whether a job is running right now

    last_error_message: bpy.props.StringProperty() # the last error reported by a job (generally job-ending)

    output_directory: bpy.props.StringProperty() # the absolute path of the directory of the final spritesheet/JSON output

    output_to_terminal: bpy.props.BoolProperty(
        name = "Terminal",
        description = "If true, render jobs will print job progress to the system console (stdout)",
        default = False
    )

    output_to_panel: bpy.props.BoolProperty(
        name = "UI",
        description = "If true, render jobs will print job progress in the Job Management panel",
        default = True
    )

    total_num_frames: bpy.props.IntProperty() # the total number of frames which will be rendered

    @property
    def estimated_time_remaining(self):
        if self.current_frame_num == 0 or self.total_num_frames == 0:
            return None

        # This isn't fully accurate since we have some time-consuming tasks regardless of the number of
        # frames, but render time is the vast majority of any substantial job, so close enough
        time_per_frame = self.elapsed_time / self.current_frame_num
        return (self.total_num_frames - self.current_frame_num) * time_per_frame

class SpritesheetPropertyGroup(bpy.types.PropertyGroup):
    """Property group for spritesheet rendering configuration"""

    def _on_render_camera_updated(self, _context):
        if self.render_camera is None:
            self.render_camera_obj = None
        else:
            self.render_camera_obj = utils.find_object_data_for_camera(self.render_camera)

    #### Animation data
    # TODO: make animations into animation sets
    selected_animation_index: bpy.props.IntProperty(
        get = lambda self: -1
    )

    animation_selections: bpy.props.CollectionProperty(type = AnimationSelectionPropertyGroup)

    output_frame_rate: bpy.props.IntProperty(
        name = "Output Frame Rate",
        description = "The frame rate of the animation in the spritesheet",
        default = 24,
        min = 1
    )

    control_animations: bpy.props.BoolProperty(
        name = "Animate During Render",
        description = "If true, the Render Targets will be animated while rendering, with one sprite being emitted per frame of animation",
        default = False
    )

    ### Materials data
    material_sets: bpy.props.CollectionProperty(type = MaterialSetPropertyGroup)

    control_materials: bpy.props.BoolProperty(
        name = "Render Multiple Materials",
        description = "If true, the Render Targets will be rendered once for each material set",
        default = False
    )

    ### Camera options
    control_camera: bpy.props.BoolProperty(
        name = "Control Camera",
        description = "If true, the Render Camera will be moved and adjusted to best fit all Render Targets in view",
        default = False
    )

    camera_control_mode: bpy.props.EnumProperty(
        name = "Control Style",
        description = "How to control the Render Camera",
        items = _get_camera_control_mode_options,
        get = _get_camera_control_mode,
        set = _set_camera_control_mode
    )

    render_camera: bpy.props.PointerProperty(
        name = "Render Camera",
        description = "The camera to control during rendering",
        type = bpy.types.Object,
        update = _on_render_camera_updated
    )

    render_camera_obj: bpy.props.PointerProperty(type = bpy.types.Object)

    ### Rotation options
    control_rotation: bpy.props.BoolProperty(
        name = "Control Rotation",
        description = "Whether to rotate the Render Target. All targets will be rotated simultaneously, but you may choose an object to rotate each around (such as a parent or armature)"
    )

    # TODO: add a rotation mode option so that you can rotate either a single object (presumably a parent of the rest of them) or each object individually

    num_rotations: bpy.props.IntProperty(
        name = "Total Angles",
        description = "How many rotations to perform",
        default = 8,
        min = 2,
        max = 72 # 5 degrees movement per render should be fine-grained enough for anyone
    )

    selected_rotation_root_index: bpy.props.IntProperty(
        get = lambda self: -1
    )

    ### Target objects
    render_targets: bpy.props.CollectionProperty(
        name = "Render Targets",
        type = RenderTargetPropertyGroup
    )

    selected_render_target_index: bpy.props.IntProperty()

    ### Output file properties
    pad_output_to_power_of_two: bpy.props.BoolProperty(
        name = "Pad to Power-of-Two",
        description = "If true, all output images will be padded with transparent pixels to the smallest power-of-two size that can fit the original output",
        default = False
    )

    separate_files_per_animation: bpy.props.BoolProperty(
        name = "Separate Files Per Animation",
        description = "If 'Control Animations' is enabled, this will generate one output file per animation action. Otherwise, all actions will be combined in a single file",
        default = False
    )

    separate_files_per_material: bpy.props.BoolProperty(
        name = "Separate Files Per Material Set",
        description = "If 'Control Materials' is enabled, this will generate one output file per material set. This cannot be disabled",
        default = True
    )

    separate_files_per_rotation: bpy.props.BoolProperty(
        name = "Separate Files Per Rotation",
        description = "If 'Rotate During Render' is enabled, this will generate one output file per rotation option",
        default = False
    )

    sprite_size: bpy.props.IntVectorProperty(
        name = "Sprite Size",
        description = "How large each individual sprite should be",
        default = (128, 128),
        min = 16,
        size = 2
    )