"""
catalog.py — Busca drivers usando Windows Update API (COM) e Microsoft Catalog como fallback
"""
import re
import time
from typing import Callable


def search_windows_update(hardware_ids: list[str]) -> list[dict]:
    """
    Usa Windows Update API (COM) pra buscar drivers.
    Funciona APENAS no Windows.
    Retorna lista de dicts com: title, size, date, download_id, hardware_id
    """
    try:
        import comtypes.client
        import comtypes.gen
        from comtypes.gen import UpdateApiLib
    except ImportError:
        return _search_catalog_fallback(hardware_ids)
    except Exception:
        return _search_catalog_fallback(hardware_ids)

    try:
        # Inicializa a sessão do Windows Update
        session = comtypes.client.CreateObject("Microsoft.Update.Session")
        searcher = session.CreateUpdateSearcher()

        # Filtra por drivers
        searcher.Online = False  # Usa cache local primeiro
        results = []

        for hid in hardware_ids[:10]:  # Limita a 10
            try:
                query = f"Driver=1 and HardwareID='{hid}'"
                search_result = searcher.Search(query)

                for update in search_result.Updates:
                    title = update.Title
                    size = update.MaxDownloadSize
                    date = str(update.LastDeploymentChangeTime)[:10] if update.LastDeploymentChangeTime else ""

                    results.append({
                        "title": title,
                        "size": size,
                        "size_str": _format_size(size),
                        "date": date,
                        "download_id": "",
                        "hardware_id": hid,
                        "source": "Windows Update",
                        "update_obj": update,
                    })

            except Exception:
                continue

        if results:
            return results

        # Se não achou local, tenta online
        searcher.Online = True
        for hid in hardware_ids[:5]:
            try:
                query = f"Driver=1 and HardwareID='{hid}'"
                search_result = searcher.Search(query)
                for update in search_result.Updates:
                    title = update.Title
                    size = update.MaxDownloadSize
                    date = str(update.LastDeploymentChangeTime)[:10] if update.LastDeploymentChangeTime else ""
                    results.append({
                        "title": title,
                        "size": size,
                        "size_str": _format_size(size),
                        "date": date,
                        "download_id": "",
                        "hardware_id": hid,
                        "source": "Windows Update",
                        "update_obj": update,
                    })
            except Exception:
                continue

        return results

    except Exception:
        return _search_catalog_fallback(hardware_ids)


def _search_catalog_fallback(hardware_ids: list[str]) -> list[dict]:
    """
    Fallback: busca no Microsoft Catalog via scraping.
    """
    try:
        import requests
        from urllib.parse import quote
    except ImportError:
        return [{"error": "requests não instalado"}]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    results = []
    seen_titles = set()

    for hid in hardware_ids[:10]:
        try:
            resp = requests.get(
                "https://www.catalog.update.microsoft.com/Search.aspx",
                params={"q": hid},
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
        except Exception:
            continue

        # Extrai resultados da tabela HTML
        rows = re.findall(
            r'<tr[^>]*class=".*?resultRow.*?"[^>]*>(.*?)</tr>',
            resp.text, re.DOTALL
        )

        for row in rows[:5]:
            title_match = re.search(
                r'<a[^>]*class=".*?updateTitle.*?"[^>]*>(.*?)</a>',
                row, re.DOTALL
            )
            title = title_match.group(1).strip() if title_match else ""
            if not title:
                # Tenta outro padrão
                title_match = re.search(
                    r'<a[^>]*>(.*?)</a>', row, re.DOTALL
                )
                title = title_match.group(1).strip() if title_match else ""

            if not title or title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())

            # Tamanho
            size_match = re.search(
                r'([\d.,]+\s*(?:KB|MB|GB))', row, re.DOTALL
            )
            size_str = size_match.group(1).strip() if size_match else "N/A"
            size_bytes = _parse_size(size_str)

            # Data
            date_match = re.search(
                r'(\d{1,2}/\d{1,2}/\d{4})', row
            )
            date = date_match.group(1) if date_match else ""

            # Download ID
            dl_match = re.search(
                r"javascript:download\(['\"](\d+)['\"]", row
            )
            dl_id = dl_match.group(1) if dl_match else ""

            results.append({
                "title": title.strip(),
                "size": size_bytes,
                "size_str": size_str,
                "date": date,
                "download_id": dl_id,
                "hardware_id": hid,
                "source": "Microsoft Catalog",
            })

        time.sleep(0.3)  # Rate limiting

    if not results:
        results.append({
            "title": "Nenhum driver encontrado no Windows Update ou Catalog",
            "size": 0,
            "size_str": "0 B",
            "date": "",
            "download_id": "",
            "hardware_id": "",
            "source": "N/A",
        })

    return results


def search_drivers(hardware_ids: list[str]) -> list[dict]:
    """
    Função principal: tenta Windows Update API, fallback Catalog.
    """
    return search_windows_update(hardware_ids)


def _parse_size(text: str) -> int:
    text = text.strip().upper()
    m = re.search(r'([\d.]+)\s*(KB|MB|GB)', text)
    if not m:
        return 0
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "KB":
        return int(val * 1024)
    elif unit == "MB":
        return int(val * 1024 * 1024)
    elif unit == "GB":
        return int(val * 1024 * 1024 * 1024)
    return 0


def _format_size(bytes_val: int) -> str:
    if bytes_val >= 1024 * 1024 * 1024:
        return f"{bytes_val / (1024*1024*1024):.1f} GB"
    elif bytes_val >= 1024 * 1024:
        return f"{bytes_val / (1024*1024):.1f} MB"
    elif bytes_val >= 1024:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{bytes_val} B"


if __name__ == "__main__":
    import sys
    ids = sys.argv[1:] if len(sys.argv) > 1 else ["PCI\\VEN_10DE&DEV_1C03"]
    results = search_drivers(ids)
    for r in results:
        print(f"  [{r.get('source','?')}] {r.get('title','?')[:80]}")
