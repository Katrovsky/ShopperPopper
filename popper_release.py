import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

GITHUB_API_URL = "https://api.github.com"
GITHUB_REPO = "Katrovsky/ShopperPopper"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def fetch_versions(url):
    response = requests.get(url)
    response.raise_for_status()
    
    root = ET.fromstring(response.content)
    namespace = {'ns': 'http://s3.amazonaws.com/doc/2006-03-01/'}
    contents = root.findall('ns:Contents', namespace)
    
    versions = []
    
    for content in contents:
        key = content.find('ns:Key', namespace).text
        last_modified_utc = content.find('ns:LastModified', namespace).text
        size_bytes = int(content.find('ns:Size', namespace).text)
        
        version = key.split('/')[-1].replace('shopper-', '').replace('.apk', '')
        last_modified_dt = datetime.fromisoformat(last_modified_utc.replace('Z', '+00:00'))
        last_modified_str = last_modified_dt.strftime('%d.%m.%y %H:%M:%S')
        size_mb = round(size_bytes / (1024 * 1024), 1)
        download_url = url + key
        
        versions.append({
            'version': version,
            'last_modified': last_modified_str,
            'size': size_mb,
            'url': download_url
        })
    
    versions.sort(key=lambda v: list(map(int, v['version'].split('.'))))
    return versions

def download(version_info):
    filename = f"Shopper_{version_info['version']}.apk"
    file_path = os.path.join(os.getcwd(), filename)

    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            response = requests.get(version_info['url'], stream=True)
            response.raise_for_status()
            
            for data in response.iter_content(1024):
                f.write(data)

    return file_path

def get_existing_releases():
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(f"{GITHUB_API_URL}/repos/{GITHUB_REPO}/releases", headers=headers)
    response.raise_for_status()
    releases = response.json()

    return [release['tag_name'].lstrip('v') for release in releases]

def create_github_release(version_info, asset_name):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    data = {
        "tag_name": f"v{version_info['version']}",
        "name": f"Shopper {version_info['version']}",
        "body": f"Версия: {version_info['version']}\nПоследнее изменение: {version_info['last_modified']}\nРазмер: {version_info['size']} MB",
        "draft": False,
        "prerelease": False
    }

    response = requests.post(f"{GITHUB_API_URL}/repos/{GITHUB_REPO}/releases", json=data, headers=headers)
    response.raise_for_status()
    release = response.json()

    upload_url = release["upload_url"].replace("{?name,label}", f"?name={asset_name}")
    return upload_url

def upload_asset_to_release(upload_url, file_path):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/vnd.android.package-archive"
    }

    with open(file_path, "rb") as f:
        response = requests.post(upload_url, headers=headers, data=f)
        response.raise_for_status()

def main():
    url = 'https://storage.yandexcloud.net/sbermarker-shopper-distribution/'
    versions = fetch_versions(url)
    existing_releases = get_existing_releases()

    for version_info in versions:
        if version_info['version'] not in existing_releases:
            print(f"Скачивание версии {version_info['version']}")
            file_path = download(version_info)
            
            if file_path:
                print(f"Создание релиза для версии {version_info['version']}")
                asset_name = f"Shopper_{version_info['version']}.apk"
                release_url = create_github_release(version_info, asset_name)
                print(f"Загрузка APK для версии {version_info['version']}")
                upload_asset_to_release(release_url, file_path)
                print(f"Релиз версии {version_info['version']} успешно создан и APK загружен.")
        else:
            print(f"Версия {version_info['version']} уже существует, пропуск.")

if __name__ == "__main__":
    main()
