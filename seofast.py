import warnings
import requests
import json
import time
import random
import hashlib
import threading
import sys
import os
import re
from datetime import datetime

# Disable insecure request warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

net_lock = threading.Lock()
is_offline = False
print_lock = threading.Lock()
RE_HASH_AJAX = re.compile(r"var hash_ajax = '(.*?)';")

RUSSIAN_NAMES = [
    "ivan", "alexander", "sergey", "dmitry", "andrey", "alexey", "maxim", "evgeny", "mikhail", "vladimir", 
    "denis", "igor", "roman", "oleg", "nikolay", "anton", "ilya", "stepan", "viktor", "pavel", "artem", 
    "kirill", "vitaly", "valery", "yuri", "boris", "vadim", "ruslan", "gleb", "stanislav", "egor", "petr", 
    "nikita", "ivanov", "smirnov", "kuznetsov", "popov", "sokolov", "lebedev", "kozlov", "novikov", 
    "morozov", "petrov", "volkov", "solovyov", "vasilyev", "zaytsev", "pavlov", "semenov"
]

def generate_russian_email():
    name = random.choice(RUSSIAN_NAMES)
    suffix = random.choice(["", str(random.randint(70, 99)), str(random.randint(1980, 2005)), str(random.randint(1, 999))])
    return f"{name}{suffix}@gmail.com"

def wait_for_internet(device_index=None):
    global is_offline
    while True:
        try:
            requests.get("http://clients3.google.com/generate_204", timeout=3)
            if is_offline:
                with net_lock:
                    if is_offline:
                        with print_lock:
                            print("[+] Koneksi internet kembali terhubung!")
                        is_offline = False
            return
        except requests.RequestException:
            with net_lock:
                if not is_offline:
                    with print_lock:
                        print("[!] Internet terputus (Menunggu Mode Pesawat)...")
                    is_offline = True
            time.sleep(2)

