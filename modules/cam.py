import cv2
import os
import time

WARMUP_FRAMES = 30 

def capture_image():
    """Capture a single frame and save to images/image.jpg."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    folder = os.path.join(project_root, 'images')
    os.makedirs(folder, exist_ok=True)

    image_path = os.path.join(folder, "image.jpg")

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        raise RuntimeError("Cannot open camera")

    try:
        time.sleep(0.1)

        for _ in range(WARMUP_FRAMES):
            ret, _ = cam.read()
            if not ret:
                raise RuntimeError("Failed to grab frame during warm-up")

        ret, image = cam.read()
        if not ret:
            raise RuntimeError("Failed to grab frame")

        cv2.imwrite(image_path, image)
        return image_path
    finally:
        cam.release()


if __name__ == "__main__":
    capture_image()
