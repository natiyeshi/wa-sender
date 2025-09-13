import asyncio
import json
import os
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
from datetime import datetime
from functools import partial
from playwright.async_api import async_playwright

# -------------------------------
# Files & Keywords
# -------------------------------
PENDING_FILE = "pending.json"
CONTACTED_FILE = "contacted.json"
FAILED_FILE = "failed.json"
CONTACTED_NUMBERS_FILE = "contacted_numbers.json"  # optional list of raw numbers

PRIORITY_KEYWORDS = ["software", "computer", "web", "branding", "marketing", "solution"]

# -------------------------------
# Helpers for JSON persistence
# -------------------------------
def load_json(filename, default):
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
# pending is a list of business objects: {"businessName": "...", "phone": "...", ...}
PENDING_LIST = load_json(PENDING_FILE, [])
# contacted is a list of objects: {"businessName": "...", "phone": "..."}
CONTACTED_LIST = load_json(CONTACTED_FILE, [])
# failed is a list of objects: {"businessName": "...", "phone": "...", "reason": "..."}
FAILED_LIST = load_json(FAILED_FILE, [])
# also maintain a simple list of numbers (for quick duplicate detection if desired)
CONTACTED_NUMBERS = load_json(CONTACTED_NUMBERS_FILE, [])

# -------------------------------
# Detect if running from PyInstaller exe
# -------------------------------
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS  # PyInstaller temp dir
    browser_path = os.path.join(base_path, "ms-playwright", ".local-browsers", "chromium-1181", "chrome-win", "chrome.exe")
else:
    browser_path = None  # Use default installed location

def save_all_state():
    save_json(PENDING_FILE, PENDING_LIST)
    save_json(CONTACTED_FILE, CONTACTED_LIST)
    save_json(FAILED_FILE, FAILED_LIST)
    save_json(CONTACTED_NUMBERS_FILE, CONTACTED_NUMBERS)

def save_contacted_item(name, phone):
    CONTACTED_LIST.append({"businessName": name, "phone": phone})
    if phone not in CONTACTED_NUMBERS:
        CONTACTED_NUMBERS.append(phone)
    save_json(CONTACTED_FILE, CONTACTED_LIST)
    save_json(CONTACTED_NUMBERS_FILE, CONTACTED_NUMBERS)

def save_failed_item(name, phone, reason=None):
    entry = {"businessName": name, "phone": phone}
    if reason:
        entry["reason"] = reason
    FAILED_LIST.append(entry)
    save_json(FAILED_FILE, FAILED_LIST)

def remove_from_pending_by_phone(phone):
    global PENDING_LIST
    PENDING_LIST = [b for b in PENDING_LIST if str(b.get("phone")) != str(phone)]
    save_json(PENDING_FILE, PENDING_LIST)

# -------------------------------
# Utilities
# -------------------------------
async def random_delay(min_ms=1000, max_ms=3000):
    await asyncio.sleep(random.uniform(min_ms/1000, max_ms/1000))

def is_priority_business(name):
    if not name:
        return False
    n = name.lower()
    return any(k in n for k in PRIORITY_KEYWORDS)

