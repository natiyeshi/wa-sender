from pages.whatsapp import WhatsAppApp
import config
from helper import load_all_state

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    load_all_state()
    app = WhatsAppApp()
    app.mainloop()
