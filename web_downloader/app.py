#!/usr/bin/env python3
"""
Academic Paper Studio - Local Web Server
Runs on Python standard library (http.server.ThreadingHTTPServer) with zero dependencies.
Exposes REST API for batch DOI processing, live progress tracking, and file streaming.
"""

import os
import sys
import json
import urllib.parse
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from downloader_core import process_batch, search_books_catalog, resolve_book_download_url

PORT = int(os.environ.get("PORT", 8765))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Global thread-safe state for real-time progress
STATE = {
    "busy": False,
    "current_index": 0,
    "total": 0,
    "message": "Listo para procesar",
    "results": [],
    "zip_file": None,
    "error": None
}
STATE_LOCK = threading.Lock()

def progress_updater(current_idx, total, message, current_item=None):
    with STATE_LOCK:
        STATE["current_index"] = current_idx + 1
        STATE["total"] = total
        STATE["message"] = message
        if current_item and not any(r["doi"] == current_item["doi"] for r in STATE["results"]):
            STATE["results"].append(current_item)

def run_background_batch(dois, options):
    global STATE
    try:
        def callback(idx, tot, msg, item):
            progress_updater(idx, tot, msg, item)

        result_data = process_batch(dois, options, progress_callback=callback, output_dir=DOWNLOADS_DIR)
        with STATE_LOCK:
            STATE["busy"] = False
            STATE["results"] = result_data["results"]
            STATE["zip_file"] = result_data["zip_file"]
            STATE["message"] = f"Completado: {result_data['success_count']} de {result_data['total']} descargados con éxito."
    except Exception as e:
        with STATE_LOCK:
            STATE["busy"] = False
            STATE["error"] = str(e)
            STATE["message"] = f"Error durante el procesamiento: {e}"

class AcademicStudioHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for local convenience and avoid caching of API
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self):
        self.do_GET(head_only=True)

    def do_GET(self, head_only=False):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. API: Get Status
        if path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            with STATE_LOCK:
                response_data = json.dumps(STATE)
            if not head_only:
                self.wfile.write(response_data.encode("utf-8"))
            return

        # 1b. API: Resolve Book MD5 Download Link (302 Redirect)
        if path == "/api/books/resolve":
            query_params = urllib.parse.parse_qs(parsed.query)
            md5_hash = (query_params.get("md5", [""])[0] or "").strip()
            target_url = resolve_book_download_url(md5_hash)
            self.send_response(302)
            self.send_header("Location", target_url)
            self.end_headers()
            return

        # 2. File Downloads
        if path.startswith("/downloads/"):
            raw_filename = urllib.parse.unquote(path[len("/downloads/"):])
            filename = os.path.basename(raw_filename)
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            if os.path.exists(filepath) and os.path.isfile(filepath):
                self.send_response(200)
                
                # RFC 6266 / RFC 5987: Clean ASCII filename for legacy clients + UTF-8 percent-encoded filename
                ascii_filename = filename.encode("ascii", "replace").decode("ascii").replace("?", "_").replace('"', '').replace(';', '')
                if not ascii_filename:
                    ascii_filename = "document.pdf" if filename.endswith(".pdf") else "download.dat"
                encoded_filename = urllib.parse.quote(filename, encoding="utf-8")
                
                disposition_header = f'inline; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'
                attachment_header = f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'

                if filename.endswith(".pdf"):
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", disposition_header)
                elif filename.endswith(".zip"):
                    self.send_header("Content-Type", "application/zip")
                    self.send_header("Content-Disposition", attachment_header)
                elif filename.endswith(".bib"):
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Disposition", attachment_header)
                elif filename.endswith(".ris"):
                    self.send_header("Content-Type", "application/x-research-info-systems; charset=utf-8")
                    self.send_header("Content-Disposition", attachment_header)
                elif filename.endswith(".enw"):
                    self.send_header("Content-Type", "application/x-endnote-refer; charset=utf-8")
                    self.send_header("Content-Disposition", attachment_header)
                elif filename.endswith(".csv"):
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                else:
                    self.send_header("Content-Type", "application/octet-stream")
                
                self.send_header("Content-Length", str(os.path.getsize(filepath)))
                self.end_headers()
                if not head_only:
                    with open(filepath, "rb") as f:
                        self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "File not found")
                return

        # 3. Serve Frontend (index.html)
        if path == "/" or path == "/index.html":
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if not head_only:
                    with open(index_path, "rb") as f:
                        self.wfile.write(f.read())
                return

        # Static assets fallback
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/process":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                dois = data.get("dois", [])
                options = data.get("options", {})

                with STATE_LOCK:
                    if STATE["busy"]:
                        self.send_response(409)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "Un lote ya está en procesamiento"}).encode("utf-8"))
                        return

                    STATE["busy"] = True
                    STATE["current_index"] = 0
                    STATE["total"] = len(dois)
                    STATE["message"] = f"Iniciando procesamiento de {len(dois)} artículos..."
                    STATE["results"] = []
                    STATE["zip_file"] = None
                    STATE["error"] = None

                # Launch processing in background thread
                th = threading.Thread(target=run_background_batch, args=(dois, options), daemon=True)
                th.start()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "message": "Proceso iniciado"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if path == "/api/reset":
            with STATE_LOCK:
                STATE["busy"] = False
                STATE["current_index"] = 0
                STATE["total"] = 0
                STATE["message"] = "Listo para procesar"
                STATE["results"] = []
                STATE["zip_file"] = None
                STATE["error"] = None

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        if path == "/api/books/search":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                query = data.get("query", "")
                lang = data.get("lang", "all")
                year_from = data.get("year_from", "")
                year_to = data.get("year_to", "")
                ext = data.get("ext", "all")
                page = data.get("page", 1)
                page_size = data.get("page_size", 25)

                res = search_books_catalog(
                    query=query,
                    lang=lang,
                    year_from=year_from,
                    year_to=year_to,
                    ext=ext,
                    page=page,
                    page_size=page_size
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        self.send_error(404, "Endpoint not found")

def start_server():
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, AcademicStudioHandler)
    print(f"\n=======================================================")
    print(f" Academic Paper Studio Server Activo")
    print(f" URL Local: http://localhost:{PORT}")
    print(f" Presiona Ctrl + C en cualquier momento para detener")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        httpd.server_close()

if __name__ == "__main__":
    start_server()
