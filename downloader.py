"""
downloader.py — Download de drivers do Microsoft Update Catalog
"""
import os
import requests
import re
from pathlib import Path


DOWNLOAD_DIR = Path(__file__).parent / "downloads"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos pra nome de arquivo."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", "_", name)
    return name.strip("_ ")[:100]


def ensure_download_dir():
    """Cria diretório de downloads se não existir."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def download_driver(driver: dict, progress_callback=None) -> str | None:
    """
    Baixa um driver do Microsoft Catalog.
    driver deve ter 'download_id' ou 'url'.
    Retorna caminho do arquivo baixado ou None se falhar.
    """
    ensure_download_dir()
    title = driver.get("title", "driver")
    filename = _sanitize_filename(title) + ".cab"

    filepath = DOWNLOAD_DIR / filename

    # Se já baixou, retorna caminho
    if filepath.exists() and filepath.stat().st_size > 0:
        return str(filepath)

    download_id = driver.get("download_id", "")
    url = driver.get("url", "")

    if not download_id and not url:
        return None

    # Constrói URL de download do Catalog
    if download_id and not url:
        url = f"https://www.catalog.update.microsoft.com/Download.aspx/{download_id}"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        # Primeiro request: pega o redirect pro .cab real
        resp = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        resp.raise_for_status()

        # Se o content-type é text/html, tenta extrair link real do .cab
        if "text/html" in resp.headers.get("Content-Type", ""):
            cab_match = re.search(
                r'href="(https?://[^"]+\.cab[^"]*)"', resp.text, re.IGNORECASE
            )
            if cab_match:
                cab_url = cab_match.group(1)
                resp = requests.get(cab_url, headers=headers, timeout=30)
                resp.raise_for_status()
            else:
                # Tenta qualquer href que pareça download
                link_match = re.search(r'href="([^"]+download[^"]+)"', resp.text, re.IGNORECASE)
                if link_match:
                    resp = requests.get(link_match.group(1), headers=headers, timeout=30)
                    resp.raise_for_status()
                else:
                    return None

        # Salva o arquivo
        with open(filepath, "wb") as f:
            f.write(resp.content)

        if progress_callback:
            progress_callback(1, 1)

        return str(filepath)

    except requests.RequestException as e:
        print(f"Erro download {title}: {e}")
        if progress_callback:
            progress_callback(0, 1)
        return None


def download_drivers(
    drivers: list[dict],
    progress_callback=None,
) -> list[dict]:
    """
    Baixa múltiplos drivers.
    Retorna lista com resultados (driver + filepath ou erro).
    """
    results = []
    total = len(drivers)
    downloaded = 0

    for driver in drivers:
        filepath = download_driver(driver, progress_callback)
        if filepath:
            downloaded += 1
            results.append({**driver, "filepath": filepath, "status": "baixado"})
        else:
            results.append({**driver, "filepath": None, "status": "erro"})

        if progress_callback:
            progress_callback(downloaded, total)

    return results


if __name__ == "__main__":
    test_driver = {
        "title": "Test Driver",
        "download_id": "123456",
    }
    print(download_driver(test_driver))
