"""
================================================================================
🚀 WeWill Restream - Google Colab Minimal Bootstrap Loader (v2.0)
================================================================================
لودر سبک و عمومی جهت اجرا در نوت‌بوک Google Colab:
- بررسی اصالت پلتفرم Google Colab
- پایش هوشمند سکرت WW_RS_KEY (هر ۱۰ ثانیه تا ۶۰ ثانیه مهلت)
- دریافت باینری نیتیو سورس‌بسته از GitHub Releases و اجرا مستقیماً در حافظه RAM
- خودتخریبی و پاکسازی رم به محض پایان اجرا
================================================================================
"""

import os
import sys
import time
import argparse
import subprocess
import shutil
import urllib.request

# Ensure UTF-8 output and instant unbuffered terminal printing
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

# GitHub Sources for compiled worker
GITHUB_REPO = "WeWillClub/wewill-restream"
RELEASE_BINARY_URLS = [
    f"https://github.com/{GITHUB_REPO}/releases/download/beta/wewill_worker.bin",
    f"https://github.com/{GITHUB_REPO}/releases/latest/download/wewill_worker.bin"
]
RAW_FALLBACK_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/wewill_worker.py"
DEFAULT_SERVER = "https://api.restream.wewill.club"

def resolve_executable_ram_dir():
    for candidate in ["/tmp/wewill", "/content/.wewill", "/dev/shm/wewill"]:
        try:
            os.makedirs(candidate, exist_ok=True)
            test_file = os.path.join(candidate, ".exec_check")
            with open(test_file, "wb") as f:
                f.write(b"#!/bin/sh\nexit 0\n")
            os.chmod(test_file, 0o755)
            res = subprocess.run([test_file], capture_output=True, timeout=1)
            try: os.remove(test_file)
            except Exception: pass
            if res.returncode == 0:
                return candidate
        except Exception:
            pass
    return "/tmp/wewill"

RAM_DIR = resolve_executable_ram_dir()


def wipe_ram_and_exit(code=1):
    try:
        if os.path.exists(RAM_DIR):
            for root, _, files in os.walk(RAM_DIR):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                        with open(fp, "wb") as fl:
                            fl.write(b"\x00" * min(sz, 65536))
                        os.remove(fp)
                    except Exception: pass
            shutil.rmtree(RAM_DIR, ignore_errors=True)
    except Exception: pass
    sys.exit(code)


def verify_colab_platform(dev_mode=False):
    if dev_mode:
        print("🛡️ [Dev Mode] اجرای محلی تایید شد.")
        return True

    has_colab_dir = os.path.exists("/opt/colab") or os.path.exists("/content")
    has_colab_env = "COLAB_RELEASE_TAG" in os.environ or "COLAB_BACKEND_VERSION" in os.environ

    if not (has_colab_dir or has_colab_env):
        print("\n" + "!" * 68)
        print("❌ [Security Alert] اجرای غیرمجاز.")
        print("⚠️ موتور WeWill Restream منحصراً بر روی Google Colab اجرا می‌شود.")
        print("!" * 68 + "\n")
        wipe_ram_and_exit(1)

    return True


def poll_colab_secrets(cli_key=None, max_attempts=6, poll_interval=10):
    if cli_key and str(cli_key).strip().startswith("ww_rs_"):
        return str(cli_key).strip()

    print("\n" + "=" * 68)
    print("🔍 در حال پایش سکرت WW_RS_KEY در Google Colab...")
    print("=" * 68)

    for attempt in range(1, max_attempts + 1):
        try:
            from google.colab import userdata
            candidate_names = [
                "WW_RS_KEY", "WW_RS_Key", "WW_RS_key", "ww_rs_key",
                "WW_RS_K", "WW_RS_k", "WW_RS", "ww_rs",
                "WEWILL_RESTREAM_KEY", "wewill_restream_key",
                "RESTREAM_KEY", "restream_key", "API_KEY", "api_key"
            ]
            for s_name in candidate_names:
                try:
                    val = userdata.get(s_name)
                    if val and str(val).strip().startswith("ww_rs_"):
                        key = str(val).strip()
                        print(f"🔑 کلید اتصال با موفقیت از بخش Colab Secrets ({s_name}) دریافت شد.")
                        return key
                except Exception as ex:
                    ex_msg = str(ex).lower()
                    if "notebookaccess" in ex_msg:
                        print(f"⚠️ سکرت {s_name} یافت شد اما لطفاً روی دکمه Grant Access در پاپ‌آپ کلَب کلیک کنید.")
        except Exception:
            pass

        env_val = (os.environ.get("WW_RS_KEY") or os.environ.get("WEWILL_RESTREAM_KEY") or "").strip()
        if env_val.startswith("ww_rs_"):
            return env_val

        if attempt == 1:
            print("💡 کلید اتصال در سکرت‌های این نوت‌بوک یافت نشد.")
            print("   لطفاً در نوار ابزار سمت چپ گوگل کلَب روی آیکون کلید 🔑 (Secrets) بزنید:")
            print("   - نام سکرت: WW_RS_KEY")
            print("   - مقدار: کلید اختصاصی شما از داشبورد وی‌ویل (شروع با ww_rs_...)")
            print("   - تیک گزینه «Notebook access» را فعال کنید.")
            print("--------------------------------------------------------------------")

        if attempt < max_attempts:
            print(f"[{time.strftime('%H:%M:%S')}] ⏳ در انتظار ثبت سکرت در کلَب (تلاش {attempt} از {max_attempts} • بررسی مجدد در {poll_interval} ثانیه)...")
            time.sleep(poll_interval)
        else:
            print(f"[{time.strftime('%H:%M:%S')}] ⏱️ مهلت ۶۰ ثانیه‌ای ثبت سکرت به پایان رسید.")

    try:
        user_in = input("لطفاً کلید ورکر (ww_rs_...) را وارد کنید: ").strip()
        if user_in.startswith("ww_rs_"):
            return user_in
    except Exception: pass

    print("❌ کلید معتبر دریافت نشد.")
    wipe_ram_and_exit(1)


