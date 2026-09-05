"""Inspect actual icon transparency. No image pixels are edited.
Passing raw checks is necessary, never sufficient, for a clean cutout.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image


def inspect(path, expected_size=None):
    path = Path(path)
    with Image.open(path) as im:
        mode, size = im.mode, im.size
        has_alpha = 'A' in im.getbands() or 'transparency' in im.info
        alpha = np.asarray(im.convert('RGBA'))[:, :, 3]
    failures = []
    if not has_alpha:
        failures.append('no_transparency_channel')
    if not np.any(alpha == 0):
        failures.append('no_fully_transparent_pixels')
    if not np.any(alpha > 0):
        failures.append('empty_foreground')
    if expected_size is not None and tuple(expected_size) != size:
        failures.append('unexpected_dimensions')
    perimeter = np.concatenate((alpha[0, :], alpha[-1, :], alpha[1:-1, 0], alpha[1:-1, -1]))
    return {
        'file': str(path.resolve()),
        'sourceSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'mode': mode, 'size': list(size), 'hasAlpha': has_alpha,
        'transparentPixels': int(np.count_nonzero(alpha == 0)),
        'opaquePixels': int(np.count_nonzero(alpha == 255)),
        'partialAlphaPixels': int(np.count_nonzero((alpha > 0) & (alpha < 255))),
        'nontransparentPerimeterFraction': float(np.mean(perimeter > 0)),
        'rawGate': 'fail' if failures else 'pass', 'failures': failures,
        'visualReviewRequired': True,
        'limits': 'Does not detect matte fringes, opaque islands, fake checkerboards inside alpha, missing foreground, or baked text. Inspect white/black/magenta backgrounds.'
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('--size', nargs=2, type=int, metavar=('WIDTH', 'HEIGHT'))
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    report = inspect(args.image, args.size)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report['rawGate'] == 'pass' else 1)
