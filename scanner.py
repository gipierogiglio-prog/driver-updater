"""
scanner.py — Escaneia drivers instalados via WMI e pnputil
"""
import subprocess
import json
import re
import sys


def _run_powershell(script: str) -> str:
    """Run PowerShell script and return stdout."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except FileNotFoundError:
        return ""


def get_drivers_wmi() -> list[dict]:
    """
    Lista drivers de terceiros via WMI (Win32_PnPSignedDriver).
    Retorna lista de dicts com: name, provider, version, date, hardware_id
    """
    ps_script = """
    Get-CimInstance Win32_PnPSignedDriver | Where-Object {
        $_.DeviceName -and $_.DriverProviderName -ne 'Microsoft'
    } | Select-Object DeviceName, DriverProviderName, DriverVersion, DriverDate,
        @{N='HardwareId';E={($_.HardwareID -join '; ')}}
    | ConvertTo-Json -Compress
    """
    raw = _run_powershell(ps_script)
    if not raw:
        return []

    try:
        items = json.loads(raw)
        if isinstance(items, dict):
            items = [items]
    except json.JSONDecodeError:
        return []

    drivers = []
    for item in items:
        drivers.append({
            "name": item.get("DeviceName", "Desconhecido"),
            "provider": item.get("DriverProviderName", "N/A"),
            "version": item.get("DriverVersion", "N/A"),
            "date": str(item.get("DriverDate", "")).split(" ")[0] if item.get("DriverDate") else "N/A",
            "hardware_id": item.get("HardwareId", ""),
        })

    return drivers


def get_drivers_problem_devices() -> list[dict]:
    """
    Lista dispositivos com erro no Device Manager via WMI.
    """
    ps_script = """
    Get-CimInstance Win32_PnPEntity | Where-Object {
        $_.ConfigManagerErrorCode -and $_.ConfigManagerErrorCode -ne 0
    } | Select-Object Name, DeviceID, ConfigManagerErrorCode,
        @{N='HardwareId';E={($_.HardwareID -join '; ')}}
    | ConvertTo-Json -Compress
    """
    raw = _run_powershell(ps_script)
    if not raw:
        return []

    try:
        items = json.loads(raw)
        if isinstance(items, dict):
            items = [items]
    except json.JSONDecodeError:
        return []

    devices = []
    for item in items:
        devices.append({
            "name": item.get("Name", "Desconhecido"),
            "device_id": item.get("DeviceID", ""),
            "error_code": item.get("ConfigManagerErrorCode", -1),
            "hardware_id": item.get("HardwareId", ""),
        })

    return devices


def get_hardware_ids() -> list[str]:
    """
    Extrai hardware IDs únicos de todos os dispositivos (inclusive Microsoft).
    Usa pnputil para maior cobertura.
    """
    ps_script = """
    $ids = @()
    Get-CimInstance Win32_PnPEntity | Where-Object { $_.HardwareID } | ForEach-Object {
        $ids += $_.HardwareID
    }
    $ids | Select-Object -Unique | ConvertTo-Json -Compress
    """
    raw = _run_powershell(ps_script)
    if not raw:
        return []

    try:
        ids = json.loads(raw)
        if isinstance(ids, str):
            ids = [ids]
    except json.JSONDecodeError:
        return []

    # Filtra só IDs relevantes (PCI, USB, ACPI)
    filtered = []
    for hid in ids:
        if any(hid.upper().startswith(prefix) for prefix in
               ["PCI\\", "USB\\", "ACPI\\", "HDAUDIO\\", "SCSI\\", "IDE\\"]):
            filtered.append(hid)

    return filtered


def extract_pci_vendor(hardware_id: str) -> str | None:
    """Extrai VEN_XXXX de um hardware ID PCI."""
    m = re.search(r'VEN_([0-9A-Fa-f]{4})', hardware_id)
    if m:
        return f"VEN_{m.group(1).upper()}"
    return None


def extract_pci_device(hardware_id: str) -> str | None:
    """Extrai DEV_XXXX de um hardware ID PCI."""
    m = re.search(r'DEV_([0-9A-Fa-f]{4})', hardware_id)
    if m:
        return f"DEV_{m.group(1).upper()}"
    return None


def get_all_drivers() -> dict:
    """
    Retorna dict consolidado com:
    - third_party: drivers de terceiros
    - problem_devices: dispositivos com erro
    - hardware_ids: todos os HW IDs
    """
    return {
        "third_party": get_drivers_wmi(),
        "problem_devices": get_drivers_problem_devices(),
        "hardware_ids": get_hardware_ids(),
    }


if __name__ == "__main__":
    import pprint
    data = get_all_drivers()
    print(f"Drivers terceiros: {len(data['third_party'])}")
    print(f"Problemas: {len(data['problem_devices'])}")
    print(f"Hardware IDs: {len(data['hardware_ids'])}")
    pprint.pprint(data)
