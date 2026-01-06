import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import subprocess
import os
import json
import time
from flask import Flask, request, jsonify
from datetime import datetime

# --- KONFIGURACJA ---
SAVE_DIR = "Kopia_S20"
PORT = 5000

# Tworzenie folderu na kopie
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# --- SERWER FLASK (BACKEND) ---
app = Flask(__name__)
gui_log_queue = [] # Prosta kolejka do przekazywania komunikatów do GUI

@app.route('/api/upload', methods=['POST'])
def upload_data():
    """Ten endpoint odbiera dane z Twojego S20"""
    try:
        data = request.json
        data_type = data.get("type", "nieznany")
        payload = data.get("payload", [])
        
        # Generowanie nazwy pliku
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{SAVE_DIR}/{data_type}_{timestamp}.json"
        
        # Zapis na dysk
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
            
        msg = f"[ODEBRANO] Typ: {data_type} | Ilość: {len(payload)} | Zapisano: {filename}"
        gui_log_queue.append(msg)
        
        return jsonify({"status": "success", "msg": "Dane zapisane na PC"})
    
    except Exception as e:
        gui_log_queue.append(f"[BŁĄD] {str(e)}")
        return jsonify({"status": "error", "msg": str(e)}), 500

def run_flask():
    # Uruchamia serwer bez logów w konsoli, żeby nie śmiecić
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='0.0.0.0', port=PORT)

# --- INTERFEJS GRAFICZNY (GUI) ---
class DrPhoneApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dr.Phone Clone - Samsung S20 Manager")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")

        # Stylizacja
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6, relief="flat", background="#0078d7", foreground="white")
        style.map("TButton", background=[('active', '#005a9e')])

        # Nagłówek
        header_frame = tk.Frame(root, bg="#333", height=60)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text="Zarządzanie Urządzeniem Mobilnym", bg="#333", fg="white", font=("Segoe UI", 16, "bold")).pack(pady=10)

        # Panel Sterowania
        control_frame = tk.Frame(root, bg="#f0f0f0")
        control_frame.pack(pady=20, padx=20, fill="x")

        # Przyciski
        self.btn_connect = ttk.Button(control_frame, text="1. POŁĄCZ (ADB)", command=self.connect_adb)
        self.btn_connect.pack(side="left", padx=10)

        self.lbl_status = tk.Label(control_frame, text="Status: Rozłączono", fg="red", bg="#f0f0f0", font=("Segoe UI", 10))
        self.lbl_status.pack(side="left", padx=10)

        # Panel Logów (Konsola)
        log_frame = tk.LabelFrame(root, text="Logi Operacji / Odebrane Dane", bg="#f0f0f0", font=("Segoe UI", 10, "bold"))
        log_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=15, font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)

        # Stopka
        tk.Label(root, text="Serwer nasłuchuje na porcie 5000...", bg="#f0f0f0", fg="#666").pack(side="bottom", pady=5)

        # Uruchomienie wątku serwera
        self.server_thread = threading.Thread(target=run_flask, daemon=True)
        self.server_thread.start()
        
        # Cykliczne sprawdzanie kolejki logów
        self.check_logs()

    def log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} > {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def check_logs(self):
        """Sprawdza czy serwer Flask odebrał jakieś dane i wyświetla je w GUI"""
        while gui_log_queue:
            msg = gui_log_queue.pop(0)
            self.log(msg)
        self.root.after(100, self.check_logs)

    def connect_adb(self):
        self.log("Próba połączenia przez ADB...")
        
        # Sprawdzanie urządzeń
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True)
            if "device" not in res.stdout.replace("List of devices attached", "").strip():
                self.lbl_status.config(text="Status: Nie wykryto telefonu!", fg="red")
                messagebox.showerror("Błąd", "Nie wykryto telefonu. Sprawdź kabel i debugowanie USB.")
                return
            
            # Zestawienie tunelu
            # To sprawia, że telefon wysyłając na localhost:5000 trafia do TEGO programu
            subprocess.run(["adb", "reverse", "tcp:5000", "tcp:5000"], check=True)
            
            self.lbl_status.config(text="Status: POŁĄCZONO (Tunel Aktywny)", fg="green")
            self.log("Sukces! Tunel ADB zestawiony (Port 5000).")
            self.log("Teraz uruchom aplikację Python na S20 i kliknij 'Wyślij'.")
            
        except FileNotFoundError:
            self.log("Błąd: Nie znaleziono komendy 'adb'. Czy zainstalowałeś sterowniki?")
        except Exception as e:
            self.log(f"Błąd krytyczny: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DrPhoneApp(root)
    root.mainloop()