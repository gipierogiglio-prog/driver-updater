@echo off
REM Build do Atualizador de Drivers - Garrinha 🦎
REM Executar no Windows com Python instalado

echo ============================================
echo  🦎 Build - Atualizador de Drivers
echo ============================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado. Instale Python 3.11+
    pause
    exit /b 1
)

REM Instalar dependencias
echo [1/4] Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias
    pause
    exit /b 1
)

REM Instalar PyInstaller
echo [2/4] Instalando PyInstaller...
pip install pyinstaller
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar PyInstaller
    pause
    exit /b 1
)

REM Limpar build anterior
echo [3/4] Compilando .exe...
if exist dist rmdir /s /q dist

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "AtualizadorDrivers_Garrinha" ^
    --icon NONE ^
    --add-data "*.py;." ^
    --clean ^
    main.py

if %errorlevel% neq 0 (
    echo [ERRO] Falha na compilacao
    pause
    exit /b 1
)

echo.
echo ============================================
echo  ✅ BUILD CONCLUIDO!
echo ============================================
echo.
echo 📁 Executavel: dist\AtualizadorDrivers_Garrinha.exe
echo.
echo ⚠️  Execute como Administrador!
echo.
pause
