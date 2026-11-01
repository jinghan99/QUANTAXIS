"""Serve the upstream community release with local dependencies and API URLs."""
import json
import mimetypes
import os
import re
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

PROFILE = os.getenv("QUANTAXIS_ENV", "dev")
SOURCE = Path(os.getenv("QA_FRONTEND_SOURCE", str(Path(__file__).resolve().parents[2] / "qamazing_community")))
PORT = int(os.getenv("QA_FRONTEND_PORT", "8080"))
BACKEND_PORT = int(os.getenv("QA_BACKEND_PORT", "18089"))
RUNTIME = Path(os.environ['LOCALAPPDATA']) / 'quantaxis-local' if os.name == 'nt' else Path.home() / '.local/share/quantaxis-local'
VENDOR = RUNTIME / "vendor"
VENDOR.mkdir(parents=True, exist_ok=True)


def asset_path(url):
    return VENDOR / url.split("/npm/", 1)[1]


def download(url):
    target = asset_path(url)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(url, timeout=60) as response:
            content = response.read()
        target.write_bytes(content)
    return target


def prepare():
    html = (SOURCE / "index.html").read_text(encoding="utf-8")
    urls = set(re.findall(r'https://cdn\.jsdelivr\.net/npm/[^"\s]+', html))
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(download, sorted(urls)))
    # Element UI's stylesheet references fonts relative to its own URL.
    for suffix in ("woff", "ttf"):
        download("https://cdn.jsdelivr.net/npm/element-ui@2.13.0/lib/theme-chalk/fonts/element-icons." + suffix)
    for url in urls:
        html = html.replace(url, "/vendor/" + url.split("/npm/", 1)[1])
    html = re.sub(r'<script>var _hmt.*?</script>', "", html, flags=re.S)
    config = """<script>
    if (!localStorage.getItem('quantaxis-local-v1')) {
      const root = location.origin;
      localStorage.setItem('URL', JSON.stringify({
        backtestURL: root + '/api', backtestQifiURL: root + '/api',
        accRealtimeURL: root + '/unavailable/realtime',
        wsURL: 'ws://' + location.host + '/unavailable/ws',
        tradeDataURL: root + '/unavailable/trade',
        klineURL: root + '/unavailable/kline',
        financialURL: root + '/unavailable/financial'
      }));
      localStorage.setItem('quantaxis-local-v1', '1');
    }
    </script>"""
    return html.replace("<head>", "<head>" + config).encode("utf-8")


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(self.server.local_index)
        elif path.startswith("/api/"):
            try:
                with urlopen("http://127.0.0.1:" + str(BACKEND_PORT) + self.path[4:], timeout=10) as response:
                    data = response.read()
                    self.send_response(response.status)
                    self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                    self.end_headers()
                    self.wfile.write(data)
            except HTTPError as exc:
                self.send_response(exc.code)
                self.end_headers()
                self.wfile.write(exc.read())
            except (URLError, TimeoutError) as exc:
                self.send_error(502, "QUANTAXIS backend unavailable: " + str(exc))
        elif path.startswith("/unavailable/"):
            self.send_response(503)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "unsupported", "message": "This optional service is not installed in the local environment.", "service": path}).encode())
        else:
            super().do_GET()

    def translate_path(self, path):
        parsed = urlparse(path).path
        if parsed.startswith("/vendor/"):
            target = (VENDOR / parsed[len("/vendor/"):]).resolve()
            if target.is_relative_to(VENDOR.resolve()):
                return str(target)
            return str(VENDOR / "__invalid__")
        return super().translate_path(path)


if __name__ == "__main__":
    index = prepare()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(SOURCE)))
    server.local_index = index
    print(f"QUANTAXIS community {PROFILE}: http://localhost:{PORT}", flush=True)
    server.serve_forever()
