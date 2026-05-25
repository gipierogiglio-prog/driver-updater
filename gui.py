"""
gui.py — Interface Tkinter do Atualizador de Drivers 🦎
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import os
import sys

# Adiciona diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner import get_all_drivers, extract_pci_vendor
from catalog import batch_search
from downloader import download_drivers, ensure_download_dir
from installer import check_admin_or_continue, install_drivers

# Cores
COLORS = {
    "bg": "#1e1e2e",
    "fg": "#cdd6f4",
    "accent": "#89b4fa",
    "success": "#a6e3a1",
    "warning": "#f9e2af",
    "error": "#f38ba8",
    "surface": "#313244",
    "surface2": "#45475a",
}


class DriverUpdaterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Atualizador de Drivers - Garrinha 🦎")
        self.root.geometry("900x650")
        self.root.minsize(700, 500)

        # Tema escuro manual
        self._setup_styles()

        # Estado
        self.drivers = []
        self.selected = {}
        self.scanning = False
        self.downloading = False

        # Build UI
        self._build_ui()

        # Center window
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_styles(self):
        self.root.configure(bg=COLORS["bg"])

        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Treeview",
            background=COLORS["surface"],
            foreground=COLORS["fg"],
            fieldbackground=COLORS["surface"],
            rowheight=28,
            font=("Segoe UI", 10),
        )
        style.configure("Treeview.Heading",
            background=COLORS["surface2"],
            foreground=COLORS["fg"],
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Treeview",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", "#11111b")],
        )

        style.configure("TButton",
            background=COLORS["accent"],
            foreground="#11111b",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 6),
        )
        style.map("TButton",
            background=[("active", "#74c7ec"), ("disabled", COLORS["surface2"])],
            foreground=[("disabled", COLORS["surface2"])],
        )

        style.configure("TLabel",
            background=COLORS["bg"],
            foreground=COLORS["fg"],
            font=("Segoe UI", 10),
        )
        style.configure("Header.TLabel",
            font=("Segoe UI", 14, "bold"),
            foreground=COLORS["accent"],
        )
        style.configure("Status.TLabel",
            font=("Segoe UI", 9),
            foreground=COLORS["surface2"],
        )
        style.configure("Success.TLabel",
            foreground=COLORS["success"],
        )
        style.configure("Error.TLabel",
            foreground=COLORS["error"],
        )

        style.configure("TFrame", background=COLORS["bg"])
        style.configure("TProgressbar",
            background=COLORS["accent"],
            troughcolor=COLORS["surface"],
        )

    def _build_ui(self):
        # Header
        header_frame = ttk.Frame(self.root, padding="15 10")
        header_frame.pack(fill=tk.X)

        ttk.Label(header_frame, text="🦎 Atualizador de Drivers",
                  style="Header.TLabel").pack(side=tk.LEFT)

        self.admin_label = ttk.Label(header_frame, text="", style="Error.TLabel")
        self.admin_label.pack(side=tk.RIGHT, padx=5)

        # Check admin
        if not check_admin_or_continue():
            self.admin_label.config(
                text="⚠️ Execute como Administrador",
                style="Warning.TLabel" if "Warning" in str(style := "") else ""
            )
            # Reconfigure since we don't have Warning style
            self.admin_label.config(foreground=COLORS["warning"])

        # Buttons frame
        btn_frame = ttk.Frame(self.root, padding="15 5")
        btn_frame.pack(fill=tk.X)

        self.btn_scan = ttk.Button(
            btn_frame, text="🔍 Verificar Drivers",
            command=self._start_scan,
        )
        self.btn_scan.pack(side=tk.LEFT, padx=5)

        self.btn_download = ttk.Button(
            btn_frame, text="⬇️ Baixar Selecionados",
            command=self._start_download,
            state=tk.DISABLED,
        )
        self.btn_download.pack(side=tk.LEFT, padx=5)

        self.btn_install = ttk.Button(
            btn_frame, text="⚙️ Instalar",
            command=self._start_install,
            state=tk.DISABLED,
        )
        self.btn_install.pack(side=tk.LEFT, padx=5)

        # Select all / none
        self.btn_select_all = ttk.Button(
            btn_frame, text="☑️ Todos",
            command=self._select_all,
            state=tk.DISABLED,
        )
        self.btn_select_all.pack(side=tk.LEFT, padx=5)

        self.btn_select_none = ttk.Button(
            btn_frame, text="⬜ Nenhum",
            command=self._select_none,
            state=tk.DISABLED,
        )
        self.btn_select_none.pack(side=tk.LEFT, padx=5)

        # Treeview
        tree_frame = ttk.Frame(self.root, padding="15 5")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("select", "driver", "provider", "version", "size", "status")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns,
            show="headings", selectmode="none",
        )

        self.tree.heading("select", text="✓", anchor=tk.CENTER)
        self.tree.heading("driver", text="Driver", anchor=tk.W)
        self.tree.heading("provider", text="Fabricante", anchor=tk.W)
        self.tree.heading("version", text="Versão", anchor=tk.W)
        self.tree.heading("size", text="Tamanho", anchor=tk.CENTER)
        self.tree.heading("status", text="Status", anchor=tk.CENTER)

        self.tree.column("select", width=40, anchor=tk.CENTER)
        self.tree.column("driver", width=300)
        self.tree.column("provider", width=150)
        self.tree.column("version", width=120)
        self.tree.column("size", width=100, anchor=tk.CENTER)
        self.tree.column("status", width=120, anchor=tk.CENTER)

        # Bind click na primeira coluna pra toggle
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Progress
        self.progress = ttk.Progressbar(self.root, mode="determinate", length=100)
        self.progress.pack(fill=tk.X, padx=15, pady=5)

        # Status label
        self.status_label = ttk.Label(self.root, text="Pronto. Clique em Verificar Drivers.",
                                      style="Status.TLabel")
        self.status_label.pack(padx=15, pady=5)

        # Log
        log_frame = ttk.Frame(self.root, padding="15 5")
        log_frame.pack(fill=tk.BOTH)

        self.log = scrolledtext.ScrolledText(
            log_frame, height=6,
            bg=COLORS["surface"],
            fg=COLORS["fg"],
            font=("Consolas", 9),
            insertbackground=COLORS["fg"],
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.log.pack(fill=tk.BOTH, expand=True)

    def _log(self, msg: str):
        self.log.insert(tk.END, f"{msg}\n")
        self.log.see(tk.END)
        self.root.update_idletasks()

    def _set_status(self, msg: str, color: str = None):
        self.status_label.config(text=msg)
        if color:
            self.status_label.config(foreground=color)
        else:
            self.status_label.config(foreground=COLORS["surface2"])
        self.root.update_idletasks()

    def _enable_buttons(self, scanning=True, downloading=True, installing=True,
                        select=True):
        state_btn = tk.NORMAL if scanning else tk.DISABLED
        self.btn_scan.config(state=state_btn)

        state_dl = tk.NORMAL if downloading and self.drivers else tk.DISABLED
        self.btn_download.config(state=state_dl)

        state_ins = tk.NORMAL if installing and any(
            d.get("filepath") for d in self.drivers
        ) else tk.DISABLED
        self.btn_install.config(state=state_ins)

        state_sel = tk.NORMAL if select and self.drivers else tk.DISABLED
        self.btn_select_all.config(state=state_sel)
        self.btn_select_none.config(state=state_sel)

    def _start_scan(self):
        if self.scanning:
            return
        self.scanning = True
        self._enable_buttons(scanning=False)
        self._log("🔍 Iniciando verificação de drivers...")
        self._set_status("Escaneando hardware...", COLORS["accent"])
        self.progress["value"] = 0
        self.progress["mode"] = "indeterminate"
        self.progress.start(10)

        thread = threading.Thread(target=self._scan_worker, daemon=True)
        thread.start()

    def _scan_worker(self):
        try:
            data = get_all_drivers()
            third_party = data["third_party"]
            problems = data["problem_devices"]
            hw_ids = data["hardware_ids"]

            self.root.after(0, lambda: self._log(
                f"  Drivers terceiros: {len(third_party)}"
            ))
            self.root.after(0, lambda: self._log(
                f"  Dispositivos com problema: {len(problems)}"
            ))
            self.root.after(0, lambda: self._log(
                f"  Hardware IDs encontrados: {len(hw_ids)}"
            ))

            if problems:
                self.root.after(0, lambda: self._log(
                    "⚠️  Dispositivos com erro detectados!"
                ))

            # Busca drivers no Microsoft Catalog
            self.root.after(0, lambda: self._set_status(
                "Consultando Microsoft Update Catalog...", COLORS["accent"]
            ))
            self.root.after(0, lambda: self._log(
                "🔎 Buscando drivers no Microsoft Update Catalog..."
            ))

            # Pega alguns hardware IDs pra busca
            search_ids = []
            for hid in hw_ids[:10]:  # Limita a 10 pra não floodar
                ven = extract_pci_vendor(hid)
                if ven:
                    search_ids.append(hid)

            # Remove duplicatas
            search_ids = list(dict.fromkeys(search_ids))

            if search_ids:
                catalog_results = batch_search(search_ids, max_per_query=3)
                self.root.after(0, lambda: self._log(
                    f"  Encontrados {len(catalog_results)} drivers no Catalog"
                ))
            else:
                catalog_results = []
                self.root.after(0, lambda: self._log(
                    "  Nenhum hardware ID PCI encontrado para busca"
                ))

            # Monta lista final de drivers
            self.drivers = []
            self.selected = {}

            for d in third_party:
                self.drivers.append({
                    "name": d["name"],
                    "provider": d["provider"],
                    "version": d["version"],
                    "date": d["date"],
                    "hardware_id": d["hardware_id"],
                    "size_str": "N/A",
                    "size": 0,
                    "status": "identificado",
                    "filepath": None,
                    "install_result": None,
                })

            for cr in catalog_results:
                # Verifica se já não existe
                existing_names = [d["name"] for d in self.drivers]
                cr_title = cr.get("title", "")
                if not any(cr_title[:30] in e for e in existing_names):
                    self.drivers.append({
                        "name": cr_title[:80],
                        "provider": cr.get("source", "Microsoft Catalog"),
                        "version": cr.get("date", ""),
                        "hardware_id": cr.get("hardware_id", ""),
                        "size_str": cr.get("size_str", "N/A"),
                        "size": cr.get("size", 0),
                        "status": "disponível",
                        "filepath": None,
                        "install_result": None,
                        "download_id": cr.get("download_id", ""),
                    })

            # Atualiza UI
            self.root.after(0, self._refresh_tree)
            self.root.after(0, lambda: self._enable_buttons(
                downloading=bool(self.drivers)
            ))

            self.root.after(0, lambda: self._log(
                f"✅ Verificação concluída. {len(self.drivers)} drivers encontrados."
            ))
            self.root.after(0, lambda: self._set_status(
                f"✅ {len(self.drivers)} drivers. Selecione os que deseja baixar.",
                COLORS["success"]
            ))

        except Exception as e:
            self.root.after(0, lambda: self._log(f"❌ Erro na verificação: {e}"))
            self.root.after(0, lambda: self._set_status(
                f"❌ Erro: {e}", COLORS["error"]
            ))

        finally:
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.progress.configure(value=0, mode="determinate"))
            self.scanning = False
            self.root.after(0, lambda: self._enable_buttons())

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, d in enumerate(self.drivers):
            selected = "☑" if self.selected.get(i, False) else "☐"
            status = d.get("status", "")
            status_icon = ""
            if status == "baixado":
                status_icon = "⬇️ Baixado"
            elif status == "instalado":
                status_icon = "✅ Instalado"
            elif status == "erro":
                status_icon = "❌ Erro"
            else:
                status_icon = "📦 Disponível" if d.get("download_id") else status

            self.tree.insert("", tk.END, iid=str(i), values=(
                selected,
                d["name"],
                d.get("provider", ""),
                d.get("version", ""),
                d.get("size_str", "N/A"),
                status_icon,
            ))

            # Cor da linha baseada no status
            tags = []
            if status == "instalado":
                tags.append("installed")
            elif status == "erro":
                tags.append("error")
            elif status == "baixado":
                tags.append("downloaded")
            if tags:
                self.tree.item(str(i), tags=tags)

        # Config tags
        self.tree.tag_configure("installed", foreground=COLORS["success"])
        self.tree.tag_configure("error", foreground=COLORS["error"])
        self.tree.tag_configure("downloaded", foreground=COLORS["accent"])

    def _on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell" and region != "tree":
            return

        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        col = self.tree.identify_column(event.x)
        # Coluna 0 = checkbox
        if col != "#0" and col != "#1":
            return

        idx = int(item_id)
        self.selected[idx] = not self.selected.get(idx, False)
        self._refresh_tree()

        has_selected = any(self.selected.values())
        self.btn_download.config(state=tk.NORMAL if has_selected else tk.DISABLED)

    def _select_all(self):
        for i in range(len(self.drivers)):
            if not self.drivers[i].get("filepath") and \
               self.drivers[i].get("status") not in ("instalado", "erro"):
                self.selected[i] = True
        self._refresh_tree()
        self.btn_download.config(state=tk.NORMAL if any(self.selected.values()) else tk.DISABLED)

    def _select_none(self):
        self.selected.clear()
        self._refresh_tree()
        self.btn_download.config(state=tk.DISABLED)

    def _start_download(self):
        if self.downloading:
            return

        selected_drivers = [
            self.drivers[i] for i in sorted(self.selected.keys())
            if self.selected[i]
        ]

        if not selected_drivers:
            return

        self.downloading = True
        self._enable_buttons(scanning=False, downloading=False, select=False)
        self._log(f"⬇️ Baixando {len(selected_drivers)} driver(s)...")
        self._set_status("Baixando...", COLORS["accent"])
        self.progress["value"] = 0
        self.progress["mode"] = "determinate"

        ensure_download_dir()

        thread = threading.Thread(
            target=self._download_worker,
            args=(selected_drivers,),
            daemon=True,
        )
        thread.start()

    def _download_worker(self, selected_drivers):
        try:
            total = len(selected_drivers)

            def progress_callback(current, total):
                pct = int((current / total) * 100) if total > 0 else 0
                self.root.after(0, lambda: self.progress.configure(value=pct))
                self.root.after(0, lambda: self._set_status(
                    f"⬇️ Baixando... {current}/{total}", COLORS["accent"]
                ))

            results = download_drivers(selected_drivers, progress_callback)

            for r in results:
                for i, d in enumerate(self.drivers):
                    if d["name"] == r.get("name"):
                        self.drivers[i]["filepath"] = r.get("filepath")
                        self.drivers[i]["status"] = r.get("status", "erro")
                        break

            success_count = sum(1 for r in results if r.get("status") == "baixado")
            self.root.after(0, lambda: self._log(
                f"✅ Download concluído: {success_count}/{total} baixados"
            ))
            self.root.after(0, lambda: self._refresh_tree())
            self.root.after(0, lambda: self._enable_buttons(
                installing=success_count > 0
            ))
            self.root.after(0, lambda: self._set_status(
                f"✅ {success_count}/{total} baixados. Pode instalar!",
                COLORS["success"]
            ))

        except Exception as e:
            self.root.after(0, lambda: self._log(f"❌ Erro download: {e}"))
            self.root.after(0, lambda: self._set_status(
                f"❌ Erro: {e}", COLORS["error"]
            ))

        finally:
            self.downloading = False

    def _start_install(self):
        to_install = [
            d for d in self.drivers
            if d.get("filepath") and d.get("status") == "baixado"
        ]

        if not to_install:
            messagebox.showinfo("Nada a instalar",
                                "Nenhum driver baixado encontrado para instalar.")
            return

        if not check_admin_or_continue():
            messagebox.showwarning(
                "Sem privilégios",
                "A instalação requer Administrador. Execute o programa como Admin."
            )
            return

        self._enable_buttons(scanning=False, downloading=False, installing=False,
                            select=False)
        self._log(f"⚙️ Instalando {len(to_install)} driver(s)...")
        self._set_status("Instalando...", COLORS["accent"])
        self.progress["value"] = 0
        self.progress["mode"] = "determinate"

        thread = threading.Thread(
            target=self._install_worker,
            args=(to_install,),
            daemon=True,
        )
        thread.start()

    def _install_worker(self, to_install):
        try:
            total = len(to_install)

            def progress_callback(current, total):
                pct = int((current / total) * 100) if total > 0 else 0
                self.root.after(0, lambda: self.progress.configure(value=pct))
                self.root.after(0, lambda: self._set_status(
                    f"⚙️ Instalando... {current}/{total}", COLORS["accent"]
                ))

            results = install_drivers(to_install, progress_callback)

            for r in results:
                ir = r.get("install_result", {})
                for i, d in enumerate(self.drivers):
                    if d.get("filepath") == r.get("filepath"):
                        self.drivers[i]["status"] = "instalado" if ir.get("success") else "erro"
                        self.drivers[i]["install_result"] = ir
                        break

            success_count = sum(
                1 for r in results
                if r.get("install_result", {}).get("success")
            )
            self.root.after(0, lambda: self._log(
                f"✅ Instalação concluída: {success_count}/{total} instalados"
            ))
            self.root.after(0, lambda: self._refresh_tree())
            self.root.after(0, lambda: self._enable_buttons())
            self.root.after(0, lambda: self._set_status(
                f"✅ {success_count}/{total} instalados. Reinicie se necessário.",
                COLORS["success"]
            ))

        except Exception as e:
            self.root.after(0, lambda: self._log(f"❌ Erro instalação: {e}"))
            self.root.after(0, lambda: self._set_status(
                f"❌ Erro: {e}", COLORS["error"]
            ))


def main():
    root = tk.Tk()
    app = DriverUpdaterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
