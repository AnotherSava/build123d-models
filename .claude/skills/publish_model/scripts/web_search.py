#!/usr/bin/env python3
"""Search for 3D models on MakerWorld and Thingiverse using Playwright."""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright, Browser, BrowserContext

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CHROME_PROFILE_DIR = str(PROJECT_ROOT / ".chrome_mw_profile")
CHROME_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def _launch_browser(pw) -> Browser:
    return pw.chromium.launch(headless=False)


def _open_chrome_context(pw) -> BrowserContext:
    """Launch real Chrome with persistent profile to bypass Cloudflare."""
    return pw.chromium.launch_persistent_context(
        CHROME_PROFILE_DIR, channel="chrome", headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )


def _new_page(browser: Browser):
    ctx = browser.new_context(user_agent=CHROME_USER_AGENT)
    return ctx.new_page()


def _extract_makerworld_category(page) -> str:
    """Extract category > subcategory from a MakerWorld model page."""
    cat_links = page.query_selector_all("a[href*='/en/3d-models/'].clickable")
    cat_parts = [el.inner_text().strip() for el in cat_links if el.inner_text().strip()]
    return " > ".join(cat_parts)


def search_makerworld(query: str, max_results: int = 10) -> list[tuple[str, str, str]]:
    """Search MakerWorld for models matching query. Returns list of (name, url, category)."""
    results = []
    with sync_playwright() as p:
        ctx = _open_chrome_context(p)
        page = ctx.new_page()
        url = f"https://makerworld.com/en/search/models?keyword={query}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector("a[title][href*='/en/models/']", timeout=30000)
        page.wait_for_timeout(2000)
        cards = page.query_selector_all("a[title][href*='/en/models/']")
        seen = set()
        urls_to_visit = []
        for card in cards:
            href = card.get_attribute("href") or ""
            title = card.get_attribute("title") or ""
            if not title or href in seen:
                continue
            seen.add(href)
            full_url = f"https://makerworld.com{href}" if href.startswith("/") else href
            urls_to_visit.append((title, full_url))
            if len(urls_to_visit) >= max_results:
                break
        # Visit each model page to extract category while browser is still open
        for title, model_url in urls_to_visit:
            category = ""
            try:
                page.goto(model_url, wait_until="domcontentloaded")
                page.wait_for_selector("h1", timeout=15000)
                page.wait_for_timeout(1500)
                category = _extract_makerworld_category(page)
            except Exception:
                pass
            results.append((title, model_url, category))
        ctx.close()
    return results


def search_thingiverse(query: str, max_results: int = 10) -> list[tuple[str, str]]:
    """Search Thingiverse for models matching query. Returns list of (name, url)."""
    results = []
    with sync_playwright() as p:
        browser = _launch_browser(p)
        page = _new_page(browser)
        url = f"https://www.thingiverse.com/search?q={query}&page=1&type=things&sort=relevant"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector("a[title][href*='/thing:']", timeout=30000)
        page.wait_for_timeout(2000)
        cards = page.query_selector_all("a[title][href*='/thing:']")
        seen = set()
        for card in cards:
            href = card.get_attribute("href") or ""
            title = card.get_attribute("title") or ""
            if not title or href in seen:
                continue
            seen.add(href)
            full_url = f"https://www.thingiverse.com{href}" if href.startswith("/") else href
            results.append((title, full_url))
            if len(results) >= max_results:
                break
        browser.close()
    return results


