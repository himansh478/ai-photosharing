import io

import pytest
from PIL import Image

from backend.validation import InvalidImage, file_sha256, strip_location, validate_image
from tests.conftest import make_image

MB = 1024 * 1024


def _write(tmp_path, name, data):
    path = tmp_path / name
    path.write_bytes(data)
    return str(path)


def test_real_images_are_accepted(tmp_path):
    for fmt in ('JPEG', 'PNG', 'WEBP', 'BMP'):
        assert validate_image(_write(tmp_path, f'ok.{fmt.lower()}', make_image(fmt)), MB) == fmt


@pytest.mark.parametrize('data', [
    b'',
    b'not an image at all',
    b'<html><script>alert(1)</script></html>',
    b'\xff\xd8\xff\xe0' + b'garbage' * 10,
])
def test_non_images_are_rejected(tmp_path, data):
    with pytest.raises(InvalidImage):
        validate_image(_write(tmp_path, 'bad.jpg', data), MB)


def test_unsupported_format_is_rejected(tmp_path):
    with pytest.raises(InvalidImage, match='Unsupported'):
        validate_image(_write(tmp_path, 'anim.gif', make_image('GIF')), MB)


def test_oversized_file_is_rejected(tmp_path):
    with pytest.raises(InvalidImage, match='larger than'):
        validate_image(_write(tmp_path, 'big.jpg', make_image()), max_bytes=100)


def test_huge_dimensions_are_rejected(tmp_path, monkeypatch):
    from backend import validation
    monkeypatch.setattr(validation.Config, 'MAX_IMAGE_PIXELS', 1000)
    with pytest.raises(InvalidImage, match='dimensions'):
        validate_image(_write(tmp_path, 'wide.jpg', make_image(size=(200, 200))), MB)


def _jpeg_with_gps():
    img = Image.new('RGB', (64, 48), (10, 200, 90))
    exif = img.getexif()
    exif[0x0112] = 6                                   # orientation, must survive
    exif[0x8825] = {1: 'N', 2: (23.0, 1.0, 30.0)}       # GPS latitude
    buf = io.BytesIO()
    img.save(buf, format='JPEG', exif=exif)
    return buf.getvalue()


def test_gps_location_is_removed_but_orientation_kept(tmp_path):
    path = _write(tmp_path, 'gps.jpg', _jpeg_with_gps())
    with Image.open(path) as img:
        assert img.getexif().get_ifd(0x8825), 'test image should start with GPS data'

    assert strip_location(path) is True

    with Image.open(path) as img:
        assert not img.getexif().get_ifd(0x8825)
        assert img.getexif()[0x0112] == 6
        assert img.size == (64, 48)
    validate_image(path, MB)


def test_image_without_gps_is_left_untouched(tmp_path):
    data = make_image()
    path = _write(tmp_path, 'plain.jpg', data)
    assert strip_location(path) is False
    assert open(path, 'rb').read() == data


def test_sha256_is_stable_and_content_based(tmp_path):
    a = _write(tmp_path, 'a.jpg', make_image(color=(1, 2, 3)))
    b = _write(tmp_path, 'b.jpg', make_image(color=(1, 2, 3)))
    c = _write(tmp_path, 'c.jpg', make_image(color=(9, 9, 9)))
    assert file_sha256(a) == file_sha256(b) != file_sha256(c)
    assert len(file_sha256(a)) == 64
