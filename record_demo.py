import asyncio
import os
import glob
from playwright.async_api import async_playwright

async def record():
    os.makedirs("recordings", exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir="recordings",
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        
        print("1. Navigating to Smart Travel Concierge app...")
        await page.goto("http://localhost:8080")
        await page.wait_for_timeout(2500)

        print("2. Submitting Prompt 1: Culture & History under $150/day...")
        await page.fill("#input", "Suggest culture & history destinations under $150/day")
        await page.wait_for_timeout(800)
        await page.click("button.send-btn")
        
        # Wait for agent response
        await page.wait_for_selector(".msg.agent .bubble:not(:has(.typing-indicator))", timeout=30000)
        print("   Prompt 1 response received!")
        await page.wait_for_timeout(5000)

        print("3. Submitting Prompt 2: Weather in Kyoto & Postcard image...")
        await page.fill("#input", "What is the weather in Kyoto right now and generate a postcard image for it?")
        await page.wait_for_timeout(800)
        await page.click("button.send-btn")
        
        # Wait for agent response containing generated image
        await page.wait_for_selector(".msg.agent img.a2img", timeout=45000)
        print("   Prompt 2 response with postcard image received!")
        await page.wait_for_timeout(6000)

        print("4. Closing page to finalize recording...")
        await page.close()
        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(record())
