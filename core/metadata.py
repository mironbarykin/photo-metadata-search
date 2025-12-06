import piexif
from PIL import Image, PngImagePlugin
import os
import logging

ENABLE_METADATA_LOGGING = False

logger = logging.getLogger("photo_metadata")
if ENABLE_METADATA_LOGGING:
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("send_this_to_miron_metadata.log", encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(fh)
else:
    logger.addHandler(logging.NullHandler())
    logger.propagate = False

def _is_jpeg_tiff(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in (".jpg", ".jpeg", ".tif", ".tiff")

def _is_png(path):
    return os.path.splitext(path)[1].lower() == ".png"

def _is_webp(path):
    return os.path.splitext(path)[1].lower() == ".webp"

def read_comment(image_path):
    try:
        if _is_jpeg_tiff(image_path):
            exif_dict = piexif.load(image_path)
            user_comment = exif_dict["Exif"].get(piexif.ExifIFD.UserComment)
            if user_comment:
                if user_comment.startswith(b"ASCII\0\0\0"):
                    user_comment = user_comment[8:]
                comment = user_comment.decode("utf-8", errors="replace").strip()
                logger.info(f"Read UserComment from {image_path}: {comment}")
                return comment
            img_desc = exif_dict["0th"].get(piexif.ImageIFD.ImageDescription)
            if img_desc:
                comment = img_desc.decode("utf-8", errors="replace").strip()
                logger.info(f"Read ImageDescription from {image_path}: {comment}")
                return comment
        elif _is_png(image_path):
            with Image.open(image_path) as im:
                meta = im.info
                for key in ("Description", "Comment", "ImageDescription"):
                    if key in meta:
                        logger.info(f"Read {key} from {image_path}: {meta[key]}")
                        return meta[key]
        elif _is_webp(image_path):
            with Image.open(image_path) as im:
                meta = im.info
                for key in ("description", "Comment", "ImageDescription"):
                    if key in meta:
                        logger.info(f"Read {key} from {image_path}: {meta[key]}")
                        return meta[key]
    except Exception as e:
        logger.error(f"Error reading metadata from {image_path}: {e}")
    return ""

def write_comment(image_path, comment):
    try:
        if _is_jpeg_tiff(image_path):
            exif_dict = piexif.load(image_path)
            user_comment = b"ASCII\0\0\0" + comment.encode("utf-8", errors="replace")
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = user_comment
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = comment.encode("utf-8", errors="replace")
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)
            logger.info(f"Wrote UserComment and ImageDescription to {image_path}: {comment}")
        elif _is_png(image_path):
            with Image.open(image_path) as im:
                meta = {}
                for k, v in im.info.items():
                    if isinstance(v, str):
                        meta[k] = v
                meta["Description"] = comment
                meta["Comment"] = comment
                pnginfo = PngImagePlugin.PngInfo()
                for k, v in meta.items():
                    pnginfo.add_text(k, v)
                im.save(image_path, pnginfo=pnginfo)
                logger.info(f"Wrote Description/Comment to PNG {image_path}: {comment}")
        elif _is_webp(image_path):
            with Image.open(image_path) as im:
                meta = {}
                for k, v in im.info.items():
                    if isinstance(v, str):
                        meta[k] = v
                meta["description"] = comment
                meta["Comment"] = comment
                im.save(image_path, "WEBP", **meta)
                logger.info(f"Wrote description/Comment to WEBP {image_path}: {comment}")
    except Exception as e:
        logger.error(f"Error writing metadata to {image_path}: {e}")
