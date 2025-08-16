import asyncio
import json
import os
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
from playwright.async_api import async_playwright

CONTACTED_FILE = "contacted.json"

# -------------------------------
# Persistence for contacted list
# -------------------------------
if os.path.exists(CONTACTED_FILE):
    try:
        with open(CONTACTED_FILE, "r", encoding="utf-8") as f:
            CONTACTED_NUMBERS = json.load(f)
    except Exception:
        CONTACTED_NUMBERS = []
else:
    CONTACTED_NUMBERS = []


# Detect if running from PyInstaller exe
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS  # PyInstaller temp dir
    browser_path = os.path.join(base_path, "ms-playwright", ".local-browsers", "chromium-1181", "chrome-win", "chrome.exe")
else:
    browser_path = None  # Use default installed location

def save_contacted():
    try:
        with open(CONTACTED_FILE, "w", encoding="utf-8") as f:
            json.dump(CONTACTED_NUMBERS, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Failed to save contacted.json:", e)


async def random_delay(min_ms=1000, max_ms=3000):
    await asyncio.sleep(random.uniform(min_ms/1000, max_ms/1000))


# -------------------------------
# Tkinter App
# -------------------------------
class WhatsAppApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WhatsApp Sender")
        self.geometry("820x620")
        self.minsize(820, 620)

        try:
            style = ttk.Style(self)
            if "vista" in style.theme_names():
                style.theme_use("vista")
        except Exception:
            pass

        # App-wide data
        self.businesses = []
        self.template_choice = "Website"  # default

        # Pages
        self.page1 = Page1(self)
        self.page_template = PageTemplate(self)
        self.page2 = Page2(self)

        self.page1.pack(fill="both", expand=True)

    def show_page1(self):
        self.page_template.pack_forget()
        self.page2.pack_forget()
        self.page1.pack(fill="both", expand=True)

    def show_template_page(self, businesses):
        self.businesses = businesses
        self.page1.pack_forget()
        self.page_template.pack(fill="both", expand=True)

    def show_page2(self):
        self.page_template.pack_forget()
        self.page2.load_contacts(self.businesses)
        self.page2.pack(fill="both", expand=True)


class Page1(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        title = ttk.Label(self, text="Paste JSON list of businesses", font=("Segoe UI", 16, "bold"))
        subtitle = ttk.Label(self, text='Example: [{"businessName": "ABC", "phone": "2519..."}, ...]', foreground="#666")

        title.pack(pady=(16, 2))
        subtitle.pack(pady=(0, 12))

        self.textbox = scrolledtext.ScrolledText(self, wrap=tk.WORD, width=100, height=24, font=("Consolas", 11))
        self.textbox.pack(padx=12, pady=6, fill="both", expand=True)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=12)

        self.next_btn = ttk.Button(btn_frame, text="Next ➡", command=self.next_page)
        self.next_btn.pack()

    def next_page(self):
        raw = self.textbox.get("1.0", tk.END).strip()
        try:
            businesses = json.loads(raw)
            if not isinstance(businesses, list):
                raise ValueError("Root JSON must be an array of objects.")
        except Exception as e:
            messagebox.showerror("Invalid JSON", f"Please paste a valid JSON array.\n\nError: {e}")
            return
        self.master.show_template_page(businesses)


class PageTemplate(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        ttk.Label(self, text="Choose Message Template", font=("Segoe UI", 16, "bold")).pack(pady=(20, 10))

        ttk.Label(self, text="Select one of the templates below:", font=("Segoe UI", 11)).pack(pady=(0, 15))

        self.choice_var = tk.StringVar(value="Website")

        logo_btn = ttk.Radiobutton(self, text="Logo", variable=self.choice_var, value="Logo")
        web_btn = ttk.Radiobutton(self, text="Website", variable=self.choice_var, value="Website")

        logo_btn.pack(anchor="w", padx=40, pady=5)
        web_btn.pack(anchor="w", padx=40, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="⬅ Back", command=self.master.show_page1).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Next ➡", command=self.confirm_choice).pack(side="left", padx=5)

    def confirm_choice(self):
        self.master.template_choice = self.choice_var.get()
        self.master.show_page2()


class Page2(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        header = ttk.Frame(self)
        header.pack(fill="x", padx=12, pady=(12, 8))

        self.back_btn = ttk.Button(header, text="⬅ Back", command=lambda: master.show_template_page(master.businesses))
        self.back_btn.pack(side="left")

        self.contact_btn = ttk.Button(header, text="📩 Contact", command=self.start_contacting)
        self.contact_btn.pack(side="right")

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.tree = ttk.Treeview(table_frame, columns=("idx", "name", "phone", "status"), show="headings")
        self.tree.heading("idx", text="#")
        self.tree.heading("name", text="Business Name")
        self.tree.heading("phone", text="Phone")
        self.tree.heading("status", text="Status")

        self.tree.column("idx", width=40, anchor="center")
        self.tree.column("name", width=320)
        self.tree.column("phone", width=180)
        self.tree.column("status", width=140)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.tree.tag_configure("sent", foreground="#0f7d0f")
        self.tree.tag_configure("skipped", foreground="#c07b00")
        self.tree.tag_configure("invalid", foreground="#b00020")
        self.tree.tag_configure("pending", foreground="#444444")
        self.tree.tag_configure("working", foreground="#0057d8")

        ttk.Label(self, text="Logs", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12)
        self.log_box = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=10, state="disabled", font=("Consolas", 10))
        self.log_box.pack(fill="x", padx=12, pady=(4, 12))

        self._iid_by_phone = {}

    def load_contacts(self, businesses):
        self._iid_by_phone.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for i, biz in enumerate(businesses, start=1):
            name = biz.get("businessName", "Unknown")
            phone = str(biz.get("phone", "")).strip()
            iid = self.tree.insert("", "end", values=(i, name, phone, "Pending"), tags=("pending",))
            self._iid_by_phone[phone] = iid

        self.safe_log(f"✅ Contacts loaded with template: {self.master.template_choice}")

    def safe_log(self, text):
        self.after(0, self._append_log, text)

    def _append_log(self, text):
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

    def set_row_status(self, phone, status_text, tag):
        self.after(0, self._apply_row_status, phone, status_text, tag)

    def _apply_row_status(self, phone, status_text, tag):
        iid = self._iid_by_phone.get(phone)
        if not iid:
            return
        vals = list(self.tree.item(iid, "values"))
        vals[-1] = status_text
        self.tree.item(iid, values=vals, tags=(tag,))

    def toggle_controls(self, enabled):
        state = "normal" if enabled else "disabled"
        self.back_btn.config(state=state)
        self.contact_btn.config(state=state)

    def start_contacting(self):
        self.toggle_controls(False)
        self.safe_log("▶ Starting sending process...")
        threading.Thread(target=self._thread_entry, daemon=True).start()

    def _thread_entry(self):
        try:
            result = asyncio.run(self.async_main())
        except Exception as e:
            result = None
            self.safe_log(f"❌ Unexpected error: {e}")
        self.after(0, self._on_done, result)

    async def async_main(self):
        return await send_messages(
            self.master.businesses,
            self.master.template_choice,
            log_cb=self.safe_log,
            status_cb=self.set_row_status
        )

    def _on_done(self, result):
        self.toggle_controls(True)
        if result is not None:
            pretty = json.dumps(result, indent=2, ensure_ascii=False)
            self.safe_log("⏹ Done.")
            messagebox.showinfo("Done", f"Results:\n{pretty}")


# -------------------------------
# WhatsApp automation (Playwright)
# -------------------------------
async def send_messages(businesses, template_choice, log_cb, status_cb):
    result = {"total": len(businesses), "contacted": 0, "notfound": 0, "alreadyContacted": 0, "composerNotFound": 0}

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="./whatsapp_session",
            executable_path=browser_path,  # If None, Playwright will find installed browser
            headless=False
        )
        # browser = await p.chromium.launch_persistent_context(user_data_dir="./whatsapp_session", headless=False)
        page = await browser.new_page()

        log_cb("📱 Opening WhatsApp Web…")
        await page.goto("https://web.whatsapp.com/")
        try:
            await page.wait_for_selector("div[role='grid']", timeout=120_000)
            log_cb("✅ Logged in successfully!")
        except Exception:
            log_cb("❌ Login timeout.")
            await browser.close()
            return result

        for biz in businesses:
            phone = str(biz.get("phone", "")).strip()
            name = biz.get("businessName", "Unknown")

            if not phone:
                log_cb(f"⚠️ Missing phone for {name}")
                continue

            if phone in CONTACTED_NUMBERS:
                log_cb(f"⏩ Already contacted: {name} ({phone})")
                status_cb(phone, "Already contacted", "skipped")
                result["alreadyContacted"] += 1
                continue

            status_cb(phone, "Opening chat…", "working")
            await page.goto(f"https://web.whatsapp.com/send?phone={phone}")
            await random_delay(5000, 7000)

            invalid = False
            try:
                await page.wait_for_selector("div[role='alert']", timeout=4000)
                html = (await page.content()).lower()
                if "invalid" in html or "not on whatsapp" in html:
                    invalid = True
            except Exception:
                pass

            if invalid:
                log_cb(f"🔴 Invalid number: {phone}")
                status_cb(phone, "Invalid", "invalid")
                result["notfound"] += 1
                continue

            try:
                composer = await page.wait_for_selector('footer div[contenteditable="true"]', timeout=15000)
            except Exception:
                log_cb(f"❌ No composer for {name} ({phone})")
                status_cb(phone, "No composer", "invalid")
                result["composerNotFound"] += 1
                continue

            messages = [
                "ሰላም ጤና ይስጥልኝ",
                f"ለ {name} {('ሎጎ' if template_choice == 'Logo' else 'Website')} ትፈልጋላችሁ?"
            ]

            try:
                for msg in messages:
                    await composer.type(msg, delay=random.randint(50, 120))
                    await random_delay(900, 1800)
                    await page.keyboard.press("Enter")
                    await random_delay(1500, 3500)

                log_cb(f"🟢 Sent to {name} ({phone})")
                status_cb(phone, "Sent", "sent")
                result["contacted"] += 1
                CONTACTED_NUMBERS.append(phone)
                save_contacted()
                await random_delay(2500, 5000)
            except Exception as e:
                log_cb(f"❌ Failed to send to {name}: {e}")
                status_cb(phone, "Failed", "invalid")

        await browser.close()

    return result


if __name__ == "__main__":
    app = WhatsAppApp()
    app.mainloop()
