#!/usr/bin/env python3
# image_check.py — validate image file format, size, dimensions
# caveman style: check file, report info, done
import sys
import os
import struct

# max file size in bytes (10 MB)
MAX_SIZE = 10 * 1024 * 1024
# supported formats and their magic bytes
FORMATS = {
    b'\xff\xd8\xff': 'JPEG',
    b'\x89PNG\r\n\x1a\n': 'PNG',
    b'RIFF': 'WebP',  # RIFF....WEBP
    b'GIF87a': 'GIF',
    b'GIF89a': 'GIF',
    b'BM': 'BMP',
    b'II\x2a\x00': 'TIFF',  # little endian
    b'MM\x00\x2a': 'TIFF',  # big endian
}

def detect_format(path):
    # read magic bytes from file header
    with open(path, 'rb') as f:
        header = f.read(16)
    # check each format magic
    for magic, fmt in FORMATS.items():
        if header.startswith(magic):
            # special check for WebP (RIFF is not unique)
            if fmt == 'WebP' and len(header) >= 12:
                return 'WebP' if header[8:12] == b'WEBP' else None
            return fmt
    return None

def get_dimensions(path, fmt):
    # extract width and height from file header
    with open(path, 'rb') as f:
        if fmt == 'PNG':
            f.read(16)
            w, h = struct.unpack('>II', f.read(8))
            return w, h
        elif fmt == 'JPEG':
            f.read(2)
            while True:
                b = f.read(1)
                if b != b'\xff':
                    break
                marker = f.read(1)
                if marker == b'\xd8' or marker == b'\xd9':
                    continue
                length = struct.unpack('>H', f.read(2))[0]
                if marker in (b'\xc0', b'\xc1', b'\xc2'):
                    f.read(1)
                    h, w = struct.unpack('>HH', f.read(4))
                    return w, h
                f.seek(length - 2, 1)
        elif fmt == 'GIF':
            w, h = struct.unpack('<HH', f.read(4))
            return w, h
        elif fmt == 'BMP':
            f.read(14)
            w, h = struct.unpack('<ii', f.read(8))
            return w, h
        elif fmt == 'WebP':
            f.read(12)
            chunk_id = f.read(4)
            if chunk_id == b'VP8 ':
                f.read(3)
                w, h = struct.unpack('<HH', f.read(4))
                return w & 0x3fff, h & 0x3fff
        elif fmt == 'TIFF':
            pass  # tiff is complex, skip
    return None, None

def main():
    if len(sys.argv) < 2:
        print("usage: image_check.py <image_path>")
        sys.exit(1)
    path = sys.argv[1]
    # check file exists
    if not os.path.isfile(path):
        print(f"ERROR: file not found: {path}")
        sys.exit(1)
    # check file size
    size = os.path.getsize(path)
    if size > MAX_SIZE:
        print(f"ERROR: file too large ({size / 1024 / 1024:.1f} MB > 10 MB)")
        sys.exit(1)
    # detect format
    fmt = detect_format(path)
    if fmt is None:
        print(f"ERROR: unsupported or invalid image format: {path}")
        sys.exit(1)
    # get dimensions
    w, h = get_dimensions(path, fmt)
    print(f"FILE: {path}")
    print(f"FORMAT: {fmt}")
    print(f"SIZE: {size / 1024:.1f} KB")
    if w and h:
        print(f"DIMENSIONS: {w}x{h}")
    else:
        print("DIMENSIONS: unavailable")

if __name__ == "__main__":
    main()
