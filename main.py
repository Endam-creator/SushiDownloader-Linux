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
    """ Gestion des chemins pour PyInstaller (icônes, images, etc.) """
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
        # Dossier de profil isolé pour ne pas polluer ton navigateur principal
        self.profile_dir = os.path.expanduser("~/SushiProfile")
        self._setup_ui()
        
        # Petit check au démarrage
        self.after(1000, self._check_dependencies)

    def _check_dependencies(self):
        """ Vérifie si les outils système sont là """
        browser = shutil.which("chromium-browser") or shutil.which("chromium")
        driver = shutil.which("chromedriver")
        
        if not browser or not driver:
            msg = "⚠️ Dépendances manquantes !\n\nsudo dnf install chromium chromedriver"
            messagebox.showwarning("Logiciel Manquant", msg)

    def _setup_ui(self):
        frame_top = tk.Frame(self)
        frame_top.pack(pady=10, padx=10, fill="x")

        lbl_instr = tk.Label(
            frame_top,
            text="L'application gère le lancement de Chromium.\nPlacez-vous sur le premier scan du chapitre une fois ouvert.",
            fg="#d32f2f", justify=tk.LEFT
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

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def lancer_chromium_automatique(self):
        """ Nettoie les verrous et lance Chromium en mode Debug """
        self.log("🧹 Nettoyage des anciennes sessions...")
        os.system("pkill -f chromium")
        
        # Suppression du verrou Singleton de Chromium (très important sur Linux)
        lock_file = os.path.join(self.profile_dir, "SingletonLock")
        if os.path.exists(lock_file):
            try: os.unlink(lock_file)
            except: pass

        browser_bin = shutil.which("chromium-browser") or shutil.which("chromium")
        if not browser_bin: return False

        self.log(f"🚀 Lancement de {browser_bin}...")
        # Commande optimisée pour AlmaLinux avec DISPLAY force
        cmd = f'DISPLAY=:0 {browser_bin} --remote-debugging-port=9222 --user-data-dir="{self.profile_dir}" --no-sandbox --disable-dev-shm-usage --disable-gpu https://sushiscan.net > /dev/null 2>&1 &'
        
        try:
            os.system(cmd)
            time.sleep(5) 
            return True
        except: return False

    def connect_driver(self):
        """ Connexion Selenium au port 9222 """
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        options.add_argument("--no-sandbox")
        
        # On utilise ton chemin /usr/bin/chromedriver confirmé
        service = Service(executable_path="/usr/bin/chromedriver")

        try:
            self.driver = webdriver.Chrome(service=service, options=options)
            return self.driver
        except:
            if self.lancer_chromium_automatique():
                try:
                    return webdriver.Chrome(service=service, options=options)
                except: pass
            messagebox.showerror("Erreur", "Impossible d'initier Selenium sur le port 9222.")
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
        """Orchestre le téléchargement, la capture précise et la création du PDF."""
        val = self.entry_pages.get()
        if not val.isdigit():
            messagebox.showerror("Erreur", "Nombre de pages invalide")
            self._reset_boutons()
            return
            
        max_pages = int(val)
        self.driver = self.connect_driver()
        if not self.driver:
            self._reset_boutons()
            return

        self.log("✅ Connecté à Chromium. Ajustement du format...")
        
        # On force une grande fenêtre pour éviter que le scan ne soit coupé
        self.driver.set_window_size(1600, 2600)
        
        os.makedirs("Downloads", exist_ok=True)
        image_paths = []

        for i in range(1, max_pages + 1):
            if self._cancel_event.is_set():
                self.log("⛔ Annulation demandée.")
                break

            self.lbl_info.config(text=f"Progression : {i}/{max_pages}")
            
            try:
                # 1. Attente que l'image soit présente dans le DOM
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div#readerarea img"))
                )
                
                # 2. Forcer le chargement de l'image (Lazy Load Fix)
                # On descend un peu puis on remonte pour "réveiller" le scan
                self.driver.execute_script("window.scrollTo(0, 800);")
                time.sleep(0.5)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1.2) # Temps pour que l'image s'affiche proprement

                # 3. Récupérer l'élément et ses coordonnées RÉELLES via JS
                target_img = self.driver.find_element(By.CSS_SELECTOR, "div#readerarea img")
                
                # Ce script calcule la position exacte par rapport au coin haut-gauche du document
                rect = self.driver.execute_script("""
                    var rect = arguments[0].getBoundingClientRect();
                    return {
                        left: rect.left + window.pageXOffset,
                        top: rect.top + window.pageYOffset,
                        width: rect.width,
                        height: rect.height
                    };
                """, target_img)

                # 4. Capture d'écran brute
                png_data = self.driver.get_screenshot_as_png()
                full_img = Image.open(io.BytesIO(png_data)).convert("RGB")

                # 5. Calcul du découpage (Crop) pour enlever le noir
                left = int(rect['left'])
                top = int(rect['top'])
                right = left + int(rect['width'])
                bottom = top + int(rect['height'])

                # Sécurité : on s'assure de ne pas dépasser les limites de la capture
                final_img = full_img.crop((
                    max(0, left), 
                    max(0, top), 
                    min(right, full_img.width), 
                    min(bottom, full_img.height)
                ))

                # 6. Ajout du filigrane et sauvegarde
                final_img = self._ajouter_filigrane(final_img)
                fname = f"Downloads/page_{i:03d}.jpg"
                
                # Sauvegarde en haute qualité (95) sans sous-échantillonnage pour un texte net
                final_img.save(fname, quality=95, subsampling=0)
                image_paths.append(fname)
                self.log(f"✅ Page {i} capturée au bon format.")

                # 7. Navigation vers la page suivante
                if i < max_pages:
                    try:
                        # On cherche le bouton "Suivant" spécifique à SushiScan
                        next_btn = self.driver.find_element(By.CSS_SELECTOR, "div.nextprev a.ch-next-btn")
                        self.driver.execute_script("arguments[0].click();", next_btn)
                        # Attente de chargement de la nouvelle page
                        time.sleep(3) 
                    except Exception:
                        self.log("⚠️ Bouton Suivant introuvable ou fin de chapitre.")
                        break

            except Exception as e:
                self.log(f"❌ Erreur critique page {i}: {e}")
                break

        # 8. Assemblage final en PDF
        if image_paths and not self._cancel_event.is_set():
            self._creer_pdf(image_paths)
        
        self._reset_boutons()
    
    def _on_start(self):
        self._cancel_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_cancel.config(state="normal")
        threading.Thread(target=self.demarrer, daemon=True).start()

    def _on_cancel(self):
        self._cancel_event.set()
        self.btn_cancel.config(state="disabled")

    def _reset_boutons(self):
        self.btn_start.config(state="normal")
        self.btn_cancel.config(state="disabled")
        self.lbl_info.config(text="Prêt.")

if __name__ == "__main__":
    app = SushiApp()
    app.mainloop()