# -------------------------------
# Tkinter App
# -------------------------------
class WhatsAppApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WhatsApp Sender Pro")
        self.geometry("1100x750")
        self.minsize(1000, 700)
        
        # Set window icon and theme
        self._set_window_icon()
        
        # Configure styles and theme
        self.configure_style()
        
        # Configure grid for main window
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Set window attributes for modern look
        self._center_window()
        
    def _center_window(self):
        """Center the window on the screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
    def _set_window_icon(self):
        """Set the application icon if available"""
        try:
            self.iconbitmap(default="icon.ico")
        except Exception as e:
            pass  # Use default icon if custom icon is not available
            
    def configure_style(self):
        style = ttk.Style(self)
        
        # Set a modern theme if available
        if "vista" in style.theme_names():
            style.theme_use("vista")
        
        # Modern color palette
        primary_color = '#4361ee'     # Vibrant blue
        secondary_color = '#f8f9ff'   # Very light blue-gray
        accent_color = '#3a0ca3'      # Darker blue for accents
        success_color = '#4cc9f0'     # Teal for success states
        warning_color = '#f72585'     # Pink for warnings/errors
        text_color = '#2b2d42'        # Dark gray for text
        light_text = '#8d99ae'        # Lighter gray for secondary text
        background = '#ffffff'         # White background
        card_bg = '#f8f9ff'           # Light blue-gray for cards
        border_color = '#e2e8f0'      # Light gray for borders
        hover_color = '#f1f5fe'       # Light blue for hover states
        
        # Configure base styles
        style.configure('.', 
                      font=('Segoe UI', 10), 
                      background=background,
                      foreground=text_color)
        
        # Configure main window
        self.configure(background=background)
        
        # Configure frames
        style.configure('TFrame', background=background)
        style.configure('Card.TFrame', 
                       background=card_bg, 
                       borderwidth=1, 
                       relief='solid',
                       borderradius=8)
        
        # Configure labels
        style.configure('TLabel', 
                       background=background,
                       foreground=text_color)
        style.configure('Header.TLabel', 
                       font=('Segoe UI', 24, 'bold'), 
                       foreground=primary_color,
                       background=background)
        style.configure('Subtitle.TLabel',
                       font=('Segoe UI', 11),
                       foreground=light_text)
        style.configure('Stat.TLabel',
                       font=('Segoe UI', 10, 'bold'),
                       foreground=text_color)
        
        # Configure buttons
        style.configure('TButton', 
                       padding=(16, 8), 
                       relief='flat',
                       borderwidth=0,
                       font=('Segoe UI', 10),
                       background='green',
                       foreground=primary_color)
        
        # Button hover effects
        style.map('TButton',
                 background=[('active', hover_color)],
                 foreground=[('active', primary_color)])
        
        # Accent button style (primary action)
        style.configure('Accent.TButton',
                      font=('Segoe UI', 11, 'bold'),
                      background=primary_color,
                      foreground='white',
                      padding=(24, 10),
                      borderwidth=0,
                      focuscolor=primary_color,
                      focusthickness=0)
        
        style.map('Accent.TButton',
                 background=[('active', '#3a56e8')],
                 foreground=[('active', 'white')])
        
        # Secondary button style
        style.configure('Secondary.TButton',
                      background='#f1f5fe',
                      foreground=primary_color,
                      padding=(16, 8),
                      borderwidth=0)
        
        style.map('Secondary.TButton',
                 background=[('active', '#e6edfd')],
                 foreground=[('active', primary_color)])
        
        # Link button style (for back buttons)
        style.configure('Link.TButton',
                      background=background,
                      foreground=primary_color,
                      borderwidth=0,
                      padding=5,
                      font=('Segoe UI', 9))
        
        style.map('Link.TButton',
                 foreground=[('active', accent_color)])
        
        # Configure notebook
        style.configure('TNotebook',
                      background=background,
                      borderwidth=0)
        
        style.configure('TNotebook.Tab',
                      padding=[20, 10],
                      font=('Segoe UI', 10, 'bold'),
                      background='#f1f5fe',
                      foreground=light_text,
                      borderwidth=0,
                      focuscolor=background)
        
        style.map('TNotebook.Tab',
                 background=[('selected', primary_color),
                           ('active', '#e6edfd')],
                 foreground=[('selected', 'white'),
                           ('active', primary_color)])
        
        # Configure entry fields
        style.configure('TEntry',
                      fieldbackground='white',
                      foreground=text_color,
                      borderwidth=1,
                      relief='solid',
                      padding=8,
                      insertcolor=primary_color)
        
        style.map('TEntry',
                 fieldbackground=[('focus', 'white')],
                 bordercolor=[('focus', primary_color)])
        
        # Configure combobox
        style.configure('TCombobox',
                      fieldbackground='white',
                      background='white',
                      arrowcolor=primary_color,
                      padding=8,
                      borderwidth=1,
                      relief='solid')
        
        style.map('TCombobox',
                 fieldbackground=[('readonly', 'white')],
                 selectbackground=[('readonly', 'white')],
                 selectforeground=[('readonly', text_color)],
                 bordercolor=[('focus', primary_color)])
        
        # Configure scrollbars
        style.configure('Vertical.TScrollbar',
                      background=background,
                      troughcolor=background,
                      arrowcolor=primary_color,
                      bordercolor=background,
                      lightcolor=background,
                      darkcolor=background)
        
        style.map('Vertical.TScrollbar',
                 background=[('active', primary_color)])
        
        # Configure Treeview
        style.configure('Treeview',
                      background='white',
                      foreground=text_color,
                      fieldbackground='white',
                      borderwidth=0,
                      rowheight=32,
                      font=('Segoe UI', 10))
        
        style.configure('Treeview.Heading',
                      background=primary_color,
                      foreground='white',
                      relief='flat',
                      borderwidth=0,
                      font=('Segoe UI', 10, 'bold'),
                      padding=(10, 8))
        
        style.map('Treeview.Heading',
                 background=[('active', '#3a56e8')],
                 relief=[('pressed', 'flat'), ('!pressed', 'flat')])
        
        # Treeview item styling
        style.configure('Treeview.Item',
                      padding=8,
                      rowheight=36)
        
        # Tag configurations for rows
        style.configure('Treeview',
                      rowheight=36,
                      fieldbackground='white',
                      background='white',
                      foreground=text_color)
        
        # Configure row colors and hover effects
        style.map('Treeview',
                 background=[('selected', '#e3f2fd')],
                 foreground=[('selected', text_color)])
        
        # Configure the treeview's border and padding
        style.layout('Treeview', [
            ('Treeview.treearea', {'sticky': 'nswe'})
        ])
        
        # Configure labels
        style.configure('Header.TLabel',
                      font=('Segoe UI', 20, 'bold'),
                      foreground=text_color,
                      background=secondary_color)
        
        style.configure('Subtitle.TLabel',
                      font=('Segoe UI', 11),
                      foreground=light_text,
                      background=secondary_color)
        
        # Configure Treeview
        style.configure('Treeview',
                      rowheight=32,
                      fieldbackground='white',
                      background='white',
                      foreground=text_color,
                      font=('Segoe UI', 10),
                      borderwidth=0,
                      relief='flat')
        
        style.configure('Treeview.Heading',
                      font=('Segoe UI', 10, 'bold'),
                      background='#f8f9fa',
                      foreground=text_color,
                      borderwidth=0,
                      relief='flat')
        
        style.map('Treeview',
                background=[('selected', '#e3f2fd')],
                foreground=[('selected', text_color)])
        
        # Card style
        style.configure('Card.TFrame',
                      background='white',
                      relief='flat',
                      borderwidth=0,
                      border=0)
        
        # Status bar style
        style.configure('Status.TLabel',
                      background='#f0f0f0',
                      foreground=light_text,
                      font=('Segoe UI', 8),
                      padding=5,
                      relief='sunken')
        
        # Stat label style
        style.configure('Stat.TLabel',
                      font=('Segoe UI', 10, 'bold'),
                      background='#f8f9fa',
                      foreground=text_color)
        
        # Template styles
        style.configure('Template.TFrame',
                      background='white',
                      relief='solid',
                      borderwidth=1,
                      border=1)
        
        style.configure('Template.TRadiobutton',
                      background='white',
                      font=('Segoe UI', 10))
        
        style.configure('TemplateContent.TFrame',
                      background='white')
        
        style.configure('TemplateDesc.TLabel',
                      font=('Segoe UI', 9),
                      foreground=light_text,
                      background='white')

        # App-wide data
        # master.businesses will be the list currently loaded in UI (pending list)
        self.businesses = list(PENDING_LIST)  # start from persisted pending if exists
        self.template_choice = "Website"  # default

        # Pages
        self.page1 = Page1(self)
        self.page_clean = PageCleanContacts(self)
        self.page_template = PageTemplate(self)
        self.page2 = Page2(self)

        self.page1.pack(fill="both", expand=True)

    def show_page1(self):
        self.page_clean.pack_forget()
        self.page_template.pack_forget()
        self.page2.pack_forget()
        self.page1.pack(fill="both", expand=True)

    def show_clean_page(self, businesses):
        # show the new cleaning page after JSON paste
        self.businesses = businesses
        self.page1.pack_forget()
        self.page_clean.load_contacts(businesses)
        self.page_clean.pack(fill="both", expand=True)

    def show_template_page(self, businesses):
        # businesses is a list (already sorted in Page1)
        self.businesses = businesses
        self.page_clean.pack_forget()
        self.page_template.pack(fill="both", expand=True)

    def show_page2(self):
        self.page_template.pack_forget()
        self.page2.load_contacts(self.businesses)
        self.page2.pack(fill="both", expand=True)

class Page1(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg='#f8f9fa')
        
        # Header with gradient background
        header = tk.Frame(self, bg='#4a90e2', height=80)
        header.pack(fill='x')
        
        title = ttk.Label(header, text="WhatsApp Sender Pro", 
                         style='Header.TLabel',
                         background='#4a90e2',
                         foreground='white')
        title.pack(pady=20)
        
        # Content frame
        content = ttk.Frame(self)
        content.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Instruction card
        card = ttk.LabelFrame(content, text=" Step 1: Paste Business Data ", padding=15)
        card.pack(fill='both', expand=True, pady=(0, 20))
        
        # Example text in a frame with subtle background
        example_frame = ttk.Frame(card, style='Card.TFrame')
        example_frame.pack(fill='x', pady=(0, 15))
        
        example_text = '''[
  {
    "businessName": "ABC Tech Solutions",
    "phone": "251911223344"
  },
  {
    "businessName": "XYZ Web Design",
    "phone": "251922334455"
  }
]'''
        
        example_label = ttk.Label(example_frame, 
                                text="Example:" + example_text,
                                font=('Consolas', 9),
                                justify='left',
                                background='#f8f9fa',
                                padding=10)
        example_label.pack(anchor='w')
        
        # Text area with scrollbar
        text_frame = ttk.Frame(card)
        text_frame.pack(fill='both', expand=True)
        
        self.textbox = scrolledtext.ScrolledText(text_frame, 
                                               wrap=tk.WORD, 
                                               width=100, 
                                               height=20, 
                                               font=("Consolas", 10),
                                               padx=10,
                                               pady=10,
                                               bd=2,
                                               relief='groove')
        self.textbox.pack(fill='both', expand=True, pady=(5, 0))

        # If there's pending saved data, prefill the box for convenience
        if PENDING_LIST:
            try:
                pretty = json.dumps(PENDING_LIST, indent=2, ensure_ascii=False)
                self.textbox.insert("1.0", pretty)
            except Exception:
                pass

        # Button container
        btn_frame = ttk.Frame(card)
        btn_frame.pack(fill='x', pady=(15, 5))
        
        # Styling for the next button
        style = ttk.Style()
        style.configure('Accent.TButton', 
                       font=('Segoe UI', 10, 'bold'),
                       padding=8,
                       background='#f1f5fe', # light blue for hover
                       foreground='#3a0ca3', # dark blue for text
                       fieldbackground='#f1f5fe', # light blue for hover
                       relief='solid',
                       borderwidth=1,
                       bordercolor='#e2e8f0')
        
        # Custom button style for the next button
        style = ttk.Style()
        style.configure('Custom.TButton', 
                       font=('Segoe UI', 10, 'bold'),
                       padding=8,
                       background='#f1f5fe', # light blue for hover
                       foreground='#3a0ca3', # dark blue for text
                       fieldbackground='#f1f5fe', # light blue for hover
                       relief='solid',
                       borderwidth=1,
                       bordercolor='#e2e8f0') # light gray for borders
                       
        self.next_btn = ttk.Button(btn_frame, 
                                 text="Continue ➔", 
                                 command=self.next_page,
                                 style='Custom.TButton')
        self.next_btn.pack(side="right")

    def next_page(self):
        raw = self.textbox.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showerror("Input Required", 
                               "Please paste your business data in the text area above.",
                               icon='error')
            return
            
        # Show loading state
        self.next_btn.config(state='disabled', text='Processing...')
        self.update_idletasks()
        
        try:
            businesses = json.loads(raw)
            if not isinstance(businesses, list):
                raise ValueError("The JSON should be an array of business objects")
                
            if len(businesses) == 0:
                raise ValueError("The list of businesses is empty")
        except json.JSONDecodeError as e:
            messagebox.showerror("Invalid JSON Format", 
                               f"The text you pasted doesn't appear to be valid JSON.\n\n"
                               f"Error: {str(e)}\n\n"
                               "Please check your input and try again.",
                               icon='error')
        except ValueError as e:
            messagebox.showerror("Invalid Data", 
                               f"The data format is incorrect.\n\n{str(e)}",
                               icon='error')
        except Exception as e:
            messagebox.showerror("Error", 
                               f"An unexpected error occurred:\n\n{str(e)}",
                               icon='error')
        finally:
            self.next_btn.config(state='normal', text='Process & Continue ➔')

        # Normalize phone to string and basic cleanup
        for b in businesses:
            # ensure keys exist
            b.setdefault("businessName", b.get("businessName", "Unknown"))
            b.setdefault("phone", str(b.get("phone", "")).strip())

        # Sort: priority businesses first (keep them at top), stable sort by name after that
        def priority_sort(b):
            name = b.get("businessName", "") or ""
            return (0 if is_priority_business(name) else 1, (name or "").lower())

        businesses.sort(key=priority_sort)

        # Save to pending and update master
        global PENDING_LIST
        PENDING_LIST = businesses
        save_json(PENDING_FILE, PENDING_LIST)

        # now show the clean page instead of directly template page
        self.master.show_clean_page(businesses)

class PageCleanContacts(tk.Frame):
    """
    Clean and review contacts page with modern UI
    """
    def __init__(self, master):
        super().__init__(master, bg='#f8f9fa')
        
        # Header with back button and title
        header = ttk.Frame(self, style='Header.TFrame')
        header.pack(fill='x', pady=(0, 15))
        
        back_btn = ttk.Button(header, text="← Back", 
                            command=self.go_back,
                            style='Link.TButton')
        back_btn.pack(side='left', padx=10)
        
        title = ttk.Label(header, 
                         text="Review & Clean Contacts", 
                         style='Header.TLabel')
        title.pack(side='left', padx=10)
        
        # Stats bar
        self.stats_frame = ttk.Frame(self, style='Card.TFrame')
        self.stats_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        self.total_label = ttk.Label(self.stats_frame, 
                                   text="Total: 0", 
                                   style='Stat.TLabel')
        self.total_label.pack(side='left', padx=15, pady=10)
        
        self.priority_label = ttk.Label(self.stats_frame, 
                                      text="Priority: 0", 
                                      style='Stat.TLabel')
        self.priority_label.pack(side='left', padx=15, pady=10)
        
        # Main content area
        content = ttk.Frame(self)
        content.pack(fill='both', expand=True, padx=20, pady=(0, 15))

        # Create treeview with modern styling
        tree_frame = ttk.Frame(content, style='Card.TFrame')
        tree_frame.pack(fill='both', expand=True)
        
        # Add search bar
        search_frame = ttk.Frame(tree_frame)
        search_frame.pack(fill='x', padx=10, pady=10)
        
        search_icon = ttk.Label(search_frame, text="🔍")
        search_icon.pack(side='left', padx=(5, 0))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, 
                               textvariable=self.search_var,
                               font=('Segoe UI', 10))
        search_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        search_entry.insert(0, 'Search contacts...')
        
        # Bind search functionality
        self.search_var.trace('w', self._on_search)
        
        # Treeview with modern styling
        tree_container = ttk.Frame(tree_frame)
        tree_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal")
        
        # Create treeview
        self.tree = ttk.Treeview(
            tree_container,
            columns=("idx", "name", "phone", "action"),
            show="headings",
            selectmode="extended",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        # Configure scrollbars
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Configure columns
        self.tree.heading("idx", text="#", anchor='center')
        self.tree.heading("name", text="Business Name", anchor='w')
        self.tree.heading("phone", text="Phone", anchor='w')
        self.tree.heading("action", text="Action", anchor='center')
        
        self.tree.column("idx", width=50, anchor='center', stretch=False)
        self.tree.column("name", width=300, anchor='w', stretch=True)
        self.tree.column("phone", width=150, anchor='w', stretch=False)
        self.tree.column("action", width=100, anchor='center', stretch=False)

        # Configure tags for row styling
        self.tree.tag_configure("priority", background='#fff3e0')  # Light orange for priority
        self.tree.tag_configure("even", background='#ffffff')     # White for even rows
        self.tree.tag_configure("odd", background='#f8f9fa')      # Light gray for odd rows
        self.tree.tag_configure("hidden", background='')          # For hidden rows
        
        # Map iid -> business object
        self._iid_map = {}
        
        # Bind events
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<Motion>", self._on_motion)
        self.tree.bind("<Leave>", self._on_leave)
        
        # Add hover effect
        self.tree.tag_configure("hover", background='#e3f2fd')  # Light blue on hover
        self._last_hover = None
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, 
                             textvariable=self.status_var, 
                             relief='sunken', 
                             anchor='w',
                             style='Status.TLabel')
        status_bar.pack(fill='x', side='bottom', ipady=5)

        # Bottom action buttons
        btn_frame = ttk.Frame(self, style='Card.TFrame')
        btn_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        # Left side buttons
        left_btn_frame = ttk.Frame(btn_frame)
        left_btn_frame.pack(side='left')
        
        back_btn = ttk.Button(
            left_btn_frame,
            text="← Back",
            command=self.master.show_page1,
            style='Secondary.TButton'
        )
        back_btn.pack(side='left', padx=5)
        
        # Right side buttons
        right_btn_frame = ttk.Frame(btn_frame)
        right_btn_frame.pack(side='right')
        
        self.next_btn = ttk.Button(
            right_btn_frame,
            text="Continue to Template →",
            command=self._confirm_and_proceed,
            style='Accent.TButton'
        )
        self.next_btn.pack(side='right', padx=5)
        
        # Add a help button
        help_btn = ttk.Button(
            right_btn_frame,
            text="ℹ Help",
            command=self._show_help,
            style='Link.TButton'
        )
        help_btn.pack(side='right', padx=5)

    def load_contacts(self, businesses):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._iid_map.clear()
        
        if not businesses:
            self.status_var.set("No contacts to display")
            return
            
        # Add items with alternating row colors
        for i, biz in enumerate(businesses, 1):
            name = biz.get("businessName", "Unknown").strip()
            phone = str(biz.get("phone", "")).strip()
            
            # Determine tags for styling
            tags = []
            if is_priority_business(name):
                tags.append("priority")
            
            # Alternate row colors
            tags.append("even" if i % 2 == 0 else "odd")
            
            # Insert the item
            iid = self.tree.insert(
                "", 
                "end", 
                values=(
                    i, 
                    name,
                    phone,
                    "✕"  # Delete icon
                ),
                tags=tuple(tags)
            )
            self._iid_map[iid] = biz
        
        # Update stats
        self._update_stats()
        self.status_var.set(f"Loaded {len(businesses)} contacts")
    
    def _update_stats(self):
        """Update the statistics display"""
        total = len(self._iid_map)
        priority = sum(1 for biz in self._iid_map.values() 
                      if is_priority_business(biz.get("businessName", "")))
        
        self.total_label.config(text=f"Total: {total}")
        self.priority_label.config(text=f"Priority: {priority}")
    
    def _on_search(self, *args):
        """Handle search functionality"""
        query = self.search_var.get().lower()
        
        for iid in self.tree.get_children():
            values = self.tree.item(iid, 'values')
            if len(values) >= 3:  # Check name and phone columns
                name = values[1].lower()
                phone = values[2].lower()
                if query in name or query in phone:
                    self.tree.attrib(iid, 'hidden', '')
                else:
                    self.tree.attrib(iid, 'hidden', '1')
    
    def _on_motion(self, event):
        """Handle mouse hover events"""
        region = self.tree.identify_region(event.x, event.y)
        if region == 'cell':
            item = self.tree.identify_row(event.y)
            if item != self._last_hover:
                if self._last_hover:
                    self.tree.item(self._last_hover, tags=self.tree.item(self._last_hover, 'tags')[:-1])
                if item:
                    current_tags = list(self.tree.item(item, 'tags'))
                    self.tree.item(item, tags=tuple(current_tags + ['hover']))
                self._last_hover = item
    
    def _on_leave(self, event):
        """Handle mouse leave event"""
        if self._last_hover:
            tags = list(self.tree.item(self._last_hover, 'tags'))
            if 'hover' in tags:
                tags.remove('hover')
                self.tree.item(self._last_hover, tags=tags)
        self._last_hover = None
    
    def _show_help(self):
        """Show help dialog"""
        help_text = """📋 Review & Clean Contacts Help

