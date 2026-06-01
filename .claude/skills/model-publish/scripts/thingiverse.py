#!/usr/bin/env python3
"""Publish 3D models to Thingiverse as drafts via the official API."""
import argparse
import http.server
import json
import os
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(ENV_PATH)

BASE_URL = "https://api.thingiverse.com"
AUTH_URL = "https://www.thingiverse.com/login/oauth/authorize"
TOKEN_URL = "https://www.thingiverse.com/login/oauth/access_token"
REDIRECT_PORT = 3000
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"


def _get_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Missing environment variable: {key}. Add it to {ENV_PATH}")
    return value


def authenticate() -> str:
    """Run OAuth2 flow to get an access token. Opens browser for user login."""
    token = os.environ.get("THINGIVERSE_ACCESS_TOKEN")
    if token:
        print("Using existing THINGIVERSE_ACCESS_TOKEN from .env")
        return token

    client_id = _get_env("THINGIVERSE_CLIENT_ID")
    client_secret = _get_env("THINGIVERSE_CLIENT_SECRET")

    captured_code: dict[str, str] = {}
    server_ready = threading.Event()

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            if "code" in params:
                captured_code["code"] = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h2>Authorization successful! You can close this tab.</h2></body></html>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code parameter")

        def log_message(self, format, *args):
            pass  # suppress request logging

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), CallbackHandler)
    server.timeout = 120

    def serve():
        server_ready.set()
        server.handle_request()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    server_ready.wait()

    auth_params = urlencode({"client_id": client_id, "redirect_uri": REDIRECT_URI, "response_type": "code"})
    auth_url = f"{AUTH_URL}?{auth_params}"
    print(f"Opening browser for Thingiverse login...")
    webbrowser.open(auth_url)

    thread.join(timeout=120)
    server.server_close()

    if "code" not in captured_code:
        raise RuntimeError("OAuth2 flow timed out — no authorization code received.")

    print("Exchanging code for access token...")
    resp = requests.post(TOKEN_URL, data={"client_id": client_id, "client_secret": client_secret, "code": captured_code["code"]})
    resp.raise_for_status()
    body = resp.text
    # Thingiverse may return JSON or URL-encoded form data
    try:
        token_data = resp.json()
        access_token = token_data.get("access_token")
    except requests.exceptions.JSONDecodeError:
        token_data = dict(parse_qs(body))
        access_token = token_data.get("access_token", [None])[0]
    if not access_token:
        raise RuntimeError(f"Failed to get access token. Status: {resp.status_code}, Body: {body[:500]}")

    # Save token to .env for reuse
    existing = ENV_PATH.read_text(encoding="utf-8")
    prefix = "" if existing.endswith("\n") else "\n"
    with open(ENV_PATH, "a") as f:
        f.write(f"{prefix}THINGIVERSE_ACCESS_TOKEN={access_token}\n")
    print(f"Access token saved to {ENV_PATH}")

    return access_token


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _category_to_slug(category: str) -> str:
    """Convert 'Category > Subcategory' to a Thingiverse API slug like 'subcategory'."""
    # Use the most specific part (last after '>'), lowercased, spaces/& replaced
    part = category.split(">")[-1].strip() if category else "other"
    return part.lower().replace(" & ", "-and-").replace(" ", "-")


def create_draft(token: str, name: str, description: str, tags: list[str], license: str = "cc-sa", category: str = "other") -> dict:
    """Create a new thing on Thingiverse as a draft."""
    cat_slug = _category_to_slug(category)
    data = {"name": name, "license": license, "category": cat_slug, "description": description, "is_wip": False, "tags": tags}
    resp = requests.post(f"{BASE_URL}/things/", headers=_headers(token), json=data)
    resp.raise_for_status()
    thing = resp.json()
    print(f"Created draft thing: {thing.get('id')} — {thing.get('public_url', thing.get('url', ''))}")
    return thing


