import asyncio
import json
import os
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import config  # Import the config module
from playwright.async_api import async_playwright

# Import from helper for functions
from helper import (
    load_json, save_json, save_all_state, save_contacted_item,
    save_failed_item, remove_from_pending_by_phone, random_delay,
    is_priority_business
)

# Local imports (uncomment when needed)
# from page1 import Page1
# from pageTemplate import PageTemplate
# from page2 import Page2
# from whatsapp import WhatsAppApp


if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS  # PyInstaller temp dir
    browser_path = os.path.join(base_path, "ms-playwright", ".local-browsers", "chromium-1181", "chrome-win", "chrome.exe")
else:
    browser_path = None  # Use default installed location


async def send_messages(businesses, template_choice, log_cb, status_cb):
    """
    businesses: list of business objects (as in config.PENDING_LIST)
    template_choice: "Website" | "Logo"
    log_cb: function(text)
    status_cb: function(phone, status_text, tag)
    """
    result = {"total": len(businesses), "contacted": 0, "notfound": 0, "alreadyContacted": 0, "composerNotFound": 0, "failed": 0}
    print("pending \n", config.PENDING_LIST)
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="./whatsapp_session",
            executable_path=browser_path,  # If None, Playwright will find installed browser
            headless=False
        )
        page = await browser.new_page()

        log_cb("📱 Opening WhatsApp Web…")
        try:
            await page.goto("https://web.whatsapp.com/", timeout=120_000)
            log_cb("- Whatsapp opened!")
        except Exception:
            log_cb("❌ Unable Accessing Whatsapp.")
            await browser.close()
            return result
        try:
            # Wait for general chats grid (logged-in indicator)
            await page.wait_for_selector("div[role='grid']", timeout=120_000)
            log_cb("✅ Logged in successfully!")
        except Exception:
            log_cb("❌ Login timeout.")
            await browser.close()
            return result

        # We'll iterate over a shallow copy — config.PENDING_LIST will be updated on disk during processing
        for biz in list(businesses):
            phone = str(biz["phone"]).strip()
            name = biz["businessName"]

            if not phone:
                log_cb(f"⚠️ Missing phone for {name}")
                continue

            isPhoneContacted = False

            for p in config.CONTACTED_LIST:
                isPhoneContacted = p["phone"] == phone or isPhoneContacted
            
            if isPhoneContacted:
                log_cb(f"⏩ Already contacted: {name} ({phone})")
                status_cb(phone, "Already contacted", "skipped")
                result["alreadyContacted"] += 1
                # Ensure it's removed from pending so we don't try it again next run
                remove_from_pending_by_phone(phone)
                continue
            

            status_cb(phone, "Opening chat…", "working")
            # open direct chat URL
            try:
                await page.goto(f"https://web.whatsapp.com/send?phone={phone}", timeout=30_000)
            except Exception:
                # If page.goto fails for this URL, mark as failed and continue
                log_cb(f"❌ Failed to open chat for {name} ({phone})")
                status_cb(phone, "Failed to open", "invalid")
                # save_failed_item(name, phone, "open_chat_failed")
                # remove_from_pending_by_phone(phone)
                result["failed"] += 1
                continue

            # await random_delay(4000, 7000)

            # detect invalid number / not on whatsapp
            invalid = False
            try:
                # wait a short time for alert that indicates invalid number
                await page.wait_for_selector("div[role='alert']", timeout=4000)
                html = (await page.content()).lower()
                if "invalid" in html or "not on whatsapp" in html or "phone number shared via url is invalid" in html:
                    invalid = True
            except Exception:
                pass

            if invalid:
                log_cb(f"🔴 Invalid number: {phone}")
                status_cb(phone, "Invalid", "invalid")
                result["notfound"] += 1
                save_failed_item(name, phone, "invalid_number")
                remove_from_pending_by_phone(phone)
                print(f"Invalid number {name} ")
                continue

            # find composer (input/footer)
            try:
                composer = await page.wait_for_selector('footer div[contenteditable="true"]', timeout=15000)
            except Exception:
                log_cb(f"❌ No composer for {name} ({phone})")
                status_cb(phone, "No composer", "invalid")
                result["composerNotFound"] += 1
                save_failed_item(name, phone, "no_composer")
                print(f"Composer not found {name} ")
                continue

            # Compose messages
            messages = [
                "ሰላም ጤና ይስጥልኝ",
                f"ለ {name} {('ሎጎ' if template_choice == 'Logo' else 'Website')} ትፈልጋላችሁ?"
            ]

            try:
                all_sent = True  # track if all messages are sent/read

                # First, send all messages
                for msg in messages:
                    await composer.type(msg, delay=random.randint(50, 55))
                    await page.keyboard.press("Enter")
                    log_cb(f"⏳ Message queued: {msg[:30]}...")
                    await asyncio.sleep(1)  # Small delay between messages

                # After all messages are sent, verify status for each message
                for i, msg in enumerate(messages, 1):
                    try:
                        # Wait for either sent (✓) or read (✓✓) status for each message
                        # Using nth-match to find the specific message's status
                        await page.wait_for_selector(
                            f'(//span[@data-icon="msg-check" or @data-icon="msg-dblcheck"])[{i}]',
                            timeout=30000
                        )
                        log_cb(f"✅ Message {i} confirmed (Sent/Read): {msg[:30]}...")
                    except Exception as e:
                        log_cb(f"❌ Message {i} not confirmed: {msg[:30]}... Error: {str(e)}")
                        all_sent = False
                        break  # Stop checking if one fails

                if all_sent:
                    log_cb(f"🟢 All messages sent to {name} ({phone})")
                    status_cb(phone, "Sent", "sent")
                    result["contacted"] += 1
                    save_contacted_item(name, phone)
                    remove_from_pending_by_phone(phone)
                else:
                    log_cb(f"❌ Not all messages sent to {name} ({phone})")
                    status_cb(phone, "Failed", "invalid")
                    result["failed"] += 1
                    save_failed_item(name, phone, "one_or_more_unsent")

            except Exception as e:
                log_cb(f"❌ Failed to send to {name}: {e}")
                status_cb(phone, "Failed", "invalid")
                result["failed"] += 1
                save_failed_item(name, phone, str(e))


        await browser.close()

    return result
