import bpy
import collections
import math
from typing import List, Optional, Tuple

from util import StringUtil
import utils

frame_data = collections.namedtuple('frame_data', 'frame_min frame_max num_frames')

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

class AnimationActionPropertyGroup(bpy.types.PropertyGroup):
    action: bpy.props.PointerProperty(
        name = "Action",
        description = "Which action to use for this Render Target during this animation set. If unset, the Render Target will be unanimated",
        type = bpy.types.Action
    )

    target: bpy.props.PointerProperty(
        name = "Animation Target",
        description = "Which object this action will be applied to",
        type = bpy.types.Object
    )

    max_frame: bpy.props.IntProperty(
        get = lambda self: -1 if not self.action else math.ceil(self.action.frame_range[1])
    )

    min_frame: bpy.props.IntProperty(
        get = lambda self: -1 if not self.action else math.floor(self.action.frame_range[0])
    )

    num_frames: bpy.props.IntProperty(
        get = lambda self: 0 if not self.action else self.max_frame - self.min_frame + 1
    )

    def get_frame_data(self) -> Optional[Tuple[int, int, int]]:
        if self.action is None:
            return None

        return frame_data(self.min_frame, self.max_frame, self.num_frames)

class AnimationSetPropertyGroup(bpy.types.PropertyGroup):
    def _get_name(self) -> str:
        # Prefer name given by user; if none, use the first action name; otherwise just blank
        name: str = self.get("name")

        if name and name.strip():
            return name.strip()

        selected_actions = [a.action for a in self.actions if a.action is not None]

        if len(selected_actions) > 0:
            return selected_actions[0].name.strip()

        return "unnamed"

    def _set_name(self, value):
        self["name"] = value

    # There should be one action per render target; this is handled elsewhere
    actions: bpy.props.CollectionProperty(type = AnimationActionPropertyGroup)

    is_previewing: bpy.props.BoolProperty(default = False)

    name: bpy.props.StringProperty(
        name = "Animation Set Name",
        description = "TBD",
        get = _get_name,
        set = _set_name
    )

    output_frame_rate: bpy.props.IntProperty(
        name = "Output Frame Rate",
        description = "The frame rate of this animation set. Not used in rendering, but included in JSON output for other tools to import",
        default = 24,
        min = 1
    )

    selected_action_index: bpy.props.IntProperty(
        name = "", # hide name in tooltip
        #get = lambda self: -1
    )

    def assign_actions_to_targets(self):
        is_valid, err = self.is_valid()

        if not is_valid:
            raise ValueError(f"Can't assign actions because animation set is invalid: {err}")

        # Go through and make sure all the render targets are in a good state before we start changing things
        for prop in self.actions:
            prop.target.animation_data_create() # just in case
            prop.target.animation_data.use_tweak_mode = False # can't change actions while in NLA's tweak mode

            if prop.target.animation_data.is_property_readonly("action"):
                # There may be other reasons the prop is readonly, but this is the only one I know of so far
                raise ValueError(f"Animation target \"{prop.target.name}\" has animation data that cannot be modified. It may be in tweak mode in Nonlinear Animation.")

        for prop in self.actions:
            prop.target.animation_data.action = prop.action

    def get_frame_data(self) -> Optional[Tuple[int, int, int]]:
        if len(self.actions) == 0:
            return None

        selected_actions = self.get_selected_actions()

        if len(selected_actions) == 0:
            return None

        frame_min = min(a.min_frame for a in selected_actions)
        frame_max = max(a.max_frame for a in selected_actions)
        num_frames = frame_max - frame_min + 1

        return frame_data(frame_min, frame_max, num_frames)

    def get_selected_actions(self) -> List[AnimationActionPropertyGroup]:
        return list([a for a in self.actions if a.action is not None])

    def is_valid(self) -> Tuple[bool, Optional[str]]:
        for index, prop in enumerate(self.actions):
            if not prop.target:
                return (False, f"Target in row {index + 1} is not set.")

            if not prop.action:
                return (False, f"Action in row {index + 1} is not set.")

        return (True, None)

