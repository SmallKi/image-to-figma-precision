"""Deterministic regression for matte spill; no model or Figma calls.

Run: python scripts/test-edge-cleanup.py --out <evidence-directory>
Synthetic ground truth covers opaque pale highlights, a hole, and a thin stem.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw


HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("chroma", HERE / "extract-chroma-cutout.py")
chroma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chroma)


def fixture():
    scale = 4
    mask = Image.new("L", (128 * scale, 128 * scale))
    draw = ImageDraw.Draw(mask)
    draw.ellipse((20*scale, 14*scale, 108*scale, 102*scale), fill=255)
    draw.ellipse((40*scale, 34*scale, 88*scale, 82*scale), fill=0)
    draw.rectangle((63*scale, 96*scale, 65*scale, 115*scale), fill=255)
    alpha = np.asarray(mask.resize((128, 128), Image.Resampling.LANCZOS))
    foreground = np.full((128, 128, 3), (221, 153, 31), dtype=np.uint8)
    foreground[20:29, 55:73] = (255, 251, 230)
    # Same-colour foreground as the matte must survive when it is known solid.
    foreground[88:95, 55:73] = (24, 96, 112)
    matte = np.array([24, 96, 112])
    a = alpha[:, :, None] / 255
    source = np.rint(foreground * a + matte * (1 - a)).astype(np.uint8)
    truth = np.dstack((foreground, alpha))
    truth[alpha == 0, :3] = 0
    return source, alpha, truth, matte


def composite(rgba, bg):
    a = rgba[:, :, 3:4] / 255
    return rgba[:, :, :3] * a + np.asarray(bg) * (1 - a)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    source, alpha, truth, matte = fixture()
    corrected, diagnostics = chroma.unmatte(source, alpha / 255, matte)
    partial = (alpha > 0) & (alpha < 255)
    before = np.dstack((source, alpha))
    checks = []

    def check(name, condition):
        checks.append({"name": name, "pass": bool(condition)})
        if not condition:
            raise AssertionError(name)

    check("alpha_and_topology_unchanged", np.array_equal(corrected[:, :, 3], alpha))
    check("opaque_highlights_and_matte_coloured_foreground_preserved",
          np.array_equal(corrected[:, :, :3][alpha == 255], source[alpha == 255]))
    check("hidden_rgb_zero", np.all(corrected[:, :, :3][alpha == 0] == 0))
    backgrounds = [(255, 255, 255), (0, 0, 0), (255, 0, 255), (0, 255, 255), tuple(matte)]
    metrics = []
    for bg in backgrounds:
        old_error = float(np.abs(composite(before, bg) - composite(truth, bg))[partial].mean())
        new_error = float(np.abs(composite(corrected, bg) - composite(truth, bg))[partial].mean())
        metrics.append({"background": list(map(int, bg)), "beforeEdgeMae": old_error, "afterEdgeMae": new_error})
        check("edge_recovery_" + str(bg), new_error < .6 and new_error < old_error / 10)

    poisoned = truth.copy()
    poisoned[alpha == 0, :3] = (255, 0, 255)
    down_clean = chroma.premultiplied_resize(truth, (48, 48))
    down_poisoned = chroma.premultiplied_resize(poisoned, (48, 48))
    check("resize_ignores_hidden_matte_rgb", np.array_equal(down_clean, down_poisoned))
    check("resize_zeroes_transparent_rgb", np.all(down_clean[down_clean[:, :, 3] == 0, :3] == 0))

    # Compare physical alpha with the former distance-key saturation.
    distance = np.linalg.norm(source.astype(float) - matte, axis=2)
    check("old_key_misclassifies_mixed_edges_as_opaque", np.any(partial & (distance >= 80)))

    Image.fromarray(source).save(out / "source-matte.png")
    Image.fromarray(alpha).save(out / "reviewed-alpha.png")
    Image.fromarray(truth).save(out / "ground-truth.png")
    Image.fromarray(before).save(out / "alpha-only-before.png")
    Image.fromarray(corrected).save(out / "unmatte-after.png")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        command = [sys.executable, str(HERE / "extract-chroma-cutout.py"),
                   str(out / "source-matte.png"), str(tmp / "candidate.png")]

        def run(options):
            return subprocess.run(command + options, capture_output=True, text=True)

        mask_args = ["--alpha-mask", str(out / "reviewed-alpha.png"), "--border", "4"]
        result = run(mask_args + ["--report", str(tmp / "report.json")])
        check("cli_independent_alpha_succeeds", result.returncode == 0)
        with Image.open(tmp / "candidate.png") as im:
            check("cli_preserves_canvas_and_matches_math", np.array_equal(np.asarray(im), corrected))
        report = json.loads((tmp / "report.json").read_text())
        check("cli_does_not_claim_visual_pass", report["status"] == "candidate-needs-visual-review")
        check("cli_requires_explicit_alpha_method", run([]).returncode != 0)
        check("cli_rejects_out_of_bounds_target", run(mask_args + ["--target-size", "32x32", "--target-box", "30,0,16,16"]).returncode != 0)
        check("cli_target_resize", run(mask_args + ["--trim", "--target-size", "48x48", "--target-box", "4,4,40,40"]).returncode == 0)
        check("heuristic_remains_explicit_candidate", run(["--allow-heuristic-alpha", "--border", "4"]).returncode == 0)
        binary = tmp / "binary.png"
        Image.fromarray((alpha >= 128).astype(np.uint8) * 255).save(binary)
        check("cli_rejects_binary_alpha_for_unmatting", run(["--alpha-mask", str(binary), "--border", "4"]).returncode != 0)
        checker = source.copy()
        checker[:4, ::2] = 255
        Image.fromarray(checker).save(tmp / "checker.png")
        original_input = command[2]
        command[2] = str(tmp / "checker.png")
        check("cli_rejects_nonuniform_background", run(mask_args).returncode != 0)
        command[2] = str(out / "ground-truth.png")
        check("cli_rejects_double_unmatting_rgba", run(mask_args).returncode != 0)
        command[2] = original_input

    # Synthetic evidence only, clearly labelled; not an actual icon acceptance.
    zoom = 3
    cell = 128 * zoom
    sheet = Image.new("RGB", (cell * 3, (cell + 28) * 2), (32, 32, 32))
    draw = ImageDraw.Draw(sheet)
    for row, bg in enumerate([(0, 0, 0), (255, 0, 255)]):
        for col, (label, rgba) in enumerate([("ALPHA ONLY / CONTAMINATED", before), ("INDEPENDENT ALPHA + UNMATTE", corrected), ("SYNTHETIC GROUND TRUTH", truth)]):
            x, y = col * cell, row * (cell + 28)
            draw.text((x + 5, y + 8), label, fill="white")
            panel = Image.fromarray(np.rint(composite(rgba, bg)).astype(np.uint8))
            sheet.paste(panel.resize((cell, cell), Image.Resampling.NEAREST), (x, y + 28))
    sheet.save(out / "comparison.png")
    summary = {"type": "synthetic-regression-not-figma-or-model-validation", "pass": all(c["pass"] for c in checks),
               "checks": checks, "metrics": metrics, "diagnostics": diagnostics}
    (out / "report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"pass": summary["pass"], "checks": len(checks), "metrics": metrics, "report": str(out / "report.json")}))


if __name__ == "__main__":
    main()
