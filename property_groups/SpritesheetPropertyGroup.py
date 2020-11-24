import bpy

class AnimationSelectionPropertyGroup(bpy.types.PropertyGroup):
    """   """
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
    """"""
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
            ("other", "Other", "Any use not fitting the options above")
        ]
    )

def GetCameraControlModeOptions(self, context):
    props = context.scene.SpritesheetPropertyGroup

    items = [
        ("move_once", "Fit All Frames", "The camera will be adjusted once before any rendering is done, so that the entire spritesheet is rendered from the same camera perspective.", 0),
        ("move_each_frame", "Fit Each Frame", "The camera will be adjusted before every render frame to fit the Target Object. Note that this will prevent the appearance of movement in the spritesheet.", 1)
    ]

    if props.useAnimations:
        items.append(("move_each_animation", "Fit Each Animation", "The camera will be adjusted at the start of each animation, so that the entire animation is rendered without subsequently moving the camera.", 2))

    if props.rotateObject:
        items.append(("move_each_rotation", "Fit Each Rotation", "The camera will be adjusted every time the Target Object is rotated, so that all frames for the rotation (including animations if enabled) are rendered without subsequently moving the camera.", 3))

    return items

def getCameraControlMode(self):
    items = GetCameraControlModeOptions(self, bpy.context)

    val = self.get("cameraControlMode")
    if val is not None:
        # Make sure the chosen value still exists in our list
        isValid = any(item[3] == val for item in items)

        if not isValid:
            val = 0 # default to moving once

    return val

def setCameraControlMode(self, value):
    self["cameraControlMode"] = value

class ReportingPropertyGroup(bpy.types.PropertyGroup):
    currentFrameNum: bpy.props.IntProperty()

    elapsedTime: bpy.props.FloatProperty()

    fileExplorerType: bpy.props.EnumProperty(
        items = [
            ("unknown",  "", ""),
            ("none", "", ""),
            ("windows", "", "")
        ]
    )

    hasAnyJobStarted: bpy.props.BoolProperty() # whether any job has started in the current session

    jobInProgress: bpy.props.BoolProperty()

    lastErrorMessage: bpy.props.StringProperty()

    outputDirectory: bpy.props.StringProperty()

    totalNumFrames: bpy.props.IntProperty()

    def estimatedTimeRemaining(self):
        if self.currentFrameNum == 0 or self.totalNumFrames == 0:
            return None

        timePerFrame = self.elapsedTime / self.currentFrameNum
        return (self.totalNumFrames - self.currentFrameNum) * timePerFrame

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
        default = True
    )

    ### Materials data
    activeMaterialSelectionIndex: bpy.props.IntProperty()
    
    materialSelections: bpy.props.CollectionProperty(type = MaterialSelectionPropertyGroup)

    useMaterials: bpy.props.BoolProperty(
        name = "Render Multiple Materials",
        description = "If true, the target object will be rendered once for each selected material",
        default = True
    )
    
    ### Render properties
    controlCamera: bpy.props.BoolProperty(
        name = "Control Camera",
        description = "If true, the Render Camera will be moved and adjusted to best fit the Target Object in view",
        default = True
    )

    cameraControlMode: bpy.props.EnumProperty(
        name = "",
        description = "How to control the Render Camera",
        items = GetCameraControlModeOptions,
        get = getCameraControlMode,
        set = setCameraControlMode
    )

    padToPowerOfTwo: bpy.props.BoolProperty(
        name = "Force Power-of-Two Output",
        description = "If true, all output images will be padded with transparent pixels to the smallest power-of-two size that can fit the original output",
        default = True
    )

    rotateObject: bpy.props.BoolProperty(
        name = "Rotate Object",
        description = "Whether to rotate the object. If true, there will be multiple output spritesheets, one for each rotation"
    )
    
    rotationNumber: bpy.props.IntProperty(
        name = "Total Angles",
        description = "How many rotations to perform",
        default = 8,
        min = 2
    )

    rotationRoot: bpy.props.PointerProperty(
        name = "",
        description = "Which object to apply rotation to, useful e.g. with armatures. If left empty, rotations will be applied to Target Object",
        type = bpy.types.Object
    )
    
    spriteSize: bpy.props.IntVectorProperty(
        name = "Sprite Size",
        description = "How large each individual sprite should be",
        default = (64, 64),
        min = 16,
        size = 2
    )

    ### Scene properties
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

    ### Output file properties
    separateFilesPerAnimation: bpy.props.BoolProperty(
        name = "Separate Files Per Animation",
        description = "If 'Animate During Render' is enabled, this will generate one output file per animation action. Otherwise, all actions will be combined in a single file",
        default = False
    )

    separateFilesPerMaterial: bpy.props.BoolProperty(
        name = "Separate Files Per Material",
        description = "If 'Render Multiple Materials' is enabled, this will generate one output file per material. This cannot be disabled",
        default = True
    )

    separateFilesPerRotation: bpy.props.BoolProperty(
        name = "Separate Files Per Rotation",
        description = "If 'Rotate During Render' is enabled, this will generate one output file per rotation option",
        default = True
    )