def fetch_model_page(url: str) -> dict[str, str]:
    """Fetch a model page and extract description, tags, and category."""
    result: dict[str, str] = {"title": "", "description": "", "tags": "", "category": ""}
    with sync_playwright() as p:
        # Use Chrome profile for MakerWorld (Cloudflare), regular browser for others
        if "makerworld.com" in url:
            ctx = _open_chrome_context(p)
            page = ctx.new_page()
        else:
            ctx = _launch_browser(p).new_context(user_agent=CHROME_USER_AGENT)
            page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        if "makerworld.com" in url:
            page.wait_for_selector("h1", timeout=30000)
            page.wait_for_timeout(2000)
            title_el = page.query_selector("h1")
            result["title"] = title_el.inner_text().strip() if title_el else ""
            desc_el = page.query_selector("div[class*='description'], div[class*='Description']")
            result["description"] = desc_el.inner_text().strip() if desc_el else ""
            tag_els = page.query_selector_all("a[href*='/en/search/models?keyword=']")
            result["tags"] = ", ".join(t.inner_text().strip() for t in tag_els if t.inner_text().strip())
            result["category"] = _extract_makerworld_category(page)
        elif "thingiverse.com" in url:
            page.wait_for_selector("h1", timeout=30000)
            page.wait_for_timeout(2000)
            title_el = page.query_selector("h1")
            result["title"] = title_el.inner_text().strip() if title_el else ""
            desc_el = page.query_selector("div[class*='description'], div[class*='Description'], div.thing-description")
            result["description"] = desc_el.inner_text().strip() if desc_el else ""
            tag_els = page.query_selector_all("a[href*='/tag:']")
            result["tags"] = ", ".join(t.inner_text().strip() for t in tag_els if t.inner_text().strip())
            # Extract category from JSON-LD Product schema embedded in page
            cat = page.evaluate("""() => {
                const scripts = document.querySelectorAll("script[type='application/ld+json']");
                for (const s of scripts) {
                    try {
                        const data = JSON.parse(s.textContent);
                        if (data["@type"] === "Product" && data.category) return data.category;
                    } catch {}
                }
                return "";
            }""")
            # Normalize comma-separated to "Category > Subcategory" format
            result["category"] = " > ".join(p.strip() for p in cat.split(",")) if cat else ""
        elif "printables.com" in url:
            page.wait_for_selector("h1", timeout=30000)
            page.wait_for_timeout(2000)
            title_el = page.query_selector("h1")
            result["title"] = title_el.inner_text().strip() if title_el else ""
            desc_el = page.query_selector("div[class*='description'], div[class*='Description']")
            result["description"] = desc_el.inner_text().strip() if desc_el else ""
            tag_els = page.query_selector_all("a[href*='/tag/']")
            result["tags"] = ", ".join(t.inner_text().strip() for t in tag_els if t.inner_text().strip())
            cat_links = page.query_selector_all("a[href*='?category=']")
            cat_parts = [el.inner_text().strip() for el in cat_links if el.inner_text().strip()]
            result["category"] = " > ".join(cat_parts)
        ctx.close()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Search for 3D models on MakerWorld and Thingiverse")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search for models")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--platform", choices=["makerworld", "thingiverse", "both"], default="both")
    search_parser.add_argument("--max", type=int, default=5, help="Max results per platform")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch model details from URL")
    fetch_parser.add_argument("url", help="Model page URL")

    args = parser.parse_args()

    if args.command == "search":
        if args.platform in ("makerworld", "both"):
            results = search_makerworld(args.query, args.max)
            if results:
                print("=== MakerWorld ===")
                for name, url, category in results:
                    print(f"Name: {name}")
                    if category:
                        print(f"Category: {category}")
                    print(f"URL: {url}\n")
            else:
                print("=== MakerWorld ===\nNo results found.\n")
        if args.platform in ("thingiverse", "both"):
            results = search_thingiverse(args.query, args.max)
            if results:
                print("=== Thingiverse ===")
                for name, url in results:
                    print(f"Name: {name}")
                    print(f"URL: {url}\n")
            else:
                print("=== Thingiverse ===\nNo results found.\n")
    elif args.command == "fetch":
        details = fetch_model_page(args.url)
        print(f"Title: {details['title']}")
        if details["category"]:
            print(f"Category: {details['category']}")
        print(f"Tags: {details['tags']}")
        print(f"\nDescription:\n{details['description']}")


if __name__ == "__main__":
    main()
