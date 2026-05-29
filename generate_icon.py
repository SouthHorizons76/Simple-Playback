"""Generates a minimal app.ico using only the Python standard library (no Pillow needed)."""
import struct
import zlib
import os


def _make_png(size: int, bg: tuple, triangle: tuple) -> bytes:
    """Create a simple PNG: solid background with a centered play triangle."""
    w = h = size
    # Build raw pixel data (RGBA)
    pixels = []
    cx, cy = w / 2, h / 2
    tri_h = h * 0.55
    tri_w = w * 0.50
    for y in range(h):
        row = []
        for x in range(w):
            # Simple circle mask
            dx = x - cx
            dy = y - cy
            r = (w * 0.45)
            in_circle = (dx * dx + dy * dy) <= r * r
            if not in_circle:
                row += [0, 0, 0, 0]  # transparent
                continue
            # Play triangle: right-pointing
            tx = x - (cx - tri_w * 0.3)
            ty = y - cy
            # Triangle defined by vertices: top-left, bottom-left, right
            # right-pointing: tip at cx+tri_w*0.5, base on left
            bx = -(tri_w * 0.35)
            tip_x = tri_w * 0.45
            slope = tri_h / 2 / (tip_x - bx)
            in_tri = (
                tx >= bx and
                ty >= -(slope * (tx - bx)) and
                ty <= (slope * (tx - bx))
            )
            if in_tri:
                row += list(triangle) + [255]
            else:
                row += list(bg) + [255]
        pixels.append(bytes(row))

    # Pack PNG
    def png_chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b""
    for row in pixels:
        raw += b"\x00" + row  # filter type None

    compressed = zlib.compress(raw, 9)

    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += png_chunk(b"IDAT", compressed)
    png += png_chunk(b"IEND", b"")
    return png


def _png_to_ico(pngs_by_size: dict) -> bytes:
    """Pack one or more PNGs into a .ico file."""
    sizes = sorted(pngs_by_size.keys())
    n = len(sizes)
    header = struct.pack("<HHH", 0, 1, n)  # reserved, type=1 (ICO), count

    # Each directory entry is 16 bytes; image data follows the directory
    dir_entries = b""
    image_data = b""
    offset = 6 + 16 * n  # header + all dir entries

    for sz in sizes:
        png = pngs_by_size[sz]
        length = len(png)
        w = sz if sz < 256 else 0
        h = sz if sz < 256 else 0
        # width, height, color_count, reserved, planes, bit_count, size, offset
        dir_entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, length, offset)
        image_data += png
        offset += length

    return header + dir_entries + image_data


def main():
    os.makedirs("icons", exist_ok=True)
    bg = (26, 26, 26)        # #1a1a1a dark surface
    tri = (74, 158, 255)     # #4a9eff accent blue

    pngs = {}
    for sz in (16, 32, 48, 64, 128, 256):
        pngs[sz] = _make_png(sz, bg, tri)

    ico_data = _png_to_ico(pngs)
    with open("icons/app.ico", "wb") as f:
        f.write(ico_data)
    print("Generated icons/app.ico")


if __name__ == "__main__":
    main()
