import bpy

def _get_camera_control_mode_options(self, context):
    #pylint: disable=unused-argument
    props = context.scene.SpritesheetPropertyGroup

    items = [
        ("move_once", "Fit All Frames", "The camera will be adjusted once before any rendering is done, so that the entire spritesheet is rendered from the same camera perspective.", 0),
        ("move_each_frame", "Fit Each Frame", "The camera will be adjusted before every render frame to fit the Target Object. Note that this will prevent the appearance of movement in the spritesheet.", 1)
    ]

    if props.useAnimations:
        items.append(("move_each_animation", "Fit Each Animation", "The camera will be adjusted at the start of each animation, so that the entire animation is rendered without subsequently moving the camera.", 2))

    if props.rotateObject:
        items.append(("move_each_rotation", "Fit Each Rotation", "The camera will be adjusted every time the Target Object is rotated, so that all frames for the rotation (including animations if enabled) " +
                                                                 "are rendered without subsequently moving the camera.", 3))

    return items

def _get_camera_control_mode(self):
    val = self.get("cameraControlMode")

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
    self["cameraControlMode"] = value

def get_material_name_options(self, context):
    #pylint: disable=unused-argument
    items = []

    for material in bpy.data.materials:
        items.append( (material.name, material.name, "") )

    return items

class AnimationSelectionPropertyGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name = "Action Name",
        default = ""
    )

    isSelectedForExport: bpy.props.BoolProperty(
        name = "", # Force no name when rendering
        default = True
    )

    numFrames: bpy.props.IntProperty()

class MaterialSelectionPropertyGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name = "Material",
        default = ""
    )

    index: bpy.props.IntProperty(
        name = "Index"
    )

    isSelectedForExport: bpy.props.BoolProperty(
        name = "", # Force no name when rendering
        default = True
    )

    role: bpy.props.EnumProperty(
        name = "",
        description = "How this material is used. Does not impact the rendered images, but is included in output metadata for import to other programs",
        items = [
            ("albedo", "Albedo/Base Color", "This material provides the albedo, or base color, of the object."),
            ("mask_unity", "Mask (Unity)", "This material is a Unity mask texture, where the red channel is metallic, green is occlusion, blue is the detail mask, and alpha is smoothness."),
            ("normal_unity", "Normal (Unity)", "This material is a normal map for use in Unity (tangent space, Y+)."),
            ("other", "Other", "Any use not fitting the options above.")
        ]
    )

class ObjectMaterialPairPropertyGroup(bpy.types.PropertyGroup):
    materialName: bpy.props.EnumProperty(
        name = "Material Name",
        description = "Which material will be applied to this object while this material set is rendering.",
        items = get_material_name_options
    )

class MaterialSetPropertyGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name = "Set Name",
        description = "(Optional) A user-friendly name you can supply to help you keep track of your material sets"
    )

    role: bpy.props.EnumProperty(
        name = "Role",
        description = "How this material set is used. Does not impact the rendered images, but is included in output metadata for import to other programs",
        items = [
            ("albedo", "Albedo/Base Color", "This material provides the albedo, or base color, of the object."),
            ("mask_unity", "Mask (Unity)", "This material is a Unity mask texture, where the red channel is metallic, green is occlusion, blue is the detail mask, and alpha is smoothness."),
            ("normal_unity", "Normal (Unity)", "This material is a normal map for use in Unity (tangent space, Y+)."),
            ("other", "Other", "Any use not fitting the options above.")
        ]
    )

    objectMaterialPairs: bpy.props.CollectionProperty(type = ObjectMaterialPairPropertyGroup)

    selectedObjectMaterialPair: bpy.props.IntProperty(
        get = lambda self: -1 # dummy getter and no setter means items in the list can't be selected
    )

class RenderTargetPropertyGroup(bpy.types.PropertyGroup):

    def _on_target_object_updated(self, context):
        #pylint: disable=invalid-name

        # When selecting an object for the first time, auto-detect its associated material and assign it
        # in all of the material sets, for convenience; also set its rotation root to itself
        if self.previousObject is None and self.object is not None and hasattr(self.object.data, "materials") and len(self.object.data.materials) > 0:
            props = context.scene.SpritesheetPropertyGroup

            self.rotationRoot = self.object

            # Figure out which index this object is, because it's the same in the material sets
            index = list(props.targetObjects).index(self)

            for material_set in props.materialSets:
                material_set.objectMaterialPairs[index].materialName = self.object.data.materials[0].name

        self.previousObject = self.object

    object: bpy.props.PointerProperty(
        name = "Render Target",
        description = "An object to be rendered into the spritesheet",
        type = bpy.types.Object,
        update = _on_target_object_updated
    )

    previousObject: bpy.props.PointerProperty(
        type = bpy.types.Object
    )

    rotationRoot: bpy.props.PointerProperty(
        name = "Rotation Root",
        description = "If 'Rotate Object' is set, this object will be rotated instead of the Render Target. This is useful for parent objects or armatures. If unset, the Render Target is rotated",
        type = bpy.types.Object
    )

