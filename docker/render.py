import bpy 
from mathutils import Vector
from pathlib import Path
import objaverse

def models_already_downloaded():
    model_dir = Path("/models/") # mounted path for the container its different then the project 
    model_files = list(model_dir.glob("*.glb"))
    return len(model_files) == 20

def download_models():
    objaverse.
    pass

def setup_camera():
    pass

def import_model():
    pass

def render_five_images():
    pass

def main():
    # download the objects that needs to be modelled through Objaverse 
    # do check if we already have them
    if not models_already_downloaded():
        models = download_models()
    setup_camera()
    import_model()
    render_five_images()

    return None

if __name__ == "__main__":
    main()