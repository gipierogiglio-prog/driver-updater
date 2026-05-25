# 🦎 Atualizador de Drivers - Garrinha

Aplicação desktop Windows para identificar, baixar e instalar drivers automaticamente.

## Funcionalidades

- 🔍 **Escaneia** drivers instalados via WMI
- 🔎 **Consulta** Microsoft Update Catalog por hardware ID
- ✅ **Seleciona** quais drivers baixar/instalar via interface gráfica
- ⬇️ **Baixa** drivers .cab
- ⚙️ **Instala** via pnputil

## Requisitos

- Windows 10/11
- Python 3.11+ (para build)
- Privilégios de **Administrador** (para instalação)

## Como usar (versão compilada)

1. Baixe o `AtualizadorDrivers_Garrinha.exe`
2. Clique com botão direito → **Executar como Administrador**
3. Clique em **Verificar Drivers**
4. Selecione os drivers desejados
5. Clique em **Baixar Selecionados**
6. Clique em **Instalar**

## Como buildar

```batch
build.bat
```

Ou no PowerShell:

```powershell
.\build.ps1
```

## Estrutura do projeto

```
driver-updater/
├── main.py          # Entry point (GUI ou console)
├── gui.py           # Interface Tkinter
├── scanner.py       # Escaneia hardware via WMI/pnputil
├── catalog.py       # Consulta Microsoft Update Catalog
├── downloader.py    # Download de drivers .cab
├── installer.py     # Instalação com pnputil/DISM
├── requirements.txt # Dependências
├── build.bat        # Script de build (CMD)
├── build.ps1        # Script de build (PowerShell)
└── README.md        # Você está aqui
```

## Modo console

```bash
python main.py --scan
```
