#!/usr/bin/env python3
"""
Proyecto 2 - Academic Paper Studio: Buscador Académico & Perfiles de Investigadores
Runs on Python standard library (http.server.ThreadingHTTPServer) with zero dependencies.
Connects to Google Scholar, ORCID Public API v3.0, and Scopus (Elsevier).
"""

import os
import sys
import json
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# Add current directory and parent to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from backend import scholar_engine, orcid_engine, scopus_engine, profile_aggregator

PORT = int(os.environ.get("PORT_PROYECTO2", 8766))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)


class Proyecto2Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
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
        query_params = urllib.parse.parse_qs(parsed.query)

        # 1. API Status
        if path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            status_data = {
                "name": "Proyecto 2 - Buscador Académico & Perfiles",
                "version": "1.0",
                "scholar_ready": scholar_engine.is_available(),
                "orcid_ready": True,
                "scopus_ready": bool(scopus_engine.get_api_key()),
                "port": PORT
            }
            if not head_only:
                self.wfile.write(json.dumps(status_data).encode("utf-8"))
            return

        # 2. API: ORCID Works by ORCID iD
        if path == "/api/orcid/works":
            orcid_id = query_params.get("id", [""])[0].strip()
            limit = int(query_params.get("limit", [30])[0])
            works = orcid_engine.get_researcher_works(orcid_id, limit=limit)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            if not head_only:
                self.wfile.write(json.dumps({"orcid_id": orcid_id, "works": works}).encode("utf-8"))
            return

        # 3. API: Scholar Author In-depth Details
        if path == "/api/scholar/author_details":
            scholar_id = query_params.get("id", [""])[0].strip()
            details = scholar_engine.get_author_details(scholar_id)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            if not head_only:
                self.wfile.write(json.dumps(details).encode("utf-8"))
            return

        # 4. Serve index.html
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

        # 5. Serve Favicon at root (/favicon.ico)
        if path == "/favicon.ico":
            ico_path = os.path.join(STATIC_DIR, "favicon.ico")
            if os.path.exists(ico_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/x-icon")
                self.send_header("Content-Length", str(os.path.getsize(ico_path)))
                self.end_headers()
                if not head_only:
                    with open(ico_path, "rb") as f:
                        self.wfile.write(f.read())
                return

        # 6. Static files (/static/*)
        if path.startswith("/static/"):
            rel_path = urllib.parse.unquote(path[len("/static/"):])
            file_path = os.path.join(STATIC_DIR, rel_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.send_response(200)
                if file_path.endswith(".png"):
                    self.send_header("Content-Type", "image/png")
                elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                    self.send_header("Content-Type", "image/jpeg")
                elif file_path.endswith(".ico"):
                    self.send_header("Content-Type", "image/x-icon")
                elif file_path.endswith(".svg"):
                    self.send_header("Content-Type", "image/svg+xml")
                elif file_path.endswith(".css"):
                    self.send_header("Content-Type", "text/css")
                elif file_path.endswith(".js"):
                    self.send_header("Content-Type", "application/javascript")
                elif file_path.endswith(".html"):
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                else:
                    self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(os.path.getsize(file_path)))
                self.end_headers()
                if not head_only:
                    with open(file_path, "rb") as f:
                        self.wfile.write(f.read())
                return

        self.send_error(404, "Recurso no encontrado")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}

        # 1. API: Search Articles (Google Scholar)
        if path == "/api/scholar/articles":
            query = payload.get("query", "").strip()
            limit = int(payload.get("limit", 10))
            year_low = payload.get("year_low")
            year_high = payload.get("year_high")
            if year_low:
                try: year_low = int(year_low)
                except ValueError: year_low = None
            if year_high:
                try: year_high = int(year_high)
                except ValueError: year_high = None

            articles = scholar_engine.search_articles(query, limit=limit, year_low=year_low, year_high=year_high)
            self._send_json({"success": True, "query": query, "count": len(articles), "articles": articles})
            return

        # 2. API: Search Authors (Google Scholar only)
        if path == "/api/scholar/authors":
            name = payload.get("name", "").strip()
            limit = int(payload.get("limit", 6))
            authors = scholar_engine.search_authors(name, limit=limit)
            self._send_json({"success": True, "query": name, "count": len(authors), "authors": authors})
            return

        # 3. API: Search Researchers (ORCID only)
        if path == "/api/orcid/search":
            query = payload.get("query", "").strip()
            rows = int(payload.get("rows", 10))
            researchers = orcid_engine.search_researchers(query, rows=rows)
            self._send_json({"success": True, "query": query, "count": len(researchers), "researchers": researchers})
            return

        # 4. API: Search Authors (Scopus only)
        if path == "/api/scopus/search":
            query = payload.get("query", "").strip()
            api_key = payload.get("api_key")
            limit = int(payload.get("limit", 8))
            res = scopus_engine.search_authors(query, api_key=api_key, limit=limit)
            self._send_json(res)
            return

        # 5. API: Multi-Source Unified Researcher Search (Scholar + ORCID + Scopus)
        if path == "/api/profiles/search":
            query = payload.get("query", "").strip()
            scopus_key = payload.get("scopus_api_key")
            unified_data = profile_aggregator.search_all_sources(query, scopus_api_key=scopus_key)
            self._send_json({"success": True, "data": unified_data})
            return

        self.send_error(404, "Endpoint no encontrado")

    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def start_server():
    server_address = ("", PORT)
    try:
        httpd = ThreadingHTTPServer(server_address, Proyecto2Handler)
    except OSError:
        print(f"Proyecto 2 ya está activo en http://localhost:{PORT}")
        return

    print(f"\n=======================================================")
    print(f" Proyecto 2: Buscador Académico & Perfiles de Investigadores")
    print(f" URL Local: http://localhost:{PORT}")
    print(f" Google Scholar + ORCID v3.0 + Scopus API")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor de Proyecto 2 detenido.")
        httpd.server_close()


if __name__ == "__main__":
    start_server()
