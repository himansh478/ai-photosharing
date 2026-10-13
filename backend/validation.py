"""Checks applied to every uploaded file before it is processed or stored."""
import hashlib
import logging
import os

from PIL import Image, UnidentifiedImageError

from backend.config import Config

logger = logging.getLogger(__name__)

# Pillow refuses to decode anything far beyond this (decompression-bomb protection).
Image.MAX_IMAGE_PIXELS = Config.MAX_IMAGE_PIXELS

_GPS_IFD = 0x8825


class InvalidImage(ValueError):
    """The uploaded file is not an image we accept. The message is safe to show to the user."""


def validate_image(path, max_bytes):
    """Raise InvalidImage unless `path` is a real image within the size limits."""
    size = os.path.getsize(path)
    if size == 0:
        raise InvalidImage('File is empty')
    if size > max_bytes:
        raise InvalidImage(f'File is larger than {max_bytes // (1024 * 1024)} MB')
    try:
        with Image.open(path) as img:
            image_format = img.format
            width, height = img.size
            img.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError):
        raise InvalidImage('Not a valid image file')
    if image_format not in Config.ALLOWED_IMAGE_FORMATS:
        raise InvalidImage('Unsupported image format')
    if width * height > Config.MAX_IMAGE_PIXELS:
        raise InvalidImage('Image dimensions are too large')
    return image_format


def strip_location(path):
    """Remove GPS coordinates from a JPEG in place. Returns True if anything was removed.

    Guests download these files, and a photo's location is nobody else's business.
    """
    try:
        with Image.open(path) as img:
            if img.format != 'JPEG':
                return False
            exif = img.getexif()
            if not exif.get_ifd(_GPS_IFD):
                return False
            del exif[_GPS_IFD]
            img.load()
            # quality='keep' reuses the original quantisation tables, so the pixels are not degraded.
            img.save(path, format='JPEG', quality='keep', subsampling='keep',
                     exif=exif, icc_profile=img.info.get('icc_profile'))
        return True
    except Exception as e:
        logger.warning(f'Could not strip location data from {os.path.basename(path)}: {e}')
        return False


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()
