"""
================================================================================
🚀 WeWill Restream - Cloud Minimal Bootstrap Loader (v2.1)
================================================================================
لودر سبک و عمومی جهت اجرا در نوت‌بوک Google Colab و Deepnote:
- بررسی اصالت پلتفرم ابری (Google Colab / Deepnote)
- پشتیبانی از کلید مستقیم در اسکریپت، آرگومان خط فرمان، سکرت و متغیرهای محیطی
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

# ==============================================================================
# 🔑 پیکربندی کلید ورکر (اختیاری: در صورت تمایل کلید خود را مستقیماً اینجا وارد کنید)
# Optional: Hardcode your worker key here (e.g. WORKER_KEY = "ww_rs_...")
# ==============================================================================
WORKER_KEY = ""

def resolve_executable_ram_dir():
    for candidate in ["/tmp/wewill", "/dev/shm/wewill", "/content/.wewill", "/work/.wewill"]:
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


def detect_cloud_platform():
    # 1. بررسی پلتفرم Deepnote
    is_deepnote = (
        "DEEPNOTE_PROJECT_ID" in os.environ
        or "DEEPNOTE_WORKSPACE_ID" in os.environ
        or "DEEPNOTE_ENV" in os.environ
        or any(k.startswith("DEEPNOTE_") for k in os.environ)
        or (os.name == "posix" and os.path.exists("/work") and (os.path.exists("/root/.deepnote") or os.path.exists("/init")))
    )
    if is_deepnote:
        return "Deepnote", True

    # 2. بررسی پلتفرم Google Colab
    is_colab = (
        "COLAB_RELEASE_TAG" in os.environ
        or "COLAB_BACKEND_VERSION" in os.environ
        or "COLAB_GPU" in os.environ
        or (os.name == "posix" and (os.path.exists("/opt/colab") or os.path.exists("/content")))
    )
    if is_colab:
        return "Google Colab", True

    return "Unknown", False


def verify_cloud_platform(dev_mode=False):
    if dev_mode:
        print("🛡️ [Dev Mode] اجرای محلی تایید شد.")
        return "Local Dev"

    platform_name, is_valid = detect_cloud_platform()
    if is_valid:
        print(f"☁️ پلتفرم تایید شد: {platform_name}")
        return platform_name

    print("\n" + "!" * 68)
    print("❌ [Security Alert] اجرای غیرمجاز.")
    print("⚠️ موتور WeWill Restream منحصراً بر روی Google Colab و Deepnote اجرا می‌شود.")
    print("!" * 68 + "\n")
    wipe_ram_and_exit(1)


def resolve_worker_key(cli_key=None, platform_name="Google Colab", max_attempts=6, poll_interval=10):
    # 1. اولویت نخست: کلید ارسال‌شده در دستور استارت (--key)
    clean_cli_key = str(cli_key or "").strip().strip("'\"")
    if clean_cli_key.startswith("ww_rs_"):
        print("🔑 کلید اتصال از دستور استارت دریافت شد.")
        return clean_cli_key

    # 2. بررسی وجود کلید اختیاری در اسکریپت (در صورت تنظیم)
    if WORKER_KEY and str(WORKER_KEY).strip().startswith("ww_rs_"):
        key = str(WORKER_KEY).strip()
        print("🔑 کلید اتصال از تنظیمات اسکریپت بارگذاری شد.")
        return key

    candidate_names = [
        "WW_RS_KEY", "WW_RS_Key", "ww_rs_key",
        "WW_RS_K", "WW_RS_k", "WW_RS", "ww_rs",
        "WEWILL_RESTREAM_KEY", "wewill_restream_key",
        "RESTREAM_KEY", "restream_key", "API_KEY", "api_key"
    ]

    # 3. اولویت دوم: متغیرهای محیطی سیستم / Deepnote Environment Variables
    for env_name in candidate_names:
        env_val = os.environ.get(env_name, "").strip()
        if env_val.startswith("ww_rs_"):
            print(f"🔑 کلید اتصال با موفقیت از متغیر محیطی ({env_name}) دریافت شد.")
            return env_val

    # 4. اولویت سوم: بررسی بلافاصله سکرت‌های Google Colab (در صورت اجرا روی کلَب)
    if platform_name == "Google Colab":
        try:
            # pyrefly: ignore [missing-import]
            from google.colab import userdata
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

    # ۵. در صورتی که کلید در دستور استارت یا سکرت‌ها یافت نشد، فرآیند پایش و راهنمایی شروع می‌شود
    print("\n" + "=" * 68)
    print(f"🔍 در حال پایش کلید اتصال WeWill در {platform_name}...")
    print("=" * 68)

    for attempt in range(1, max_attempts + 1):
        if platform_name == "Google Colab":
            try:
                # pyrefly: ignore [missing-import]
                from google.colab import userdata
                for s_name in candidate_names:
                    try:
                        val = userdata.get(s_name)
                        if val and str(val).strip().startswith("ww_rs_"):
                            key = str(val).strip()
                            print(f"🔑 کلید اتصال با موفقیت از بخش Colab Secrets ({s_name}) دریافت شد.")
                            return key
                    except Exception:
                        pass
            except Exception:
                pass

        for env_name in candidate_names:
            env_val = os.environ.get(env_name, "").strip()
            if env_val.startswith("ww_rs_"):
                print(f"🔑 کلید اتصال با موفقیت از متغیر محیطی ({env_name}) دریافت شد.")
                return env_val

        if attempt == 1:
            if platform_name == "Deepnote":
                print("💡 کلید اتصال در دستور استارت یا تنظیمات این پروژه یافت نشد.")
                print("   لطفاً کلید اختصاصی خود را به یکی از روش‌های زیر تنظیم کنید:")
                print("   ۱. ارسال کلید در دستور استارت: --key ww_rs_YOUR_KEY")
                print("   ۲. در منوی سمت چپ Deepnote وارد بخش Integrations -> Environment variables شوید:")
                print("      - نام متغیر: WW_RS_KEY")
                print("      - مقدار: کلید اختصاصی شما از داشبورد وی‌ویل (شروع با ww_rs_...)")
                print("--------------------------------------------------------------------")
            else:
                print("💡 کلید اتصال در دستور استارت یا سکرت‌های این نوت‌بوک یافت نشد.")
                print("   لطفاً کلید اختصاصی خود را به یکی از روش‌های زیر تنظیم کنید:")
                print("   ۱. ارسال کلید در دستور استارت: --key ww_rs_YOUR_KEY")
                print("   ۲. در نوار ابزار سمت چپ گوگل کلَب روی آیکون کلید 🔑 (Secrets) بزنید:")
                print("      - نام سکرت: WW_RS_KEY")
                print("      - مقدار: کلید اختصاصی شما از داشبورد وی‌ویل (شروع با ww_rs_...)")
                print("      - تیک گزینه «Notebook access» را فعال کنید.")
                print("--------------------------------------------------------------------")

        if attempt < max_attempts:
            print(f"[{time.strftime('%H:%M:%S')}] ⏳ در انتظار ثبت کلید (تلاش {attempt} از {max_attempts} • بررسی مجدد در {poll_interval} ثانیه)...")
            time.sleep(poll_interval)
        else:
            print(f"[{time.strftime('%H:%M:%S')}] ⏱️ مهلت ۶۰ ثانیه‌ای بررسی کلید به پایان رسید.")

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
                print("✅ اطلاعات مورد نیاز بارگذاری شد.")
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
    print("🚀 WeWill Restream - شروع پردازش سرور ری استریم")
    print("=" * 68)

    # 1. Verify Platform
    detected_platform = verify_cloud_platform(dev_mode=args.dev)

    # 2. Resolve Worker Key
    worker_key = resolve_worker_key(cli_key=args.key, platform_name=detected_platform)

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
