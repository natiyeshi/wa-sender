import os

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PENDING_FILE = os.path.join(BASE_DIR, "pending.json")
CONTACTED_FILE = os.path.join(BASE_DIR, "contacted.json")
FAILED_FILE = os.path.join(BASE_DIR, "failed.json")
CONTACTED_NUMBERS_FILE = os.path.join(BASE_DIR, "contacted.json")

# Application constants
PRIORITY_KEYWORDS = ["software", "computer", "web", "branding", "marketing", "solution"]

# Initialize empty lists that will be populated by helper.py
PENDING_LIST = []
CONTACTED_LIST = []
FAILED_LIST = []
CONTACTED_NUMBERS = []
