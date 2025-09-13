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
# from whatsapp import WhatsAppApp
from .sendMessage import send_messages

from datetime import datetime

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
        self.master.businesses = list(config.PENDING_LIST)
        self.safe_log(f"🗑 Deleted {deleted} contact(s) and saved to {config.PENDING_FILE}.")
