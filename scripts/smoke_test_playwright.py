#!/usr/bin/env python3
"""Minimal Playwright smoke test for the v3 browser stack."""
import asyncio
from patchright.async_api import async_playwright
from playwright_stealth import Stealth


async def main():
    print("=== Playwright + Stealth Smoke Test ===")

    async with async_playwright() as p:
        print("[1/4] Launching Chromium (persistent context)...")
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir="/tmp/mindmap_v3_smoke_profile",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await ctx.new_page()

        print("[2/4] Applying stealth...")
        await Stealth().apply_stealth_async(page)

        print("[3/4] Navigating to example.com...")
        await page.goto("https://example.com", timeout=30000)
        title = await page.title()
        print(f"      Page title: {title}")

        print("[4/4] Checking stealth markers...")
        is_webdriver = await page.evaluate("navigator.webdriver")
        print(f"      navigator.webdriver = {is_webdriver}")

        if is_webdriver is None or is_webdriver is False:
            print("Stealth appears to be working (navigator.webdriver is hidden)")
        else:
            print("navigator.webdriver still visible — stealth may need tuning")

        await ctx.close()

    print("\nSmoke test completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())