import subprocess
import os


def capture_image():
    """Capture a single frame using libcamera and save to images/image.jpg."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    folder = os.path.join(project_root, 'images')
    os.makedirs(folder, exist_ok=True)

    image_path = os.path.join(folder, "image.jpg")

    # Use libcamera-still for Pi camera module (CSI)
    result = subprocess.run(
        [
            'libcamera-still',
            '-o', image_path,
            '--width', '640',
            '--height', '480',
            '--nopreview',
            '-t', '500',        # 500ms exposure/warmup time
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:
        raise RuntimeError(f"libcamera-still failed: {result.stderr.strip()}")

    if not os.path.isfile(image_path):
        raise RuntimeError("Image file was not created")

    return image_path


if __name__ == "__main__":
    path = capture_image()
    print(f"Saved to {path}")