• Click the '✕' to remove a contact
• Use the search box to filter contacts
• Priority contacts are highlighted
• Click 'Continue' when you're ready to proceed

Tip: You can select multiple contacts using Ctrl+Click or Shift+Click"""
        
        messagebox.showinfo("Help", help_text)

    def _on_click(self, event):
        """
        Detect if user clicked the 'action' column for a row. If so, delete that contact.
        """
        global PENDING_LIST
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)  # returns like '#1', '#2', ...
        row = self.tree.identify_row(event.y)
        if not row or not col:
            return
        # action column is the 4th column (index 4 -> '#4') because we defined 4 columns
        if col == "#4":
            # Delete this row
            biz = self._iid_map.pop(row, None)
            if biz:
                # remove from PENDING_LIST (by matching phone and name)
                phone = str(biz.get("phone", "")).strip()
                name = biz.get("businessName", "")
                # remove exact object matches in PENDING_LIST
                new_pending = []
                removed = False
                for b in PENDING_LIST:
                    if not removed and str(b.get("phone", "")).strip() == phone and b.get("businessName", "") == name:
                        removed = True
                        continue
                    new_pending.append(b)
                # fallback: if not removed, try removing by phone only
                if not removed:
                    new_pending = [b for b in PENDING_LIST if str(b.get("phone", "")).strip() != phone]
                # update global pending
                PENDING_LIST = new_pending
                save_json(PENDING_FILE, PENDING_LIST)
            # remove row from treeview regardless
            try:
                self.tree.delete(row)
            except Exception:
                pass

    def _confirm_and_proceed(self):
        """
        When user presses Next: ensure pending is updated from what's left in the _iid_map
        and proceed to template page.
        """
        global PENDING_LIST
        # Rebuild pending based on what's left in the tree (_iid_map values)
        remaining = list(self._iid_map.values())
        # Sometimes user deleted by other means, so normalize phones and names
        normalized = []
        for b in remaining:
            nb = dict(b)  # shallow copy
            nb.setdefault("businessName", nb.get("businessName", "Unknown"))
            nb.setdefault("phone", str(nb.get("phone", "")).strip())
            normalized.append(nb)
        # Save
        PENDING_LIST = normalized
        save_json(PENDING_FILE, PENDING_LIST)
        # Move on
        self.master.show_template_page(PENDING_LIST)

class PageTemplate(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg='#f8f9fa')
        
        # Header with back button and title
        header = ttk.Frame(self, style='Header.TFrame')
        header.pack(fill='x', pady=(0, 15))
        
        back_btn = ttk.Button(header, 
                            text="← Back", 
                            command=lambda: self.master.show_clean_page(self.master.businesses),
                            style='Link.TButton')
        back_btn.pack(side='left', padx=10)
        
        title = ttk.Label(header, 
                         text="Choose Message Template", 
                         style='Header.TLabel')
        title.pack(side='left', padx=10)
        
        # Main content
        content = ttk.Frame(self, style='Card.TFrame')
        content.pack(fill='both', expand=True, padx=20, pady=10)
        
        ttk.Label(content, 
                 text="Select a message template:", 
                 font=('Segoe UI', 11),
                 style='Subtitle.TLabel').pack(pady=(15, 20))
        
        # Template selection frame
        template_frame = ttk.Frame(content)
        template_frame.pack(pady=10)
        
        self.choice_var = tk.StringVar(value="Website")
        
        # Template options with cards
        templates = [
            {
                'id': 'Website',
                'title': 'Website Development',
                'description': 'Template for offering website development services',
                'icon': '🌐'
            },
            {
                'id': 'Logo',
                'title': 'Logo Design',
                'description': 'Template for offering logo design services',
                'icon': '🎨'
            }
        ]
        
        for i, template in enumerate(templates):
            frame = ttk.Frame(template_frame, style='Template.TFrame')
            frame.pack(fill='x', pady=5, padx=20)
            
            # Radio button
            rb = ttk.Radiobutton(
                frame,
                text='',
                variable=self.choice_var,
                value=template['id'],
                style='Template.TRadiobutton'
            )
            rb.pack(side='left', padx=(0, 10))
            
            # Template content
            content_frame = ttk.Frame(frame, style='TemplateContent.TFrame')
            content_frame.pack(side='left', fill='x', expand=True, pady=10)
            
            # Icon and title
            title_frame = ttk.Frame(content_frame)
            title_frame.pack(fill='x', pady=(0, 5))
            
            icon = ttk.Label(title_frame, 
                           text=template['icon'], 
                           font=('Segoe UI', 16))
            icon.pack(side='left', padx=(0, 10))
            
            title = ttk.Label(title_frame, 
                            text=template['title'],
                            font=('Segoe UI', 12, 'bold'))
            title.pack(side='left')
            
            # Description
            desc = ttk.Label(content_frame,
                           text=template['description'],
                           style='TemplateDesc.TLabel')
            desc.pack(anchor='w')
        
        # Preview section
        preview_frame = ttk.LabelFrame(content, 
                                     text=" Preview ",
                                     padding=15)
        preview_frame.pack(fill='x', padx=20, pady=20)
        
        self.preview_text = tk.Text(preview_frame,
                                  wrap=tk.WORD,
                                  height=6,
                                  font=('Segoe UI', 10),
                                  padx=10,
                                  pady=10,
                                  bd=1,
                                  relief='solid')
        self.preview_text.pack(fill='x')
        self.preview_text.config(state='disabled')
        
        # Update preview when selection changes
        self.choice_var.trace('w', self._update_preview)
        self._update_preview()
        
        # Navigation buttons
        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill='x', pady=(10, 5), padx=20)
        
        ttk.Button(btn_frame,
                  text="← Back",
                  command=lambda: self.master.show_clean_page(self.master.businesses),
                  style='Secondary.TButton').pack(side='left')
        
        ttk.Button(btn_frame,
                  text="Continue →",
                  command=self.confirm_choice,
                  style='Accent.TButton').pack(side='right')
    
    def _update_preview(self, *args):
        """Update the preview based on selected template"""
        template = self.choice_var.get()
        if template == "Logo":
            preview = "Hello [Business Name],\n\nWe noticed your business and think we could help with your logo design needs. Our team creates professional logos that capture your brand's essence.\n\nWould you be interested in seeing some samples?"
        else:  # Website
            preview = "Hello [Business Name],\n\nWe specialize in creating modern, responsive websites that help businesses like yours grow online. We'd love to discuss how we can help you establish a strong web presence.\n\nWould you be interested in a free consultation?"
        
        self.preview_text.config(state='normal')
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, preview)
        self.preview_text.config(state='disabled')

    def confirm_choice(self):
        """Handle template selection confirmation"""
        self.master.template_choice = self.choice_var.get()
        self.master.show_page2()
class Page2(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg='#f8f9fa')
        
        # Header with back button and title
        header = ttk.Frame(self, style='Header.TFrame')
        header.pack(fill='x', pady=(0, 15))
        
        # Back button
        self.back_btn = ttk.Button(
            header, 
            text="← Back to Templates", 
            command=lambda: master.show_template_page(master.businesses),
            style='Link.TButton'
        )
        self.back_btn.pack(side='left', padx=10)
        
        # Title
        title = ttk.Label(
            header, 
            text="Send Messages", 
            style='Header.TLabel'
        )
        title.pack(side='left', padx=10)
        
        # Action buttons on the right
        btn_container = ttk.Frame(header)
        btn_container.pack(side='right', padx=10)
        
        # Delete selected button
        self.delete_btn = ttk.Button(
            btn_container,
            text="🗑 Delete Selected",
            command=self.delete_selected,
            style='Danger.TButton',
            width=15
        )
        self.delete_btn.pack(side='right', padx=5)
        
        # Start sending button
        self.contact_btn = ttk.Button(
            btn_container,
            text="📩 Start Sending",
            command=self.start_contacting,
            style='Accent.TButton',
            width=15
        )
        self.contact_btn.pack(side='right', padx=5)

        # Main content area
        content = ttk.Frame(self, style='Card.TFrame')
        content.pack(fill='both', expand=True, padx=20, pady=(0, 15))
        
        # Stats bar
        self.stats_frame = ttk.Frame(content, style='Stats.TFrame')
        self.stats_frame.pack(fill='x', pady=(0, 15))
        
        # Stats labels
        self.total_label = ttk.Label(
            self.stats_frame, 
            text="Total: 0", 
            style='Stat.TLabel',
            font=('Segoe UI', 10, 'bold')
        )
        self.total_label.pack(side='left', padx=15, pady=8)
        
        self.sent_label = ttk.Label(
            self.stats_frame, 
            text="Sent: 0", 
            style='StatSent.TLabel',
            font=('Segoe UI', 10, 'bold')
        )
        self.sent_label.pack(side='left', padx=15, pady=8)
        
        self.failed_label = ttk.Label(
            self.stats_frame, 
            text="Failed: 0", 
            style='StatFailed.TLabel',
            font=('Segoe UI', 10, 'bold')
        )
        self.failed_label.pack(side='left', padx=15, pady=8)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            self.stats_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            style='Custom.Horizontal.TProgressbar'
        )
        self.progress.pack(side='right', fill='x', expand=True, padx=15, pady=8)
        
        # Table frame with search
        table_container = ttk.Frame(content)
        table_container.pack(fill='both', expand=True)
        
        # Search bar
        search_frame = ttk.Frame(table_container)
        search_frame.pack(fill='x', pady=(0, 10))
        
        search_icon = ttk.Label(search_frame, text="🔍")
        search_icon.pack(side='left', padx=(5, 0))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(
            search_frame, 
            textvariable=self.search_var,
            font=('Segoe UI', 10),
            width=40
        )
        search_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        search_entry.insert(0, 'Search contacts...')
        
        # Bind search functionality
        self.search_var.trace('w', self._on_search)
        
        # Table with scrollbars
        table_frame = ttk.Frame(table_container, style='Card.TFrame')
        table_frame.pack(fill='both', expand=True)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")
        
        # Create treeview
        self.tree = ttk.Treeview(
            table_frame,
            columns=("idx", "name", "phone", "status"),
            show="headings",
            selectmode="extended",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            style='Custom.Treeview'
        )
        
        # Configure scrollbars
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Configure columns
        self.tree.heading("idx", text="#", anchor='center')
        self.tree.heading("name", text="Business Name", anchor='w')
        self.tree.heading("phone", text="Phone", anchor='w')
        self.tree.heading("status", text="Status", anchor='center')
        
        self.tree.column("idx", width=50, anchor='center', stretch=False)
        self.tree.column("name", width=350, anchor='w', stretch=True)
        self.tree.column("phone", width=180, anchor='w', stretch=False)
        self.tree.column("status", width=150, anchor='center', stretch=False)
        
        # Configure tags for row styling
        self.tree.tag_configure("sent", background='#e8f5e9', foreground='#1b5e20')  # Green for sent
        self.tree.tag_configure("skipped", background='#fff8e1', foreground='#e65100')  # Orange for skipped
        self.tree.tag_configure("invalid", background='#ffebee', foreground='#c62828')  # Red for invalid
        self.tree.tag_configure("pending", background='#ffffff', foreground='#424242')  # Gray for pending
        self.tree.tag_configure("working", background='#e3f2fd', foreground='#0d47a1')  # Blue for working
        self.tree.tag_configure("priority", background='#f3e5f5', foreground='#4a148c')  # Purple for priority
        
        # Add hover effect
        self.tree.tag_configure("hover", background='#f5f5f5')
        self._last_hover = None
        self.tree.bind("<Motion>", self._on_motion)
        self.tree.bind("<Leave>", self._on_leave)

        # Logs section
        logs_frame = ttk.LabelFrame(
            self, 
            text=" Activity Log ",
            padding=10,
            style='Card.TLabelframe'
        )
        logs_frame.pack(fill='both', expand=False, padx=20, pady=(0, 20))
        
        # Log controls
        log_controls = ttk.Frame(logs_frame)
        log_controls.pack(fill='x', pady=(0, 5))
        
        ttk.Label(
            log_controls, 
            text="Logs:", 
            font=('Segoe UI', 9, 'bold')
        ).pack(side='left')
        
        # Clear logs button
        ttk.Button(
            log_controls,
            text="Clear Logs",
            command=self._clear_logs,
            style='Link.TButton'
        ).pack(side='right')
        
        # Log text area
        self.log_box = scrolledtext.ScrolledText(
            logs_frame,
            wrap=tk.WORD,
            height=8,
            state="disabled",
            font=('Consolas', 9),
            padx=10,
            pady=10,
            bd=1,
            relief='solid',
            bg='#f8f9fa'
        )
        self.log_box.pack(fill='both', expand=True)

        # Helper map from iid -> business object (for reliable deletion)
        self._iid_map = {}
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            self, 
            textvariable=self.status_var, 
            relief='sunken', 
            anchor='w',
            style='Status.TLabel',
            padding=(10, 5)
        )
        status_bar.pack(fill='x', side='bottom', ipady=2)
        
        # Bind window events
        self.bind('<Configure>', self._on_configure)
        
        # Initialize stats
        self._update_stats()

    def load_contacts(self, businesses):
        # Clear existing items
        self._iid_map.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        
        if not businesses:
            self.safe_log("⚠️ No contacts to display")
            self._update_stats()
            return
        
        # Add items to treeview
        for i, biz in enumerate(businesses, 1):
            name = biz.get("businessName", "Unknown").strip()
            phone = str(biz.get("phone", "")).strip()
            
            # Determine tags for styling
            tags = []
            if is_priority_business(name):
                tags.append("priority")
            tags.append("pending")
            
            # Insert the item
            iid = self.tree.insert(
                "", 
                "end", 
                values=(
                    i, 
                    name,
                    phone,
                    "⏳ Pending"
                ),
                tags=tuple(tags)
            )
            self._iid_map[iid] = biz
        
        # Update stats and log
        self._update_stats()
        self.safe_log(f"✅ Loaded {len(businesses)} contacts with template: {self.master.template_choice}")
        self.status_var.set(f"Ready to send messages to {len(businesses)} contacts")
    
    def _on_search(self, *args):
        """Handle search functionality"""
        query = self.search_var.get().lower()
        
        for iid in self.tree.get_children():
            values = self.tree.item(iid, 'values')
            if len(values) >= 3:  # Check name and phone columns
                name = values[1].lower()
                phone = values[2].lower()
                if query in name or query in phone:
                    self.tree.attrib(iid, 'hidden', '')
                else:
                    self.tree.attrib(iid, 'hidden', '1')
    
    def _on_motion(self, event):
        """Handle mouse hover events"""
        region = self.tree.identify_region(event.x, event.y)
        if region == 'cell':
            item = self.tree.identify_row(event.y)
            if item != self._last_hover:
                if self._last_hover:
                    self.tree.item(self._last_hover, tags=self.tree.item(self._last_hover, 'tags')[:-1])
                if item:
                    current_tags = list(self.tree.item(item, 'tags'))
                    self.tree.item(item, tags=tuple(current_tags + ['hover']))
                self._last_hover = item
    
    def _on_leave(self, event):
        """Handle mouse leave event"""
        if self._last_hover:
            tags = list(self.tree.item(self._last_hover, 'tags'))
            if 'hover' in tags:
                tags.remove('hover')
                self.tree.item(self._last_hover, tags=tags)
        self._last_hover = None
    
    def _update_stats(self):
        """Update the statistics display"""
        total = len(self._iid_map)
        if total == 0:
            self.total_label.config(text="Total: 0")
            self.sent_label.config(text="Sent: 0")
            self.failed_label.config(text="Failed: 0")
            self.progress_var.set(0)
            return
            
        sent = sum(1 for iid in self.tree.get_children() 
                  if self.tree.item(iid, 'values')[-1].startswith("✅"))
        failed = sum(1 for iid in self.tree.get_children() 
                    if self.tree.item(iid, 'values')[-1].startswith("❌"))
        
        self.total_label.config(text=f"Total: {total}")
        self.sent_label.config(text=f"Sent: {sent}")
        self.failed_label.config(text=f"Failed: {failed}")
        
        # Update progress
        progress = ((sent + failed) / total) * 100 if total > 0 else 0
        self.progress_var.set(progress)
    
    def _clear_logs(self):
        """Clear the log box"""
        self.log_box.config(state='normal')
        self.log_box.delete(1.0, tk.END)
        self.log_box.config(state='disabled')
    
    def _on_configure(self, event=None):
        """Handle window resize events"""
        # Update UI elements on resize if needed
        pass

    def safe_log(self, text):
        """Thread-safe logging"""
        self.after(0, self._append_log, text)
    
    def _append_log(self, text):
        """Append text to log box with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {text}"
        
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, log_entry + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")
        
        # Also update status bar for important messages
        if text.startswith(('✅', '❌', '⚠️')):
            self.status_var.set(text)

    def set_row_status(self, phone, status_text, tag):
        """Update the status of a row identified by phone number"""
        self.after(0, self._apply_row_status, phone, status_text, tag)
    
    def _apply_row_status(self, phone, status_text, tag):
        """Apply status update to the row"""
        # Add emoji based on status
        status_map = {
            'sent': '✅',
            'skipped': '⚠️',
            'invalid': '❌',
            'pending': '⏳',
            'working': '🔄'
        }
        
        emoji = status_map.get(tag, 'ℹ️')
        display_text = f"{emoji} {status_text}"
        
        # Find and update matching rows
        updated = 0
        for iid in self.tree.get_children():
            vals = list(self.tree.item(iid, "values"))
            if len(vals) >= 3:  # Ensure we have enough columns
                row_phone = str(vals[2])
                if row_phone == str(phone):
                    # Preserve existing values except status
                    if len(vals) >= 4:
                        vals[-1] = display_text
                    else:
                        vals.append(display_text)
                    
                    # Update the item with new values and tags
                    self.tree.item(iid, values=vals, tags=(tag,))
                    updated += 1
        
        # Update stats after status change
        if updated > 0:
            self._update_stats()
            
            # Auto-scroll to the updated row if it's not visible
            if self.tree.selection():
                self.tree.see(self.tree.selection()[-1])

    def toggle_controls(self, enabled):
        """Enable or disable UI controls"""
        state = "normal" if enabled else "disabled"
        
        # Update button states
        for btn in [self.back_btn, self.contact_btn, self.delete_btn]:
            btn.config(state=state)
        
        # Update cursor
        cursor = "" if enabled else "wait"
        self.config(cursor=cursor)
        self.tree.config(cursor=cursor)
        
        # Update status
        if not enabled:
            self.status_var.set("Processing...")
        else:
            self.status_var.set("Ready")

    def start_contacting(self):
        if not self.master.businesses:
            messagebox.showwarning("No contacts", "No contacts to contact. Please add/paste them first.")
            return
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

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        confirm = messagebox.askyesno("Confirm Delete", f"Delete {len(selected)} selected contact(s) from pending?")
        if not confirm:
            return
        deleted = 0
        for iid in selected:
            biz = self._iid_map.get(iid)
            if not biz:
                # fallback: extract phone from row
                vals = self.tree.item(iid, "values")
                phone = vals[2] if len(vals) > 2 else ""
                # remove from pending list by phone
                remove_from_pending_by_phone(phone)
            else:
                phone = str(biz.get("phone", ""))
                # Remove all instances with this phone in PENDING_LIST
                remove_from_pending_by_phone(phone)
            try:
                self.tree.delete(iid)
                self._iid_map.pop(iid, None)
                deleted += 1
            except Exception:
                pass
        # Also update master.businesses
        self.master.businesses = list(PENDING_LIST)
        self.safe_log(f"🗑 Deleted {deleted} contact(s) and saved to {PENDING_FILE}.")