class SeoFastBot:
    def __init__(self, email, password, device_index, proxy=None):
        self.email = email
        self.password = password
        self.device_index = device_index
        self.gmail = generate_russian_email()
        self.session = requests.Session()
        self.session.verify = False
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
            
        self.base_url = "https://seo-fast.bz/webapp/ajax/ajax_views.php"
        
        # Tambahkan random.random() agar beda tiap thread walau dipanggil bersamaan
        self.id_device = "secure_" + hashlib.md5((str(time.time()) + str(random.random())).encode()).hexdigest()[:16]
        self.hash_ajax = None
        
        # Hitung App Token secara dinamis
        package_name = "com.example.seofast"
        salt = "seo_fast_SFk1gR5h5DGH"
        string_to_hash = f"{self.id_device}:{package_name}:{salt}"
        self.app_token = hashlib.sha256(string_to_hash.encode()).hexdigest()
        
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 13; WayDroid x86_64 Device Build/TQ3A.230901.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/111.0.5563.116 Safari/537.36 SeoFast-App/1.0",
            'Accept': "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01",
            'X-Requested-With': "XMLHttpRequest",
            'X-App-Version': "1.1.0",
            'X-App-Token': self.app_token,
            'X-Device-Id': self.id_device,
            'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
            'Origin': "https://seo-fast.bz",
            'Referer': "https://seo-fast.bz/webapp/?pg=login",
            'Accept-Language': "en-US,en;q=0.9",
            'Sec-Fetch-Site': "same-origin",
            'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty"
        }

        # Template data_json untuk complete_task (diambil dari HAR)
        self.device_info_template = {
            "device_id": self.id_device,
            "device_type": "secure_device",
            "is_emulator": False,
            "is_secure": True,
            "emulator_type": "",
            "emulator_details": {
                "build_properties": False, "hardware": False, "files": False, "memu": False,
                "bluestacks": False, "nox": False, "genymotion": False, "google_emulator": False,
                "masking_detected": True
            },
            "google_email": self.gmail,
            "hardware": {
                "brand": "waydroid", "model": "WayDroid x86_64 Device", "device": "waydroid_x86_64",
                "hardware": "unknown", "manufacturer": "Waydroid", "product": "lineage_waydroid_x86_64",
                "board": "unknown"
            },
            "os": {"sdk_int": 33, "release": "13", "incremental": "eng.aleast.20260403.113748"},
            "display": {"width_px": 1920, "height_px": 965, "density_dpi": 180, "density": 1.125},
            "locale": {"language": "en", "country": "US", "variant": ""},
            "timezone": "Asia/Jakarta",
            "extra": {
                "fingerprint": "waydroid/lineage_waydroid_x86_64/waydroid_x86_64:13/TQ3A.230901.001/eng.aleast.20260403.113748:userdebug/test-keys",
                "tags": "test-keys", "type": "userdebug", "user": "aleasto", "host": "zero"
            },
            "masking_detected": True,
            "masking_evidence": {}
        }

    def log(self, message):
        with print_lock:
            print(f"[Device-{self.device_index}] {message}")

    def request(self, method, url, **kwargs):
        retries = 0
        while retries < 3:
            wait_for_internet(self.device_index)
            try:
                if method.lower() == 'get':
                    return self.session.get(url, timeout=10, **kwargs)
                elif method.lower() == 'post':
                    return self.session.post(url, timeout=10, **kwargs)
            except requests.RequestException as e:
                retries += 1
                wait_for_internet(self.device_index)
                self.log(f"[-] Koneksi gagal/timeout, percobaan {retries}/3...")
                time.sleep(2)
        raise Exception("Gagal terhubung ke server setelah 3 kali percobaan.")

    def login(self):
        self.log("[*] Mencoba login otomatis...")
        try:
            # 1. Ambil hash awal dari halaman login
            headers = self.headers.copy()
            res_page = self.request('get', "https://seo-fast.bz/webapp/?pg=login", headers=headers)
            
            match = RE_HASH_AJAX.search(res_page.text)
            if not match:
                self.log("[-] Gagal mengambil hash login.")
                return False
            
            self.hash_ajax = match.group(1)
            
            # 2. Kirim request login
            login_url = "https://seo-fast.bz/webapp/ajax/ajax_login.php"
            payload = {
                "login": self.email,
                "password": self.password,
                "hash": self.hash_ajax,
                "ajax_func": "login"
            }
            
            # Login uses form-urlencoded
            headers['Content-Type'] = "application/x-www-form-urlencoded; charset=UTF-8"
            res_login = self.request('post', login_url, data=payload, headers=headers)
            
            if "location.replace('?pg=job')" in res_login.text:
                self.log("[+] Login Berhasil!")
                # Ambil hash baru dari halaman job
                self.get_session_info()
                return True
            else:
                self.log(f"[-] Login Gagal: {res_login.text}")
        except Exception as e:
            self.log(f"[-] Error saat login: {e}")
        return False

    def get_session_info(self):
        self.log("[*] Memperbarui hash_ajax untuk sesi tugas...")
        headers = self.headers.copy()
        headers['Content-Type'] = "text/html"
        try:
            res = self.request('get', "https://seo-fast.bz/webapp/?pg=job", headers=headers)
            match = RE_HASH_AJAX.search(res.text)
            if match:
                self.hash_ajax = match.group(1)
                self.log(f"[+] Hash Ajax terbaru: {self.hash_ajax}")
                # Update base headers for future JSON requests
                self.headers['Content-Type'] = "application/json"
                return True
        except: pass
        return False

    def get_task(self):
        self.log(f"[*] [{datetime.now().strftime('%H:%M:%S')}] Mengambil tugas baru...")
        payload = {
            "ajax_func": "get_task",
            "id_device": self.id_device,
            "hash_ajax": self.hash_ajax
        }
        try:
            res = self.request('post', self.base_url, json=payload, headers=self.headers)
            if res.status_code == 200:
                data = res.json()
                if data.get("status"):
                    return data
                else:
                    self.log(f"[!] Tidak ada tugas tersedia atau error: {res.text}")
                    return "RESTART"
            else:
                self.log(f"[-] Gagal ambil tugas ({res.status_code}): {res.text}")
                return "RESTART"
        except Exception as e:
            self.log(f"[-] Error get_task: {e}")
        return None

    def complete_task(self, id_status):
        self.log(f"[*] [{datetime.now().strftime('%H:%M:%S')}] Menyelesaikan tugas ID: {id_status}...")
        
        # Update timestamp di data_json
        device_info = self.device_info_template.copy()
        
        for attempt in range(5):
            device_info["timestamp"] = int(time.time() * 1000)
            
            payload = {
                "ajax_func": "complete_task",
                "id_status": str(id_status),
                "id_device": self.id_device,
                "data_json": json.dumps(device_info),
                "hash_ajax": self.hash_ajax
            }
            
            try:
                res = self.request('post', self.base_url, json=payload, headers=self.headers)
                if res.status_code == 200:
                    data = res.json()
                    balance = data.get('balance', 'N/A')
                    earned = data.get('earned', 'N/A')
                    self.log(f"[+] Tugas selesai! Saldo: {balance} RUB (Total Earned: {earned})")
                    return True
                else:
                    if attempt < 4:
                        time.sleep(0.5)
                    else:
                        self.log(f"[-] Gagal selesaikan tugas ({res.status_code}): {res.text}")
            except Exception as e:
                if attempt < 4:
                    time.sleep(0.5)
                else:
                    self.log(f"[-] Error complete_task: {e}")
        return False

    def update_data(self):
        self.log(f"[*] [{datetime.now().strftime('%H:%M:%S')}] Mengirim up_data awal...")
        url = "https://seo-fast.bz/webapp/ajax/ajax_data.php"
        
        device_info = self.device_info_template.copy()
        device_info["timestamp"] = int(time.time() * 1000)
        
        payload = {
            "ajax_func": "up_data",
            "hash_ajax": self.hash_ajax,
            "id_device": self.id_device,
            "email": self.gmail,
            "os_version": "13",
            "screen_resolution": "1920x965",
            "locale_language": "en",
            "locale_country": "US",
            "data_json": json.dumps(device_info)
        }
        
        try:
            res = self.request('post', url, json=payload, headers=self.headers)
            self.log(f"[+] Up Data Response: {res.text}")
            return True
        except Exception as e:
            self.log(f"[-] Error update_data: {e}")
        return False

    def run(self):
        self.log("="*40)
        self.log("   SEO-FAST.BZ AUTO BOT STARTED")
        self.log("="*40)
        
        if not self.login():
            return "RESTART"
            
        # Kirim update data sekali di awal
        self.update_data()
        
        while True:
            task = self.get_task()
            if task == "RESTART":
                self.log("[*] Tidak ada tugas, meregenerasi device dan mengganti proxy...")
                return "RESTART"
            elif task:
                id_status = task.get("id_status")
                timer = int(task.get("timer", 15))
                url = task.get("url")
                
                self.log(f"[i] Menjalankan: {url}")
                self.log(f"[i] Menunggu timer {timer} detik...")
                
                # Sleep untuk timer karena multi thread output tumpang tindih
                time.sleep(timer + 1)
                
                self.complete_task(id_status)
            else:
                self.log("[*] Menunggu 30 detik sebelum mencoba lagi...")
                time.sleep(30)

