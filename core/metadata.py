import piexif
from PIL import Image, PngImagePlugin
import os

def _is_jpeg_tiff(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in (".jpg", ".jpeg", ".tif", ".tiff")

def _is_png(path):
    return os.path.splitext(path)[1].lower() == ".png"

def _is_webp(path):
    return os.path.splitext(path)[1].lower() == ".webp"

def read_comment(image_path):
    if _is_jpeg_tiff(image_path):
        try:
            exif_dict = piexif.load(image_path)
            # Try UserComment
            user_comment = exif_dict["Exif"].get(piexif.ExifIFD.UserComment)
            if user_comment:
                try:
                    # Remove encoding prefix if present
                    if user_comment.startswith(b"ASCII\0\0\0"):
                        user_comment = user_comment[8:]
                    return user_comment.decode("utf-8", errors="replace").strip()
                except Exception:
                    return str(user_comment)
            # Try ImageDescription
            img_desc = exif_dict["0th"].get(piexif.ImageIFD.ImageDescription)
            if img_desc:
                return img_desc.decode("utf-8", errors="replace").strip()
        except Exception:
            pass
    elif _is_png(image_path):
        try:
            with Image.open(image_path) as im:
                meta = im.info
                # Standard PNG text fields
                for key in ("Description", "Comment", "ImageDescription"):
                    if key in meta:
                        return meta[key]
        except Exception:
            pass
    elif _is_webp(image_path):
        try:
            with Image.open(image_path) as im:
                meta = im.info
                # WebP supports XMP as "description" or "Comment"
                for key in ("description", "Comment", "ImageDescription"):
                    if key in meta:
                        return meta[key]
        except Exception:
            pass
    return ""

def write_comment(image_path, comment):
    if _is_jpeg_tiff(image_path):
        try:
            exif_dict = piexif.load(image_path)
            # Write UserComment (with ASCII prefix)
            user_comment = b"ASCII\0\0\0" + comment.encode("utf-8", errors="replace")
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = user_comment
            # Write ImageDescription
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = comment.encode("utf-8", errors="replace")
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)
        except Exception:
            pass
    elif _is_png(image_path):
        try:
            with Image.open(image_path) as im:
                meta = im.info.copy()
                meta["Description"] = comment
                meta["Comment"] = comment
                pnginfo = PngImagePlugin.PngInfo()
                for k, v in meta.items():
                    pnginfo.add_text(k, v)
                im.save(image_path, pnginfo=pnginfo)
        except Exception:
            pass
    elif _is_webp(image_path):
        try:
            with Image.open(image_path) as im:
                meta = im.info.copy()
                meta["description"] = comment
                meta["Comment"] = comment
                im.save(image_path, "WEBP", **meta)
        except Exception:
            pass

