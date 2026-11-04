#!/usr/bin/env python3

import sys
import re
from playwright.sync_api import sync_playwright


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)


def main():

    if len(sys.argv) != 2:
        print('Usage: python rum.py "<rumble-url>"')
        sys.exit(1)

    url = sys.argv[1].strip()

    if "rumble.com" not in url.lower():
        print("ERROR: Not a Rumble URL.")
        sys.exit(1)

    is_short = "/shorts/" in url.lower()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            viewport={
                "width": 1280,
                "height": 720
            },
            locale="en-US",
            user_agent=UA
        )

        page = context.new_page()

        try:

            print("Opening Rumble...")

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            # Give Rumble's JS player time to initialize.
            page.wait_for_timeout(8000)

            html = page.content()

            # =================================================
            # RUMBLE SHORTS
            # =================================================

            if is_short:

                print()
                print("TYPE: SHORT")

                # ---------------------------------------------
                # Find clip-id
                #
                # Example:
                #
                # <rum-shorts-player
                #     clip-id="0-3--v7diruq-s1a12fe83">
                # ---------------------------------------------

                clip_matches = re.findall(
                    r'<rum-shorts-player[^>]*'
                    r'clip-id=["\']([^"\']+)["\']',
                    html,
                    re.IGNORECASE
                )

                clip_id = None

                if clip_matches:
                    clip_id = clip_matches[0]

                # ---------------------------------------------
                # Find media-id from the actual <video>
                #
                # Example:
                #
                # <video data-media-id="v7diruq">
                # ---------------------------------------------

                video_matches = re.findall(
                    r'<video[^>]*'
                    r'data-media-id=["\']([^"\']+)["\']',
                    html,
                    re.IGNORECASE
                )

                video_id = None

                if video_matches:
                    video_id = video_matches[0]

                # ---------------------------------------------
                # Fallback: rum-player-media
                # ---------------------------------------------

                if not clip_id:

                    media_matches = re.findall(
                        r'<rum-player-media[^>]*'
                        r'media-id=["\']([^"\']+)["\']',
                        html,
                        re.IGNORECASE
                    )

                    if media_matches:

                        candidate = media_matches[0]

                        # Shorts internal clip IDs generally
                        # look like 0-3--...
                        if candidate.startswith("0-3--"):
                            clip_id = candidate

                # ---------------------------------------------
                # Output
                # ---------------------------------------------

                print()
                print("=" * 60)
                print("VIDEO ID")
                print("=" * 60)

                print(
                    video_id
                    if video_id
                    else "NOT FOUND"
                )

                print()
                print("=" * 60)
                print("CLIP ID")
                print("=" * 60)

                print(
                    clip_id
                    if clip_id
                    else "NOT FOUND"
                )

                print()

                if not video_id and not clip_id:

                    print(
                        "ERROR: Could not find the "
                        "Short's player IDs."
                    )

                    sys.exit(2)

                return

            # =================================================
            # NORMAL RUMBLE VIDEO
            # =================================================

            print()
            print("TYPE: VIDEO")

            embed_id = None

            # ---------------------------------------------
            # Existing iframe
            # ---------------------------------------------

            iframe_matches = re.findall(
                r'<iframe[^>]+src=["\']'
                r'([^"\']*rumble\.com/embed/[^"\']+)'
                r'["\']',
                html,
                re.IGNORECASE
            )

            if iframe_matches:

                match = re.search(
                    r'/embed/([^/?#]+)',
                    iframe_matches[0],
                    re.IGNORECASE
                )

                if match:
                    embed_id = match.group(1)

            # ---------------------------------------------
            # Rumble("play", {video: "..."})
            # ---------------------------------------------

            if not embed_id:

                patterns = [

                    r'Rumble\s*\(\s*["\']play["\']'
                    r'\s*,\s*\{[^}]*?'
                    r'["\']?video["\']?\s*:\s*'
                    r'["\']([^"\']+)["\']',

                    r'["\']embedUrl["\']\s*:\s*'
                    r'["\']https?://(?:www\.)?'
                    r'rumble\.com/embed/'
                    r'([^/"\']+)',

                    r'https?://(?:www\.)?'
                    r'rumble\.com/embed/'
                    r'([^/"\']+)',
                ]

                for pattern in patterns:

                    match = re.search(
                        pattern,
                        html,
                        re.IGNORECASE
                    )

                    if match:

                        embed_id = match.group(1)
                        break

            # ---------------------------------------------
            # Look at iframe elements directly.
            # ---------------------------------------------

            if not embed_id:

                try:

                    iframe_srcs = page.locator(
                        "iframe"
                    ).evaluate_all(
                        """
                        elements =>
                            elements
                                .map(e => e.src)
                                .filter(Boolean)
                        """
                    )

                    for src in iframe_srcs:

                        match = re.search(
                            r'/embed/([^/?#]+)',
                            src,
                            re.IGNORECASE
                        )

                        if match:

                            embed_id = match.group(1)
                            break

                except Exception:
                    pass

            # ---------------------------------------------
            # Output
            # ---------------------------------------------

            print()
            print("=" * 60)
            print("VIDEO ID")
            print("=" * 60)

            if not embed_id:

                print("NOT FOUND")

                print()
                print(
                    "Rumble did not expose a traditional "
                    "embed ID on this page."
                )

                sys.exit(2)

            print(embed_id)

            embed_url = (
                f"https://rumble.com/embed/"
                f"{embed_id}/"
            )

            print()
            print("=" * 60)
            print("IFRAME")
            print("=" * 60)

            print(
                f'<iframe class="rumble" '
                f'width="640" '
                f'height="360" '
                f'src="{embed_url}" '
                f'frameborder="0" '
                f'allowfullscreen></iframe>'
            )

        except Exception as e:

            print()
            print(
                f"ERROR: {e}"
            )

            sys.exit(1)

        finally:

            browser.close()


if __name__ == "__main__":
    main()