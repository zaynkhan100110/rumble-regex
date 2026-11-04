
#!/usr/bin/env python3
"""
Rumble Regex
============

Extract actual Rumble player identifiers from public Rumble pages.

Supported:
    - Standard Rumble videos
    - Rumble Shorts
    - Embed IDs
    - Clip IDs
    - Media IDs
    - JavaScript-rendered player elements
    - Embedded JSON configuration
    - Multiple HTML extraction fallbacks

Requirements:
    pip install playwright
    python -m playwright install chromium

Usage:
    python rumble.py "https://rumble.com/vXXXX-example.html"
    python rumble.py "https://rumble.com/shorts/XXXX"
"""

import argparse
import json
import re
import sys

from urllib.parse import urlparse

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)


# ============================================================
# EXTRACTION PATTERNS
# ============================================================

EMBED_PATTERNS = [

    # iframe embed URL
    r'<iframe\b[^>]*src=["\']([^"\']*rumble\.com/embed/[^"\']+)',

    # Embed URL configuration
    r'["\'](?:embedUrl|embed_url|embedURL)["\']\s*:\s*["\']([^"\']+)',

    # Direct embed URL
    r'https?://(?:www\.)?rumble\.com/embed/([^/"\'?#\s]+)',

    # Rumble player initialization
    r'Rumble\s*\(\s*["\']play["\']\s*,\s*\{[\s\S]{0,3000}?["\']?video["\']?\s*:\s*["\']([^"\']+)',

    # Video configuration
    r'["\'](?:video|videoId|video_id)["\']\s*:\s*["\']([A-Za-z0-9_-]{4,})',

    # Embed identifiers
    r'["\'](?:embedId|embed_id|embedID)["\']\s*:\s*["\']([A-Za-z0-9_-]{4,})',

    # Player configuration
    r'["\'](?:videoID|videoIDHash|video_id_hash)["\']\s*:\s*["\']([A-Za-z0-9_-]{4,})',

    # Player elements
    r'<rum-player\b[^>]*video-id=["\']([^"\']+)',

    # Data attributes
    r'data-video-id=["\']([^"\']+)',

    r'data-embed-id=["\']([^"\']+)',

]


SHORTS_PATTERNS = [

    r'<rum-shorts-player\b[^>]*clip-id=["\']([^"\']+)',

    r'["\']clip-id["\']\s*:\s*["\']([^"\']+)',

    r'["\']clipId["\']\s*:\s*["\']([^"\']+)',

    r'data-clip-id=["\']([^"\']+)',

    r'["\']shortsId["\']\s*:\s*["\']([^"\']+)',

]


MEDIA_PATTERNS = [

    r'<video\b[^>]*data-media-id=["\']([^"\']+)',

    r'<rum-player-media\b[^>]*media-id=["\']([^"\']+)',

    r'["\']mediaId["\']\s*:\s*["\']([^"\']+)',

    r'["\']media_id["\']\s*:\s*["\']([^"\']+)',

    r'data-media-id=["\']([^"\']+)',

]


# ============================================================
# URL VALIDATION
# ============================================================

def validate_url(url):

    url = url.strip()

    if not url:
        raise ValueError("No URL supplied.")

    if "://" not in url:
        url = "https://" + url

    parsed = urlparse(url)

    hostname = (parsed.hostname or "").lower()

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS URLs are supported.")

    if not (
        hostname == "rumble.com"
        or hostname.endswith(".rumble.com")
    ):
        raise ValueError("Not a valid Rumble domain.")

    if not parsed.path or parsed.path == "/":
        raise ValueError("URL does not identify a video.")

    return url


# ============================================================
# REGEX HELPERS
# ============================================================

def find_pattern(patterns, content):

    for pattern in patterns:

        match = re.search(
            pattern,
            content,
            re.IGNORECASE
        )

        if match:

            value = match.group(1).strip()

            if value:
                return value

    return None


# ============================================================
# EMBED ID EXTRACTION
# ============================================================

def extract_embed_id(content):

    for pattern in EMBED_PATTERNS:

        match = re.search(
            pattern,
            content,
            re.IGNORECASE
        )

        if not match:
            continue

        value = match.group(1).strip()

        # Extract ID from an embed URL.
        if "rumble.com/embed/" in value.lower():

            embed_match = re.search(
                r"/embed/([^/?#\"'\s]+)",
                value,
                re.IGNORECASE
            )

            if embed_match:
                return embed_match.group(1)

        elif value:

            return value

    return None


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json_ids(content):

    results = {
        "embed_id": None,
        "media_id": None,
    }

    blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>',
        content,
        re.IGNORECASE
    )

    for block in blocks:

        try:

            data = json.loads(block)

            text = json.dumps(data)

            results["embed_id"] = (
                results["embed_id"]
                or extract_embed_id(text)
            )

            results["media_id"] = (
                results["media_id"]
                or find_pattern(MEDIA_PATTERNS, text)
            )

        except (ValueError, TypeError):
            continue

    return results


# ============================================================
# LIVE DOM EXTRACTION
# ============================================================

DOM_SCRIPT = r"""
() => {

    const selectors = [
        "iframe",
        "video",
        "rum-shorts-player",
        "rum-player",
        "rum-player-media",
        "[data-media-id]",
        "[data-video-id]",
        "[data-embed-id]",
        "[data-clip-id]"
    ];

    const results = [];

    for (const selector of selectors) {

        document.querySelectorAll(selector).forEach(element => {

            results.push({

                src: element.getAttribute("src") || "",

                clipId:
                    element.getAttribute("clip-id") ||
                    element.getAttribute("data-clip-id") ||
                    "",

                mediaId:
                    element.getAttribute("media-id") ||
                    element.getAttribute("data-media-id") ||
                    "",

                videoId:
                    element.getAttribute("data-video-id") ||
                    element.getAttribute("video-id") ||
                    "",

                embedId:
                    element.getAttribute("data-embed-id") ||
                    "",

                html: element.outerHTML || ""

            });

        });

    }

    return results;
}
"""


