import base64
import json
import math
import os
import urllib.request

def fetch_and_decode(url):
    """دریافت و دکود کردن محتوای لینک ساب"""
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8').strip()
            # بررسی اینکه آیا محتوا Base64 است یا خیر
            try:
                decoded = base64.b64decode(content).decode('utf-8')
                return decoded.splitlines()
            except Exception:
                return content.splitlines()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def is_valid_config(line):
    """بررسی معتبر بودن لینک کانفیگ و تمام پروتکل‌ها"""
    protocols = (
        'vless://', 'vmess://', 'trojan://', 'ss://', 
        'ssr://', 'hysteria2://', 'hy2://', 'tuic://', 'socks://', 'http://'
    )
    return line.strip().startswith(protocols)

def main():
    # خواندن لینک‌های ساب‌اسکریپشن ورودی از سکرت گیت‌هاب
    raw_urls = os.environ.get("SUB_URLS", "")
    urls = [u.strip() for u in raw_urls.splitlines() if u.strip()]

    if not urls:
        print("No URLs found in SUB_URLS secret!")
        return

    all_configs = []

    # ۱. جمع‌آوری کانفیگ‌ها از تمامی منابع
    for url in urls:
        print(f"Fetching from: {url}")
        lines = fetch_and_decode(url)
        for line in lines:
            line = line.strip()
            if is_valid_config(line) and line not in all_configs:
                all_configs.append(line)

    print(f"Total valid configs found: {len(all_configs)}")

    if not all_configs:
        print("No valid configs fetched.")
        return

    # ۲. ذخیره تمام کانفیگ‌های متنی در فایل javidsub
    with open("javidsub", "w", encoding="utf-8") as f:
        f.write("\n".join(all_configs))

    # ۳. تقسیم‌بندی به بسته‌های ۱۰۰۰ تایی و ذخیره به صورت JSON
    chunk_size = 1000
    total_chunks = math.ceil(len(all_configs) / chunk_size)
    
    os.makedirs("json_configs", exist_ok=True)

    for i in range(total_chunks):
        chunk = all_configs[i * chunk_size : (i + 1) * chunk_size]
        json_data = {
            "chunk_index": i + 1,
            "total_configs": len(chunk),
            "configs": chunk
        }
        file_path = f"json_configs/configs_{i + 1}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

    # ۴. ساخت فایل ساب نهایی (Base64) برای نرم‌افزارها
    b64_content = base64.b64encode("\n".join(all_configs).encode("utf-8")).decode("utf-8")
    with open("final_sub.txt", "w", encoding="utf-8") as f:
        f.write(b64_content)

if __name__ == "__main__":
    main()
