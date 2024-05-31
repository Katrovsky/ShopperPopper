import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os
from tqdm import tqdm

GITHUB_API_URL = "https://api.github.com"
GITHUB_REPO = "Katrovsky/ShopperPopper"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def fetch_versions(url):
    response = requests.get(url)
    response.raise_for_status()
    
    root = ET.fromstring(response.content)
    namespace = {'ns': 'http://s3.amazonaws.com/doc/2006-03-01/'}
    contents = root.findall('ns:Contents', namespace)
    contents.reverse()
    
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
    
    return versions

def download(version_info):
    filename = f"Shopper_{version_info['version']}.apk"
    file_path = os.path.join(os.getcwd(), filename)

    with open(file_path, "wb") as f:
        response = requests.get(version_info['url'], stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, desc=filename, ncols=100)
        
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            f.write(data)
        
        progress_bar.close()

    if os.path.getsize(file_path) == total_size:
        print(f"Файл успешно скачан. Путь: {file_path}")
        return file_path
    else:
        print("Ошибка: Размер загруженного файла не соответствует ожидаемому размеру.")
        return None

def create_github_release(version_info):
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

    return release["upload_url"].replace("{?name,label}", "")

def upload_asset_to_release(upload_url, file_path):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/zip"  # Adjust if the file is not a zip
    }

    with open(file_path, "rb") as f:
        response = requests.post(f"{upload_url}?name={os.path.basename(file_path)}", headers=headers, data=f)
        response.raise_for_status()

def main():
    url = 'https://storage.yandexcloud.net/sbermarker-shopper-distribution/'
    versions = fetch_versions(url)
    
    for version_info in versions:
        print(f"Загружается версия: {version_info['version']}")
        file_path = download(version_info)
        
        if file_path:
            release_url = create_github_release(version_info)
            upload_asset_to_release(release_url, file_path)

if __name__ == "__main__":
    main()
