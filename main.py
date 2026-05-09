import subprocess
import shutil
# ... (garde tes autres imports : tkinter, selenium, etc.)

class SushiApp(tk.Tk):
    def __init__(self):
        # ... (ton code actuel)
        self.profile_dir = os.path.expanduser("~/SushiProfile")

    def lancer_chromium_automatique(self):
        """Remplace le launcher.sh : lance Chromium en mode debug"""
        self.log("🚀 Tentative de lancement de Chromium...")
        
        # Détection du binaire (chromium ou chromium-browser)
        browser_bin = shutil.which("chromium") or shutil.which("chromium-browser")
        
        if not browser_bin:
            self.log("❌ Erreur : Chromium n'est pas installé sur le système.")
            return False

        # Commande équivalente au launcher.sh
        cmd = [
            browser_bin,
            "--remote-debugging-port=9222",
            f"--user-data-dir={self.profile_dir}",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "https://sushiscan.net"
        ]

        try:
            # On lance en arrière-plan sans bloquer Python
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log("⏳ Attente de 5 secondes pour l'initialisation de Chromium...")
            time.sleep(5)
            return True
        except Exception as e:
            self.log(f"❌ Erreur lors du lancement de Chromium : {e}")
            return False

    def connect_driver(self):
        """Connexion au port 9222 avec tentative de lancement si échec"""
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver_path = shutil.which("chromedriver") or "/usr/bin/chromedriver"
        service = Service(executable_path=driver_path)

        try:
            self.driver = webdriver.Chrome(service=service, options=options)
            return self.driver
        except Exception:
            # Si la connexion échoue, c'est que Chromium n'est pas lancé
            # Alors on tente de le lancer nous-mêmes
            if self.lancer_chromium_automatique():
                try:
                    self.driver = webdriver.Chrome(service=service, options=options)
                    return self.driver
                except Exception as e:
                    self.log(f"❌ Échec de connexion après lancement : {e}")
            return None

    # ... (Garde le reste de tes fonctions : demarrer, _capturer_page, etc.)
