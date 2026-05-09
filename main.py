import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageFont
import img2pdf
import os
import time
import threading
import io
import sys
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def resource_path(relative_path):
    """ Gestion des chemins pour PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SushiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SushiScan Downloader - Created by Endam")
        self.geometry("700x800")
        self.driver = None
        self._cancel_event = threading.Event()
        self._setup_ui()
        
        # Vérification des pré-requis au lancement
        self.after(1000, self._check_dependencies)

    def _check_dependencies(self):
        """ Vérifie si Chromium et le Driver sont présents sur le système Linux """
        deps = {
            "chromium-browser": ["/usr/bin/chromium-browser", "/usr/bin/chromium"],
            "chromedriver": ["/usr/bin/chromedriver", "/usr/lib/chromium-browser/chromedriver"]
        }
        
        missing = []
        for name, paths in deps.items():
            if not any(os.path.exists(p) for p in paths) and shutil.which(name) is None:
                missing.append(name)
        
        if missing:
            msg = "⚠️ Dépendances manquantes détectées !\n\n"
            msg += "Pour faire fonctionner l'appli sur ce Linux, lancez :\n"
            msg += "sudo apt install chromium-browser chromium-chromedriver\n"
            msg += "(ou sudo dnf install chromium chromedriver)"
            messagebox.showwarning("Logiciel Manquant", msg)
            self.log("❌ Erreur : Chromium ou Chromedriver introuvable sur le système.")

    def _setup_ui(self):
        frame_top = tk.Frame(self)
        frame_top.pack(pady=10, padx=10, fill="x")

        lbl_instr = tk.Label(
            frame_top,
            text="1. Ouvrez Chromium en mode debug sur le port 9222\n(Commande: chromium-browser --remote-debugging-port=9222)",
            fg="red",
            justify=tk.LEFT
        )
        lbl_instr.pack(side=tk.TOP, pady=5)

        frame_input = tk.Frame(frame_top)
        frame_input.pack(pady=5)

        tk.Label(frame_input, text="Nombre de pages :").pack(side=tk.LEFT)
        self.entry_pages = tk.Entry(frame_input, width=10)
        self.entry_pages.pack(side=tk.LEFT, padx=5)
        self.entry_pages.insert(0, "64")

        self.btn_start = tk.Button(
            frame_top,
            text="🚀 Démarrer le téléchargement",
            command=self._on_start,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
        )
        self.btn_start.pack(side=tk.TOP, fill="x", pady=(10, 4))

        self.btn_cancel = tk.Button(
            frame_top,
            text="⛔ Annuler",
            command=self._on_cancel,
            bg="#e53935",
            fg="white",
            font=("Arial", 11, "bold"),
            state="disabled",
        )
        self.btn_cancel.pack(side=tk.TOP, fill="x", pady=(0, 6))

        self.lbl_info = tk.Label(self, text="Prêt.", fg="blue")
        self.lbl_info.pack(pady=5)

        self.log_text = tk.Text(self, height=15, width=80)
        self.log_text.pack(padx=10, pady=5)

    def _on_start(self):
        self._cancel_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_cancel.config(state="normal")
        threading.Thread(target=self.demarrer, daemon=True).start()

    def _on_cancel(self):
        self._cancel_event.set()
        self.btn_cancel.config(state="disabled")
        self.lbl_info.config(text="Annulation en cours...")

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    # ----------------------------------------------------------- Selenium ---

    def connect_driver(self):
        """Connexion optimisée pour Linux (Raspberry & Alma)"""
        if self.driver is not None:
            return self.driver
            
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        
        # Options indispensables pour Linux
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Chemins possibles du driver sur Raspberry/Alma
        possible_drivers = ["/usr/bin/chromedriver", "/usr/lib/chromium-browser/chromedriver"]
        driver_path = next((p for p in possible_drivers if os.path.exists(p)), "chromedriver")

        try:
            service = Service(executable_path=driver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            return self.driver
        except Exception as e:
            self.lbl_info.config(text="Erreur de connexion !")
            self.log(f"Erreur Selenium: {e}")
            messagebox.showerror("Erreur", "Impossible de se connecter à Chromium.\nAssurez-vous qu'il est ouvert sur le port 9222.")
            return None

    # ----------------------------------------------------------- Filigrane ---

    def _ajouter_filigrane(self, original_image):
        try:
            base = original_image.convert("RGBA")
            txt_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)

            text = "Created by Endam"
            # Chemins de polices compatibles Debian/Alma
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/liberation/LiberationSans-Regular.ttf"
            ]
            font_path = next((p for p in font_paths if os.path.exists(p)), None)
            
            try:
                font = ImageFont.truetype(font_path, 12) if font_path else ImageFont.load_default()
            except:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), text, font=font)
            x = base.width - (bbox[2] - bbox[0]) - 10
            y = base.height - (bbox[3] - bbox[1]) - 10
            draw.text((x, y), text, font=font, fill=(150, 150, 150, 180))

            return Image.alpha_composite(base, txt_layer).convert("RGB")
        except Exception as e:
            return original_image

    # ------------------------------------------------------- Orchestration ---

    def _valider_et_preparer(self):
        try:
            max_pages = int(self.entry_pages.get())
        except ValueError:
            messagebox.showerror("Erreur", "Nombre de pages invalide")
            return None

        self.driver = self.connect_driver()
        if not self.driver: return None

        self.lbl_info.config(text="Initialisation...")
        try:
            self.driver.set_window_size(1200, 3000)
        except: pass
        time.sleep(1)

        try:
            url_parts = self.driver.current_url.strip("/").split("/")
            titre_vol = url_parts[-2] if "volume" in url_parts[-2] else url_parts[-1]
        except:
            titre_vol = "scan_output"

        return max_pages, titre_vol

    def demarrer(self):
        result = self._valider_et_preparer()
        if result is None:
            self._reset_boutons()
            return
        
        max_pages, titre_vol = result
        os.makedirs("Downloads", exist_ok=True)
        image_paths = []

        self.log(f"🚀 Début du téléchargement : {titre_vol}")

        for i in range(1, max_pages + 1):
            if self._cancel_event.is_set():
                break

            self.lbl_info.config(text=f"Page {i}/{max_pages}")
            
            try:
                # Capture
                self.driver.execute_script("window.scrollTo(0,0);")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div#readerarea img"))
                )
                
                target_img = self.driver.find_element(By.CSS_SELECTOR, "div#readerarea img")
                loc, size = target_img.location, target_img.size
                
                png_data = self.driver.get_screenshot_as_png()
                full_img = Image.open(io.BytesIO(png_data)).convert("RGB")
                
                left, top = int(loc["x"]), int(loc["y"])
                right, bottom = left + int(size["width"]), top + int(size["height"])
                
                final_img = full_img.crop((left, top, right, bottom))
                final_img = self._ajouter_filigrane(final_img)
                
                fname = f"Downloads/page_{i:03d}.jpg"
                final_img.save(fname, quality=90)
                image_paths.append(fname)
                self.log(f"✅ Page {i} récupérée")

                # Suivant
                if i < max_pages:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, "div.nextprev a.ch-next-btn")
                    self.driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(2)

            except Exception as e:
                self.log(f"⚠️ Erreur page {i}: {e}")
                break

        if image_paths and not self._cancel_event.is_set():
            self._creer_pdf(image_paths, titre_vol)
        
        self._reset_boutons()

    def _creer_pdf(self, image_paths, titre_vol):
        self.lbl_info.config(text="Génération du PDF...")
        pdf_path = f"Downloads/{titre_vol}.pdf"
        try:
            with open(pdf_path, "wb") as f:
                f.write(img2pdf.convert(image_paths))
            self.log(f"🎉 Terminé ! PDF disponible : {pdf_path}")
            for p in image_paths: os.remove(p)
        except Exception as e:
            self.log(f"❌ Erreur PDF: {e}")

    def _reset_boutons(self):
        self.btn_start.config(state="normal")
        self.btn_cancel.config(state="disabled")
        self.lbl_info.config(text="Prêt.")

if __name__ == "__main__":
    app = SushiApp()
    app.mainloop()
