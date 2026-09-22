"""Run against the built frontend; API responses are isolated browser fixtures."""
import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(("127.0.0.1", 0),
    functools.partial(QuietHandler, directory=str(ROOT / "frontend" / "dist")))
threading.Thread(target=server.serve_forever, daemon=True).start()
state = {"upload_error": False, "start_error": False, "status": "Completed", "starts": 0, "polls": 0}
errors = []

def api(route):
    url = route.request.url
    status = 200
    if route.request.method == "OPTIONS":
        body = {}
    elif "/history/" in url:
        body = {"projects": []}
    elif url.endswith("/upload"):
        if state["upload_error"]:
            status, body = 422, {"detail": "Unsupported media file type."}
        else:
            body = {"path": "C:/uploads/media.png"}
    elif url.endswith("/start"):
        state["starts"] += 1
        state["payload"] = route.request.post_data_json
        if state["start_error"]:
            status, body = 422, {"detail": "Audio: file not found."}
        else:
            state["polls"] = 0
            body = {"project_id": 1, "output": "result.mp4"}
    else:
        state["polls"] += 1
        body = {"status": "Processing" if state["polls"] == 1 else state["status"]}
    route.fulfill(status=status, json=body, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "*",
    })

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("http://localhost:8000/**", api)
        page.goto(f"http://127.0.0.1:{server.server_port}")
        generate = page.get_by_role("button", name="Generate Video", exact=True)
        generate.click()
        expect(page.get_by_role("status")).to_contain_text("Select the required")
        page.locator("select").first.select_option("visualizer")
        assert page.locator('input[type="file"]').nth(1).get_attribute("accept") == "image/*"
        assert page.locator('input[type="file"]').nth(1).get_attribute("multiple") == ""
        expect(page.get_by_text("Media Settings", exact=True)).to_be_visible()
        expect(page.get_by_text("Visualizer Settings", exact=True)).to_be_visible()
        state["upload_error"] = True
        page.locator('input[type="file"]').first.set_input_files({
            "name": "audio.wav", "mimeType": "audio/wav", "buffer": b"fixture",
        })
        expect(page.get_by_role("status")).to_contain_text("Upload failed")
        state["upload_error"] = False
        page.locator('input[type="file"]').first.set_input_files({
            "name": "audio.wav", "mimeType": "audio/wav", "buffer": b"fixture",
        })
        expect(page.get_by_text("Uploading...", exact=True)).to_have_count(0)
        page.locator('input[type="file"]').nth(1).set_input_files([
            {"name": "image-a.png", "mimeType": "image/png", "buffer": b"fixture"},
            {"name": "image-b.png", "mimeType": "image/png", "buffer": b"fixture"},
        ])
        expect(page.get_by_text("Uploading...", exact=True)).to_have_count(0)
        expect(page.get_by_text("2 images selected", exact=True)).to_be_visible()
        page.locator("#vis-style").select_option("Mirror Bar")
        page.locator("#vis-position").select_option("center")
        state["start_error"] = True
        generate.click()
        expect(page.get_by_role("status")).to_contain_text("Audio: file not found")
        expect(generate).to_be_enabled()
        state["start_error"] = False
        state["status"] = "Failed"
        generate.click()
        expect(page.get_by_role("status")).to_contain_text("Generation failed", timeout=10000)
        state["status"] = "Completed"
        generate.click()
        expect(page.get_by_role("button", name="Rendering...", exact=True)).to_be_disabled()
        expect(page.get_by_role("status")).to_have_text("Video ready.", timeout=10000)
        expect(page.get_by_role("link", name="Download generated video")).to_have_attribute(
            "href", "http://localhost:8000/api/v1/generator/1/download")
        assert state["payload"]["mode"] == "visualizer"
        assert state["payload"]["background_type"] == "images"
        assert len(state["payload"]["image_files"]) == 2
        assert state["payload"]["style"] == "Mirror Bar"
        assert state["payload"]["visualizer_position"] == "center"
        (ROOT / "test_output").mkdir(exist_ok=True)
        page.screenshot(path=str(ROOT / "test_output" / "visualizer-settings.png"), full_page=True)
        page.get_by_label("Background Source").select_option("video")
        assert page.locator('input[type="file"]').nth(1).get_attribute("accept") == "video/*"
        page.locator("#vis-audio-mode").select_option("mix")
        expect(page.get_by_label("Original Volume")).to_be_visible()
        page.locator("select").first.select_option("loop")
        assert page.locator('input[type="file"]').nth(1).get_attribute("accept") == "video/*"
        page.locator("select").first.select_option("simple")
        generate.click()
        expect(page.get_by_role("status")).to_contain_text("Select the required")
        assert state["starts"] == 3
        assert not errors, errors
        (ROOT / "test_output").mkdir(exist_ok=True)
        page.screenshot(path=str(ROOT / "test_output" / "generator-browser-check.png"), full_page=True)
        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.on("pageerror", lambda error: errors.append(str(error)))
        mobile.route("http://localhost:8000/**", api)
        mobile.goto(f"http://127.0.0.1:{server.server_port}")
        mobile.locator("select").first.select_option("visualizer")
        expect(mobile.get_by_text("Visualizer Settings", exact=True)).to_be_visible()
        assert mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        mobile.close()
        browser.close()
    print("PASS: multi-image upload, visualizer settings, video audio modes, validation, errors, busy state, download, mode reset; no JS exceptions.")
finally:
    server.shutdown()