class RenderTargetMaterialPropertyGroup(bpy.types.PropertyGroup):
    # All of these types have a materials property
    # Keep in sync with description of "target" property
    _valid_target_types = { "CURVE", "GPENCIL", "MESH", "META", "VOLUME" }

    def _is_obj_valid_target(self, obj):
        return obj.type in RenderTargetMaterialPropertyGroup._valid_target_types

    def _is_mat_valid_for_target(self, mat):
        # Non-grease-pencil materials are valid for everything
        if not mat.is_grease_pencil:
            return True

        # Grease pencil materials can only be used with grease pencil objects
        if self.target is not None and self.target.type == "GPENCIL":
            return True

        return False

    material: bpy.props.PointerProperty(
        name = "Material",
        description = "The material which will be applied to the Target Object while this material set is active. Cannot be empty. Some materials are only valid for certain object types, and this list is filtered accordingly",
        type = bpy.types.Material,
        poll = _is_mat_valid_for_target
    )

    target: bpy.props.PointerProperty(
        name = "Target Object",
        description = "The object to which this material will be applied. Can be a Mesh, Curve, Volume, Metaball, or Grease Pencil",
        type = bpy.types.Object,
        poll = _is_obj_valid_target
    )

class MaterialSetPropertyGroup(bpy.types.PropertyGroup):

    def _get_name(self) -> str:
        name = self.get("name")

        return name.strip() if name and name.strip() else utils.enum_display_name_from_identifier(self, "role", self.role)

    def _set_name(self, value: str):
        self["name"] = value

    def _is_mat_valid_to_share(self, mat):
        # Non-grease-pencil materials are valid for everything
        if not mat.is_grease_pencil:
            return True

        if all(item.target is not None and item.target.type == "GPENCIL" for item in self.materials):
            return True

        return False

    mode: bpy.props.EnumProperty(
        name = "Mode",
        description = "How materials should be assigned within this set",
        items = [
            ("individual", "Material Per Target", "Each Render Target is manually assigned a material in this set."),
            ("shared", "Shared Material", "A single material is chosen which will be applied to every Render Target when this set is being rendered. " +
                                          "This is mostly useful for certain effects, such as rendering object normals from the camera's perspective.")
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

    selected_material_index: bpy.props.IntProperty(name = "")

    shared_material: bpy.props.PointerProperty(
        name = "Shared Material",
        description = "The material to use for all targets while rendering this material set. Grease pencil materials will only be available if all targets are grease pencils",
        type = bpy.types.Material,
        poll = _is_mat_valid_to_share
    )

    def assign_materials_to_targets(self):
        if not self.is_valid():
            raise ValueError("Material set is not in a valid state to assign materials")

        for index, prop in enumerate(self.materials):

            if len(prop.target.material_slots) == 0:
                prop.target.material_slots.new(None)

            prop.target.material_slots[0].material = self.material_at(index)

    def is_valid(self) -> Tuple[bool, Optional[str]]:
        if len(self.materials) == 0:
            return (False, "There are no materials in the material set.")

        any_target_unassigned = any(item.target is None for item in self.materials)

        if any_target_unassigned:
            return (False, "One or more target objects are unassigned.")

        targets_too_many_mat_slots = [item.target.name for item in self.materials if len(item.target.material_slots) > 1]

        if len(targets_too_many_mat_slots) > 0:
            return (False, f"Each target object can only have one material slot. These objects have multiple: {StringUtil.join_with_commas(targets_too_many_mat_slots)}")

        if self.mode == "shared" and self.shared_material is None:
            return (False, "Shared material has not been assigned.")

        if self.mode == "individual":
            any_material_unassigned = any(item.material is None for item in self.materials)

            if any_material_unassigned:
                return (False, "One or more materials are unassigned.")

        # Check for the same target referenced multiple times
        unique_targets = { item.target for item in self.materials }

        if len(unique_targets) != len(self.materials):
            return (False, "One or more targets is repeated in the material set. Remove any duplicates.")

        return (True, None)

    def material_at(self, index: int) -> Optional[bpy.types.Material]:
        assert 0 <= index < len(self.materials)

        return self.materials[index].material if self.mode == "individual" else self.shared_material

class RenderTargetPropertyGroup(bpy.types.PropertyGroup):

    def _on_target_mesh_updated(self, _context):
        #pylint: disable=invalid-name

        # Sync up the mesh_object property for convenience
        self.mesh_object = None if self.mesh is None else utils.find_object_data_for_mesh(self.mesh)
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
    animation_sets: bpy.props.CollectionProperty(type = AnimationSetPropertyGroup)

    control_animations: bpy.props.BoolProperty(
        name = "Control Animations",
        description = "If true, the Render Targets will be animated while rendering, with one sprite being emitted per frame of animation",
        default = False
    )

    ### Materials data
    material_sets: bpy.props.CollectionProperty(type = MaterialSetPropertyGroup)

    control_materials: bpy.props.BoolProperty(
        name = "Control Materials",
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

    render_camera_obj: bpy.props.PointerProperty(type = bpy.types.Object) # Automatically set; not for users

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
    # TODO: add targets in camera and rotations and get rid of render targets completely
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