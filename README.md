
# Rumble Regex

**Extract actual Rumble video player IDs, embed IDs, Shorts clip IDs, and media IDs from Rumble URLs using Python, regular expressions, and Playwright.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Browser-Playwright-green)](https://playwright.dev/python/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](#requirements)

Repository: https://github.com/zaynkhan100110/rumble-regex

---

## Overview

Rumble Regex is a lightweight Python command-line utility designed to inspect Rumble video pages and extract the identifiers used by Rumble's video player.

A normal Rumble video URL does not necessarily expose the same identifier used by its embedded player.

For example, a page URL may look like:

```text
https://rumble.com/v123456-example-video.html
```

However, the corresponding player may use an embed URL in this format:

```text
https://rumble.com/embed/EMBED_ID/
```

This project attempts to locate the actual player identifier by examining the page's HTML, JavaScript-rendered content, iframe elements, player configuration, and embedded metadata.

It also supports Rumble Shorts, where the clip ID and underlying media ID may be different identifiers.

## Features

- Extract standard Rumble video embed IDs.
- Detect Rumble Shorts.
- Extract Shorts clip IDs.
- Extract underlying media IDs when exposed.
- Search iframe embed URLs.
- Inspect Rumble player configuration.
- Search multiple regular expression patterns.
- Inspect JavaScript-rendered page content.
- Inspect live browser DOM elements.
- Inspect embedded JSON metadata.
- Generate an iframe embed snippet.
- Configurable browser initialization wait.
- Configurable navigation timeout.
- Optional visible-browser debugging.
- Strict Rumble hostname validation.
- Automatic Chromium browser cleanup.

## Project Structure

```text
rumble-regex/
│
├── rumble.py
├── README.md
└── LICENSE
```

## Requirements

- Python 3.10 or newer
- pip
- Playwright for Python
- Chromium browser installed through Playwright
- Internet connection
- Access to the public Rumble page being inspected

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/zaynkhan100110/rumble-regex.git
```

### 2. Enter the project directory

```bash
cd rumble-regex
```

### 3. Create a virtual environment

Recommended for keeping dependencies isolated.

Windows:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Playwright

```bash
python -m pip install --upgrade pip
python -m pip install playwright
```

### 5. Install Chromium

```bash
python -m playwright install chromium
```

Linux users may also need system browser dependencies:

```bash
python -m playwright install --with-deps chromium
```

## Usage

The script is named `rumble.py`.

### Standard Rumble video

```bash
python rumble.py "https://rumble.com/v123456-example-video.html"
```

### Rumble Shorts

```bash
python rumble.py "https://rumble.com/shorts/EXAMPLE"
```

Replace the example URLs with actual Rumble URLs.

## Command-Line Options

| Option | Description | Default |
|---|---|---|
| `url` | Rumble video or Shorts URL | Required |
| `--timeout` | Navigation timeout in milliseconds | 60000 |
| `--wait` | Additional JavaScript initialization wait | 8000 |
| `--headed` | Show the Chromium browser window | Disabled |

### Increase the initialization wait

```bash
python rumble.py "YOUR_RUMBLE_URL" --wait 15000
```

Useful when the player takes longer to initialize.

### Increase the navigation timeout

```bash
python rumble.py "YOUR_RUMBLE_URL" --timeout 90000
```

### Open the browser visibly

```bash
python rumble.py "YOUR_RUMBLE_URL" --headed
```

Useful for investigating page-loading problems and player initialization.

### Display help

```bash
python rumble.py --help
```

## Understanding the Extracted IDs

Rumble may expose several different identifiers.

They should not be treated as interchangeable.

### 1. Embed ID

The embed ID identifies the player embed.

It can be used to construct a standard embed URL:

```text
https://rumble.com/embed/EMBED_ID/
```

Example iframe:

```html
<iframe
    class="rumble"
    width="640"
    height="360"
    src="https://rumble.com/embed/EMBED_ID/"
    frameborder="0"
    allowfullscreen>
</iframe>
```

### 2. Shorts Clip ID

A Shorts clip ID identifies a particular Shorts player item.

An example internal representation might look like:

```text
0-3--example-clip-id
```

The exact format depends on Rumble's implementation.

A clip ID should not automatically be treated as a standard embed ID.

### 3. Media ID

A media ID identifies an underlying media object when the page exposes it.

For example:

```html
<video data-media-id="MEDIA_ID">
```

The media ID and clip ID may be different.

### 4. Direct Media URL

A direct media URL is an actual video stream or file address.

It is different from an embed ID, clip ID, or media ID.

**This project extracts player identifiers. It does not currently download videos or guarantee discovery of direct media URLs.**

## How Does It Work?

The extraction process has several stages.

### Stage 1: URL Validation

The script validates the supplied URL.

It checks:

- HTTP or HTTPS protocol.
- Rumble hostname.
- Non-empty video path.

It rejects unrelated domains and lookalike hostnames.

### Stage 2: Browser Initialization

Playwright launches Chromium in headless mode by default.

The browser context uses:

- Desktop viewport.
- English locale.
- Configured browser user agent.

### Stage 3: Page Navigation

The browser navigates to the requested Rumble page.

The script waits for the initial document to load.

It can also continue inspecting the available page if navigation reaches its timeout.

### Stage 4: JavaScript Initialization

The script waits for the configured initialization interval.

This gives the Rumble player scripts time to create their elements.

### Stage 5: HTML Inspection

Regular expressions inspect the page HTML.

The extraction engine searches for:

- iframe embed URLs.
- Embed URL configuration.
- Rumble player initialization.
- Video identifiers.
- Embed identifiers.
- Shorts clip identifiers.
- Media identifiers.
- Player data attributes.

### Stage 6: JSON Inspection

The script inspects JSON-LD metadata embedded in script elements.

This provides another possible source of video and media information.

### Stage 7: Live DOM Inspection

Playwright inspects the rendered page.

It looks for:

- iframe elements.
- video elements.
- rum-shorts-player.
- rum-player.
- rum-player-media.
- data-media-id.
- data-video-id.
- data-embed-id.
- data-clip-id.

This is particularly useful when the page creates player elements after JavaScript execution.

### Stage 8: Fallback Extraction

The script combines the results from:

1. Original page HTML.
2. Embedded JSON metadata.
3. Live DOM elements.

It reports the identifiers it found.

### Stage 9: Embed Generation

When a standard embed ID is found, the script generates:

- Embed URL.
- HTML iframe snippet.

## Extraction Strategies

The project uses multiple regular expression patterns because Rumble may expose player information in different formats.

### Standard Video Patterns

The extraction engine searches for:

```text
iframe src
embedUrl
embed_url
embedURL
Rumble("play", ...)
video
videoId
video_id
embedId
embed_id
videoID
videoIDHash
data-video-id
data-embed-id
```

### Shorts Patterns

The extraction engine searches for:

```text
clip-id
clipId
data-clip-id
shortsId
```

### Media Patterns

The extraction engine searches for:

```text
data-media-id
media-id
mediaId
media_id
```

These patterns are best-effort extraction strategies, not an official Rumble API specification.

## Example Output

The exact output depends on the page and which identifiers Rumble exposes.

### Standard Video

```text
Opening Rumble...

============================================================
RUMBLE EXTRACTION RESULTS
============================================================

TYPE: VIDEO

------------------------------------------------------------
VIDEO / EMBED ID:
EXAMPLE_EMBED_ID

MEDIA ID:
NOT FOUND

------------------------------------------------------------
EMBED URL:
https://rumble.com/embed/EXAMPLE_EMBED_ID/

IFRAME:
<iframe class="rumble" width="640" height="360" src="https://rumble.com/embed/EXAMPLE_EMBED_ID/" frameborder="0" allowfullscreen></iframe>
```

### Shorts

```text
Opening Rumble...

============================================================
RUMBLE EXTRACTION RESULTS
============================================================

TYPE: SHORT

------------------------------------------------------------
VIDEO / MEDIA ID:
EXAMPLE_MEDIA_ID

CLIP ID:
EXAMPLE_CLIP_ID

EMBED ID:
NOT FOUND
```

These outputs are illustrative examples, not real extracted identifiers.

## Exit Codes

| Exit Code | Meaning |
|---|---|
| 0 | At least one identifier was found |
| 1 | Invalid input or runtime/browser error |
| 2 | Page inspected, but no recognized identifier found |

## Troubleshooting

### Chromium executable not found

Run:

```bash
python -m playwright install chromium
```

### Missing Linux dependencies

Run:

```bash
python -m playwright install --with-deps chromium
```

### No player ID found

Possible reasons:

- The video has been removed.
- The video is private.
- The page requires authentication.
- The page is region-restricted.
- Rumble changed its player implementation.
- The player has not finished initializing.
- A browser challenge prevented the page from loading.
- The identifier is not exposed in the inspected page.

Try:

```bash
python rumble.py "YOUR_RUMBLE_URL" --wait 15000
```

You can also inspect the browser visually:

```bash
python rumble.py "YOUR_RUMBLE_URL" --headed
```

### Navigation timeout

The script attempts to inspect whatever page content has loaded, even after a navigation timeout.

A timeout does not necessarily mean that the page contains no useful information.

### Invalid Rumble URL

Use an actual Rumble video or Shorts URL.

Supported hostname examples:

```text
rumble.com
www.rumble.com
```

The script also accepts subdomains of rumble.com.

## Limitations

Rumble can change its:

- HTML structure.
- Player initialization.
- JavaScript configuration.
- Embedded metadata.
- Player custom elements.
- Identifier formats.

Consequently, regex-based extraction cannot guarantee compatibility with every video.

The project relies on publicly exposed page information and browser-rendered DOM elements.

It does not bypass:

- DRM.
- Authentication requirements.
- Private video restrictions.
- Geo-restrictions.
- Access controls.
- Rate limits.

An extracted ID does not guarantee that a video can be downloaded or embedded in every environment.

## Security and Responsible Use

Use this project only with content you are authorized to access.

Respect:

- Rumble's terms of service.
- Copyright laws.
- Creator rights.
- Video privacy settings.
- Applicable content distribution restrictions.

The extraction of an identifier does not grant permission to download, redistribute, or republish a video.

Do not publish session cookies, authentication tokens, or private account information in bug reports.

## Contributing

Contributions are welcome.

If you discover a Rumble page that the current extraction engine cannot recognize, consider opening an issue.

Useful information includes:

- Whether the URL is a normal video or a Short.
- Whether the page is publicly accessible.
- Which extraction patterns failed.
- The relevant non-sensitive player HTML.
- The error output.

Do not submit private account credentials or session cookies.

Pull requests improving extraction accuracy, fallback handling, testing, and documentation are welcome.

## Future Improvements

Potential future improvements include:

- More player configuration extraction patterns.
- Additional Shorts player support.
- Automated extraction tests using saved HTML fixtures.
- Structured JSON output.
- Batch URL processing.
- Better player detection.
- Optional direct media URL inspection where publicly exposed.
- Optional metadata extraction.
- Improved compatibility monitoring.

These are potential improvements and are not all implemented in the current version.

## License

See the repository's LICENSE file for licensing information.

---

**Repository:** https://github.com/zaynkhan100110/rumble-regex

**Main script:** `rumble.py`

**Documentation:** `README.md`
