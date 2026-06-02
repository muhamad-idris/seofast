import requests
import json
import time
import random
import hashlib
import threading
import string
import re
import os
import sys
from urllib.parse import urlparse, parse_qs
from datetime import datetime

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

task_lock = threading.Lock()
net_lock = threading.Lock()
is_offline = False

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

global_balance = 0.0
stop_event = threading.Event()
print_lock = threading.Lock()

def print_error(msg):
    with print_lock:
        sys.stdout.write("\r\033[K")
        print(msg)
        pct = min(100, int((global_balance / 500.0) * 100))
        bar = "█" * (pct // 2) + "-" * (50 - (pct // 2))
        sys.stdout.write(f"\r[+] Progress: [{bar}] {global_balance:.2f} / 500 RUB")
        sys.stdout.flush()

def update_balance_progress(balance_str):
    global global_balance
    try:
        bal = float(balance_str)
        if bal > global_balance:
            global_balance = bal
            with print_lock:
                pct = min(100, int((global_balance / 500.0) * 100))
                bar = "█" * (pct // 2) + "-" * (50 - (pct // 2))
                sys.stdout.write(f"\r\033[K[+] Progress: [{bar}] {global_balance:.2f} / 500 RUB")
                sys.stdout.flush()
                
            if global_balance >= 500:
                stop_event.set()
    except Exception:
        pass


def wait_for_internet():
    global is_offline
    while True:
        try:
            requests.get("http://clients3.google.com/generate_204", timeout=3)
            if is_offline:
                with net_lock:
                    if is_offline:
                        print_error("[+] Koneksi internet kembali terhubung!")
                        is_offline = False
            return
        except requests.RequestException:
            with net_lock:
                if not is_offline:
                    print_error("[!] Internet terputus (Menunggu Mode Pesawat)...")
                    is_offline = True
            time.sleep(2)

class SeoFastBot:
    def __init__(self, email, password, proxy=None, device_mode="emulator", device_email=None, id_device=None, emu_type=None, acc_path=None):
        self.session = requests.Session()
        self.session.verify = False
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self.email = email
        self.password = password
        self.device_mode = device_mode
        self.acc_path = acc_path
        
        if id_device:
            self.id_device = id_device
            self.emu_type = emu_type if emu_type != "None" else None
        else:
            if self.device_mode == "emulator":
                self.emu_type = random.choice(["bluestacks", "waydroid", "nox", "memu", "genymotion"])
                self.id_device = f"{self.emu_type}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
            else:
                self.emu_type = None
                self.id_device = f"secure_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
            
        self.device_email = device_email if device_email else generate_russian_email()
        
        package_name = "com.example.seofast"
        salt = "seo_fast_SFk1gR5h5DGH"
        string_to_hash = f"{self.id_device}:{package_name}:{salt}"
        self.app_token = hashlib.sha256(string_to_hash.encode()).hexdigest()
        self.device_info = self.get_device_info()
        self.hash_ajax = ""
        
        info = self.device_info
        hw = info['hardware']
        
        self.headers = {
            'User-Agent': f"Mozilla/5.0 (Linux; Android {info['os']['release']}; {hw['model']} Build/{info['extra']['fingerprint'].split('/')[3]}; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/148.0.7778.178 Mobile Safari/537.36 SeoFast-App/1.0",
            'Accept': "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01",
            'X-Requested-With': "XMLHttpRequest",
            'X-App-Version': "1.1.0",
            'X-App-Token': self.app_token,
            'X-Device-Id': self.id_device,
            'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
            'Origin': "https://seo-fast.bz",
            'Referer': "https://seo-fast.bz/webapp/?pg=login",
            'Accept-Language': "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            'Sec-Fetch-Site': "same-origin",
            'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty"
        }
        
        self.base_url = "https://seo-fast.bz/webapp/ajax/ajax_views.php"

    def get_device_info(self):
        masked_email = "invalid_email"
        if "@" in self.device_email:
            parts = self.device_email.split("@")
            if len(parts) == 2:
                local, domain = parts
                if len(local) <= 2:
                    masked_email = f"***@{domain}"
                else:
                    masked_email = f"{local[0]}***{local[-1]}@{domain}"

        device_file = None
        if self.acc_path:
            devices_dir = os.path.join(self.acc_path, "devices")
            if not os.path.exists(devices_dir):
                try:
                    os.makedirs(devices_dir)
                except Exception:
                    pass
            device_file = os.path.join(devices_dir, f"{self.id_device}.json")
            if os.path.exists(device_file):
                try:
                    with open(device_file, "r") as f:
                        saved_info = json.load(f)
                    saved_info["timestamp"] = int(time.time() * 1000)
                    saved_info["google_email"] = masked_email
                    return saved_info
                except Exception:
                    pass
                    
        rnd = random.Random(self.id_device)
        ver = rnd.choice(["11", "12", "13"])
        sdk_map = {"11": 30, "12": 31, "13": 33}
        sdk_int = sdk_map.get(ver, 33)
        
        if self.device_mode == "real":
            real_devices = [
                {"brand": "samsung", "manufacturer": "samsung", "model": "SM-S918B", "device": "dm3q", "product": "dm3qnsxx", "board": "msmnile", "hardware": "qcom"},
                {"brand": "google", "manufacturer": "Google", "model": "Pixel 7 Pro", "device": "cheetah", "product": "cheetah", "board": "cheetah", "hardware": "cheetah"},
                {"brand": "xiaomi", "manufacturer": "Xiaomi", "model": "2210132G", "device": "nuwa", "product": "nuwa", "board": "nuwa", "hardware": "qcom"},
                {"brand": "OPPO", "manufacturer": "OPPO", "model": "CPH2239", "device": "OP4F7D", "product": "OP4F7D", "board": "mt6765", "hardware": "mt6765"},
                {"brand": "vivo", "manufacturer": "vivo", "model": "V2027", "device": "2027", "product": "2027", "board": "mt6765", "hardware": "mt6765"}
            ]
            hw = rnd.choice(real_devices)
            build_prefix = {"11": "RP1A", "12": "SP1A", "13": "TP1A"}.get(ver, "TP1A")
            build_id = f"{build_prefix}.{rnd.randint(200000, 240000)}.{rnd.randint(1, 999):03d}"
            incremental = str(int(time.time() * 1000) - rnd.randint(10000000000, 50000000000))
            fingerprint = f"{hw['brand']}/{hw['product']}/{hw['device']}:{ver}/{build_id}/{incremental}:user/release-keys"
            tags = "release-keys"
            type_str = "user"
            user_str = "root" if rnd.choice([True, False]) else "android-build"
            host_str = f"phy-u{rnd.randint(10, 99)}-jn-{rnd.randint(10, 99)}-{rnd.randint(10, 99)}" if hw['brand'] == 'OPPO' else f"host-{rnd.randint(1000, 9999)}"
        else:
            emulators_hw = {
                "bluestacks": {"brand": "samsung", "manufacturer": "samsung", "model": "SM-S918B", "device": "dm3q", "product": "dm3qnsxx", "board": "msmnile", "hardware": "qcom"},
                "waydroid": {"brand": "waydroid", "manufacturer": "Waydroid", "model": "WayDroid x86_64 Device", "device": "waydroid_x86_64", "product": "lineage_waydroid_x86_64", "board": "unknown", "hardware": "waydroid_x86_64"},
                "nox": {"brand": "google", "manufacturer": "Google", "model": "Pixel 7 Pro", "device": "cheetah", "product": "cheetah", "board": "cheetah", "hardware": "cheetah"},
                "memu": {"brand": "xiaomi", "manufacturer": "Xiaomi", "model": "2210132G", "device": "nuwa", "product": "nuwa", "board": "nuwa", "hardware": "qcom"},
                "genymotion": {"brand": "samsung", "manufacturer": "samsung", "model": "SM-G991B", "device": "o1s", "product": "o1sxq", "board": "exynos2100", "hardware": "exynos2100"}
            }
            hw = emulators_hw.get(self.emu_type, emulators_hw["bluestacks"])
            
            if self.emu_type == "waydroid":
                build_id = f"eng.aleast.{rnd.randint(20250000, 20260403)}.{rnd.randint(100000, 999999)}"
                incremental = build_id
                fingerprint = f"{hw['brand']}/{hw['product']}/{hw['device']}:{ver}/TQ3A.{rnd.randint(230000, 230999)}.001/{build_id}:userdebug/test-keys"
                tags = "test-keys"
                type_str = "userdebug"
                user_str = "aleasto"
                host_str = "zero"
            else:
                build_prefix = {"11": "RP1A", "12": "SP1A", "13": "TP1A"}.get(ver, "TP1A")
                build_id = f"{build_prefix}.{rnd.randint(200000, 240000)}.{rnd.randint(1, 999):03d}"
                incremental = str(rnd.randint(1000000, 9999999))
                fingerprint = f"{hw['brand']}/{hw['product']}/{hw['device']}:{ver}/{build_id}/{incremental}:user/release-keys"
                tags = "release-keys"
                type_str = "user"
                user_str = "android-build"
                host_str = f"host-{rnd.randint(1000, 9999)}"

        if self.device_mode == "real":
            device_type_val = "secure_device"
            is_secure_val = True
            
            payload = {
                "device_id": self.id_device,
                "device_type": device_type_val,
                "is_emulator": False,
                "is_secure": is_secure_val,
                "timestamp": int(time.time() * 1000),
                "google_email": masked_email,
                "hardware": {
                    "brand": hw["brand"],
                    "model": hw["model"],
                    "device": hw["device"],
                    "hardware": hw.get("hardware", "unknown"),
                    "manufacturer": hw["manufacturer"],
                    "product": hw["product"],
                    "board": hw["board"]
                },
                "os": {
                    "sdk_int": sdk_int,
                    "release": ver,
                    "incremental": incremental
                },
                "display": {
                    "width_px": rnd.choice([1080, 720]),
                    "height_px": rnd.choice([2400, 1600, 1448]),
                    "density_dpi": rnd.choice([320, 440, 480]),
                    "density": rnd.choice([2.0, 2.75, 3.0])
                },
                "locale": {
                    "language": "in",
                    "country": "ID",
                    "variant": ""
                },
                "timezone": "Asia/Jakarta",
                "extra": {
                    "fingerprint": fingerprint,
                    "tags": tags,
                    "type": type_str,
                    "user": user_str,
                    "host": host_str
                }
            }
            if device_file:
                try:
                    with open(device_file, "w") as f:
                        json.dump(payload, f, indent=4)
                except Exception:
                    pass
            return payload

        build_props_emu = False
        hardware_emu = False
        files_emu = False
        masking_detected = not (build_props_emu or hardware_emu)
        
        emulator_details = {
            "build_properties": build_props_emu,
            "hardware": hardware_emu,
            "files": files_emu,
            "memu": self.emu_type == "memu",
            "bluestacks": self.emu_type == "bluestacks",
            "nox": self.emu_type == "nox",
            "genymotion": self.emu_type == "genymotion",
            "google_emulator": False,
            "masking_detected": masking_detected
        }
        
        masking_evidence = {}
        if masking_detected:
            if hw["brand"].lower() == "google" and hw["manufacturer"].lower() == "google":
                if hw["board"].lower() == "intel":
                    masking_evidence["intel_hardware"] = "Google устройство с Intel процессором маловероятно"
                if hw["model"] == "G011A" or hw["device"] == "G011A":
                    masking_evidence["suspicious_model"] = "Модель G011A характерна для эмуляторов"
                if "mv-dev" in fingerprint:
                    masking_evidence["mv_dev_fingerprint"] = "Fingerprint содержит mv-dev (Microvirt)"
            if hw["board"].lower() == "intel" and hw["brand"].lower() != "intel":
                masking_evidence["hardware_brand_mismatch"] = "Intel hardware с не-Intel брендом"
        
        payload = {
            "device_id": self.id_device,
            "device_type": "emulator",
            "is_emulator": True,
            "is_secure": False,
            "timestamp": int(time.time() * 1000),
            "emulator_type": self.emu_type,
            "emulator_details": emulator_details,
            "google_email": masked_email,
            "hardware": {
                "brand": hw["brand"],
                "model": hw["model"],
                "device": hw["device"],
                "hardware": hw.get("hardware", "unknown") if self.emu_type != "waydroid" else "unknown",
                "manufacturer": hw["manufacturer"],
                "product": hw["product"],
                "board": hw["board"]
            },
            "os": {
                "sdk_int": sdk_int,
                "release": ver,
                "incremental": incremental
            },
            "display": {
                "width_px": rnd.choice([1080, 720]),
                "height_px": rnd.choice([2400, 1600, 1448]),
                "density_dpi": rnd.choice([320, 440, 480]),
                "density": rnd.choice([2.0, 2.75, 3.0])
            },
            "locale": {
                "language": "in",
                "country": "ID",
                "variant": ""
            },
            "timezone": "Asia/Jakarta",
            "extra": {
                "fingerprint": fingerprint,
                "tags": tags,
                "type": type_str,
                "user": user_str,
                "host": host_str
            },
            "masking_detected": masking_detected,
            "masking_evidence": masking_evidence
        }
        if device_file:
            try:
                with open(device_file, "w") as f:
                    json.dump(payload, f, indent=4)
            except Exception:
                pass
        return payload

    def request(self, method, url, **kwargs):
        retries = 0
        while retries < 3:
            wait_for_internet()
            try:
                if method.lower() == 'get':
                    return self.session.get(url, timeout=10, **kwargs)
                elif method.lower() == 'post':
                    return self.session.post(url, timeout=10, **kwargs)
            except requests.RequestException as e:
                retries += 1
                wait_for_internet()
                print_error(f"[-] Koneksi gagal/timeout, percobaan {retries}/3...")
                time.sleep(2)
        raise Exception("Gagal terhubung ke server setelah 3 kali percobaan.")

    def login(self):
        try:
            res = self.request('get', "https://seo-fast.bz/webapp/?pg=login")
            match = RE_HASH_AJAX.search(res.text)
            if match:
                self.hash_ajax = match.group(1)
            else:
                print_error("[-] Gagal mengambil hash login.")
                return False
                
            payload = {
                "login": self.email,
                "password": self.password,
                "hash": self.hash_ajax,
                "ajax_func": "login"
            }
            
            res_login = self.request('post', "https://seo-fast.bz/webapp/ajax/ajax_login.php", data=payload, headers=self.headers)
            
            if "location.replace('?pg=job')" in res_login.text:
                self.get_session_info()
                return True
            else:
                print_error(f"[-] Login Gagal: {res_login.text}")
                return False
        except Exception as e:
            print_error(f"[-] Error saat login: {e}")
            return False

    def get_session_info(self):
        try:
            res = self.request('get', "https://seo-fast.bz/webapp/?pg=job")
            match = RE_HASH_AJAX.search(res.text)
            if match:
                self.hash_ajax = match.group(1)
                self.headers['Content-Type'] = "application/json"
        except Exception as e:
            print_error(f"[-] Error get_session_info: {e}")

    def get_task(self):
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
                elif "Google" in str(data.get("mess", "")):
                    print_error("[!] Google email terdeteksi, membuat device baru...")
                    return "RESTART"
                else:
                    print_error(f"[-] Gagal ambil tugas ({self.id_device})({res.status_code}): {res.json()}")
            else:
                print_error(f"[-] Gagal ambil tugas ({self.id_device})({res.status_code}): {res.text}")
        except Exception as e:
            print_error(f"[-] Error get_task: {e}")
        return None

    def complete_youtube_task(self, task_url):
        try:
            parsed = urlparse(task_url)
            params = parse_qs(parsed.query)
            
            hash_val = params.get('hash', [None])[0]
            report_id = params.get('report_id', [None])[0]
            task_id = params.get('task_id', [None])[0]
            timer = params.get('timer', [15])[0]
            video_id = params.get('video_id', [None])[0]
            
            if not all([hash_val, report_id, task_id, video_id]):
                print_error("[-] Parameter Youtube tidak lengkap.")
                return False
                
            time.sleep(int(timer) + 2)
            
            report_url = "https://seo-fast.bz/statica/ajax/ajax-youtube-external.php"
            payload = {
                "hash": hash_val,
                "report_id": report_id,
                "task_id": task_id,
                "timer": timer,
                "player_time": float(timer) - random.uniform(0.1, 0.9),
                "video_id": video_id,
                "stage": "1",
                "player_state": "1",
                "duration": random.randint(300, 900),
                "quality": "hd1080",
                "button": "",
                "ismuted": "100",
                "time_v": int(timer) + 1
            }
            
            headers = self.headers.copy()
            headers['Content-Type'] = "application/x-www-form-urlencoded; charset=UTF-8"
            
            res = self.request('post', report_url, data=payload, headers=headers)
            return "ok" in res.text.lower()
        except Exception as e:
            print_error(f"[-] Error complete_youtube_task: {e}")
        return False

    def complete_task(self, id_status):
        device_info = self.device_info.copy()
        
        for attempt in range(5):
            device_info['timestamp'] = int(time.time() * 1000)
            
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
                    update_balance_progress(balance)
                    return True
                else:
                    if attempt < 4:
                        time.sleep(0.5)
                    else:
                        print_error(f"[-] Gagal selesaikan tugas ({res.status_code}): {res.text}")
            except Exception as e:
                if attempt < 4:
                    time.sleep(0.5)
                else:
                    print_error(f"[-] Error complete_task: {e}")
        return False

    def update_data(self):
        url = "https://seo-fast.bz/webapp/ajax/ajax_data.php"
        
        device_info = self.device_info.copy()
        device_info['timestamp'] = int(time.time() * 1000)
        
        payload = {
            "ajax_func": "up_data",
            "hash_ajax": self.hash_ajax,
            "id_device": self.id_device,
            "email": self.device_email,
            "os_version": device_info['os']['release'],
            "screen_resolution": "1080x2400",
            "locale_language": "ru",
            "locale_country": "RU",
            "data_json": json.dumps(device_info)
        }
        
        try:
            res = self.request('post', url, json=payload, headers=self.headers)
            return True
        except Exception as e:
            print_error(f"[-] Error update_data: {e}")
        return False

    def run(self):
        if not self.login():
            return
            
        self.update_data()
        
        while not stop_event.is_set():
            task = self.get_task()
            if task == "RESTART":
                return "RESTART"
            if task:
                id_status = task.get("id_status")
                timer = int(task.get("timer", 15))
                url = task.get("url")
                
                is_external_youtube = ("video_id=" in url and "hash=" in url)
                
                if is_external_youtube:
                    if self.complete_youtube_task(url):
                        self.complete_task(id_status)
                else:
                    time.sleep(timer + 1)
                    self.complete_task(id_status)
            else:
                time.sleep(60)

if __name__ == "__main__":
    os.system('clear' if os.name == 'posix' else 'cls')
    print("=== seo-fast.bz AUTO BOT SINGLE DEVICE (NO PROXY) ===")
    
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
    
    mode_input = input("[?] Mode Device (1 = Emulator, 2 = Real Device) [default: 1]: ").strip()
    device_mode = "real" if mode_input == "2" else "emulator"
    
    identity_file = os.path.join(acc_path, "device_identity.txt")
    
    def start_bot():
        print("\n[+] Menjalankan bot (Single Device, Tanpa Proxy)... Progress bar akan muncul setelah tugas pertama selesai.")
        while not stop_event.is_set():
            g, dev_id, emu = None, None, None
            if os.path.exists(identity_file):
                with open(identity_file, "r") as f:
                    content = f.read().strip()
                    if content:
                        parts = content.split("|")
                        if len(parts) >= 3:
                            g, dev_id, emu = parts[0], parts[1], parts[2]
            
            if not dev_id:
                g = generate_russian_email()
                if device_mode == "emulator":
                    emu = random.choice(["bluestacks", "waydroid", "nox", "memu", "genymotion"])
                    dev_id = f"{emu}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
                else:
                    emu = "None"
                    dev_id = f"secure_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
                with open(identity_file, "w") as f:
                    f.write(f"{g}|{dev_id}|{emu}")
                    
            bot = SeoFastBot(main_email, main_password, proxy=None, device_mode=device_mode, device_email=g, id_device=dev_id, emu_type=emu, acc_path=acc_path)
            res = bot.run()
            if res == "RESTART":
                print_error("[*] Meregenerasi device baru...")
                if os.path.exists(identity_file):
                    os.remove(identity_file)
                time.sleep(1)
                continue
            break
            
    start_bot()
    
    print("\n\n" + r"""
  _______    _____  _  __  _____   ____  _   _ ______ _ 
 |__   __|  / ____|| |/ / |  __ \ / __ \| \ | |  ____| |
    | |    | (___  | ' /  | |  | | |  | |  \| | |__  | |
    | |     \___ \ |  <   | |  | | |  | | . ` |  __| | |
    | |     ____) || . \  | |__| | |__| | |\  | |____|_|
    |_|    |_____/ |_|\_\ |_____/ \____/|_| \_|______(_)
                                                        
""")
    print(f"\n[+] TUGAS HABIS atau SALDO MENCAPAI TARGET (500). Script telah berhenti.\n")
