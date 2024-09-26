import bpy
from bpy.types import Context, Operator, Panel

# Operator to render images for every camera
class HAR_OT_RenderAllCameras(Operator):
    bl_idname = "har.render_all_cameras"
    bl_label = "Render All Cameras"

    def execute(self, context):
        scene = bpy.context.scene
        original_camera = scene.camera
        original_render_filepath = scene.render.filepath


        for obj in scene.objects:
            if obj.type == 'CAMERA':
                scene.camera = obj
                scene.render.filepath = f"{original_render_filepath}/{obj.name}"
                bpy.ops.render.render(write_still=True)
                
                # Writing tag property to txt file
                tag = obj.get('tag', '')
                with open(f"{original_render_filepath}/{obj.name}.txt", 'w') as tag_file:
                    tag_file.write(tag)

        
        scene.render.filepath = original_render_filepath
        scene.camera = original_camera
        return {'FINISHED'}

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
        
        # Display the render properties
        layout.prop(scene.render, "filepath")

        row = layout.row()
        row.label(text="Resolution")
        row.prop(scene.render, "resolution_x", text="X")
        row.prop(scene.render, "resolution_y", text="Y")
        
        layout.prop(scene.render, "engine")

        # Conditionally display EEVEE and Cycles properties
        if scene.render.engine.startswith('BLENDER_EEVEE'):
            layout.prop(scene.eevee, "taa_render_samples")
        elif scene.render.engine == 'CYCLES':
            layout.prop(scene.cycles, "samples")
            layout.prop(scene.cycles, "device")

        # Render all cameras button
        layout.operator(HAR_OT_RenderAllCameras.bl_idname)

class HAR_PT_UtilitiesPanel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "HAR"
    bl_label = "Utilities"

    def draw(self, context):
        layout = self.layout
        
        # Add Tag button
        layout.operator(HAR_OT_AddTagProperty.bl_idname)