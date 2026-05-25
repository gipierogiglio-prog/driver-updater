"""
catalog.py — Consulta Microsoft Update Catalog por hardware ID
"""
import re
import requests
import time
from urllib.parse import quote


MICROSOFT_CATALOG_URL = "https://www.catalog.update.microsoft.com/Search.aspx"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def search_microsoft_catalog(query: str, max_results: int = 10) -> list[dict]:
    """
    Busca drivers no Microsoft Update Catalog.
    Retorna lista de dicts: title, size, url, date, id
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    params = {"q": query}

    try:
        resp = requests.get(
            MICROSOFT_CATALOG_URL,
            params=params,
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return [{"error": f"Erro ao consultar catalog: {e}"}]

    return _parse_catalog_results(resp.text, max_results)


def _parse_size(text: str) -> int:
    """Converte string de tamanho (ex: '1.5 MB') pra bytes."""
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
    """Formata bytes pra string legível."""
    if bytes_val >= 1024 * 1024 * 1024:
        return f"{bytes_val / (1024*1024*1024):.1f} GB"
    elif bytes_val >= 1024 * 1024:
        return f"{bytes_val / (1024*1024):.1f} MB"
    elif bytes_val >= 1024:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{bytes_val} B"


def _parse_catalog_results(html: str, max_results: int) -> list[dict]:
    """
    Parseia o HTML de resultados do Microsoft Catalog.
    Extrai tabela de resultados com títulos, links de download, tamanhos.
    """
    results = []

    # Procura tabela de resultados
    # O Catalog renderiza uma table#ctl00_catalogBody_ResultsGrid
    table_pattern = r'<table[^>]*id="ctl00_catalogBody_ResultsGrid"[^>]*>.*?</table>'
    table_match = re.search(table_pattern, html, re.DOTALL | re.IGNORECASE)
    if not table_match:
        # Tenta pattern alternativo
        table_match = re.search(r'class="catalog-table".*?<table.*?>.*?</table>', html, re.DOTALL)

    # Extrai linhas da tabela
    row_pattern = r'<tr[^>]*>(.*?)</tr>'
    if table_match:
        rows = re.findall(row_pattern, table_match.group(0), re.DOTALL)
    else:
        # Fallback: procura qualquer padrão de resultado
        rows = re.findall(r'class=".*?resultRow.*?".*?>(.*?)</tr>', html, re.DOTALL)

    for row in rows:
        if len(results) >= max_results:
            break

        # Título
        title_match = re.search(r'<a[^>]*class=".*?updateTitle.*?"[^>]*>(.*?)</a>', row, re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        if not title:
            continue

        # Tamanho
        size_match = re.search(r'class=".*?sizeCol.*?"[^>]*>\s*([\d.,]+\s*(?:KB|MB|GB))', row, re.DOTALL)
        size_str = size_match.group(1).strip() if size_match else "0 B"
        size_bytes = _parse_size(size_str)

        # Data
        date_match = re.search(r'class=".*?dateCol.*?"[^>]*>\s*(\d{1,2}/\d{1,2}/\d{4})', row, re.DOTALL)
        date = date_match.group(1).strip() if date_match else ""

        # Link de download (o catalog gera onclick dinâmico)
        download_match = re.search(
            r"javascript:download\(['\"](\d+)['\"]", row, re.DOTALL
        )
        download_id = download_match.group(1) if download_match else ""

        # Tenta extrair link direto
        link_match = re.search(r'<a[^>]*href="(.*?)"[^>]*>.*?</a>', row, re.DOTALL)
        url = link_match.group(1) if link_match else ""

        results.append({
            "title": title,
            "size": size_bytes,
            "size_str": _format_size(size_bytes),
            "date": date,
            "download_id": download_id,
            "url": url,
            "source": "Microsoft Catalog",
        })

    # Se não encontrou nada via parsing, retorna info
    if not results:
        results.append({
            "title": f"Consulte manualmente: {MICROSOFT_CATALOG_URL}?q=...",
            "size": 0,
            "size_str": "N/A",
            "date": "",
            "download_id": "",
            "url": MICROSOFT_CATALOG_URL,
            "source": "Microsoft Catalog",
            "manual": True,
        })

    return results


def search_driver(query: str) -> list[dict]:
    """
    Busca drivers para um hardware ID específico.
    """
    return search_microsoft_catalog(query)


def batch_search(hardware_ids: list[str], max_per_query: int = 5) -> list[dict]:
    """
    Busca drivers para múltiplos hardware IDs.
    Limita a max_per_query por busca pra não floodar.
    """
    all_results = []
    seen_titles = set()
    limited_ids = hardware_ids[:20]  # Máximo de 20 IDs pra não demorar

    for hid in limited_ids:
        results = search_microsoft_catalog(hid, max_results=3)
        time.sleep(0.5)  # Rate limiting

        for r in results:
            title_lower = r.get("title", "").lower()
            if title_lower and title_lower not in seen_titles:
                seen_titles.add(title_lower)
                r["hardware_id"] = hid
                all_results.append(r)

    return all_results


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "PCI\\VEN_10DE"
    print(f"Buscando: {query}")
    results = search_driver(query)
    for r in results[:10]:
        print(f"  [{r.get('size_str','?')}] {r['title'][:80]}")
