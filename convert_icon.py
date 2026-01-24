"""Convert PNG icon to ICO format for Windows executable."""
from pathlib import Path
from PIL import Image

def convert_png_to_ico(png_path: str | Path, ico_path: str | Path) -> None:
    """Convert PNG image to ICO format."""
    png_path = Path(png_path)
    ico_path = Path(ico_path)
    
    if not png_path.exists():
        raise FileNotFoundError(f"PNG file not found: {png_path}")
    
    # Open the PNG image
    img = Image.open(png_path)
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Create ICO file with multiple sizes (Windows prefers multiple sizes)
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    # Resize image to each size and save as ICO
    img.save(
        ico_path,
        format='ICO',
        sizes=[(s, s) for s in [16, 32, 48, 64, 128, 256]],
    )
    
    print(f"Successfully converted {png_path} to {ico_path}")

if __name__ == "__main__":
    import sys
    png_path = Path("resources/spoon.png")
    ico_path = Path("resources/spoon.ico")
    
    print(f"Converting {png_path} to {ico_path}...")
    try:
        convert_png_to_ico(png_path, ico_path)
        print(f"Success! ICO file created: {ico_path.absolute()}")
        if ico_path.exists():
            print(f"File exists: {ico_path.exists()}, Size: {ico_path.stat().st_size} bytes")
        else:
            print("ERROR: ICO file was not created!")
            sys.exit(1)
    except Exception as e:
        import traceback
        print(f"Error converting icon: {e}")
        traceback.print_exc()
        sys.exit(1)
