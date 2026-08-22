"""Static server for the review viewer, with HTTP Range support and a save endpoint.

Python's stock http.server ignores Range headers and answers 200 with the whole file. Browsers
need 206 partial responses to seek inside a video, so without this a reviewer can only watch
forward from the start — which is useless for frame-stepping to a specific event.

It also accepts POST /save, because the viewer is no longer only for looking. Hand-marked ball
positions are the one thing this project has never had: there is no ball ground truth anywhere,
which is why every tuning decision so far has been argued rather than measured. A browser cannot
write to disk, so the labels come back here.

Writes go through a temporary file and an atomic rename, so a save interrupted halfway cannot
destroy a labelling session that took a person an hour.
"""
import argparse
import json
import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


class RangeHandler(SimpleHTTPRequestHandler):
    save_dir = "."

    def do_POST(self):
        if self.path.rstrip("/") != "/save":
            self.send_error(404, "Only /save accepts POST")
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0 or n > 32 * 1024 * 1024:
                raise ValueError(f"implausible body length {n}")
            body = json.loads(self.rfile.read(n))
            name = str(body.get("name", "labels")).strip()
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", name):
                raise ValueError(f"unsafe label file name {name!r}")
            dest = os.path.join(self.save_dir, f"{name}.json")
            tmp = dest + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(body, fh, indent=1, sort_keys=True)
            os.replace(tmp, dest)          # atomic: a half-written save cannot clobber
            n_lab = len(body.get("labels", {}))
        except Exception as exc:
            self.send_error(400, f"save failed: {exc}")
            return
        out = json.dumps({"ok": True, "path": dest, "n": n_lab}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)
        print(f"saved {n_lab} labels -> {dest}", flush=True)

    def send_head(self):
        rng = self.headers.get("Range")
        if not rng:
            return super().send_head()

        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None

        size = os.fstat(f.fileno()).st_size
        m = RANGE_RE.match(rng.strip())
        if not m:
            f.close()
            self.send_error(400, "Malformed Range header")
            return None
        start_s, end_s = m.groups()
        if start_s:
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
        else:                                   # suffix form: bytes=-N
            start, end = max(0, size - int(end_s)), size - 1
        if start >= size:
            f.close()
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        end = min(end, size - 1)

        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        f.seek(start)
        self._limit = end - start + 1
        return _Limited(f, self._limit)

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        if "206" not in (args[1] if len(args) > 1 else ""):
            super().log_message(fmt, *args)


class _Limited:
    """File wrapper that stops after n bytes, so copyfile sends only the requested range."""

    def __init__(self, f, n):
        self.f, self.n = f, n

    def read(self, size=-1):
        if self.n <= 0:
            return b""
        if size is None or size < 0:
            size = self.n
        chunk = self.f.read(min(size, self.n))
        self.n -= len(chunk)
        return chunk

    def close(self):
        self.f.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default="viewer")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--labels", default=None,
                   help="where POST /save writes (default: alongside the served files)")
    a = p.parse_args()
    RangeHandler.save_dir = a.labels or a.dir
    handler = partial(RangeHandler, directory=a.dir)
    srv = ThreadingHTTPServer(("0.0.0.0", a.port), handler)
    print(f"serving {a.dir} on http://0.0.0.0:{a.port} with Range support; "
          f"POST /save writes to {RangeHandler.save_dir}/", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
