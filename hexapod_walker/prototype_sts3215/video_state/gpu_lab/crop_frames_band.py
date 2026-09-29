"""Tighten the E5 pose crops: keep the top 220 rows of the 880x360 robot-band crops made by prep_upload_data/crop step (see RESULTS.md E5)."""
import glob, cv2, os
from concurrent.futures import ProcessPoolExecutor
def job(p):
    im = cv2.imread(p); dst = p.replace("/crops/", "/crops220/")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    cv2.imwrite(dst, im[0:220], [cv2.IMWRITE_JPEG_QUALITY, 85]); return 1
if __name__ == "__main__":
    fs = glob.glob(os.path.expanduser("~/hexapod-vision-data/crops/*/*.jpg"))
    with ProcessPoolExecutor(16) as ex: print(sum(ex.map(job, fs, chunksize=256)), "files")
