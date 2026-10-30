"""Web server for the Lexical Analyzer Tool (standard library only).  Run: python app.py [port]"""
import json, mimetypes, os, sys, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from lexer import analyze, LANGS

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
SAMPLES = [
 {'name': 'C - factorial & sum', 'language': 'c', 'code': '#include <stdio.h>\n/* Sum and average */\nint main() {\n    int count = 10, total = 0;\n    float avg = 0.0;\n    for (int i = 1; i <= count; i++) {\n        total += i;\n    }\n    avg = total / 2.5;\n    printf("Total = %d\\n", total);\n    return 0;\n}\n'},
 {'name': 'C - with lexical errors', 'language': 'c', 'code': 'int main() {\n    int 2x = 5;\n    int $price = 3;\n    char c = \'ab;\n    printf("hello);\n    if (x > 0 {\n        x = x @ 2;\n    }\n}\n'},
 {'name': 'Java - class', 'language': 'java', 'code': 'public class Hello {\n    // entry point\n    public static void main(String[] args) {\n        int x = 0x1F + 42;\n        boolean ok = x >= 10 && true;\n        System.out.println("Value: " + x);\n    }\n}\n'},
 {'name': 'Python - function', 'language': 'python', 'code': 'def area(r):\n    # circle area\n    return 3.14159 * r ** 2\n\nif __name__ == "__main__":\n    print(f"Area: {area(5)}")\n'},
 {'name': 'JavaScript - arrow fn', 'language': 'js', 'code': 'const add = (a, b) => a + b;\nlet total = add(2, 3) * 1.5e2;\nif (total === 750 && !false) {\n  console.log(`Total ${total}`);\n}\n'},
]

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, ctype='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status=200):
        self._send(status, json.dumps(obj).encode())

    def do_GET(self):
        p = self.path.split('?')[0]
        if p == '/api/meta':
            return self._json({'languages': LANGS, 'samples': SAMPLES})
        f = os.path.normpath(os.path.join(ROOT, 'index.html' if p == '/' else p.lstrip('/')))
        if not f.startswith(ROOT) or not os.path.isfile(f):
            return self._send(404, b'Not found', 'text/plain')
        with open(f, 'rb') as fh:
            self._send(200, fh.read(), mimetypes.guess_type(f)[0] or 'application/octet-stream')

    def do_POST(self):
        if self.path != '/api/analyze':
            return self._json({'error': 'Not found'}, 404)
        n = int(self.headers.get('Content-Length') or 0)
        if n > 1_000_000:
            return self._json({'error': 'Input too large (max 1 MB)'}, 413)
        try:
            d = json.loads(self.rfile.read(n))
            res = analyze(str(d.get('code', '')), d.get('language', 'c'))
        except (ValueError, AttributeError):
            return self._json({'error': 'Invalid request'}, 400)
        self._json(res)

    def log_message(self, *a):
        pass

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    while True:
        try:
            srv = ThreadingHTTPServer(('127.0.0.1', port), Handler); break
        except OSError:
            port += 1
    url = 'http://127.0.0.1:%d' % port
    print('Lexical Analyzer Tool running at', url, '(Ctrl+C to stop)')
    if '--no-browser' not in sys.argv:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
