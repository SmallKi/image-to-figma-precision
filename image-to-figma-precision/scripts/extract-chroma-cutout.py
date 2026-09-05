"""Convert a high-resolution solid-chroma render into a decontaminated RGBA cutout.

Use an independently reviewed alpha mask and a verified solid background.
Colour-distance alpha is available only as an explicitly requested heuristic:
it cannot identify mixed edge colours or distinguish highlights from background.
This produces a candidate, never a visual pass. See references/edge-cleanup.md.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def parse_pair(value):
    a, b = value.lower().split("x")
    return int(a), int(b)


def parse_box(value):
    result = tuple(int(v) for v in value.split(","))
    if len(result) != 4:
        raise argparse.ArgumentTypeError("target box must be x,y,w,h")
    return result


def premultiplied_resize(rgba, size):
    if len(size) != 2 or min(size) <= 0:
        raise ValueError("Resize dimensions must be positive")
    rgba = rgba.astype(np.float32) / 255
    alpha = rgba[:, :, 3:4]
    premul = rgba[:, :, :3] * alpha
    channels = []
    for index in range(3):
        plane = Image.fromarray(np.clip(premul[:, :, index] * 65535, 0, 65535).astype(np.uint16), "I;16")
        channels.append(np.asarray(plane.resize(size, Image.Resampling.LANCZOS), dtype=np.float32) / 65535)
    alpha_image = Image.fromarray(np.clip(alpha[:, :, 0] * 65535, 0, 65535).astype(np.uint16), "I;16")
    resized_alpha = np.asarray(alpha_image.resize(size, Image.Resampling.LANCZOS), dtype=np.float32) / 65535
    resized_premul = np.stack(channels, axis=2)
    rgb = np.zeros_like(resized_premul)
    valid = resized_alpha > 1 / 65535
    rgb[valid] = resized_premul[valid] / resized_alpha[valid, None]
    result = np.rint(np.dstack((np.clip(rgb * 255, 0, 255), np.clip(resized_alpha * 255, 0, 255)))).astype(np.uint8)
    result[result[:, :, 3] == 0, :3] = 0
    return result


def unmatte(rgb, alpha, background):
    """Uncompose in the input RGB encoding; caller must establish this model.

    Preserve all fully opaque RGB and every alpha value, including thin parts
    and holes. Low-alpha estimates amplify source quantization, so report them.
    No erosion, colour-key deletion, blur, or invented inward colour propagation.
    """
    rgb = np.asarray(rgb, dtype=np.float64)
    alpha = np.asarray(alpha, dtype=np.float64)
    background = np.asarray(background, dtype=np.float64)
    if rgb.shape != (*alpha.shape, 3) or background.shape != (3,):
        raise ValueError("RGB, alpha and background shapes do not match")
    if not all(np.isfinite(a).all() for a in (rgb, alpha, background)):
        raise ValueError("Non-finite input")
    if np.any((alpha < 0) | (alpha > 1)) or np.any((background < 0) | (background > 255)):
        raise ValueError("Alpha or background outside valid range")
    partial = (alpha > 0) & (alpha < 1)
    foreground = rgb.copy()
    foreground[partial] = (rgb[partial] - (1 - alpha[partial, None]) * background) / alpha[partial, None]
    out_of_gamut = partial & ((foreground < -2) | (foreground > 257)).any(axis=2)
    result = np.rint(np.dstack((np.clip(foreground, 0, 255), alpha * 255))).astype(np.uint8)
    result[result[:, :, 3] == 0, :3] = 0
    diagnostics = {
        "partialPixels": int(partial.sum()),
        "lowAlphaPixels": int(((alpha > 0) & (alpha < .1)).sum()),
        "outOfGamutPixels": int(out_of_gamut.sum()),
        "outOfGamutFraction": float(out_of_gamut.sum() / max(1, partial.sum())),
        "alphaChangedPixels": 0,
        "opaqueRgbChangedPixels": int((result[:, :, :3][alpha == 1] != np.rint(rgb[alpha == 1])).any(axis=1).sum()),
    }
    return result, diagnostics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--low", type=float)
    parser.add_argument("--high", type=float, default=80)
    parser.add_argument("--border", type=int, default=48)
    parser.add_argument("--target-size", type=parse_pair)
    parser.add_argument("--target-box", type=parse_box)
    parser.add_argument("--report")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--alpha-mask", help="Registered grayscale PNG alpha, obtained independently of colour distance")
    mode.add_argument("--allow-heuristic-alpha", action="store_true", help="Legacy colour key; unreviewed candidate only")
    parser.add_argument("--background-rgb", help="Verified solid matte R,G,B; border is still checked")
    parser.add_argument("--max-border-distance", type=float, default=5,
                        help="Maximum 99th-percentile border RGB distance from the solid matte")
    parser.add_argument("--trim", action="store_true", help="Opt in to cropping; otherwise preserve registration")
    args = parser.parse_args()

    if Path(args.input).resolve() == Path(args.output).resolve():
        parser.error("Keep the source; output must be a different file")
    if args.alpha_mask and Path(args.alpha_mask).resolve() == Path(args.output).resolve():
        parser.error("Output must not overwrite the alpha mask")
    if args.alpha_mask and (args.low is not None or args.high != 80):
        parser.error("Colour thresholds do not apply to an independent alpha mask")
    if args.border < 1 or not np.isfinite(args.max_border_distance) or args.max_border_distance < 0:
        parser.error("Invalid border parameters")
    if args.target_box and not args.target_size:
        parser.error("--target-box requires --target-size")
    if args.target_size:
        tw, th = args.target_size
        x, y, bw, bh = args.target_box or (0, 0, tw, th)
        if min(tw, th, bw, bh) <= 0 or min(x, y) < 0 or x + bw > tw or y + bh > th:
            parser.error("Target box must be positive and inside the target canvas")
    with Image.open(args.input) as source:
        if np.any(np.asarray(source.convert("RGBA"))[:, :, 3] != 255):
            parser.error("Input must be a matte-composited image; do not unmatte already transparent RGBA")
        rgb = np.asarray(source.convert("RGB"), dtype=np.float32)
    h, w = rgb.shape[:2]
    border = max(1, min(args.border, h // 4, w // 4))
    samples = np.concatenate((rgb[:border].reshape(-1, 3), rgb[-border:].reshape(-1, 3),
                              rgb[:, :border].reshape(-1, 3), rgb[:, -border:].reshape(-1, 3)))
    background = np.median(samples, axis=0)
    if args.background_rgb:
        try:
            background = np.asarray([float(v) for v in args.background_rgb.split(",")])
        except ValueError:
            parser.error("--background-rgb must be R,G,B")
        if background.shape != (3,) or not np.isfinite(background).all() or np.any((background < 0) | (background > 255)):
            parser.error("--background-rgb must contain three values in 0..255")
    border_distance = np.sqrt(((samples - background) ** 2).sum(axis=1))
    border_p99 = float(np.quantile(border_distance, .99))
    if border_p99 > args.max_border_distance:
        parser.error("Border is not a verified solid matte; use a clean background estimate or another extraction method")
    low = None
    if args.alpha_mask:
        with Image.open(args.alpha_mask) as mask:
            if mask.size != (w, h) or mask.mode not in ("1", "L"):
                parser.error("Alpha mask must be registered 8-bit grayscale at input dimensions")
            alpha = np.asarray(mask.convert("L"), dtype=np.float64) / 255
        if not np.any(alpha == 0) or not np.any(alpha == 1):
            parser.error("Solid icon alpha needs transparent exterior and opaque core")
        if not np.any((alpha > 0) & (alpha < 1)):
            parser.error("Binary alpha cannot recover mixed edges; supply a reviewed antialiased mask")
    else:
        low = args.low if args.low is not None else max(8.0, float(np.quantile(border_distance, .999)) + 2)
        if not np.isfinite(low) or not np.isfinite(args.high) or low < 0 or args.high <= low:
            parser.error("--high must exceed the nonnegative transparent threshold")
        distance = np.sqrt(((rgb - background) ** 2).sum(axis=2))
        t = np.clip((distance - low) / (args.high - low), 0, 1)
        alpha = t * t * (3 - 2 * t)
    rgba, diagnostics = unmatte(rgb, alpha, background)

    ys, xs = np.where(rgba[:, :, 3] > 0)
    if not len(xs):
        raise SystemExit("No foreground detected")
    pad = 4
    crop = (0, 0, w, h)
    if args.trim:
        crop = (max(0, int(xs.min()) - pad), max(0, int(ys.min()) - pad),
                min(w, int(xs.max()) + pad + 1), min(h, int(ys.max()) + pad + 1))
    rgba = rgba[crop[1]:crop[3], crop[0]:crop[2]]

    if args.target_size:
        target_w, target_h = args.target_size
        box = args.target_box or (0, 0, target_w, target_h)
        x, y, box_w, box_h = box
        scale = min(box_w / rgba.shape[1], box_h / rgba.shape[0])
        resized_size = (max(1, round(rgba.shape[1] * scale)), max(1, round(rgba.shape[0] * scale)))
        resized = premultiplied_resize(rgba, resized_size)
        canvas = np.zeros((target_h, target_w, 4), dtype=np.uint8)
        px = x + (box_w - resized_size[0]) // 2
        py = y + (box_h - resized_size[1]) // 2
        canvas[py:py + resized_size[1], px:px + resized_size[0]] = resized
        rgba = canvas

    output = Path(args.output)
    Image.fromarray(rgba, "RGBA").save(output)
    alpha_out = rgba[:, :, 3]
    report = {
        "input": str(args.input), "output": str(output), "size": list(Image.open(output).size),
        "sampledBackgroundRgb": [round(float(v), 3) for v in background],
        "method": "independent-alpha-unmatte" if args.alpha_mask else "heuristic-chroma-unmatte",
        "status": "candidate-needs-visual-review",
        "inputSha256": hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),
        "alphaMaskSha256": hashlib.sha256(Path(args.alpha_mask).read_bytes()).hexdigest() if args.alpha_mask else None,
        "sourceCrop": list(crop), "targetBox": list(box) if args.target_size else None,
        "borderDistanceP99": border_p99, "unmatteDiagnostics": diagnostics,
        "transparentDistance": low, "opaqueDistance": args.high if not args.alpha_mask else None,
        "alphaLevels": int(np.unique(alpha_out).size),
        "transparentPixels": int((alpha_out == 0).sum()),
        "partialAlphaPixels": int(((alpha_out > 0) & (alpha_out < 255)).sum()),
        "opaquePixels": int((alpha_out == 255).sum()),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