class ReportingPropertyGroup(bpy.types.PropertyGroup):
    currentFrameNum: bpy.props.IntProperty() # which frame we are currently rendering

    elapsedTime: bpy.props.FloatProperty() # how much time has elapsed in the current job, in seconds

    hasAnyJobStarted: bpy.props.BoolProperty() # whether any job has started in the current session

    jobInProgress: bpy.props.BoolProperty() # whether a job is running right now

    lastErrorMessage: bpy.props.StringProperty() # the last error reported by a job (generally job-ending)

    outputDirectory: bpy.props.StringProperty() # the absolute path of the directory of the final spritesheet/JSON output

    outputToTerminal: bpy.props.BoolProperty(
        name = "Terminal",
        description = "If true, render jobs will print job progress to the system console (stdout)",
        default = False
    )

    outputToUI: bpy.props.BoolProperty(
        name = "UI",
        description = "If true, render jobs will print job progress in the Job Management panel",
        default = True
    )

    systemType: bpy.props.EnumProperty( # what kind of file explorer is available on this system
        items = [
            ("unchecked",  "", ""),
            ("unknown", "", ""),
            ("windows", "", "")
        ]
    )

    totalNumFrames: bpy.props.IntProperty() # the total number of frames which will be rendered

    def estimated_time_remaining(self):
        if self.currentFrameNum == 0 or self.totalNumFrames == 0:
            return None

        # This isn't fully accurate since we have some time-consuming tasks regardless of the number of
        # frames, but render time is the vast majority of any substantial job, so close enough
        time_per_frame = self.elapsedTime / self.currentFrameNum
        return (self.totalNumFrames - self.currentFrameNum) * time_per_frame

class SpritesheetPropertyGroup(bpy.types.PropertyGroup):
    """Property group for spritesheet rendering configuration"""

    #### Animation data
    activeAnimationSelectionIndex: bpy.props.IntProperty()

    animationSelections: bpy.props.CollectionProperty(type = AnimationSelectionPropertyGroup)

    outputFrameRate: bpy.props.IntProperty(
        name = "Output Frame Rate",
        description = "The frame rate of the animation in the spritesheet",
        default = 24,
        min = 1
    )

    useAnimations: bpy.props.BoolProperty(
        name = "Animate During Render",
        description = "If true, the Target Object will be animated during rendering",
        default = False
    )

    ### Materials data
    activeMaterialSelectionIndex: bpy.props.IntProperty() # TODO delete

    materialSelections: bpy.props.CollectionProperty(type = MaterialSelectionPropertyGroup) # TODO delete

    materialSets: bpy.props.CollectionProperty(type = MaterialSetPropertyGroup)

    selectedMaterialSetIndex: bpy.props.IntProperty()

    useMaterials: bpy.props.BoolProperty(
        name = "Render Multiple Materials",
        description = "If true, the target object will be rendered once for each selected material",
        default = False
    )

    ### Render properties
    controlCamera: bpy.props.BoolProperty(
        name = "Control Camera",
        description = "If true, the Render Camera will be moved and adjusted to best fit the Target Object in view",
        default = False
    )

    cameraControlMode: bpy.props.EnumProperty(
        name = "Control Style",
        description = "How to control the Render Camera",
        items = _get_camera_control_mode_options,
        get = _get_camera_control_mode,
        set = _set_camera_control_mode
    )

    rotateObject: bpy.props.BoolProperty(
        name = "Rotate Objects",
        description = "Whether to rotate the target objects. All objects will be rotated simultaneously, but you may choose an object to rotate each around (such as a parent or armature)"
    )

    rotationNumber: bpy.props.IntProperty(
        name = "Total Angles",
        description = "How many rotations to perform",
        default = 8,
        min = 2
    )

    rotationRoot: bpy.props.PointerProperty( # TODO delete
        name = "",
        description = "Which object to apply rotation to, useful e.g. with armatures. If left empty, rotations will be applied to Target Object",
        type = bpy.types.Object
    )

    ### Scene properties
    # TODO restrict this to camera objects, using the camera's name to look up the object
    renderCamera: bpy.props.PointerProperty(
        name = "Render Camera",
        description = "The camera to use for rendering; defaults to the scene's camera if unset",
        type = bpy.types.Object
    )

    targetObject: bpy.props.PointerProperty(
        name = "Target Object",
        description = "The object which will be animated and rendered into the spritesheet",
        type = bpy.types.Object
    )

    targetObjects: bpy.props.CollectionProperty(
        name = "Render Targets",
        type = RenderTargetPropertyGroup
    )

    selectedTargetObjectIndex: bpy.props.IntProperty()

    selectedRotationRootIndex: bpy.props.IntProperty(
        get = lambda self: -1
    )

    ### Output file properties
    padToPowerOfTwo: bpy.props.BoolProperty(
        name = "Pad to Power-of-Two",
        description = "If true, all output images will be padded with transparent pixels to the smallest power-of-two size that can fit the original output",
        default = True
    )

    separateFilesPerAnimation: bpy.props.BoolProperty(
        name = "Separate Files Per Animation",
        description = "If 'Control Animations' is enabled, this will generate one output file per animation action. Otherwise, all actions will be combined in a single file",
        default = False
    )

    separateFilesPerMaterial: bpy.props.BoolProperty(
        name = "Separate Files Per Material Set",
        description = "If 'Control Materials' is enabled, this will generate one output file per material set. This cannot be disabled",
        default = True
    )

    separateFilesPerRotation: bpy.props.BoolProperty(
        name = "Separate Files Per Rotation",
        description = "If 'Rotate During Render' is enabled, this will generate one output file per rotation option",
        default = False
    )

    spriteSize: bpy.props.IntVectorProperty(
        name = "Sprite Size",
        description = "How large each individual sprite should be",
        default = (128, 128),
        min = 16,
        size = 2
    )