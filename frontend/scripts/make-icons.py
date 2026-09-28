"""Draw the PWA icons (public/icons/*.png) from the favicon's shape, with the Python standard library only.

Run: python frontend/scripts/make-icons.py   (the PNGs are committed; rerun only when the mark changes)

The mark is the favicon's: a white roof and ground line on --brand (#24594A). "maskable" keeps the mark
inside the central 60 % safe zone so launchers that crop to a circle do not cut it.
"""

import math
import struct
import zlib
from pathlib import Path

BRAND = (0x24, 0x59, 0x4A)
WHITE = (0xFF, 0xFF, 0xFF)
# Favicon paths on a 32-unit grid: M6 22h20 and M9 22V12l7-4 7 4v10, stroke 2.4.
SEGMENTS = [((6, 22), (26, 22)), ((9, 22), (9, 12)), ((9, 12), (16, 8)), ((16, 8), (23, 12)),
            ((23, 12), (23, 22))]
STROKE = 2.4
OUT = Path(__file__).resolve().parent.parent / "public" / "icons"


def _dist(px: float, py: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def draw(size: int, scale: float) -> bytes:
    """RGB rows of one icon; `scale` is the share of the icon the 32-unit mark fills."""
    rows = bytearray()
    unit = size * scale / 32
    off = size * (1 - scale) / 2
    for y in range(size):
        rows.append(0)
        for x in range(size):
            gx, gy = (x + 0.5 - off) / unit, (y + 0.5 - off) / unit
            d = min(_dist(gx, gy, a, b) for a, b in SEGMENTS)
            # Two-pixel soft edge so the strokes are not jagged.
            cover = max(0.0, min(1.0, (STROKE / 2 - d) * unit / 1.5 + 0.5))
            rows.extend(round(BRAND[i] + (WHITE[i] - BRAND[i]) * cover) for i in range(3))
    return bytes(rows)


def png(size: int, scale: float) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    head = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", zlib.compress(draw(size, scale), 9))
            + chunk(b"IEND", b""))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, size, scale in [("icon-192.png", 192, 1.0), ("icon-512.png", 512, 1.0),
                              ("icon-maskable-512.png", 512, 0.6), ("apple-touch-icon.png", 180, 1.0)]:
        (OUT / name).write_bytes(png(size, scale))
        print(f"wrote {OUT / name}")
