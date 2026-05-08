import shutil
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageFont
import img2pdf
import os
import time
import threading
import io

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SushiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SushiScan Downloader - Created by Endam")
        self.geometry("700x800")
        self.driver = None
        self._cancel_event = threading.Event()  # bouton annuler
        self._setup_ui()

    # ------------------------------------------------------------------ UI ---

    def _setup_ui(self):
        frame_top = tk.Frame(self)
        frame_top.pack(pady=10, padx=10, fill="x")

        lbl_instr = tk.Label(
            frame_top,
            text="1. Ouvrez Chromium (Page 1)\n2. Regardez le nombre total de pages",
            fg="red",
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
            text="Démarrer le téléchargement",
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

        lbl_credit = tk.Label(
            self, text="Created by Endam", font=("Arial", 10, "italic"), fg="#666666"
        )
        lbl_credit.pack(side=tk.BOTTOM, pady=10)

    def _on_start(self):
        self._cancel_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_cancel.config(state="normal")
        threading.Thread(target=self.demarrer, daemon=True).start()

    def _on_cancel(self):
        self._cancel_event.set()
        self.btn_cancel.config(state="disabled")
        self.lbl_info.config(text="Annulation en cours...")
        self.log("⛔ Annulation demandée — fin après la page en cours.")

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        print(message)

    # ----------------------------------------------------------- Selenium ---

    def connect_driver(self):
        """Connexion au Chromium déjà ouvert sur le port 9222."""
        if self.driver is not None:
            return self.driver
            
        # --- NOUVEAU : Cherche le chemin automatiquement ---
        chemin_driver = shutil.which("chromedriver")
        if not chemin_driver:
            self.lbl_info.config(text="Erreur: Chromedriver introuvable sur ce PC !")
            self.log("Erreur : Impossible de trouver chromedriver. Est-il installé ?")
            return None

        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        service = Service(executable_path=chemin_driver)
        
        try:
            self.driver = webdriver.Chrome(service=service, options=options)
            return self.driver
        except Exception as e:
            self.lbl_info.config(text="Erreur: Lancez Chromium sur port 9222 !")
            self.log(f"connect_driver: {e}")
            return None

    # ----------------------------------------------------------- Filigrane ---

    def _ajouter_filigrane(self, original_image):
        """Ajoute un filigrane discret 'Created by Endam' en bas à droite."""
        try:
            base = original_image.convert("RGBA")
            txt_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)

            text = "Created by Endam"
            try:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10
                )
            except Exception:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), text, font=font)
            x = base.width - (bbox[2] - bbox[0]) - 5
            y = base.height - (bbox[3] - bbox[1]) - 5
            draw.text((x, y), text, font=font, fill=(150, 150, 150, 180))

            return Image.alpha_composite(base, txt_layer).convert("RGB")

        except Exception as e:
            self.log(f"Warning Filigrane: {e}")
            return original_image

    # ------------------------------------------------------- Etapes métier ---

    def _valider_et_preparer(self):
        """Valide la saisie, connecte le driver et prépare la session.

        Retourne (max_pages, titre_vol) ou None en cas d'erreur.
        """
        try:
            max_pages = int(self.entry_pages.get())
        except ValueError:
            messagebox.showerror("Erreur", "Nombre de pages invalide")
            return None

        self.driver = self.connect_driver()
        if not self.driver:
            return None

        self.lbl_info.config(text="Démarrage...")

        self.log("Redimensionnement fenêtre (3000px)...")
        try:
            self.driver.set_window_size(1200, 3000)
        except Exception:
            pass
        time.sleep(1)

        try:
            url_parts = self.driver.current_url.strip("/").split("/")
            titre_vol = url_parts[-2] if "volume" in url_parts[-2] else url_parts[-1]
        except Exception:
            titre_vol = "scan_output"

        return max_pages, titre_vol

    def _pages_deja_telechargees(self, max_pages):
        """Retourne le set des numéros de pages déjà présentes dans Downloads/."""
        os.makedirs("Downloads", exist_ok=True)
        existantes = set()
        for i in range(1, max_pages + 1):
            if os.path.exists(f"Downloads/page_{i:03d}.jpg"):
                existantes.add(i)
        return existantes

    def _capturer_page(self, i):
        """Capture la page courante avec WebDriverWait, applique le filigrane et sauvegarde.

        Retourne le chemin du fichier sauvegardé, ou None en cas d'échec.
        """
        self.driver.execute_script("window.scrollTo(0,0);")

        # Attente intelligente : on attend qu'une image de hauteur suffisante soit présente
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#readerarea img"))
            )
        except Exception:
            self.log(f"Page {i} : Timeout attente image")
            return None

        target_img = None
        for img in self.driver.find_elements(By.CSS_SELECTOR, "div#readerarea img"):
            if img.size["height"] > 200:
                target_img = img
                break

        if not target_img:
            self.log(f"Page {i} : Image introuvable")
            return None

        loc = target_img.location
        size = target_img.size
        left, top = int(loc["x"]), int(loc["y"])
        right, bottom = int(loc["x"] + size["width"]), int(loc["y"] + size["height"])

        if right <= left or bottom <= top:
            self.log(f"Page {i} : Erreur dimensions")
            return None

        png_data = self.driver.get_screenshot_as_png()
        full_img = Image.open(io.BytesIO(png_data)).convert("RGB")
        final_img = full_img.crop((left, top, right, bottom))
        final_img = self._ajouter_filigrane(final_img)

        os.makedirs("Downloads", exist_ok=True)
        fname = f"Downloads/page_{i:03d}.jpg"
        final_img.save(fname, quality=90, dpi=(96, 96))
        self.log(f"Page {i} : OK")
        return fname

    def _naviguer_suivant(self):
        """Clique sur le bouton Suivant et attend le chargement via WebDriverWait.

        Retourne True si la navigation a réussi, False sinon.
        """
        try:
            next_btns = self.driver.find_elements(
                By.CSS_SELECTOR, "div.nextprev a.ch-next-btn"
            )
            if not next_btns:
                next_btns = self.driver.find_elements(
                    By.XPATH, "//a[contains(text(), 'Suivant')]"
                )

            if not next_btns:
                self.log("Bouton Suivant introuvable ! Arrêt.")
                return False

            # On mémorise le src de l'image actuelle pour détecter le changement
            old_imgs = self.driver.find_elements(By.CSS_SELECTOR, "div#readerarea img")
            old_src = old_imgs[0].get_attribute("src") if old_imgs else None

            self.driver.execute_script("arguments[0].click();", next_btns[-1])

            # Stratégie 1 : attente que le src de l'image change (navigation AJAX)
            if old_src:
                try:
                    WebDriverWait(self.driver, 15).until(
                        lambda d: any(
                            img.get_attribute("src") != old_src
                            for img in d.find_elements(By.CSS_SELECTOR, "div#readerarea img")
                            if img.get_attribute("src")
                        )
                    )
                    return True
                except Exception:
                    pass  # fallback ci-dessous

            # Stratégie 2 : fallback sleep si la détection AJAX échoue
            time.sleep(3)
            return True

        except Exception as e:
            self.log(f"Erreur Nav: {e}")
            return False

    def _creer_pdf(self, image_paths, titre_vol):
        """Assemble les JPG en PDF via img2pdf puis supprime les fichiers temporaires."""
        self.lbl_info.config(text="Création PDF...")

        safe_title = "".join(
            c for c in titre_vol if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        pdf_path = f"Downloads/{safe_title}.pdf"

        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(image_paths))

        self.log(f"--- PDF CRÉÉ : {pdf_path} ---")

        for p in image_paths:
            if os.path.exists(p):
                os.remove(p)

    # ---------------------------------------------------- Orchestration ---

    def demarrer(self):
        """Point d'entrée principal — orchestre les étapes de téléchargement."""
        result = self._valider_et_preparer()
        if result is None:
            self._reset_boutons()
            return
        max_pages, titre_vol = result

        # --- REPRISE SUR ERREUR ---
        deja_faites = self._pages_deja_telechargees(max_pages)
        if deja_faites:
            self.log(f"↩️  Reprise : {len(deja_faites)} page(s) déjà téléchargée(s), on continue.")

        self.log(f"--- Scan de {max_pages} pages : {titre_vol} ---")

        # On reconstruit la liste complète (pages existantes + nouvelles)
        image_paths = [f"Downloads/page_{i:03d}.jpg" for i in sorted(deja_faites)]
        premiere_page_manquante = min(
            (i for i in range(1, max_pages + 1) if i not in deja_faites),
            default=None
        )

        if premiere_page_manquante is None:
            self.log("Toutes les pages sont déjà téléchargées.")
            self._creer_pdf(image_paths, titre_vol)
            self._reset_boutons()
            return

        for i in range(premiere_page_manquante, max_pages + 1):
            # --- VÉRIFICATION ANNULATION ---
            if self._cancel_event.is_set():
                self.log("⛔ Téléchargement annulé.")
                break

            if i in deja_faites:
                self.log(f"Page {i} : déjà téléchargée, skip.")
                continue

            self.lbl_info.config(text=f"Page {i}/{max_pages}...")
            try:
                path = self._capturer_page(i)
                if path:
                    image_paths.append(path)
                    # On trie pour garder l'ordre correct dans le PDF
                    image_paths.sort()

                if i < max_pages and not self._cancel_event.is_set():
                    if not self._naviguer_suivant():
                        break

            except Exception as e:
                self.log(f"Erreur Page {i}: {e}")
                break

        if image_paths and not self._cancel_event.is_set():
            self._creer_pdf(image_paths, titre_vol)
        elif image_paths and self._cancel_event.is_set():
            self.log(f"💾 {len(image_paths)} page(s) conservées dans Downloads/ pour reprise.")

        self._reset_boutons()

    def _reset_boutons(self):
        """Remet l'UI dans l'état initial après fin ou annulation."""
        self.btn_start.config(state="normal")
        self.btn_cancel.config(state="disabled")
        self.lbl_info.config(text="Terminé !" if not self._cancel_event.is_set() else "Annulé.")


if __name__ == "__main__":
    app = SushiApp()
    app.mainloop()