def upload_file(token: str, thing_id: int, file_path: Path) -> dict:
    """Upload a file to a thing (3-step: register, S3 upload, finalize)."""
    # Step 1: Register upload
    resp = requests.post(f"{BASE_URL}/things/{thing_id}/files", headers=_headers(token), json={"filename": file_path.name})
    resp.raise_for_status()
    upload_info = resp.json()

    # Step 2: Upload file
    s3_url = upload_info["action"]
    fields = upload_info.get("fields", {})
    finalize_url = fields.get("success_action_redirect", "")
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f)}
        s3_resp = requests.post(s3_url, data=fields, files=files, allow_redirects=False)
        # S3 may return 303 redirect to finalize URL — that counts as success
        if s3_resp.status_code not in (200, 201, 303):
            s3_resp.raise_for_status()

    # Step 3: Finalize
    if finalize_url:
        resp = requests.post(finalize_url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()

    print(f"Uploaded: {file_path.name}")
    return upload_info


def _parse_description_file(path: Path) -> dict[str, str | list[str]]:
    """Parse a description file with Name/Category/Tags header.

    Format:
        Name: <name>
        Category: <category>
        Tags: <comma separated tags>

        <description body>

    Returns dict with keys: name, category, tags (list), description.
    """
    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")
    result: dict[str, str | list[str]] = {"name": "", "category": "", "tags": [], "description": ""}
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            body_start = i + 1
            break
        if stripped.startswith("Name:"):
            result["name"] = stripped[5:].strip()
        elif stripped.startswith("Category:"):
            result["category"] = stripped[9:].strip()
        elif stripped.startswith("Tags:"):
            result["tags"] = [t.strip() for t in stripped[5:].split(",") if t.strip()]
    result["description"] = "\n".join(lines[body_start:]).strip()
    return result


def create_draft_from_description(description_dir: str, photo_dir: str | None = None, files: list[str] | None = None) -> None:
    """Create a Thingiverse draft from a description directory."""
    desc_path = Path(description_dir)
    thingiverse_md = desc_path / "thingiverse.md"

    if not thingiverse_md.exists():
        raise FileNotFoundError(f"Missing {thingiverse_md}")

    parsed = _parse_description_file(thingiverse_md)
    name = parsed["name"]
    description = parsed["description"]
    tags = parsed["tags"]
    category = parsed["category"]

    token = authenticate()
    thing = create_draft(token, name, description, tags, category=category or "other")
    thing_id = thing["id"]

    # Upload photos — cover first (rank 0), then additional photos in order
    if photo_dir:
        photo_path = Path(photo_dir)
        cover = list(photo_path.glob("cover_4x3.*"))
        if cover:
            upload_file(token, thing_id, cover[0])
        additional = sorted(photo_path.glob("photo_*"))
        for photo in additional:
            upload_file(token, thing_id, photo)

    # Upload model files (3mf, stl, etc.)
    if files:
        for file_str in files:
            file_path = Path(file_str)
            if file_path.exists():
                upload_file(token, thing_id, file_path)
            else:
                print(f"Warning: file not found, skipping: {file_path}")

    print(f"\nDraft created successfully!")
    print(f"Thing ID: {thing_id}")
    url = thing.get("public_url", f"https://www.thingiverse.com/thing:{thing_id}")
    print(f"URL: {url}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish 3D models to Thingiverse as drafts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    auth_parser = subparsers.add_parser("auth", help="Authenticate with Thingiverse (get OAuth2 token)")

    draft_parser = subparsers.add_parser("draft", help="Create a draft from description directory")
    draft_parser.add_argument("description_dir", help="Path to description directory (containing thingiverse.md)")
    draft_parser.add_argument("--photo-dir", help="Path to photo directory (cover_4x3.*, photo_01.*, etc.)")
    draft_parser.add_argument("--files", nargs="+", help="Model files to upload (3mf, stl, etc.)")

    args = parser.parse_args()

    if args.command == "auth":
        token = authenticate()
        print(f"Authenticated successfully. Token starts with: {token[:10]}...")
    elif args.command == "draft":
        create_draft_from_description(args.description_dir, args.photo_dir, args.files)


if __name__ == "__main__":
    main()
