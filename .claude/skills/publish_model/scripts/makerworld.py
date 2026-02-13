#!/usr/bin/env python3
"""Publish 3D models to MakerWorld as drafts via Playwright browser automation."""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright, BrowserContext, Page

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CHROME_PROFILE_DIR = str(PROJECT_ROOT / ".chrome_mw_profile")


def _open_context(pw) -> BrowserContext:
    """Launch real Chrome with a persistent profile to bypass Cloudflare."""
    return pw.chromium.launch_persistent_context(
        CHROME_PROFILE_DIR,
        channel="chrome",
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )


def _wait_for_cloudflare(page: Page, timeout: int = 60000) -> bool:
    """Wait for Cloudflare challenge to clear. Returns True if page loaded."""
    if "just a moment" not in page.title().lower():
        return True
    print("Cloudflare challenge detected. Please click 'Verify you are human' if prompted...")
    try:
        page.wait_for_function("document.title !== 'Just a moment...'", timeout=timeout)
        page.wait_for_timeout(3000)  # let page finish loading
        return True
    except Exception:
        print("Timed out waiting for Cloudflare challenge.")
        return False


def login() -> None:
    """Open browser for manual MakerWorld login. Session persists in Chrome profile."""
    with sync_playwright() as p:
        ctx = _open_context(p)
        page = ctx.new_page()
        page.goto("https://makerworld.com/en", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        if not _wait_for_cloudflare(page):
            ctx.close()
            return

        # Click Log In and wait for the user to complete sign-in
        try:
            login_btn = page.query_selector("text=Log In")
            if login_btn:
                print("Clicking 'Log In' button...")
                login_btn.click()
                page.wait_for_timeout(3000)
                _wait_for_cloudflare(page)
                print(f"Sign-in page: {page.url}")
            else:
                print("Already logged in or 'Log In' button not found.")
        except Exception as e:
            print(f"Note: {e}")

        print("Please complete the login in the browser.")
        print("Close the browser window when you are done.")

        # Wait for ALL pages to close (handles popups/tabs)
        try:
            while ctx.pages:
                ctx.pages[0].wait_for_event("close", timeout=300_000)
        except Exception:
            pass

        ctx.close()
        print("Login complete. Session saved in Chrome profile.")


def _wait_and_find(page: Page, selector: str, timeout: int = 30000):
    """Wait for a selector and return the element."""
    page.wait_for_selector(selector, timeout=timeout)
    return page.query_selector(selector)


def inspect_upload_page() -> None:
    """Navigate to the upload page and dump its structure for development."""
    output_dir = PROJECT_ROOT / "tmp"
    output_dir.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = _open_context(p)
        page = ctx.new_page()

        print("Navigating to MakerWorld...")
        page.goto("https://makerworld.com/en", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        if not _wait_for_cloudflare(page):
            ctx.close()
            return

        # Find all links that might be upload/create related
        links = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                href: a.href,
                text: a.textContent?.trim()?.slice(0, 100) || '',
                cls: a.className?.toString()?.slice(0, 200) || ''
            })).filter(a => /upload|create|publish|design|new.*model/i.test(a.href + ' ' + a.text));
        }""")
        print(f"Found {len(links)} upload-related links:")
        for link in links:
            print(f"  {link['text'][:60].encode('ascii', 'replace').decode()} -> {link['href']}")

        # Find upload button/link in header area
        header_links = page.evaluate("""() => {
            // Get all clickable elements in the top area (y < 60px)
            const els = document.querySelectorAll('a[href], button');
            return Array.from(els).filter(el => {
                const rect = el.getBoundingClientRect();
                return rect.y < 60 && rect.width > 0;
            }).map(el => ({
                tag: el.tagName,
                href: el.href || '',
                text: el.textContent?.trim()?.slice(0, 50) || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                title: el.title || '',
                cls: el.className?.toString()?.slice(0, 150) || '',
                rect: {x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y), w: Math.round(el.getBoundingClientRect().width)}
            }));
        }""")
        print(f"\nHeader clickable elements ({len(header_links)}):")
        for el in header_links:
            label = el['text'] or el['ariaLabel'] or el['title'] or '(no label)'
            print(f"  [{el['tag']}] {label[:40].encode('ascii', 'replace').decode()} -> {el['href'][:80]}  cls={el['cls'][:60]}")

        # Click Upload -> 3D original model to reach the upload form
        try:
            upload_btn = page.query_selector("button:has-text('Upload')")
            if upload_btn:
                print("\nClicking 'Upload' button...")
                upload_btn.click()
                page.wait_for_timeout(2000)

                # Click "3D original model" option
                original_opt = page.query_selector("text=3D original model")
                if original_opt:
                    print("Clicking '3D original model'...")
                    original_opt.click()
                    page.wait_for_timeout(5000)
                    _wait_for_cloudflare(page)
                print(f"Upload page URL: {page.url}")

                # Dismiss cookie banner
                try:
                    accept_btn = page.query_selector("#truste-consent-button")
                    if accept_btn:
                        accept_btn.click()
                        page.wait_for_timeout(1000)
                except Exception:
                    pass

                # Step 1: Select "Yes" (Bambu 3MF) and click Next
                yes_label = page.query_selector("label:has-text('Yes (earn extra')")
                if yes_label:
                    print("Selecting 'Yes (Bambu 3MF)'...")
                    yes_label.click()
                    page.wait_for_timeout(500)

                next_btn = page.query_selector("button:has-text('Next Step')")
                if next_btn:
                    print("Clicking 'Next Step'...")
                    next_btn.click()
                    page.wait_for_timeout(5000)

                print(f"Step 2 URL: {page.url}")
                screenshot_path = output_dir / "mw_upload_step2.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"Screenshot saved to {screenshot_path}")

                # Dump all form elements
                import json
                form_els = page.evaluate("""() => {
                    const els = document.querySelectorAll('input, textarea, select, button, [contenteditable], [role="textbox"], [class*="upload"], [class*="editor"], [class*="tag"], [class*="title"], [class*="description"], [class*="category"], [class*="drop"], label, [class*="rich"], [class*="ql-"]');
                    return Array.from(els).map(el => {
                        const rect = el.getBoundingClientRect();
                        return {
                            tag: el.tagName,
                            type: el.type || '',
                            id: el.id || '',
                            name: el.name || '',
                            cls: el.className?.toString()?.slice(0, 200) || '',
                            placeholder: el.placeholder || '',
                            role: el.getAttribute('role') || '',
                            contentEditable: el.contentEditable || '',
                            ariaLabel: el.getAttribute('aria-label') || '',
                            text: el.textContent?.trim()?.slice(0, 100) || '',
                            visible: rect.width > 0 && rect.height > 0,
                            rect: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)}
                        };
                    });
                }""")
                dom_path = output_dir / "mw_upload_dom.json"
                dom_path.write_text(json.dumps(form_els, indent=2), encoding="utf-8")
                print(f"DOM dump saved to {dom_path} ({len(form_els)} elements)")
        except Exception as e:
            print(f"Error: {e}")

        print("Keeping browser open for 20 seconds...")
        page.wait_for_timeout(20000)
        ctx.close()


def _dismiss_cookie_banner(page: Page) -> None:
    """Dismiss the cookie consent banner if present."""
    try:
        btn = page.query_selector("#truste-consent-button")
        if btn:
            btn.click()
            page.wait_for_timeout(500)
    except Exception:
        pass


def _navigate_to_upload_form(page: Page) -> bool:
    """Navigate from homepage to the upload form. Returns True on success."""
    print("Navigating to MakerWorld...")
    page.goto("https://makerworld.com/en", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    if not _wait_for_cloudflare(page):
        return False

    # Check if logged in (look for Upload button, not Log In)
    login_btn = page.query_selector("text=Log In")
    if login_btn:
        print("Not logged in. Run 'makerworld.py login' first.")
        return False

    _dismiss_cookie_banner(page)

    # Click Upload button in header
    upload_btn = page.query_selector("button:has-text('Upload')")
    if not upload_btn:
        print("Upload button not found in header.")
        return False
    print("Clicking 'Upload'...")
    upload_btn.click()
    page.wait_for_timeout(2000)

    # Select "3D original model"
    original_opt = page.query_selector("text=3D original model")
    if not original_opt:
        print("'3D original model' option not found.")
        return False
    print("Selecting '3D original model'...")
    original_opt.click()
    page.wait_for_timeout(5000)
    _wait_for_cloudflare(page)

    if "publish" not in page.url:
        print(f"Unexpected URL after upload click: {page.url}")
        return False

    print(f"Upload form loaded: {page.url}")
    return True


def _upload_step1_file_type(page: Page) -> bool:
    """Step 1: Select 'Yes (Bambu 3MF)' and click Next."""
    yes_label = page.query_selector("label:has-text('Yes (earn extra')")
    if not yes_label:
        print("'Yes (Bambu 3MF)' option not found.")
        return False
    yes_label.click()
    page.wait_for_timeout(500)

    next_btn = page.query_selector("button:has-text('Next Step')")
    if not next_btn:
        print("'Next Step' button not found.")
        return False
    print("Step 1: Selected 'Yes (Bambu 3MF)' -> Next")
    next_btn.click()
    page.wait_for_timeout(3000)
    return True


def _upload_step2_files(page: Page, bambu_3mf: Path, extra_files: list[Path]) -> bool:
    """Step 2: Upload Bambu 3MF and optional raw model files, then Next."""
    # Find all file inputs — first is Bambu 3MF, second is raw model files
    file_inputs = page.query_selector_all("input[type='file']")
    if len(file_inputs) < 2:
        print(f"Expected at least 2 file inputs, found {len(file_inputs)}.")
        return False

    # Upload Bambu 3MF
    print(f"Uploading Bambu 3MF: {bambu_3mf.name}")
    file_inputs[0].set_input_files(str(bambu_3mf))
    page.wait_for_timeout(3000)

    # Upload extra files (STL etc.) to the raw model files input
    if extra_files:
        extra_paths = [str(f) for f in extra_files]
        print(f"Uploading raw files: {', '.join(f.name for f in extra_files)}")
        file_inputs[1].set_input_files(extra_paths)
        page.wait_for_timeout(3000)

    # Wait for uploads to complete (look for file names appearing on page)
    page.wait_for_timeout(5000)

    # Click Next Step
    next_btn = page.query_selector("button:has-text('Next Step')")
    if not next_btn:
        print("'Next Step' button not found on step 2.")
        return False
    print("Step 2: Files uploaded -> Next")
    next_btn.click()
    page.wait_for_timeout(5000)
    return True


def _dump_page_state(page: Page, output_dir: Path, prefix: str) -> None:
    """Save screenshot and DOM dump for debugging."""
    import json
    screenshot_path = output_dir / f"{prefix}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"Screenshot saved to {screenshot_path}")

    form_els = page.evaluate("""() => {
        const els = document.querySelectorAll('input, textarea, select, button, [contenteditable="true"], [role="textbox"], [class*="upload"], [class*="editor"], [class*="tag"], [class*="title"], [class*="description"], [class*="category"], [class*="drop"], label, [class*="rich"], [class*="ql-"]');
        return Array.from(els).map(el => {
            const rect = el.getBoundingClientRect();
            return {
                tag: el.tagName, type: el.type || '', id: el.id || '', name: el.name || '',
                cls: el.className?.toString()?.slice(0, 200) || '',
                placeholder: el.placeholder || '', role: el.getAttribute('role') || '',
                contentEditable: el.contentEditable || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                text: el.textContent?.trim()?.slice(0, 100) || '',
                visible: rect.width > 0 && rect.height > 0,
                rect: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)}
            };
        });
    }""")
    dom_path = output_dir / f"{prefix}_dom.json"
    dom_path.write_text(json.dumps(form_els, indent=2), encoding="utf-8")
    print(f"DOM dump saved to {dom_path} ({len(form_els)} elements)")


def _dismiss_cropper_dialog(page: Page) -> None:
    """Dismiss the image cropper dialog that appears after uploading cover images."""
    try:
        # Look for confirm/save button in the dialog
        dialog = page.wait_for_selector(".MuiDialog-root", timeout=5000)
        if dialog:
            # Try common button texts for confirming the crop
            for text in ["Confirm", "Save", "OK", "Apply", "Done"]:
                btn = page.query_selector(f".MuiDialog-root button:has-text('{text}')")
                if btn:
                    btn.click()
                    page.wait_for_timeout(2000)
                    return
            # If no named button found, try the primary/contained button in the dialog
            btn = page.query_selector(".MuiDialog-root button.MuiButton-containedPrimary")
            if btn:
                btn.click()
                page.wait_for_timeout(2000)
                return
            print("Warning: cropper dialog found but no confirm button detected.")
    except Exception:
        pass  # No dialog appeared


def _upload_step3_model_info(page: Page, name: str, description: str, tags: list[str], category: str | None, cover_4x3: Path | None, cover_3x4: Path | None, extra_photos: list[Path]) -> bool:
    """Step 3: Fill in model information and save as draft."""
    # Wait for any upload overlay to disappear
    try:
        page.wait_for_selector(".MuiBackdrop-root:has-text('uploading')", state="hidden", timeout=30000)
    except Exception:
        pass
    page.wait_for_timeout(2000)

    # Upload cover images via dropzone file inputs
    # The dropzones have specific text: "4:3 Cover" and "3:4 Cover"
    # After upload, a cropper dialog appears — must confirm it
    if cover_4x3:
        cover_43_dropzone = page.query_selector("div.dropzone:has-text('4:3 Cover')")
        if cover_43_dropzone:
            file_input = cover_43_dropzone.query_selector("input[type='file']")
            if file_input:
                print(f"Uploading 4:3 cover: {cover_4x3.name}")
                file_input.set_input_files(str(cover_4x3))
                page.wait_for_timeout(3000)
                _dismiss_cropper_dialog(page)

    if cover_3x4:
        cover_34_dropzone = page.query_selector("div.dropzone:has-text('3:4 Cover')")
        if cover_34_dropzone:
            file_input = cover_34_dropzone.query_selector("input[type='file']")
            if file_input:
                print(f"Uploading 3:4 cover: {cover_3x4.name}")
                file_input.set_input_files(str(cover_3x4))
                page.wait_for_timeout(3000)
                _dismiss_cropper_dialog(page)

    # Upload additional photos via "Add Photo" area
    for photo in extra_photos:
        # The model pictures section has a file input after the covers
        # Find by looking for the "Add Photo" text area
        add_photo = page.query_selector("text=Add Photo")
        if add_photo:
            # The file input is a sibling/child of the parent dropzone
            parent = add_photo.evaluate_handle("el => el.closest('[role=\"button\"]') || el.parentElement")
            file_input = parent.as_element().query_selector("input[type='file']")
            if file_input:
                print(f"Uploading photo: {photo.name}")
                file_input.set_input_files(str(photo))
                page.wait_for_timeout(3000)

    # Fill Model Name (max 50 chars)
    title_input = page.query_selector("input[name='title']")
    if title_input:
        truncated_name = name[:50]
        print(f"Setting model name: {truncated_name}")
        title_input.click()
        title_input.fill(truncated_name)
        page.wait_for_timeout(500)

    # Fill Category — format is "Category > Subcategory", type the subcategory for a more specific match
    category_input = page.query_selector(".modelCategory input[role='combobox']")
    if category_input and category:
        # Parse "Category > Subcategory" format — search by subcategory for a precise match
        search_term = category.split(">")[-1].strip() if ">" in category else category
        print(f"Setting category: {category} (searching: {search_term})")
        category_input.click()
        category_input.fill(search_term)
        page.wait_for_timeout(2000)
        # Select first matching option from dropdown
        first_option = page.query_selector("[role='listbox'] [role='option']")
        if first_option:
            option_text = first_option.text_content().strip()
            print(f"Selected category: {option_text}")
            first_option.click()
            page.wait_for_timeout(500)
        else:
            print(f"Warning: no category match for '{search_term}', trying 'other'...")
            category_input.fill("")
            category_input.fill("other")
            page.wait_for_timeout(2000)
            first_option = page.query_selector("[role='listbox'] [role='option']")
            if first_option:
                first_option.click()

    # Fill Tags — type each tag and press Enter
    tags_input = page.query_selector(".modelTags input[role='combobox']")
    if tags_input and tags:
        print(f"Adding {len(tags)} tags...")
        tags_input.click()
        for tag in tags:
            tags_input.fill(tag)
            page.wait_for_timeout(500)
            tags_input.press("Enter")
            page.wait_for_timeout(300)

    # Fill Description via CKEditor
    editor = page.query_selector("div.ck-content[role='textbox']")
    if editor:
        print("Setting description...")
        # Convert markdown description to simple HTML
        html_desc = _markdown_to_simple_html(description)
        # Set content via CKEditor 5 API (innerHTML alone doesn't update the internal model)
        success = page.evaluate("""(html) => {
            const editorEl = document.querySelector('.ck-content[role="textbox"]');
            if (!editorEl) return false;
            // CKEditor 5 exposes the instance on the editable element
            if (editorEl.ckeditorInstance) {
                editorEl.ckeditorInstance.setData(html);
                return true;
            }
            // Fallback: try innerHTML + input event
            editorEl.focus();
            editorEl.innerHTML = html;
            editorEl.dispatchEvent(new Event('input', { bubbles: true }));
            return false;
        }""", html_desc)
        if success:
            print("Description set via CKEditor API.")
        else:
            print("Warning: CKEditor instance not found, used innerHTML fallback.")
        page.wait_for_timeout(1000)

    # Click "Save to draft"
    save_btn = page.query_selector("button:has-text('Save to draft')")
    if save_btn:
        print("Saving draft...")
        save_btn.click()
        page.wait_for_timeout(5000)
        print(f"Draft saved! URL: {page.url}")
        return True

    print("'Save to draft' button not found.")
    return False


def _markdown_to_simple_html(md: str) -> str:
    """Convert simple markdown to HTML for CKEditor."""
    import re
    lines = md.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<p>&nbsp;</p>")
            continue

        # Bold headers: **text** on its own line → <h3>
        if re.match(r'^\*\*(.+)\*\*$', stripped):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            inner = re.match(r'^\*\*(.+)\*\*$', stripped).group(1)
            html_lines.append(f"<h3>{inner}</h3>")
            continue

        # Bullet points: - text or * text
        if re.match(r'^[-*]\s+', stripped):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            item = re.sub(r'^[-*]\s+', '', stripped)
            # Handle inline bold and italic
            item = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item)
            item = re.sub(r'\*(.+?)\*', r'<em>\1</em>', item)
            html_lines.append(f"<li>{item}</li>")
            continue

        if in_list:
            html_lines.append("</ul>")
            in_list = False

        # Italic line: *text*
        if re.match(r'^\*(.+)\*$', stripped):
            inner = re.match(r'^\*(.+)\*$', stripped).group(1)
            html_lines.append(f"<p><em>{inner}</em></p>")
            continue

        # Regular paragraph with inline formatting
        text = stripped
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        html_lines.append(f"<p>{text}</p>")

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


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


def create_draft(description_dir: str, photo_dir: str | None = None, files: list[str] | None = None) -> None:
    """Create a MakerWorld draft by automating the web form.

    Args:
        description_dir: Path to directory containing makerworld.md (or thingiverse.md)
        photo_dir: Path to directory containing cover and additional photos
        files: List of model file paths (bambu.3mf, STL files, etc.)
    """
    desc_path = Path(description_dir)

    # Find description file (prefer makerworld.md, fall back to thingiverse.md)
    md_file = desc_path / "makerworld.md"
    if not md_file.exists():
        md_file = desc_path / "thingiverse.md"
    if not md_file.exists():
        raise FileNotFoundError(f"Missing description file in {desc_path}")

    parsed = _parse_description_file(md_file)
    name = parsed["name"]
    description = parsed["description"]
    tags = parsed["tags"]
    category = parsed["category"] or None
    if not category:
        print("Warning: no Category in description file. Category will be skipped.")

    # Separate bambu 3mf from other files
    file_paths = [Path(f) for f in (files or [])]
    bambu_3mf = None
    extra_files = []
    for fp in file_paths:
        if not fp.exists():
            print(f"Warning: file not found, skipping: {fp}")
            continue
        if fp.name == "bambu.3mf":
            bambu_3mf = fp
        else:
            extra_files.append(fp)

    if not bambu_3mf:
        raise FileNotFoundError("No bambu.3mf file provided. Always required for MakerWorld upload.")

    # Collect photos by type
    cover_4x3 = None
    cover_3x4 = None
    extra_photos = []
    if photo_dir:
        photo_path = Path(photo_dir)
        covers_43 = list(photo_path.glob("cover_4x3.*"))
        if covers_43:
            cover_4x3 = covers_43[0]
        covers_34 = list(photo_path.glob("cover_3x4.*"))
        if covers_34:
            cover_3x4 = covers_34[0]
        extra_photos = sorted(photo_path.glob("photo_*"))

    photo_count = sum(1 for x in [cover_4x3, cover_3x4] if x) + len(extra_photos)
    print(f"Model: {name}")
    print(f"Category: {category or '(none)'}")
    print(f"Files: {bambu_3mf.name} + {len(extra_files)} extra")
    print(f"Photos: {photo_count}")
    print(f"Tags: {', '.join(tags[:5])}{'...' if len(tags) > 5 else ''}")

    with sync_playwright() as p:
        ctx = _open_context(p)
        page = ctx.new_page()

        if not _navigate_to_upload_form(page):
            ctx.close()
            return

        _dismiss_cookie_banner(page)

        if not _upload_step1_file_type(page):
            ctx.close()
            return

        if not _upload_step2_files(page, bambu_3mf, extra_files):
            ctx.close()
            return

        # Step 3: Fill in model information and save as draft
        print(f"\nStep 3 reached: {page.url}")
        if not _upload_step3_model_info(page, name, description, tags, category, cover_4x3, cover_3x4, extra_photos):
            tmp_dir = PROJECT_ROOT / "tmp"
            tmp_dir.mkdir(exist_ok=True)
            _dump_page_state(page, tmp_dir, "mw_step3_error")
            print("Step 3 failed. Screenshot saved for debugging.")
            page.wait_for_timeout(15000)

        ctx.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish 3D models to MakerWorld as drafts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("login", help="Log in to MakerWorld (opens browser)")
    subparsers.add_parser("inspect", help="Inspect upload page structure (for development)")

    draft_parser = subparsers.add_parser("draft", help="Create a draft from description directory")
    draft_parser.add_argument("description_dir", help="Path to description directory")
    draft_parser.add_argument("--photo-dir", help="Path to photo directory")
    draft_parser.add_argument("--files", nargs="+", help="Model files to upload")

    args = parser.parse_args()

    if args.command == "login":
        login()
    elif args.command == "inspect":
        inspect_upload_page()
    elif args.command == "draft":
        create_draft(args.description_dir, getattr(args, "photo_dir", None), getattr(args, "files", None))


if __name__ == "__main__":
    main()
