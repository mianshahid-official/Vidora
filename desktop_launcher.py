import os
import sys
import time
import shutil
import subprocess
import threading
import urllib.request

APP_URL = "http://127.0.0.1:8000"
APP_TITLE = "OmniDownloader Pro"

def find_browser_app_executable():
    # Candidates in order of preference for standalone --app window
    candidates = [
        # Microsoft Edge (Installed on all Windows 10/11)
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        # Google Chrome
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        # Brave
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    
    for path in candidates:
        if os.path.exists(path):
            return path
            
    # Check PATH
    for name in ["msedge", "chrome", "brave"]:
        found = shutil.which(name)
        if found:
            return found
            
    return None

def wait_for_server(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False

def main():
    print("\n" + "=" * 60)
    print("  OmniDownloader Pro - Launching Desktop Application")
    print("=" * 60 + "\n")
    
    # 1. Start Server in Subprocess
    server_process = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    try:
        # 2. Wait for server to respond
        print("[*] Starting backend engine...")
        wait_for_server(APP_URL, timeout=8)
        
        # 3. Find desktop browser app executable
        browser_exe = find_browser_app_executable()
        
        if browser_exe:
            print(f"[*] Launching Desktop App Window via: {os.path.basename(browser_exe)}")
            # Launch in standalone --app mode (no browser address bar, no tabs, native window frame)
            cmd = [
                browser_exe,
                f"--app={APP_URL}",
                "--window-size=1300,880",
                "--window-position=80,40",
                "--disable-background-networking",
                f"--app-id=OmniDownloaderPro"
            ]
            app_proc = subprocess.Popen(cmd)
            app_proc.wait()
            print("[*] Desktop window closed. Shutting down OmniDownloader Pro...")
        else:
            print("[!] No Chromium browser found for --app mode. Opening in default browser...")
            import webbrowser
            webbrowser.open(APP_URL)
            server_process.wait()
            
    except KeyboardInterrupt:
        print("\n[*] Stopping application...")
    finally:
        # Cleanly terminate server
        if server_process.poll() is None:
            server_process.terminate()
            try:
                server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_process.kill()
        print("[✓] OmniDownloader Pro stopped.")

if __name__ == "__main__":
    main()