def fetch_worker_into_ram():
    os.makedirs(RAM_DIR, exist_ok=True)
    bin_target = os.path.join(RAM_DIR, "wewill_worker.bin")
    py_target = os.path.join(RAM_DIR, "wewill_worker.py")

    # 1. Try local worker if running in dev or same repo
    local_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "wewill_worker.py"))
    if os.path.exists(local_script):
        shutil.copy2(local_script, py_target)
        return py_target, False

    # 2. Download pre-compiled binary from GitHub Releases (Primary for closed-source production)
    print("⏳ در حال دریافت اطلاعات...")
    for bin_url in RELEASE_BINARY_URLS:
        try:
            req = urllib.request.Request(bin_url, headers={'User-Agent': 'WeWill-Loader/2.0'})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = resp.read()
            if len(data) > 50000:
                with open(bin_target, "wb") as bf:
                    bf.write(data)
                os.chmod(bin_target, 0o755)
                print("✅ باینری سورس‌بسته با موفقیت در رم بارگذاری شد.")
                return bin_target, True
        except Exception:
            pass

    # 3. Fallback: Fetch raw worker script if binary release is unavailable
    try:
        req = urllib.request.Request(RAW_FALLBACK_URL, headers={'User-Agent': 'WeWill-Loader/2.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        if len(data) > 1000:
            with open(py_target, "wb") as out:
                out.write(data)
            print("✅ اطلاعات بارگذاری شد.")
            return py_target, False
    except Exception:
        pass

    print("❌ خطا در دریافت فایل‌های هسته از گیت‌هاب.")
    wipe_ram_and_exit(1)


def main():
    parser = argparse.ArgumentParser(description="WeWill Restream Bootstrap Loader")
    parser.add_argument("--key", type=str, default="", help="Worker Key (ww_rs_...)")
    parser.add_argument("--server", type=str, default=DEFAULT_SERVER, help="WeWill Central Server URL")
    parser.add_argument("--dev", action="store_true", help="Development mode")
    args = parser.parse_args()

    print("\n" + "=" * 68)
    print("🚀 WeWill Restream - آغاز راه‌اندازی موتور ابری استریم")
    print("=" * 68)

    # 1. Verify Platform
    verify_colab_platform(dev_mode=args.dev)

    # 2. Poll Secrets
    worker_key = poll_colab_secrets(cli_key=args.key)

    # 3. Load Engine into RAM
    worker_executable, is_binary = fetch_worker_into_ram()

    # 4. Launch Core in RAM
    if is_binary:
        cmd = [worker_executable, "--key", worker_key, "--server", args.server]
    else:
        cmd = [sys.executable, "-u", worker_executable, "--key", worker_key, "--server", args.server]

    if args.dev:
        cmd.append("--dev")

    sub_env = os.environ.copy()
    sub_env["PYTHONUNBUFFERED"] = "1"

    try:
        proc = subprocess.run(cmd, cwd=RAM_DIR, env=sub_env)
        wipe_ram_and_exit(proc.returncode)
    except KeyboardInterrupt:
        print("\n🛑 خروج توسط کاربر.")
        wipe_ram_and_exit(0)
    except Exception as e:
        print(f"\n❌ خطای اجرا: {e}")
        wipe_ram_and_exit(1)


if __name__ == "__main__":
    main()