def worker(email, password, device_index, proxy_list):
    while True:
        current_proxy = random.choice(proxy_list) if proxy_list else None
        if current_proxy and not current_proxy.startswith("http"):
            current_proxy = f"http://{current_proxy}"
            
        bot = SeoFastBot(email, password, device_index, current_proxy)
        res = bot.run()
        
        if res == "RESTART":
            time.sleep(2)
            continue
        break

if __name__ == "__main__":
    os.system('clear' if os.name == 'posix' else 'cls')
    print("=== SEO-FAST.BZ AUTO BOT (MULTI-DEVICE) ===")
    
    if not os.path.exists("akun"):
        os.makedirs("akun")
        
    accounts = [d for d in os.listdir("akun") if os.path.isdir(os.path.join("akun", d))]
    if not accounts:
        print("[-] Tidak ada folder akun di dalam folder 'akun/'.")
        sys.exit(1)
        
    print("[*] Pilih Akun:")
    for idx, acc in enumerate(accounts):
        print(f"  {idx + 1}. {acc}")
        
    try:
        acc_idx = int(input("[?] Masukkan nomor akun: ").strip()) - 1
        if acc_idx < 0 or acc_idx >= len(accounts):
            raise ValueError
        selected_account = accounts[acc_idx]
    except ValueError:
        print("[-] Pilihan tidak valid.")
        sys.exit(1)
        
    acc_path = os.path.join("akun", selected_account)
    acc_file = os.path.join(acc_path, "acc")
    
    main_email = ""
    main_password = ""
    proxy_list = []
    
    proxy_file = os.path.join(acc_path, "proxies.txt")
    if os.path.exists(proxy_file):
        with open(proxy_file, 'r') as p:
            for line in p:
                px = line.strip()
                if px:
                    proxy_list.append(px)
                    
    if os.path.exists(acc_file):
        with open(acc_file, "r") as f:
            for line in f:
                if line.startswith("email="):
                    main_email = line.strip().split("=")[1]
                elif line.startswith("pass="):
                    main_password = line.strip().split("=")[1]
                    
    if not main_email or not main_password:
        print(f"[-] Gagal membaca email/pass dari {acc_file}")
        sys.exit(1)
        
    print(f"[+] Login sebagai: {main_email}")
    print(f"[+] Ditemukan {len(proxy_list)} proxy.")
        
    try:
        num_devices = int(input("[?] Jumlah Device (Thread): ").strip())
    except ValueError:
        print("[-] Jumlah device harus angka.")
        sys.exit(1)

    threads = []
    for i in range(1, num_devices + 1):
        t = threading.Thread(target=worker, args=(main_email, main_password, i, proxy_list))
        t.daemon = True
        threads.append(t)
        t.start()
        time.sleep(1) # Jeda sedikit agar request awal tidak bersamaan

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Dihentikan oleh user.")
