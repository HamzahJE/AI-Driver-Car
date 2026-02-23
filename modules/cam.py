import subprocess
import os


def capture_image():
    """Capture a single frame using libcamera and save to images/image.jpg."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    folder = os.path.join(project_root, 'images')
    os.makedirs(folder, exist_ok=True)

    image_path = os.path.join(folder, "image.jpg")

    # Use rpicam-still for Pi camera module (CSI)
    # Small image = faster base64 encode + faster LLM processing
    result = subprocess.run(
        [
            'rpicam-still',
            '-o', image_path,
            '--width', '320',
            '--height', '240',
            '--nopreview',
            '-t', '100',        # 100ms — minimal warmup since car is stopped
            '-q', '50',         # Lower JPEG quality for smaller payload
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:
        raise RuntimeError(f"rpicam-still failed: {result.stderr.strip()}")

    if not os.path.isfile(image_path):
        raise RuntimeError("Image file was not created")

    return image_path


if __name__ == "__main__":
    path = capture_image()
    print(f"Saved to {path}")
