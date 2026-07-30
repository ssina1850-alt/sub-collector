import base64
import json
import math
import os
import urllib.request
from urllib.parse import parse_qs, unquote, urlparse


def fetch_and_decode(url):
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8').strip()
            try:
                decoded = base64.b64decode(content).decode('utf-8')
                return decoded.splitlines()
            except Exception:
                return content.splitlines()
    except Exception as e:
        print(f'Error fetching {url}: {e}')
        return []


def parse_vless_to_outbound(vless_url, tag_name):
    try:
        parsed = urlparse(vless_url)
        if parsed.scheme != 'vless':
            return None

        uuid = parsed.username
        address = parsed.hostname
        port = parsed.port or 443
        params = parse_qs(parsed.query)

        network = params.get('type', ['tcp'])[0]
        security = params.get('security', ['none'])[0]
        path = unquote(params.get('path', ['/'])[0])
        host = params.get('host', [''])[0]
        sni = params.get('sni', [''])[0]
        fp = params.get('fp', ['chrome'])[0]
        alpn_raw = params.get('alpn', [''])[0]
        alpn = alpn_raw.split(',') if alpn_raw else []

        outbound = {
            'mux': {'concurrency': -1, 'enabled': False},
            'protocol': 'vless',
            'settings': {
                'vnext': [
                    {
                        'address': address,
                        'port': int(port),
                        'users': [{'encryption': 'none', 'id': uuid, 'level': 8}],
                    }
                ]
            },
            'streamSettings': {'network': network},
            'tag': tag_name,
        }

        if network == 'ws':
            ws_settings = {'headers': {}}
            if host:
                ws_settings['headers']['Host'] = host
            if path:
                ws_settings['path'] = path
            outbound['streamSettings']['wsSettings'] = ws_settings

        if security == 'tls':
            outbound['streamSettings']['security'] = 'tls'
            tls_settings = {'allowInsecure': False, 'show': False}
            if sni:
                tls_settings['serverName'] = sni
            if fp:
                tls_settings['fingerprint'] = fp
            if alpn:
                tls_settings['alpn'] = alpn
            outbound['streamSettings']['tlsSettings'] = tls_settings

        return outbound
    except Exception as e:
        return None


def generate_full_json_config(outbound_proxies, remark_name):
    """تولید یک کانفیگ کامل JSON"""
    base_config = {
        'dns': {
            'hosts': {
                'domain:googleapis.cn': 'googleapis.com',
                'dns.alidns.com': ['223.5.5.5', '223.6.6.6'],
                'one.one.one.one': ['1.1.1.1', '1.0.0.1'],
                'dns.google': ['8.8.8.8', '8.8.4.4'],
            },
            'servers': ['1.1.1.1'],
            'tag': 'dns-module',
        },
        'inbounds': [
            {
                'listen': '127.0.0.1',
                'port': 10808,
                'protocol': 'socks',
                'settings': {'auth': 'noauth', 'udp': True, 'userLevel': 8},
                'tag': 'socks',
            }
        ],
        'log': {'loglevel': 'warning'},
        'observatory': {
            'enableConcurrency': True,
            'probeInterval': '3m',
            'probeUrl': 'https://www.gstatic.com/generate_204',
            'subjectSelector': ['proxy-'],
        },
        'outbounds': [],
        'policy': {
            'levels': {
                '8': {
                    'connIdle': 300,
                    'downlinkOnly': 1,
                    'handshake': 4,
                    'uplinkOnly': 1,
                }
            }
        },
        'remarks': remark_name,
        'routing': {
            'balancers': [
                {
                    'selector': ['proxy-'],
                    'strategy': {'type': 'leastPing'},
                    'tag': 'proxy-round',
                }
            ],
            'rules': [
                {
                    'balancerTag': 'proxy-round',
                    'network': 'tcp,udp',
                    'type': 'field',
                }
            ],
        },
    }

    base_config['outbounds'].extend(outbound_proxies)
    base_config['outbounds'].append(
        {'protocol': 'freedom', 'settings': {'domainStrategy': 'UseIP'}, 'tag': 'direct'}
    )
    base_config['outbounds'].append(
        {'protocol': 'blackhole', 'settings': {'response': {'type': 'http'}}, 'tag': 'block'}
    )

    return base_config


def main():
    raw_urls = os.environ.get('SUB_URLS', '')
    urls = [u.strip() for u in raw_urls.splitlines() if u.strip()]

    if not urls:
        print('No URLs found!')
        return

    all_raw_configs = []
    for url in urls:
        lines = fetch_and_decode(url)
        for line in lines:
            line = line.strip()
            if line.startswith('vless://') and line not in all_raw_configs:
                all_raw_configs.append(line)

    all_outbounds = []
    for idx, link in enumerate(all_raw_configs, start=1):
        outbound = parse_vless_to_outbound(link, tag_name=f'proxy-{idx}')
        if outbound:
            all_outbounds.append(outbound)

    # تقسیم به بسته‌های ۱,۰۰۰ تایی
    chunk_size = 1000
    total_chunks = math.ceil(len(all_outbounds) / chunk_size)

    json_strings_list = []

    # ساخت ۵0 فایل JSON کامپکت شده (یا به تعداد چانک‌ها)
    for i in range(total_chunks):
        chunk = all_outbounds[i * chunk_size : (i + 1) * chunk_size]
        json_obj = generate_full_json_config(chunk, remark_name=f'javidsub Pack {i + 1}')

        # تبدیل به رشته JSON فشرده (بدون Space اضافی)
        compact_json = json.dumps(json_obj, ensure_ascii=False, separators=(',', ':'))
        json_strings_list.append(compact_json)

    # چسباندن همه JSONها با خط جدید
    combined_json_content = '\n'.join(json_strings_list)

    # کدگذاری Base64 کل خروجی
    encoded_sub = base64.b64encode(combined_json_content.encode('utf-8')).decode('utf-8')

    # ذخیره در final_sub.txt
    with open('final_sub.txt', 'w', encoding='utf-8') as f:
        f.write(encoded_sub)

    print(
        f'Successfully packed {len(json_strings_list)} JSON configs into single Base64 sub!'
    )


if __name__ == '__main__':
    main()
