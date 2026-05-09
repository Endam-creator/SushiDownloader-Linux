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
import subprocess

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
        self.profile_dir = os.path.expanduser("~/SushiProfile")
        self._setup_ui()
        
        # Vérification des pré-requis au lancement
        self.after(1000, self._check_dependencies)

    def _check_dependencies(self):
        """ Vérifie si Chromium et le Driver sont présents sur le système Linux """
        deps = {
            "chromium": ["/usr/bin/chromium-browser", "/usr/bin/chromium"],
            "chromedriver": ["/usr/bin/chromedriver", "/usr/lib/chromium-browser/chromedriver"]
        }
        missing = []
        for name, paths in deps.items():
            if not any(os.path.exists(p) for p in paths) and shutil.which(name) is None:
                missing.append(name)
        
        if missing:
            msg = "⚠️ Dépendances manquantes !\n\nsudo apt install chromium-browser chromium-chromedriver"
            messagebox.showwarning("Logiciel Manquant", msg)

    def _setup_ui(self):
        frame_top = tk.Frame(self)
        frame_top.pack(pady=10, padx=10, fill="x")

        lbl_instr = tk.Label(
            frame_top,
            text="L'application lancera Chromium automatiquement.\nAssurez-vous d'être sur la Page 1 du chapitre.",
            fg="red", justify=tk.LEFT
        )
        lbl_instr.pack(side=tk.TOP, pady=5)

        frame_input = tk.Frame(frame_top)
        frame_input.pack(pady=5)

        tk.Label(frame_input, text="Nombre de pages :").pack(side=tk.LEFT)
        self.entry_pages = tk.Entry(frame_input, width=10)
        self.entry_pages.pack(side=tk.LEFT, padx=5)
        self.entry_pages.insert(0, "64")

        self.btn_start = tk.Button(
            frame_top, text="🚀 Démarrer le téléchargement",
            command=self._on_start, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
        )
        self.btn_start.pack(side=tk.TOP, fill="x", pady=(10, 4))

        self.btn_cancel = tk.Button(
            frame_top, text="⛔ Annuler",
            command=self._on_cancel, bg="#e53935", fg="white", font=("Arial", 11, "bold"),
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

    def lancer_chromium_automatique(self):
        """ Logique du launcher.sh intégrée """
        self.log("🚀 Lancement de Chromium en mode Debug...")
        browser_bin = shutil.which("chromium-browser") or shutil.which("chromium")
        
        if not browser_bin: return False

        cmd = [
            browser_bin,
            "--remote-debugging-port=9222",
            f"--user-data-dir={self.profile_dir}",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "https://sushiscan.net"
        ]
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5) # Laisse le temps au port 9222 de s'ouvrir
            return True
        except: return False

    def connect_driver(self):
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        options.add_argument("--no-sandbox")
        
        driver_path = shutil.which("chromedriver") or "/usr/bin/chromedriver"
        service = Service(executable_path=driver_path)

        try:
            self.driver = webdriver.Chrome(service=service, options=options)
            return self.driver
        except:
            if self.lancer_chromium_automatique():
                try:
                    return webdriver.Chrome(service=service, options=options)
                except: pass
            messagebox.showerror("Erreur", "Impossible de piloter Chromium.")
            return None

    def _ajouter_filigrane(self, original_image):
        try:
            base = original_image.convert("RGBA")
            txt_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            text = "Created by Endam"
            font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), text, font=font)
            x, y = base.width - (bbox[2]-bbox[0]) - 10, base.height - (bbox[3]-bbox[1]) - 10
            draw.text((x, y), text, font=font, fill=(150, 150, 150, 180))
            return Image.alpha_composite(base, txt_layer).convert("RGB")
        except: return original_image

    def demarrer(self):
        max_pages_str = self.entry_pages.get()
        if not max_pages_str.isdigit():
            messagebox.showerror("Erreur", "Nombre de pages invalide")
            self._reset_boutons()
            return
            
        max_pages = int(max_pages_str)
        self.driver = self.connect_driver()
        if not self.driver:
            self._reset_boutons()
            return

        self.log("🔗 Connecté à Chromium. Début du téléchargement...")
        os.makedirs("Downloads", exist_ok=True)
        image_paths = []

        for i in range(1, max_pages + 1):
            if self._cancel_event.is_set(): break
            self.lbl_info.config(text=f"Page {i}/{max_pages}")
            
            try:
                self.driver.execute_script("window.scrollTo(0,0);")
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#readerarea img")))
                target_img = self.driver.find_element(By.CSS_SELECTOR, "div#readerarea img")
                
                png_data = self.driver.get_screenshot_as_png()
                full_img = Image.open(io.BytesIO(png_data)).convert("RGB")
                
                loc, size = target_img.location, target_img.size
                left, top = int(loc["x"]), int(loc["y"])
                right, bottom = left + int(size["width"]), top + int(size["height"])
                
                final_img = full_img.crop((left, top, right, bottom))
                final_img = self._ajouter_filigrane(final_img)
                
                fname = f"Downloads/page_{i:03d}.jpg"
                final_img.save(fname, quality=90)
                image_paths.append(fname)
                self.log(f"✅ Page {i} OK")

                if i < max_pages:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, "div.nextprev a.ch-next-btn")
                    self.driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(2)
            except Exception as e:
                self.log(f"⚠️ Erreur page {i}: {e}")
                break

        if image_paths and not self._cancel_event.is_set():
            self._creer_pdf(image_paths, "SushiScan_Download")
        self._reset_boutons()

    def _creer_pdf(self, image_paths, title):
        pdf_path = f"Downloads/{title}_{int(time.time())}.pdf"
        try:
            with open(pdf_path, "wb") as f:
                f.write(img2pdf.convert(image_paths))
            self.log(f"🎉 PDF créé : {pdf_path}")
            for p in image_paths: os.remove(p)
        except Exception as e: self.log(f"❌ Erreur PDF: {e}")

    def _reset_boutons(self):
        self.btn_start.config(state="normal")
        self.btn_cancel.config(state="disabled")
        self.lbl_info.config(text="Prêt.")

if __name__ == "__main__":
    app = SushiApp()
    app.mainloop()
