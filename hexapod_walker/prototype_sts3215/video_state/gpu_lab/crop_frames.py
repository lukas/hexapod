"""Crop the robot band (top of frame, full 1280x720 resolution) from every labelled vision_frames jpg."""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import cv2
AS = Path.home() / "Library/Application Support/Hexapod Lab/v2/runs"
OUT = Path.home() / "hexapod-vision-data/crops"
X0, X1, Y0, Y1 = 200, 1080, 0, 360   # robot sits at the top edge, roughly centred

def job(rel):
    run, proto = rel.split("/")[1].split("__", 1)
    src = AS / run / proto / "vision_frames" / Path(rel).name
    dst = OUT / rel.split("/", 1)[1]
    if dst.exists():
        return True
    im = cv2.imread(str(src))
    if im is None:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst), im[Y0:Y1, X0:X1], [cv2.IMWRITE_JPEG_QUALITY, 90])
    return True

if __name__ == "__main__":
    rows = [json.loads(l)["frame"] for l in open(Path.home() / "hexapod-vision-data/labels.jsonl")]
    with ProcessPoolExecutor(16) as ex:
        ok = sum(ex.map(job, rows, chunksize=128))
    print("cropped", ok, "of", len(rows))