def extract_dom_ids(elements):

    results = {
        "embed_id": None,
        "clip_id": None,
        "media_id": None,
    }

    for element in elements:

        src = element.get("src", "")

        if src and not results["embed_id"]:

            match = re.search(
                r"/embed/([^/?#]+)",
                src,
                re.IGNORECASE
            )

            if match:
                results["embed_id"] = match.group(1)

        if not results["clip_id"]:

            results["clip_id"] = (
                element.get("clipId")
                or find_pattern(
                    SHORTS_PATTERNS,
                    element.get("html", "")
                )
            )

        if not results["media_id"]:

            results["media_id"] = (
                element.get("mediaId")
                or find_pattern(
                    MEDIA_PATTERNS,
                    element.get("html", "")
                )
            )

        if not results["embed_id"]:

            results["embed_id"] = (
                element.get("embedId")
                or extract_embed_id(
                    element.get("html", "")
                )
            )

        if not results["media_id"]:

            results["media_id"] = (
                element.get("videoId")
                or results["media_id"]
            )

    return results


# ============================================================
# COMPLETE EXTRACTION
# ============================================================

def extract_all(html, dom_elements, is_short):

    json_ids = extract_json_ids(html)

    dom_ids = extract_dom_ids(dom_elements)

    return {

        "type": "SHORT" if is_short else "VIDEO",

        "embed_id": (
            extract_embed_id(html)
            or json_ids["embed_id"]
            or dom_ids["embed_id"]
        ),

        "clip_id": (
            find_pattern(SHORTS_PATTERNS, html)
            or dom_ids["clip_id"]
        ),

        "media_id": (
            find_pattern(MEDIA_PATTERNS, html)
            or json_ids["media_id"]
            or dom_ids["media_id"]
        ),

    }


# ============================================================
# OUTPUT
# ============================================================

def print_results(result):

    print()
    print("=" * 60)
    print("RUMBLE EXTRACTION RESULTS")
    print("=" * 60)

    print()
    print("TYPE:", result["type"])

    print()
    print("-" * 60)

    if result["type"] == "SHORT":

        print("VIDEO / MEDIA ID:")
        print(result["media_id"] or "NOT FOUND")

        print()
        print("CLIP ID:")
        print(result["clip_id"] or "NOT FOUND")

        print()
        print("EMBED ID:")
        print(result["embed_id"] or "NOT FOUND")

    else:

        print("VIDEO / EMBED ID:")
        print(result["embed_id"] or "NOT FOUND")

        print()
        print("MEDIA ID:")
        print(result["media_id"] or "NOT FOUND")

    print()
    print("-" * 60)

    if result["embed_id"] and result["type"] == "VIDEO":

        embed_url = (
            f"https://rumble.com/embed/"
            f"{result['embed_id']}/"
        )

        print("EMBED URL:")
        print(embed_url)

        print()
        print("IFRAME:")

        print(
            f'<iframe class="rumble" '
            f'width="640" height="360" '
            f'src="{embed_url}" '
            f'frameborder="0" allowfullscreen></iframe>'
        )

    if not any((
        result["embed_id"],
        result["clip_id"],
        result["media_id"]
    )):

        print()
        print("ERROR: No recognized player IDs found.")

        print(
            "The page may be private, unavailable, "
            "restricted, or using an unsupported player structure."
        )

    print()


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Extract Rumble video and Shorts player IDs."
    )

    parser.add_argument(
        "url",
        help="Rumble video or Shorts URL"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=60000,
        help="Navigation timeout in milliseconds."
    )

    parser.add_argument(
        "--wait",
        type=int,
        default=8000,
        help="Extra JavaScript initialization wait in milliseconds."
    )

    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the Chromium browser."
    )

    args = parser.parse_args()

    try:

        url = validate_url(args.url)

    except ValueError as error:

        print(f"ERROR: {error}", file=sys.stderr)

        return 1

    is_short = "/shorts/" in url.lower()

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=not args.headed
            )

            try:

                context = browser.new_context(

                    viewport={
                        "width": 1280,
                        "height": 720
                    },

                    locale="en-US",

                    user_agent=UA

                )

                page = context.new_page()

                print("Opening Rumble...")

                try:

                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=args.timeout
                    )

                except PlaywrightTimeoutError:

                    print(
                        "WARNING: Navigation timed out. "
                        "Inspecting available page content.",
                        file=sys.stderr
                    )

                if args.wait > 0:

                    page.wait_for_timeout(args.wait)

                html = page.content()

                try:

                    dom_elements = page.evaluate(
                        DOM_SCRIPT
                    )

                except Exception:

                    dom_elements = []

                result = extract_all(
                    html,
                    dom_elements,
                    is_short
                )

                print_results(result)

                if any((
                    result["embed_id"],
                    result["clip_id"],
                    result["media_id"]
                )):
                    return 0

                return 2

            finally:

                browser.close()

    except Exception as error:

        print(
            f"ERROR: {error}",
            file=sys.stderr
        )

        print(
            "Check Playwright and Chromium installation.",
            file=sys.stderr
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())
