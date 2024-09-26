import bpy
from bpy.types import Context, Operator, Panel

class HAR_OT_RenderAllCameras(Operator):
    bl_idname = "har.render_all_cameras"
    bl_label = "Render All Cameras"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None

    def __init__(self):
        self.current_camera_index = 0
        self.cameras = []
        self.original_camera = None
        self.original_render_filepath = ""

    def invoke(self, context, event):
        scene = context.scene
        self.original_camera = scene.camera
        self.original_render_filepath = scene.render.filepath

        # Collect all cameras
        self.cameras = [obj for obj in scene.objects if obj.type == 'CAMERA']

        bpy.context.scene.frame_set(scene.frame_start)
        
        # Ensure correct number of digits in frame number
        min_digits = len(str(scene.frame_end))
        if scene.frame_num_digits < min_digits:
            scene.frame_num_digits = min_digits

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}
    
    def step(self, context):
        
        # file names
        
        scene = context.scene
        camera = self.cameras[self.current_camera_index]
        frame_str = f"{scene.frame_current:0{scene.frame_num_digits}d}"
        
        if scene.frame_num_pos == 'PREFIX':
            filename = f"{frame_str} {camera.name}"
        else:
            filename = f"{camera.name} {frame_str}"
            
        tag_filename = f"{filename}.txt"
        
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

        # Progress
        
        ## to next camera
        self.current_camera_index += 1
        if self.current_camera_index >= len(self.cameras):
            ## to next frame
            bpy.context.scene.frame_set(scene.frame_current + 1)
            self.current_camera_index = 0

        # update progress bar

        total_tasks = len(self.cameras) * (scene.frame_end - scene.frame_start + 1)
        progress = (self.current_camera_index + len(self.cameras) * (scene.frame_current - scene.frame_start + 1)) / total_tasks
        context.scene.render_progress = progress  # Store progress in scene property


    def modal(self, context, event):
        if context.scene.frame_current > context.scene.frame_end:
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

        # Header
        
        layout.separator()
        layout.label(text="File:")
        
        # Output
        
        layout.prop(scene.render, "filepath")
        
        # Frame Digits
        row = layout.row()
        row.label(text="Frame Number:")
        row.prop(scene, "frame_num_digits", text="Digits")
        row.prop(scene, "frame_num_pos", expand=True)
        
        # Header
        
        layout.separator()
        layout.label(text="Params:")

        # Resolution
        
        row = layout.row()
        
        row.label(text="Resolution")
        
        sublayout = row.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)      
        sublayout.prop(scene.render, "resolution_x", text="X")
        sublayout.prop(scene.render, "resolution_y", text="Y")

        # Frame Range
        
        row = layout.row()
        
        row.label(text="Frame Range")
        
        sublayout = row.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)
        sublayout.prop(scene, "frame_start", text="Start")
        sublayout.prop(scene, "frame_end", text="End")
        
        # Header
        
        layout.separator()
        layout.label(text="Render Engine:")
        
        # Render Engine

        layout.prop(scene.render, "engine")

        # Conditionally display EEVEE and Cycles properties
        if scene.render.engine in {'BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'}:
            layout.prop(scene.eevee, "taa_render_samples")
        elif scene.render.engine == 'CYCLES':
            layout.prop(scene.cycles, "samples")
            layout.prop(scene.cycles, "device")
            
        #

        layout.separator()

        # Render All Cameras button 
        
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
    
    bpy.types.Scene.render_progress = bpy.props.FloatProperty(name="Render Progress", default=0.0, min=0, max=1)

    bpy.types.Scene.frame_num_digits = bpy.props.IntProperty(name="Frame Number Digits", default=4)
    
    bpy.types.Scene.frame_num_pos = bpy.props.EnumProperty(
        name="Frame Num Position",
        description="A simple switch with two options",
        items=[
            ('PREFIX', "Prefix", "Prefix"),
            ('POSTFIX', "Postfix", "Postfix")
        ],
        default='PREFIX'
    )

def unregister():
    
    del bpy.types.Scene.render_progress
    
    del bpy.types.Scene.frame_num_digits
    
    del bpy.types.Scene.frame_num_pos 
    
if __name__ == "__main__":
    register()