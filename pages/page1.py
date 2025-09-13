import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import config  # Import the config module
from playwright.async_api import async_playwright

# Import from helper for functions
from helper import (
    load_json, save_json, save_all_state, save_contacted_item,
    save_failed_item, remove_from_pending_by_phone, random_delay,
    is_priority_business
)

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
        if config.PENDING_LIST:
            try:
                pretty = json.dumps(config.PENDING_LIST, indent=2, ensure_ascii=False)
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
        config.PENDING_LIST = businesses
        save_json(config.PENDING_FILE, config.PENDING_LIST)

        # now show the clean page instead of directly template page
        self.master.show_clean_page(businesses)
