# -*- coding: utf-8 -*-
"""
Download Pretendard static OTF weights (Regular/Medium/SemiBold/Bold) into a
fonts/ directory so figstyle.py can register them with matplotlib.

Usage:  python fetch_pretendard.py [target_fonts_dir]      (default: ./fonts)
Pretendard is SIL OFL 1.1 — redistribution and bundling permitted.
"""
import io
import os
import sys
import zipfile
import urllib.request

VERSION = "1.3.9"
URL = (f"https://github.com/orioncactus/pretendard/releases/download/"
       f"v{VERSION}/Pretendard-{VERSION}.zip")
WEIGHTS = ("Pretendard-Regular.otf", "Pretendard-Medium.otf",
           "Pretendard-SemiBold.otf", "Pretendard-Bold.otf")


def main(target="fonts"):
    os.makedirs(target, exist_ok=True)
    print("downloading", URL)
    data = urllib.request.urlopen(URL, timeout=180).read()
    print(f"  {len(data) / 1e6:.1f} MB")
    zf = zipfile.ZipFile(io.BytesIO(data))
    members = {os.path.basename(n): n for n in zf.namelist()
               if "static" in n and os.path.basename(n) in WEIGHTS}
    for w in WEIGHTS:
        if w not in members:
            print("  WARN missing", w)
            continue
        with zf.open(members[w]) as src, open(os.path.join(target, w), "wb") as out:
            out.write(src.read())
        print("  saved", w)
    print("done ->", os.path.abspath(target))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fonts")
