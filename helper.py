import asyncio
import json
import os
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import config
from playwright.async_api import async_playwright

def load_json(filename, default=None):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save {filename}: {e}")


# -------------------------------
# Load persisted lists
# -------------------------------

def load_all_state():
    """Load all application state from their respective files"""
    config.PENDING_LIST = load_json(config.PENDING_FILE, [])
    config.CONTACTED_LIST = load_json(config.CONTACTED_FILE, [])
    config.FAILED_LIST = load_json(config.FAILED_FILE, [])
    # Also update CONTACTED_NUMBERS to match CONTACTED_LIST
    config.CONTACTED_NUMBERS = [contact['phone'] for contact in config.CONTACTED_LIST if 'phone' in contact]

def save_all_state():
    """Save all application state to their respective files"""
    save_json(config.PENDING_FILE, config.PENDING_LIST)
    save_json(config.CONTACTED_FILE, config.CONTACTED_LIST)
    save_json(config.FAILED_FILE, config.FAILED_LIST)

def save_contacted_item(name, phone):
    """Save a contacted item to the contacted list and update the numbers cache"""
    config.CONTACTED_LIST.append({"businessName": name, "phone": phone})
    if phone not in config.CONTACTED_NUMBERS:
        config.CONTACTED_NUMBERS.append(phone)
    save_json(config.CONTACTED_FILE, config.CONTACTED_LIST)
    config.CONTACTED_NUMBERS.append(phone)

def save_failed_item(name, phone, reason=None):
    entry = {"businessName": name, "phone": phone}
    if reason:
        entry["reason"] = reason
    config.FAILED_LIST.append(entry)
    save_json(config.FAILED_FILE, config.FAILED_LIST)

def remove_from_pending_by_phone(phone):
    print(f"Removing {phone} from pending list")
    print(config.PENDING_LIST)
    config.PENDING_LIST = [b for b in config.PENDING_LIST if str(b["phone"]) != str(phone)]
    save_json(config.PENDING_FILE, config.PENDING_LIST)

async def random_delay(min_ms=1000, max_ms=3000):
    await asyncio.sleep(random.uniform(min_ms/1000, max_ms/1000))

def is_priority_business(name):
    if not name:
        return False
    n = name.lower()
    return any(k in n for k in config.PRIORITY_KEYWORDS)
