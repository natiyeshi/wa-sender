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
                            command=self.master.show_page1,
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
                # Clear hover from previous item if it still exists
                if self._last_hover and self._last_hover in self.tree.get_children():
                    try:
                        current_tags = list(self.tree.item(self._last_hover, 'tags'))
                        if 'hover' in current_tags:
                            current_tags.remove('hover')
                            self.tree.item(self._last_hover, tags=current_tags)
                    except tk.TclError:
                        pass  # Item no longer exists
                
                # Add hover to new item
                if item and item in self.tree.get_children():
                    try:
                        current_tags = list(self.tree.item(item, 'tags'))
                        if 'hover' not in current_tags:
                            current_tags.append('hover')
                            self.tree.item(item, tags=current_tags)
                        self._last_hover = item
                    except tk.TclError:
                        self._last_hover = None
                else:
                    self._last_hover = None
    
    def _on_leave(self, event):
        """Handle mouse leave event"""
        if self._last_hover and self._last_hover in self.tree.get_children():
            try:
                tags = list(self.tree.item(self._last_hover, 'tags'))
                if 'hover' in tags:
                    tags.remove('hover')
                    self.tree.item(self._last_hover, tags=tags)
            except tk.TclError:
                pass  # Item no longer exists
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
        global config
        print(config.PENDING_LIST,"ON delete")
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if not row or not col:
            return
        
        # action column is the 4th column (index 4 -> '#4') because we defined 4 columns
        if col == "#4":
            # Get business data before deleting
            biz = self._iid_map.get(row)
            if not biz:
                return
                
            # Remove from treeview first
            try:
                self.tree.delete(row)
            except tk.TclError:
                pass  # Item already deleted
                
            # Remove from _iid_map
            self._iid_map.pop(row, None)
            
            # Update PENDING_LIST
            if biz:
                phone = str(biz.get("phone", "")).strip()
                name = biz.get("businessName", "")
                
                # Remove from PENDING_LIST
                new_pending = []
                for b in config.PENDING_LIST:
                    b_phone = str(b.get("phone", "")).strip()
                    b_name = b.get("businessName", "")
                    if b_phone == phone and b_name == name:
                        continue  # Skip this item
                    new_pending.append(b)
                
                # Update global pending
                config.PENDING_LIST = new_pending
                save_json(config.PENDING_FILE, config.PENDING_LIST)
                
                # Update stats
                self._update_stats()
    
    def _confirm_and_proceed(self):
        """
        When user presses Next: ensure pending is updated from what's left in the _iid_map
        and proceed to template page.
        """
        global config
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
        config.PENDING_LIST = normalized
        print(normalized,"Normalized")
        save_json(config.PENDING_FILE, config.PENDING_LIST)
        # save_all_state()  # Save the complete application state
        # Move on
        self.master.show_template_page(config.PENDING_LIST)
