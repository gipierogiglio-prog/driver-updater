"""
Atualizador de Drivers - Garrinha 🦎

Aplicação desktop Windows que:
1. Escaneia drivers instalados via WMI
2. Busca atualizações no Microsoft Update Catalog
3. Baixa e instala drivers selecionados

Uso:
    python main.py         # Modo GUI
    python main.py --scan  # Modo console (escaneia e mostra)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def console_mode():
    """Modo console: escaneia e mostra drivers encontrados."""
    from scanner import get_all_drivers, extract_pci_vendor
    from catalog import batch_search
    import json

    print("🔍 Escaneando drivers...")
    data = get_all_drivers()

    print(f"\nDrivers de terceiros: {len(data['third_party'])}")
    for d in data["third_party"][:20]:
        print(f"  - {d['name']} ({d['provider']}) v{d['version']}")

    if data["problem_devices"]:
        print(f"\n⚠️ Dispositivos com problema: {len(data['problem_devices'])}")
        for p in data["problem_devices"]:
            print(f"  - {p['name']} (erro {p['error_code']})")

    print(f"\nHardware IDs encontrados: {len(data['hardware_ids'])}")

    # Busca alguns no Catalog
    search_ids = data["hardware_ids"][:5]
    if search_ids:
        print(f"\n🔎 Buscando no Microsoft Catalog...")
        results = batch_search(search_ids)
        print(f"Encontrados {len(results)} drivers:")
        for r in results[:10]:
            print(f"  [{r.get('size_str','?')}] {r['title'][:80]}")

    return data


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--scan", "--console", "-s"):
        console_mode()
    else:
        from gui import main as gui_main
        gui_main()


if __name__ == "__main__":
    main()
