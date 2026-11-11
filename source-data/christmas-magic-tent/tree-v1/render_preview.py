import bpy,math
from mathutils import Vector
from pathlib import Path

root=Path(__file__).resolve().parent/'generated'
output=str(Path(__file__).resolve().parents[3]/'public/media/christmas-magic-tent/tree/tree-v1-preview.png')

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def mat(name,color,metal=0,rough=0.7):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bsdf=m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Metallic'].default_value=metal
    bsdf.inputs['Roughness'].default_value=rough
    return m
tree=mat('Satin green PETG CAD concept',(0.21,.59,.35))
base=mat('Dark green PETG CAD concept',(.18,.39,.28))
background=mat('Background neutral',(.93,.94,.90))
def import_stl(name):
    p=root/(name+'.stl')
    bpy.ops.wm.stl_import(filepath=str(p))
    obj=bpy.context.object;obj.name=name
    return obj
a=import_stl('tree_panel_top_slot');a.rotation_euler[0]=math.pi/2;a.location=(0,1.8,4);a.data.materials.append(tree)
b=import_stl('tree_panel_bottom_slot');b.rotation_euler[0]=math.pi/2;b.rotation_euler[2]=math.pi/2;b.location=(-1.8,0,4);b.data.materials.append(tree)
c=import_stl('tree_cross_base');c.data.materials.append(base)
# background plane, z=-2mm
bpy.ops.mesh.primitive_plane_add(size=2,location=(0,0,-2))
floor=bpy.context.object;floor.name='CAD preview background';floor.scale=(300,300,1);floor.data.materials.append(background)
# lights and rendering
def area(name,loc,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,90))-ob.location).to_track_quat('-Z','Y').to_euler()
area('Softbox front',(260,-320,450),700,350)
area('Softbox rear',(-300,280,380),430,280)
camera_data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',camera_data);bpy.context.collection.objects.link(camera)
camera.location=(370,-420,310);look=Vector((0,0,115))-camera.location;camera.rotation_euler=look.to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=390
sc=bpy.context.scene;sc.camera=camera;sc.render.engine='BLENDER_EEVEE';sc.render.resolution_x=900;sc.render.resolution_y=700;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.filepath=output
sc.world.color=(.8,.8,.8)
sc.view_settings.view_transform='Standard';sc.view_settings.look='Medium High Contrast';sc.view_settings.exposure=1.5
bpy.ops.render.render(write_still=True)
print('RENDERED',output)
