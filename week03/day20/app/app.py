import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

print("Hello world", flush=True)

greeting = os.environ.get("GREETING")
if not greeting:
    print("ERROR: GREETING env is required")
    sys.exit(1)

print("GREETING =", greeting)
print("APP_VERSION =", os.environ.get("APP_VERSION"))
print("PID =", os.getpid(), flush=True)


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        super().do_GET()


HTTPServer(("", 8080), Handler).serve_forever()
