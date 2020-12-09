import bpy
import collections
import json
import math
import os
import pathlib
import sys
import tempfile
import time
import traceback
from typing import Any, Dict, Generator, List, Optional, Tuple

import preferences

from property_groups import MaterialSetPropertyGroup, ReportingPropertyGroup, SpritesheetPropertyGroup
from util import Camera as CameraUtil
from util import ImageMagick
from util.TerminalOutput import TerminalWriter
from util.SceneSnapshot import SceneSnapshot
from util import StringUtil
import utils

class SPRITESHEET_OT_RenderSpritesheetOperator(bpy.types.Operator):
    """Operator for executing spritesheet rendering. This is a modal operator which is expected to run for a long time."""
    bl_idname = "spritesheet.render"
    bl_label = "Render Spritesheet"
    bl_description = "Render a spritesheet according to the input settings"

    renderDisabledReason = ""

    @classmethod
    def poll(cls, context):
        # For some reason, if an error occurs in this method, Blender won't report it.
        # So the whole thing is wrapped in a try/except block so we can know what happened.
        try:
            validators = [
                cls._validate_image_magick_install,
                cls._validate_render_targets,
                cls._validate_animation_options,
                cls._validate_camera_options,
                cls._validate_material_options
            ]

            for validator in validators:
                is_valid, cls.renderDisabledReason = validator(context)

                if not is_valid:
                    return False

            cls.renderDisabledReason = ""
            return True
        except:
            traceback.print_exc()
            return False

    @classmethod
    def _validate_animation_options(cls, context: bpy.types.Context) -> Tuple[bool, Optional[str]]:
        props = context.scene.SpritesheetPropertyGroup

        if not props.control_animations:
            return (True, None)

        if all(not target.mesh_object.animation_data for target in props.render_targets):
            return (False, "'Control Animations' is enabled, but none of the Render Targets have animation data.")

        enabled_action_selections = [a for a in props.animation_selections if a.is_selected_for_export]

        if len(enabled_action_selections) == 0:
            return (False, "'Control Animations' is enabled, but no animations have been selected for use.")

        return (True, None)

    @classmethod
    def _validate_camera_options(cls, context: bpy.types.Context) -> Tuple[bool, Optional[str]]:
        props = context.scene.SpritesheetPropertyGroup

        if not props.control_camera:
            return (True, None)

        if not props.render_camera:
            return (False, "'Control Camera' is enabled, but Render Camera is not set.")

        if props.render_camera.type != "ORTHO":
            return (False, "'Control Camera' is currently only supported for orthographic cameras.")

        return (True, None)

    @classmethod
    def _validate_image_magick_install(cls, _context: bpy.types.Context) -> Tuple[bool, Optional[str]]:
        if not preferences.PrefsAccess.image_magick_path:
            return (False, "ImageMagick path is not set in Addon Preferences.")

        return (True, None)

    @classmethod
    def _validate_material_options(cls, context: bpy.types.Context) -> Tuple[bool, Optional[str]]:
        props = context.scene.SpritesheetPropertyGroup

        if not props.control_materials:
            return (True, None)

        if len(props.material_sets) == 0:
            return (False, "'Control Materials' is enabled, but no material sets have been created.")

        # Check that each material set role is only used once, except for Other
        material_sets_by_role: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
        for set_index, material_set in enumerate(props.material_sets):
            material_sets_by_role[material_set.role].append({ "index": set_index, "set": material_set })

            # While we're already iterating the sets, make sure all the materials are assigned
            if material_set.mode == "individual":
                for object_mat_pair in material_set.materials:
                    if object_mat_pair.material is None:
                        return (False, f"One or more materials has not been assigned in Material Set {set_index + 1} - {material_set.name}.")
            elif material_set.mode == "shared" and material_set.shared_material is None:
                return (False, f"The shared material has not been assigned in Material Set {set_index + 1} - {material_set.name}.")

        for role, sets in material_sets_by_role.items():
            if len(sets) > 1 and role != "other":
                role_name = utils.enum_display_name_from_identifier(sets[0]["set"], "role", role)
                set_indices = StringUtil.join_with_commas([str(set_tuple["index"] + 1) for set_tuple in sets])
                return (False, f"There are {len(sets)} material sets ({set_indices}) using the role '{role_name}'. This role can only be used once.")

        # Check each render target's material slots
        for index, target in enumerate(props.render_targets):
            num_material_slots = len(target.mesh.materials)
            if num_material_slots > 1:
                return (False, f"If 'Control Materials' is enabled, each Render Target must have exactly 1 material slot. Mesh #{index + 1} (\"{target.mesh.name}\") has {num_material_slots}. "
                              + "(You may need to select child meshes instead, or split your mesh by material.)")

            if num_material_slots == 0:
                return (False, f"If 'Control Materials' is enabled, each Render Target must have exactly 1 material slot. Mesh #{index + 1} (\"{target.mesh.name}\") has none.")

        return (True, None)

    @classmethod
    def _validate_render_targets(cls, context: bpy.types.Context) -> Tuple[bool, Optional[str]]:
        props = context.scene.SpritesheetPropertyGroup

        if not props.render_targets or len(props.render_targets) == 0:
            return (False, "There are no Render Targets set.")

        for index, o in enumerate(props.render_targets):
            obj = o.mesh_object

            if obj is None:
                return (False, f"Target Mesh slot #{index + 1} has no mesh selected. If unwanted, remove the slot.")

        # Check if any mesh is selected twice
        seen_meshes = []

        for target in props.render_targets:
            if target.mesh in seen_meshes:
                return (False, f"Mesh \"{target.mesh.name}\" is referenced more than once in Render Targets.")

            seen_meshes.append(target.mesh)

        return (True, None)

    def invoke(self, context, _event):
        reporting_props = context.scene.ReportingPropertyGroup

        self._json_data: Dict[str, Any] = {}
        self._output_dir: Optional[str] = None
        self._error: Optional[str]  = None
        self._last_job_id: int = -1
        self._last_job_start_time: Optional[float] = None
        self._next_job_id: int = 0
        self._scene_snapshot: SceneSnapshot = SceneSnapshot(context)
        self._start_time: float = time.clock()
        self._terminal_writer: TerminalWriter = TerminalWriter(sys.stdout, not reporting_props.output_to_terminal)

        # Execute generator a single time to set up all reporting properties and validate config; this won't render anything yet
        self._generator: Generator[None, None, None] = self._generate_frames_and_spritesheets(context)
        next(self._generator)

        self.execute(context)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        reporting_props = context.scene.ReportingPropertyGroup
        reporting_props.elapsed_time = time.clock() - self._start_time

        if event.type in {"ESC"}:
            self._error = "Job cancelled by request of user"
            self.cancel(context)
            return {"CANCELLED"}

        if event.type != "TIMER":
            return {"PASS_THROUGH"} # ignore non-timer events

        # Check if the generator is done (i.e. we're finished rendering)
        sentinel = object()
        if next(self._generator, sentinel) == sentinel and not self._error:
            self.cancel(context)
            return {"FINISHED"}

        # Check if error flag has been set
        if self._error:
            self.cancel(context)
            return {"CANCELLED"}

        # If it's not done and there's no error, then we're continuing; leave this event for others to handle if needed
        return {"PASS_THROUGH"}

    def execute(self, context):
        reporting_props = context.scene.ReportingPropertyGroup
        wm = context.window_manager

        self._timer = wm.event_timer_add(0.25, window = context.window)
        wm.modal_handler_add(self)

        reporting_props.has_any_job_started = True
        reporting_props.job_in_progress = True
        reporting_props.output_directory = self._base_output_dir()

    def cancel(self, context):
        reporting_props = context.scene.ReportingPropertyGroup
        reporting_props.last_error_message = self._error if self._error else ""
        reporting_props.job_in_progress = False

        context.window_manager.event_timer_remove(self._timer)

        if self._error:
            self._terminal_writer.indent = 0
            self._terminal_writer.write("\n\nError occurred, cancelling operator: {}\n\n".format(self._error))
            self.report({'ERROR'}, self._error)

    def _generate_frames_and_spritesheets(self, context: bpy.types.Context) -> Generator[None, None, None]:
        #pylint: disable=too-many-branches
        #pylint: disable=too-many-statements
        scene = context.scene
        props = scene.SpritesheetPropertyGroup
        reporting_props = scene.ReportingPropertyGroup

        reporting_props.current_frame_num = 0
        reporting_props.total_num_frames = 0

        self._terminal_writer.write("\n\n---------- Starting spritesheet render job ----------\n\n")

        try:
            succeeded, error = ImageMagick.validate_image_magick_at_path()
            if not succeeded:
                self._error = "ImageMagick check failed\n" + error
                return
        except:
            self._error = "Failed to validate ImageMagick executable. Check that the path is correct in Addon Preferences."
            return

        self._set_render_settings(context)
        self._terminal_writer.clear()

        if props.control_camera:
            scene.camera = props.render_camera_obj

        enabled_actions: List[Optional[bpy.types.Action]]
        separate_files_per_animation: bool
        if props.control_animations:
            enabled_actions = [bpy.data.actions.get(a.name) for a in props.animation_selections if a.is_selected_for_export]
            separate_files_per_animation = props.separate_files_per_animation
        else:
            enabled_actions = [None]
            separate_files_per_animation = False

        material_sets = props.material_sets if props.control_materials else [None]

        # TODO there's no reason the rotation couldn't be float, except for determining the output file name
        rotations: List[int]
        separate_files_per_rotation: bool
        if props.control_rotation:
            rotations = [int(n * (360 / props.num_rotations)) for n in range(props.num_rotations)]
            separate_files_per_rotation = props.separate_files_per_rotation
        else:
            rotations = [None]
            separate_files_per_rotation = False

        # Variables for progress tracking
        material_number = 0
        num_expected_json_files = (len(rotations) if props.separate_files_per_rotation else 1) * (len(enabled_actions) if props.separate_files_per_animation else 1) # materials never result in separate JSON files

        reporting_props.total_num_frames = self._count_total_frames(material_sets, rotations, enabled_actions)
        self._terminal_writer.write("Expecting to render a total of {} frames\n".format(reporting_props.total_num_frames))

        if separate_files_per_animation:
            output_mode = "per animation"
        elif separate_files_per_rotation:
            output_mode = "per rotation"
        else:
            output_mode = "per material"

        self._terminal_writer.write("File output will be generated {}\n\n".format(output_mode))

        # We yield once before modifying the scene at all, so that all of the reporting properties are set up
        yield

        if props.control_camera and props.camera_control_mode == "move_once":
            self._optimize_camera(context, rotations = rotations, enabled_actions = enabled_actions)

        self._terminal_writer.write("\n")

        frames_since_last_output = 0

        for material_set_index, material_set in enumerate(material_sets):
            material_number += 1
            material_set_name = material_set.name if material_set else "N/A"
            render_data = []
            temp_dir = tempfile.TemporaryDirectory()

            self._terminal_writer.write("Rendering material set {} of {}: \"{}\"\n".format(material_number, len(material_sets), material_set_name))
            self._terminal_writer.indent += 1

            if material_set is not None:
                self._assign_materials_from_set(context, material_set)

            rotation_number = 0
            for rotation_angle in rotations:
                rotation_number += 1
                action_number = 0

                self._terminal_writer.write("Rendering angle {} of {}: {} degrees\n".format(rotation_number, len(rotations), rotation_angle))
                self._terminal_writer.indent += 1

                if props.control_rotation:
                    self._rotate_target_objects(context, rotation_angle)

                if props.control_camera and props.camera_control_mode == "move_each_rotation":
                    self._optimize_camera(context, rotations = rotations, enabled_actions = enabled_actions, current_rotation = rotation_angle)

                temp_dir_path = temp_dir.name

                for action in enabled_actions:
                    action_number += 1

                    if action is not None:
                        self._terminal_writer.write("Processing action {} of {}: \"{}\"\n".format(action_number, len(enabled_actions), action.name))
                        self._terminal_writer.indent += 1

                        # Yield after each frame of the animation to update the UI
                        for val in self._render_action(context, action, rotation_angle, temp_dir_path):
                            action_data = val
                            yield

                        render_data.append(action_data)
                        frames_since_last_output += action_data["numFrames"]

                        # Combine sprites now if files are being split by animation, so we can wipe out all the per-frame
                        # files before processing the next animation
                        if separate_files_per_animation:
                            self._terminal_writer.write("\nCombining image files for action {} of {}\n".format(action_number, len(enabled_actions)))
                            image_magick_result = self._run_image_magick(props, reporting_props, material_set_index, action, frames_since_last_output, temp_dir_path, rotation_angle)

                            if not image_magick_result["succeeded"]: # error running ImageMagick
                                return

                            self._create_json_file(props, reporting_props, material_sets, render_data, image_magick_result)
                            self._terminal_writer.write("\n")

                            frames_since_last_output = 0
                            render_data = []
                            temp_dir = tempfile.TemporaryDirectory() # change directories for per-frame files

                        self._terminal_writer.indent -= 1
                    else:
                        still_data = self._render_still(context, rotation_angle, frames_since_last_output, temp_dir_path)
                        render_data.append(still_data)
                        frames_since_last_output += 1

                        yield

                    # End of for(actions)

                if separate_files_per_rotation and not separate_files_per_animation:
                    self._terminal_writer.write("\nCombining image files for angle {} of {}\n".format(rotation_number, len(rotations)))
                    self._terminal_writer.indent += 1

                    # Output one file for the whole rotation, with all animations in it
                    image_magick_result = self._run_image_magick(props, reporting_props, material_set_index, None, frames_since_last_output, temp_dir_path, rotation_angle)

                    if not image_magick_result["succeeded"]: # error running ImageMagick
                        return

                    self._create_json_file(props, reporting_props, material_sets, render_data, image_magick_result)
                    self._terminal_writer.write("\n")
                    self._terminal_writer.indent -= 1

                    frames_since_last_output = 0
                    render_data = []
                    temp_dir = tempfile.TemporaryDirectory() # change directories for per-frame files

                self._terminal_writer.indent -= 1

                # End of for(rotations)

            if not separate_files_per_rotation and not separate_files_per_animation:
                self._terminal_writer.write("\nCombining image files for material set {} of {}\n".format(material_number, len(material_sets)))
                self._terminal_writer.indent += 1

                # Output one file for the entire material
                image_magick_result = self._run_image_magick(props, reporting_props, material_set_index, None, frames_since_last_output, temp_dir_path, None)

                if not image_magick_result["succeeded"]: # error running ImageMagick
                    return

                self._create_json_file(props, reporting_props, material_sets, render_data, image_magick_result)
                self._terminal_writer.write("\n")
                self._terminal_writer.indent -= 1

                frames_since_last_output = 0
                render_data = []
                temp_dir = tempfile.TemporaryDirectory() # change directories for per-frame files

            self._terminal_writer.indent -= 1

            # End of for(materials)

        # Reset scene variables to their original state
        self._scene_snapshot.restore_from_snapshot(context)

        # Do some sanity checks and modify the final output based on the result
        sanity_checks_passed = self._perform_ending_sanity_checks(num_expected_json_files, reporting_props)
        total_elapsed_time = time.clock() - self._start_time
        time_string = StringUtil.time_as_string(total_elapsed_time)

        completion_message = "Rendering complete in " + time_string if sanity_checks_passed else "Rendering FAILED after " + time_string

        # Final output: show operator total time and a large completion message to be easily noticed
        term_size = os.get_terminal_size()
        self._terminal_writer.write("\n")
        self._terminal_writer.write(term_size.columns * "=" + "\n")
        self._terminal_writer.write( (term_size.columns // 2) * " " + completion_message + "\n")
        self._terminal_writer.write(term_size.columns * "=" + "\n\n")

        return

    def _assign_materials_from_set(self, context: bpy.types.Context, material_set: MaterialSetPropertyGroup):
        props = context.scene.SpritesheetPropertyGroup

        for index, target in enumerate(props.render_targets):
            material: bpy.types.Material

            if material_set.mode == "individual":
                # Indices match between objects and their entries in the material set
                material = material_set.materials[index].material
            elif material_set.mode == "shared":
                material = material_set.shared_material

            target.mesh.materials[0] = material

    def _base_output_dir(self) -> str:
        if bpy.data.filepath:
            out_dir = os.path.dirname(bpy.data.filepath)
            return os.path.join(out_dir, "Rendered spritesheets")

        # Use the user's home directory
        return os.path.join(str(pathlib.Path.home()), "Rendered spritesheets")

    def _create_file_path(self, props: SpritesheetPropertyGroup, material_set_index: int, action: bpy.types.Action, rotation_angle: int, include_material_set: bool = True) -> str:
        if bpy.data.filepath:
            filename, _ = os.path.splitext(os.path.basename(bpy.data.filepath))
        else:
            filename = "spritesheet"

        output_file_path = os.path.join(self._base_output_dir(), filename)

        # Make sure output directory exists
        pathlib.Path(os.path.dirname(output_file_path)).mkdir(exist_ok = True)

        material_set = props.material_sets[material_set_index]
        if include_material_set and material_set is not None:
            # Possible TODO: only include index if necessary (i.e. multiple material sets have the same role). Pretty low priority
            output_file_path += "_" + self._format_string_for_filename(material_set.role) + "_" + str(material_set_index)

        if props.control_animations and props.separate_files_per_animation:
            output_file_path += "_" + self._format_string_for_filename(action.name)

        if props.control_rotation and props.separate_files_per_rotation:
            output_file_path += "_rot" + str(rotation_angle).zfill(3)

        return output_file_path

    def _create_json_file(self, props: SpritesheetPropertyGroup, reporting_props: ReportingPropertyGroup, material_sets: List[MaterialSetPropertyGroup], render_data: Dict[str, Any], image_magick_data: Dict[str, Any]):
        job_id = self._get_next_job_id()
        self._report_job("JSON dump", "writing JSON attributes", job_id, reporting_props)

        # Action and rotation are the same for each record if using separate files, so just grab the first value
        action: Optional[bpy.types.Action] = render_data[0]["action"] if props.control_animations and props.separate_files_per_animation else None
        rotation: Optional[int] = render_data[0]["rotation"] if props.control_rotation and props.separate_files_per_rotation else None

        json_file_path = self._create_file_path(props, 0, action, rotation, include_material_set = False) + ".ssdata"

        # Since the material isn't part of the file path, we could end up writing each JSON file multiple times.
        # They all have the same data, so just skip writing if that's the case.
        if json_file_path in self._json_data:
            self._report_job("JSON dump", "JSON file already written at " + json_file_path, job_id, reporting_props, is_skipped = True)
            return

        padding: Tuple[int, int] = image_magick_data["args"]["padding"] if "padding" in image_magick_data["args"] else (0, 0)

        json_data = {
            "baseObjectName": utils.blend_file_name(default_value = "object"),
            "spriteWidth": props.sprite_size[0],
            "spriteHeight": props.sprite_size[1],
            "paddingWidth": padding[0],
            "paddingHeight": padding[1],
            "numColumns": image_magick_data["args"]["numColumns"],
            "numRows": image_magick_data["args"]["numRows"]
        }

        if props.control_materials:
            # If using materials, need to reference where the spritesheet for each material is located
            json_data["materialData"] = []

            for index, material_set in enumerate(material_sets):
                image_path = self._create_file_path(props, index, action, rotation) + ".png"
                self._output_dir = os.path.dirname(image_path)
                relative_path = os.path.basename(image_path)

                json_data["materialData"].append({
                    "name": material_set.name,
                    "file": relative_path,
                    "role": material_set.role
                })
        else:
            # When not using materials, there's only one image file per JSON file
            image_path = self._create_file_path(props, 0, action, rotation, include_material_set = False) + ".png"
            self._output_dir = os.path.dirname(image_path)

            json_data["imageFile"] = os.path.basename(image_path)

        if props.control_animations:
            json_data["animations"] = []
        else:
            json_data["stills"] = []

        for in_data in render_data:
            out_data = { }

            # Animation data (if present)
            if props.control_animations:
                assert "action" in in_data, "props.control_animations is enabled, but data object didn't have 'action' key"

                out_data["frameRate"] = props.output_frame_rate # the same for all animations, but may not always be
                out_data["name"] = in_data["action"].name
                out_data["numFrames"] = in_data["numFrames"]
                out_data["rotation"] = in_data["rotation"]

                # The starting frame may not match the expected value, depending on what order ImageMagick combined
                # the files in. We need to find the matching file in the ImageMagick arguments to figure out the frame number.
                out_data["startFrame"] = image_magick_data["args"]["inputFiles"].index(in_data["firstFrameFilepath"])

                json_data["animations"].append(out_data)
            else:
                out_data["frame"] = image_magick_data["args"]["inputFiles"].index(in_data["filepath"])
                out_data["rotation"] = in_data["rotation"]

                json_data["stills"].append(out_data)

        with open(json_file_path, "w") as f:
            json.dump(json_data, f, indent = "\t")

        self._json_data[json_file_path] = json_data
        self._report_job("JSON dump", "output is at " + json_file_path, job_id, reporting_props, is_complete = True)

    def _count_total_frames(self, material_sets: List[MaterialSetPropertyGroup], rotations: List[int], actions: List[bpy.types.Action]) -> int:
        total_frames_across_actions = 0

        for action in actions:
            if action is None:
                total_frames_across_actions += 1
            else:
                frame_min = math.floor(action.frame_range[0])
                frame_max = math.ceil(action.frame_range[1])
                num_frames = frame_max - frame_min + 1
                total_frames_across_actions += num_frames

        return total_frames_across_actions * len(material_sets) * len(rotations)

    def _format_string_for_filename(self, string: str) -> str:
        return string.replace(' ', '_').lower()

    def _get_next_job_id(self) -> int:
        self._next_job_id += 1
        return self._next_job_id

    def _next_power_of_two(self, val: int) -> int:
        """Returns the smallest power of two which is equal to or greater than val"""
        return 1 if val == 0 else 2 ** math.ceil(math.log2(val))

    def _optimize_camera(self, context: bpy.types.Context, rotations = None, enabled_actions = None, current_action: Optional[bpy.types.Action] = None, current_rotation: Optional[int] = None, report_job: bool = True):
        props = context.scene.SpritesheetPropertyGroup
        reporting_props = context.scene.ReportingPropertyGroup

        if not props.control_camera:
            raise RuntimeError("_optimizeCamera called without control_camera option enabled")

        job_id = self._get_next_job_id()
        job_title = "Optimizing camera"

        if props.camera_control_mode == "move_once":
            if report_job:
                self._report_job(job_title, "finding parameters to cover the entire render", job_id, reporting_props)

            CameraUtil.optimize_for_all_frames(context, rotations, enabled_actions)
        elif props.camera_control_mode == "move_each_frame":
            if report_job:
                self._report_job(job_title, "finding parameters to cover the current frame", job_id, reporting_props)

            CameraUtil.fit_camera_to_render_targets(context)
        elif props.camera_control_mode == "move_each_animation":
            if report_job:
                self._report_job(job_title, "finding parameters to cover the current animation", job_id, reporting_props)

            CameraUtil.optimize_for_action(context, current_action)
        elif props.camera_control_mode == "move_each_rotation":
            if report_job:
                self._report_job(job_title, "finding parameters to cover the current rotation angle", job_id, reporting_props)

            CameraUtil.optimize_for_rotation(context, current_rotation, enabled_actions)

        complete_msg = "Camera will render from {}, with an ortho_scale of {}".format(StringUtil.format_number(props.render_camera_obj.location), StringUtil.format_number(props.render_camera.ortho_scale))

        if report_job:
            self._report_job(job_title, complete_msg, job_id, reporting_props, is_complete = True)

    def _perform_ending_sanity_checks(self, num_expected_json_files: int, reporting_props: ReportingPropertyGroup) -> bool:
        job_id = self._get_next_job_id()

        if reporting_props.current_frame_num != reporting_props.total_num_frames:
            self._error = "Expected to render {} frames, but actually rendered {}".format(reporting_props.total_num_frames, reporting_props.current_frame_num)
            return False

        # Make sure all the file paths we wrote in the JSON actually exist
        self._terminal_writer.write("Rendering complete. Performing sanity checks before ending operation.\n")
        self._terminal_writer.indent += 1
        if num_expected_json_files == len(self._json_data):
            self._report_job("Sanity check", "wrote the expected number of JSON files ({})".format(num_expected_json_files), job_id, reporting_props, is_complete = True)
        else:
            msg = f"expected to write {num_expected_json_files} JSON files but found {len(self._json_data)}"
            self._report_job("Sanity check", msg, job_id, reporting_props, is_error = True)
            self._error = "An internal error occurred while writing JSON files: " + msg
            return False

        job_id = self._get_next_job_id()
        json_num = 1
        for _, data in self._json_data.items():
            self._report_job("Sanity check", "validating JSON data {} of {}".format(json_num, len(self._json_data)), job_id, reporting_props)
            json_num += 1

            # Check that file paths for image files are correct
            expected_files = []

            if "imageFile" in data:
                expected_files.append(data["imageFile"])

            if "materialData" in data:
                if len(expected_files) != 0:
                    msg = "JSON should not have both 'imageFile' and 'materialData' keys"
                    self._report_job("Sanity check", msg, job_id, reporting_props, is_error = True)
                    self._error = "An internal error occurred while writing JSON files: " + msg
                    return False

                for material_data in data["materialData"]:
                    expected_files.append(material_data["file"])

            for file_path in expected_files:
                abs_path = os.path.join(self._output_dir, file_path)

                if not os.path.isfile(abs_path):
                    msg = "expected file not found at " + abs_path
                    self._report_job("Sanity check", msg, job_id, reporting_props, is_error = True)
                    self._error = "An internal error occurred while writing JSON files: " + msg
                    return False

        self._report_job("Sanity check", "successfully validated JSON data for {} file(s)".format(len(self._json_data)), job_id, reporting_props, is_complete = True)
        self._terminal_writer.indent -= 1
        return True

    def _progress_bar(self, title: str, numerator: int, denominator: int, width: int = None, show_percentage: bool = True, show_numbers: bool = True, numbers_label: str = "") -> str:
        numbers_label = " " + numbers_label if numbers_label else ""
        numbers_display = f"({numerator}/{denominator}{numbers_label}) " if show_numbers else ""
        text_prefix = f"{title} {numbers_display}"

        if width is None:
            width = os.get_terminal_size().columns - len(text_prefix) - 10

        progress_percent = numerator / denominator
        completed_places = math.floor(progress_percent * width)
        pending_places = width - completed_places

        bar_string = "[{completed}{pending}]".format(completed = "#" * completed_places, pending = "-" * pending_places)

        if show_percentage:
            bar_string = bar_string + " {}%".format(math.floor(100 * progress_percent))

        return text_prefix + bar_string

    def _render_action(self, context: bpy.types.Context, action: bpy.types.Action, rotation: int, temp_dir_path: str) -> Generator[None, None, Dict[str, Any]]:
        scene = context.scene
        props = scene.SpritesheetPropertyGroup
        reporting_props = scene.ReportingPropertyGroup

        # TODO replace this with animation sets
        for obj in [o.mesh_object for o in props.render_targets if o.mesh_object.animation_data]:
            obj.animation_data.action = action

        frame_min: int = math.floor(action.frame_range[0])
        frame_max: int = math.ceil(action.frame_range[1])
        num_frames: int = frame_max - frame_min + 1
        num_digits_in_frame_max: int = int(math.log10(frame_max)) + 1

        action_data = {
            "action": action,
            "frameData": [],
            "rotation": rotation
        }

        if props.control_camera and props.camera_control_mode == "move_each_animation":
            self._optimize_camera(context, current_action = action)

        # Go frame-by-frame and render the object
        job_id = self._get_next_job_id()
        rendered_frames = 0
        for index in range(frame_min, frame_max + 1):
            text = "({}/{})".format(index - frame_min + 1, num_frames)
            self._report_job("Rendering frames", text, job_id, reporting_props)

            # Order of properties in filename is important; they need to sort lexicographically
            # in such a way that sequential frames naturally end up sequential in the sorted file list,
            # no matter what configuration options we're using
            filename = action.name + "_"

            if props.control_rotation:
                filename += "rot" + str(rotation).zfill(3) + "_"

            filename += str(index).zfill(num_digits_in_frame_max)

            filepath = os.path.join(temp_dir_path, filename)

            if index == frame_min:
                action_data["firstFrameFilepath"] = filepath + ".png"

            scene.frame_set(index)
            scene.render.filepath = filepath

            self._run_render_without_stdout(context)
            rendered_frames += 1

            # Yield after each frame to let the UI render
            yield

        action_data["numFrames"] = rendered_frames
        self._report_job("Rendering frames", "completed rendering {} frames".format(rendered_frames), job_id, reporting_props, is_complete = True)

        yield action_data

    def _render_still(self, context: bpy.types.Context, rotation_angle: int, frame_number: int, temp_dir_path: str) -> Dict[str, Any]:
        # Renders a single frame
        scene = context.scene
        props = scene.SpritesheetPropertyGroup
        reporting_props = scene.ReportingPropertyGroup

        filename = "out_still_" + str(frame_number).zfill(4)

        if props.control_rotation:
            filename += "_rot" + str(rotation_angle).zfill(3)

        filename += ".png"
        filepath = os.path.join(temp_dir_path, filename)

        data = {
            "filepath": filepath,
            "rotation": rotation_angle
        }

        job_id = self._get_next_job_id()
        self._report_job("Single frame", "rendering", job_id, reporting_props)

        scene.render.filepath = filepath
        self._run_render_without_stdout(context)

        self._report_job("Single frame", "rendered successfully", job_id, reporting_props, is_complete = True)

        return data

    def _report_job(self, title: str, text: str, job_id: int, reporting_props: ReportingPropertyGroup, is_complete: bool = False, is_error: bool = False, is_skipped: bool = False):
        assert [is_complete, is_error, is_skipped].count(True) <= 1

        if job_id != self._last_job_id:
            if job_id < self._last_job_id:
                self._terminal_writer.write("\nWARNING: incoming job ID {} is smaller than the last job ID {}. This indicates a coding error in the addon.\n\n".format(job_id, self._last_job_id))

            self._last_job_id = job_id
            self._last_job_start_time = time.clock()

        job_time_spent = time.clock() - self._last_job_start_time
        job_time_spent_string = "[{}]".format(StringUtil.time_as_string(job_time_spent, precision = 2, include_hours = False))

        msg = title + ": " + text

        if is_error:
            msg_prefix = "[ERROR] "
            persist_message = True
        elif is_complete:
            msg_prefix = "[DONE] "
            persist_message = True
        elif is_skipped:
            msg_prefix = "[SKIPPED] "
            persist_message = True
        else:
            msg_prefix = "[ACTIVE] "
            persist_message = False

        msg_prefix = (msg_prefix + job_time_spent_string).ljust(22)
        msg = msg_prefix + msg + "\n"

        # Show a progress bar estimating completion of the entire operator
        progress_bar = "\n" + self._progress_bar("Overall progress", reporting_props.current_frame_num, reporting_props.total_num_frames, numbers_label = "frames rendered") + "\n\n"

        # Show elapsed and remaining time
        if reporting_props.current_frame_num > 0:
            time_elapsed_string =   f"Time elapsed:   {StringUtil.time_as_string(reporting_props.elapsed_time, precision = 2)}"
            time_remaining_string = f"Time remaining: {StringUtil.time_as_string(reporting_props.estimated_time_remaining, precision = 2)}"

            # Make the strings repeat on the right side of the terminal, with a small indent
            columns_remaining = os.get_terminal_size().columns - len(time_elapsed_string) - 10
            fmt_string = "{0} {1:>" + str(columns_remaining) + "}\n"
            time_elapsed_string = fmt_string.format(time_elapsed_string, time_elapsed_string)

            columns_remaining = os.get_terminal_size().columns - len(time_remaining_string) - 10
            fmt_string = "{0} {1:>" + str(columns_remaining) + "}\n\n"
            time_remaining_string = fmt_string.format(time_remaining_string, time_remaining_string)

            time_string = time_elapsed_string + time_remaining_string
        else:
            time_string = ""

        # Don't persist the progress bar and time or else they'd fill the terminal every time we write
        self._terminal_writer.write(msg, unpersisted_portion = progress_bar + time_string, persist_msg = persist_message)

    def _rotate_target_objects(self, context: bpy.types.Context, angle_degrees: int):
        props = context.scene.SpritesheetPropertyGroup

        for target in props.render_targets:
            rotation_root = target.rotation_root if target.rotation_root else target.mesh_object
            rotation_root.rotation_euler[2] = math.radians(angle_degrees)

    def _run_render_without_stdout(self, context: bpy.types.Context):
        """Renders a single frame without printing the norma message to stdout

        When saving a rendered image, usually Blender outputs a message like 'Saved <filepath> ...', which clogs the output.
        This method renders without that message being printed."""

        props = context.scene.SpritesheetPropertyGroup
        reporting_props = context.scene.ReportingPropertyGroup

        if props.control_camera and props.camera_control_mode == "move_each_frame":
            # Don't report job because this method is always being called inside of another job
            self._optimize_camera(context, report_job = False)

        # Get the original stdout file, close its fd, and open devnull in its place
        original_stdout = os.dup(1)
        sys.stdout.flush()
        os.close(1)
        os.open(os.devnull, os.O_WRONLY)

        try:
            bpy.ops.render.render(write_still = True)
            reporting_props.current_frame_num += 1
        finally:
            # Reopen stdout in its original position as fd 1
            os.close(1)
            os.dup(original_stdout)
            os.close(original_stdout)

    def _run_image_magick(self, props: SpritesheetPropertyGroup, reporting_props: ReportingPropertyGroup, material_set_index: int, action: bpy.types.Action, total_num_frames: int, temp_dir_path: str, rotation_angle: int) -> Dict[str, Any]:
        job_id = self._get_next_job_id()
        self._report_job("ImageMagick", "Combining {} frames into spritesheet with ImageMagick".format(total_num_frames), job_id, reporting_props)

        output_file_path = self._create_file_path(props, material_set_index, action, rotation_angle, include_material_set = props.control_materials) + ".png"
        image_magick_output = ImageMagick.assemble_frames_into_spritesheet(props.sprite_size, total_num_frames, temp_dir_path, output_file_path)

        if not image_magick_output["succeeded"]:
            self._error = str(image_magick_output["stderr"]).replace("\\n", "\n").replace("\\r", "\r")
            self._report_job("ImageMagick", self._error, job_id, reporting_props, is_error = True)
        else:
            msg = "output file is at {}".format(output_file_path)
            self._report_job("ImageMagick", msg, job_id, reporting_props, is_complete = True)

        if props.pad_output_to_power_of_two:
            job_id = self._get_next_job_id()
            image_size = image_magick_output["args"]["outputImageSize"]
            target_size = (self._next_power_of_two(image_size[0]), self._next_power_of_two(image_size[1]))
            target_size_str = "{}x{}".format(target_size[0], target_size[1])

            if target_size == image_size:
                self._report_job("ImageMagick", "Padding not necessary; image output size {} is already power-of-two".format(target_size_str), job_id, reporting_props, is_skipped = True)
            else:
                self._report_job("ImageMagick", "Padding output image to power-of-two size {}".format(target_size_str), job_id, reporting_props)
                ImageMagick.pad_image_to_size(image_magick_output["args"]["outputFilePath"], target_size)
                self._report_job("ImageMagick", "Output image successfully padded to power-of-two size {}".format(target_size_str), job_id, reporting_props, is_complete = True)

                # Record padding in JSON for tool integration
                padding_amount = (target_size[0] - image_size[0], target_size[1] - image_size[1])
                image_magick_output["args"]["padding"] = padding_amount

        return image_magick_output

    def _set_render_settings(self, context: bpy.types.Context):
        scene = context.scene
        props = scene.SpritesheetPropertyGroup

        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.film_transparent = True  # Transparent PNG
        scene.render.bake_margin = 0
        scene.render.resolution_x = props.sprite_size[0]
        scene.render.resolution_y = props.sprite_size[1]