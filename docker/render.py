import bpy 
from mathutils import Vector

# bpy.ops.mesh.primitive_cube_add(
#     size=2,
#     location=(0,0,0), # where do we want to position our 3D object
# )

# # adding lights
# bpy.ops.object.light_add(type='POINT', location=light_positions[0])
# # putting the camera at the position 
# bpy.ops.object.camera_add(location=(0,-8,5))
# # facing the camera towards the object before capturing 
# ## first getting the camera
# camera = bpy.context.object
# ## target = cube position
# target = Vector((0,0,0))
# direction = target - camera.location
# ##rotate the camera in that direction
# camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# bpy.context.scene.camera = camera
# bpy.context.scene.render.filepath = "/output/test.png"
# bpy.ops.render.render(write_still=True)

def create_five_images (bpy, light_positions):
    # will use the 20 objects and then loop them each over the different lighting positions
    return ""

def pick_twenty_objects():
    # will return array of list of 20 objects
    return ""

# adding light positions leaving bottom
light_positions = [
    (-5, 0, 5),
    (5, 0, 5),
    (0, -5, 5),
    (0, 5, 5),
    (0, 0, 8)
]

def instantiate_twenty_objects():
    pass

def render_images(list_of_objects, bpy):
    pass

def main():
    # instantiate the bpy camera object just the camerea not the object itself
    bpy.ops.object.camera_add(location=(0,-8,5))
    # define the lighting positions (done already above)

    # call a function to get a bpy  list of object (20) like 3d figure positioned at 0,0,0
    list_of_objects = instantiate_twenty_objects()
    # pass the object the camera and the lighting function to a function create_five_images click the images
        # once one object has been clicked 5 times we need to clear bpy state within the loop
    render_images(list_of_objects, bpy)
    # store the images on local mounted folder
    return None

if __name__ == "__main__":
    main()