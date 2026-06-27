from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pgai_patient_bot.checkpoint import load_config, twiml_for_stream


def media_websocket_url(config):
    base = config.public_media_base_url or config.public_base_url
    if base.startswith("https://"):
        base = "wss://" + base.removeprefix("https://")
    elif base.startswith("http://"):
        base = "ws://" + base.removeprefix("http://")
    return f"{base}/media"


def response_for_path(path, config):
    if path == "/twiml":
        return (
            200,
            {"Content-Type": "text/xml"},
            twiml_for_stream(
                media_websocket_url(config),
                status_callback_url=f"{config.public_base_url}/stream-status",
            ),
        )
    return 404, {"Content-Type": "text/plain"}, "not found\n"


def make_handler(config):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            status, headers, body = response_for_path(self.path, config)
            payload = body.encode()
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format, *args):
            pass

    return Handler


def make_server(env, host="127.0.0.1", port=8000, server_class=ThreadingHTTPServer):
    config = load_config(env)
    return server_class((host, port), make_handler(config))


def serve(env, host="127.0.0.1", port=8000):
    make_server(env, host, port).serve_forever()
