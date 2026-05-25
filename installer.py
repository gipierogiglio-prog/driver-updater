"""
installer.py — Instala drivers via pnputil e DISM
"""
import subprocess
import sys
import os


def is_admin() -> bool:
    """Verifica se o script está rodando como Administrador."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except (AttributeError, ImportError):
        return False


def check_admin_or_continue() -> bool:
    """Se não for admin, alerta mas permite continuar (instalação não vai funcionar)."""
    if not is_admin():
        print("⚠️  A instalação de drivers requer privilégios de Administrador.")
        return False
    return True


def install_driver_pnputil(cab_path: str) -> dict:
    """
    Instala um driver .cab via pnputil.
    Retorna dict com sucesso/mensagem.
    """
    if not os.path.exists(cab_path):
        return {"success": False, "message": f"Arquivo não encontrado: {cab_path}"}

    try:
        cmd = ["pnputil", "/add-driver", cab_path, "/install"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        success = result.returncode == 0

        # pnputil retorna 0 mesmo com alguns erros, verifica output
        if "successfully" in stdout.lower() or "instalado" in stdout.lower():
            success = True
        elif "failed" in stdout.lower() or "falhou" in stdout.lower():
            success = False

        return {
            "success": success,
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "message": "✅ Instalado" if success else f"❌ Falha: {stdout[:200]}",
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "message": "⏱️ Timeout - instalação demorou demais"}
    except FileNotFoundError:
        return {"success": False, "message": "❌ pnputil não encontrado"}
    except Exception as e:
        return {"success": False, "message": f"❌ Erro: {e}"}


def install_driver_dism(cab_path: str) -> dict:
    """
    Alternativa usando DISM pra instalar .cab.
    """
    if not os.path.exists(cab_path):
        return {"success": False, "message": f"Arquivo não encontrado: {cab_path}"}

    try:
        cmd = [
            "dism", "/Online", "/Add-Package",
            f"/PackagePath:{cab_path}",
            "/Quiet", "/NoRestart",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        success = result.returncode == 0

        return {
            "success": success,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "message": "✅ Instalado via DISM" if success else f"⚠️ DISM falhou: {result.stdout[:200]}",
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "message": "⏱️ Timeout"}
    except FileNotFoundError:
        return {"success": False, "message": "❌ DISM não encontrado"}
    except Exception as e:
        return {"success": False, "message": f"❌ Erro: {e}"}


def install_driver(cab_path: str, method: str = "pnputil") -> dict:
    """
    Instala driver .cab. Tenta pnputil primeiro, fallback DISM.
    """
    if method == "dism":
        return install_driver_dism(cab_path)

    result = install_driver_pnputil(cab_path)
    if not result["success"]:
        # Fallback pra DISM
        fallback = install_driver_dism(cab_path)
        if fallback["success"]:
            return fallback

    return result


def install_drivers(drivers: list[dict], progress_callback=None) -> list[dict]:
    """
    Instala múltiplos drivers.
    drivers: lista com dicts que tenham 'filepath'
    Retorna lista com resultados.
    """
    results = []
    total = len(drivers)
    done = 0

    for driver in drivers:
        filepath = driver.get("filepath")
        if not filepath:
            results.append({**driver, "install_result": {"success": False, "message": "❌ Sem arquivo para instalar"}})
            done += 1
            if progress_callback:
                progress_callback(done, total)
            continue

        result = install_driver(filepath)
        results.append({**driver, "install_result": result})
        done += 1
        if progress_callback:
            progress_callback(done, total)

    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = install_driver(sys.argv[1])
        print(result["message"])
    else:
        print(f"Admin: {is_admin()}")
