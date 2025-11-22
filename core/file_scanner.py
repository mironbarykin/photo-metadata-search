import os

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")

def scan_images(folder):
    images = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(SUPPORTED_EXTENSIONS):
                images.append(os.path.join(root, f))
    return images
