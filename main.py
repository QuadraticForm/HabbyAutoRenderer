import bpy
from bpy.types import Context, Operator, Panel

class HAR_OT_RenderAllCameras(Operator):
    bl_idname = "har.render_all_cameras"
    bl_label = "Render All Cameras"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None

    def __init__(self):
        self.current_camera_index = 0
        self.current_frame = 0
        self.cameras = []
        self.original_camera = None
        self.original_render_filepath = ""

    def invoke(self, context, event):
        scene = context.scene
        self.original_camera = scene.camera
        self.original_render_filepath = scene.render.filepath

        # Collect all cameras
        self.cameras = [obj for obj in scene.objects if obj.type == 'CAMERA']

        # Ensure correct number of digits in frame number
        min_digits = len(str(scene.frame_end))
        if scene.frame_digits < min_digits:
            scene.frame_digits = min_digits

        wm = context.window_manager
        wm.progress_begin(0, len(self.cameras) * (scene.frame_end - scene.frame_start + 1))
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}
    
    def step(self, context):
        scene = context.scene
        camera = self.cameras[self.current_camera_index]
        frame_str = f"{scene.frame_current:0{scene.frame_digits}d}"
        
        if scene.frame_prefix:
            filename = f"{camera.name}_{frame_str}.png"
            tag_filename = f"{camera.name}_{frame_str}.txt"
        else:
            filename = f"{camera.name}_{frame_str}.png"
            tag_filename = f"{camera.name}_{frame_str}.txt"
        
        filepath = f"{self.original_render_filepath}/{filename}"
        tagpath = f"{self.original_render_filepath}/{tag_filename}"

        # Render frame
        scene.camera = camera
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)

        # Save tag property to txt file
        tag = camera.get('tag', '')
        with open(tagpath, 'w') as tag_file:
            tag_file.write(tag)

        # Update current frame and progress
        self.current_frame += 1
        if self.current_frame > scene.frame_end:
            self.current_frame = scene.frame_start
            self.current_camera_index += 1

        total_tasks = len(self.cameras) * (scene.frame_end - scene.frame_start + 1)
        progress = (self.current_camera_index * (scene.frame_end - scene.frame_start + 1) + (self.current_frame - scene.frame_start)) / total_tasks
        context.scene.render_progress = progress  # Store progress in scene property
        context.window_manager.progress_update(progress)


    def modal(self, context, event):
        if self.current_camera_index >= len(self.cameras):
            # Cleanup and finish
            self.finish(context)
            context.scene.render_progress = 0  # Reset progress
            self.report({'INFO'}, "Rendering completed")
            return {'FINISHED'}

        if event.type == 'TIMER':
            self.step(context)

        if event.type == 'ESC':
            # Cleanup and cancel
            self.finish(context)
            context.scene.render_progress = 0  # Reset progress
            self.report({'INFO'}, "Rendering cancelled")
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def finish(self, context):
        # Restore original state and remove timer
        context.scene.camera = self.original_camera
        context.scene.render.filepath = self.original_render_filepath
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        wm.progress_end()

# Operator to add custom property to cameras if not present
class HAR_OT_AddTagProperty(Operator):
    bl_idname = "har.add_tag_property"
    bl_label = "Add 'Tag' Property to Cameras"
    
    def execute(self, context):
        for obj in bpy.context.scene.objects:
            if obj.type == 'CAMERA' and "tag" not in obj:
                obj["tag"] = ""
        return {'FINISHED'}

class HAR_PT_RenderPanel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "HAR"
    bl_label = "Habby Auto Renderer"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Display render properties
        layout.prop(scene.render, "filepath")

        row = layout.row()
        row.label(text="Resolution")
        row.prop(scene.render, "resolution_x", text="X")
        row.prop(scene.render, "resolution_y", text="Y")

        row = layout.row()
        row.label(text="Frame Range")
        row.prop(scene, "frame_start", text="Start")
        row.prop(scene, "frame_end", text="End")

        layout.prop(scene, "frame_prefix", text="Prefix Frame Number")
        
        layout.prop(scene, "frame_digits", text="Frame Number Digits")

        layout.separator()

        layout.prop(scene.render, "engine")

        # Conditionally display EEVEE and Cycles properties
        if scene.render.engine in {'BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'}:
            layout.prop(scene.eevee, "taa_render_samples")
        elif scene.render.engine == 'CYCLES':
            layout.prop(scene.cycles, "samples")
            layout.prop(scene.cycles, "device")

        layout.separator()

        # Add Render All Cameras button
        layout.operator(HAR_OT_RenderAllCameras.bl_idname)

        # Draw the progress bar if rendering is in progress
        if scene.render_progress > 0:
            layout.separator()
            layout.label(text="Rendering... ESC to stop")
            layout.prop(scene, "render_progress", slider=True)


class HAR_PT_UtilitiesPanel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "HAR"
    bl_label = "Utilities"

    def draw(self, context):
        layout = self.layout
        
        # Add Tag button
        layout.operator(HAR_OT_AddTagProperty.bl_idname)

  
def register():
    # class registers are handled by xuxing's auto_load, so not needed here
    # Store additional properties on the scene
    bpy.types.Scene.render_progress = bpy.props.FloatProperty(name="Render Progress", default=0.0, min=0, max=1)
    bpy.types.Scene.frame_prefix = bpy.props.BoolProperty(name="Prefix Frame Number", default=True)
    bpy.types.Scene.frame_digits = bpy.props.IntProperty(name="Frame Number Digits", default=4)

def unregister():
    # class unregisters are handled by xuxing's auto_load, so not needed here
    del bpy.types.Scene.render_progress
    del bpy.types.Scene.frame_prefix
    del bpy.types.Scene.frame_digits

if __name__ == "__main__":
    register()