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
# from page2 import Page2
# from whatsapp import WhatsAppApp

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
