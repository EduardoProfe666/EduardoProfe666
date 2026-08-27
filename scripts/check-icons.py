#!/usr/bin/env python3
"""Check that all external image URLs in README.md return HTTP 200.

Extracts every <img> tag from the entire README, skips local file paths
(assets/), and validates each external URL returns a successful HTTP status.
Exits with code 1 if any URL is broken.
"""

import re
import sys
import urllib.request
import urllib.error

README_PATH = "README.md"
TIMEOUT = 15  # seconds per request


def extract_all_image_urls(content: str) -> list[tuple[str, str, str]]:
    """Extract (alt_text, url, section_name) from all <img> tags.

    Skips local file references (assets/*).
    """
    img_pattern = re.compile(r'<img[^>]*\s+src="([^"]+)"[^>]*\s+alt="([^"]*)"[^>]*>')
    urls: list[tuple[str, str, str]] = []

    lines = content.splitlines()
    current_section = "(top)"

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Track current section heading
        if stripped.startswith("## "):
            current_section = stripped.lstrip("#").strip()
            continue

        for match in img_pattern.finditer(line):
            url = match.group(1)
            alt = match.group(2)

            # Skip local file references
            if url.startswith("assets/") or url.startswith("./") or url.startswith("../"):
                continue

            urls.append((alt, url, current_section))

    return urls


def check_url(alt: str, url: str) -> tuple[str, int | str, bool]:
    """Check a single URL. Returns (alt, status_or_error, is_ok)."""
    try:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; IconChecker/1.0)"
                ),
            },
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.status
            # Accept 200 and 304 (Not Modified — cached but valid)
            return (alt, status, status in (200, 304))
    except urllib.error.HTTPError as e:
        return (alt, f"HTTP {e.code}", False)
    except urllib.error.URLError as e:
        return (alt, str(e.reason), False)
    except Exception as e:
        return (alt, str(e), False)


def main() -> int:
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    images = extract_all_image_urls(content)
    if not images:
        print(f"::error::No external image URLs found in {README_PATH}")
        return 1

    print(f"Checking {len(images)} external image URLs...\n")

    failed = 0
    current_section = None

    for alt, url, section in images:
        # Print section header when section changes
        if section != current_section:
            current_section = section
            print(f"\n--- {section} ---")

        alt_text, status, ok = check_url(alt, url)
        status_icon = "[OK]" if ok else "[FAIL]"
        if not ok:
            failed += 1

        safe_url = url.encode("utf-8", errors="replace").decode("utf-8")
        print(f"  {alt_text}: {safe_url}")
        print(f"    {status_icon} {status}")
        print()

    summary = (
        f"\n{'='*50}\n"
        f"{len(images)} URLs checked across all sections, {failed} failed"
    )
    if failed:
        print(f"{summary}\n::error::[FAIL] {failed} URL(s) returned errors")
    else:
        print(f"{summary}\n[OK] All external image URLs OK")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
