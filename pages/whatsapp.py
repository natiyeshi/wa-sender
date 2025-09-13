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

# Local imports
from .page1 import Page1
from .pageTemplate import PageTemplate
from .page2 import Page2
from .pageCleanContact import PageCleanContacts

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
        self.businesses = list(config.PENDING_LIST)  # start from persisted pending if exists
        self.template_choice = "Website"  # default

        # Pages
        self.page1 = Page1(self)
        self.page_clean = PageCleanContacts(self)
        self.page_template = PageTemplate(self)
        self.page2 = Page2(self)

        self.page1.pack(fill="both", expand=True)

    def _hide_all_pages(self):
        """Helper method to hide all pages"""
        for page in [self.page1, self.page_clean, self.page_template, self.page2]:
            page.pack_forget()

    def show_page1(self):
        """Show the first page (business data entry)"""
        self._hide_all_pages()
        self.page1.pack(fill="both", expand=True)
        self.update_idletasks()

    def show_clean_page(self, businesses):
        """Show the contact cleaning page"""
        self._hide_all_pages()
        self.businesses = businesses
        self.page_clean.load_contacts(businesses)
        self.page_clean.pack(fill="both", expand=True)
        self.update_idletasks()

    def show_template_page(self, businesses):
        """Show the template selection page"""
        self._hide_all_pages()
        self.businesses = businesses
        self.page_template.pack(fill="both", expand=True)
        self.update_idletasks()

    def show_page2(self):
        """Show the final page (sending page)"""
        self._hide_all_pages()
        self.page2.load_contacts(self.businesses)
        self.page2.pack(fill="both", expand=True)
        self.update_idletasks()