# -------------------------------
# WhatsApp automation (Playwright)
# -------------------------------
async def send_messages(businesses, template_choice, log_cb, status_cb):
    """
    businesses: list of business objects (as in PENDING_LIST)
    template_choice: "Website" | "Logo"
    log_cb: function(text)
    status_cb: function(phone, status_text, tag)
    """
    result = {"total": len(businesses), "contacted": 0, "notfound": 0, "alreadyContacted": 0, "composerNotFound": 0, "failed": 0}

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

        # We'll iterate over a shallow copy — PENDING_LIST will be updated on disk during processing
        for biz in list(businesses):
            phone = str(biz.get("phone", "")).strip()
            name = biz.get("businessName", "Unknown")

            if not phone:
                log_cb(f"⚠️ Missing phone for {name}")
                continue

            # Check duplicates based on CONTACTED_NUMBERS
            if phone in CONTACTED_NUMBERS or any(p.get("phone") == phone for p in CONTACTED_LIST):
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
                save_failed_item(name, phone, "open_chat_failed")
                remove_from_pending_by_phone(phone)
                result["failed"] += 1
                continue

            await random_delay(4000, 7000)

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
                continue

            # find composer (input/footer)
            try:
                composer = await page.wait_for_selector('footer div[contenteditable="true"]', timeout=15000)
            except Exception:
                log_cb(f"❌ No composer for {name} ({phone})")
                status_cb(phone, "No composer", "invalid")
                result["composerNotFound"] += 1
                save_failed_item(name, phone, "no_composer")
                remove_from_pending_by_phone(phone)
                continue

            # Compose messages
            messages = [
                "ሰላም ጤና ይስጥልኝ",
                f"ለ {name} {('ሎጎ' if template_choice == 'Logo' else 'Website')} ትፈልጋላችሁ?"
            ]

            try:
                for msg in messages:
                    # type message
                    await composer.type(msg, delay=random.randint(50, 120))
                    await random_delay(800, 1600)
                    await page.keyboard.press("Enter")
                    await random_delay(1200, 2800)

                log_cb(f"🟢 Sent to {name} ({phone})")
                status_cb(phone, "Sent", "sent")
                result["contacted"] += 1
                # Add to contacted list (object with name & phone) and numbers list
                save_contacted_item(name, phone)
                # Remove from pending on disk
                remove_from_pending_by_phone(phone)
                await random_delay(2500, 5000)
            except Exception as e:
                log_cb(f"❌ Failed to send to {name}: {e}")
                status_cb(phone, "Failed", "invalid")
                result["failed"] += 1
                save_failed_item(name, phone, str(e))
                remove_from_pending_by_phone(phone)

        await browser.close()

    return result

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    app = WhatsAppApp()
    app.mainloop()
