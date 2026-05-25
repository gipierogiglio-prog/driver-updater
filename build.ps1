# Build do Atualizador de Drivers - Garrinha 🦎
# Executar no PowerShell do Windows

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 🦎 Build - Atualizador de Drivers" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verificar Python
try {
    python --version
} catch {
    Write-Host "[ERRO] Python não encontrado. Instale Python 3.11+" -ForegroundColor Red
    exit 1
}

# Instalar dependências
Write-Host "[1/4] Instalando dependências..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao instalar dependências" -ForegroundColor Red
    exit 1
}

# Instalar PyInstaller
Write-Host "[2/4] Instalando PyInstaller..." -ForegroundColor Yellow
pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao instalar PyInstaller" -ForegroundColor Red
    exit 1
}

# Limpar build anterior
Write-Host "[3/4] Compilando .exe..." -ForegroundColor Yellow
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

python -m PyInstaller `
    --onefile `
    --windowed `
    --name "AtualizadorDrivers_Garrinha" `
    --icon NONE `
    --add-data "*.py;." `
    --clean `
    main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha na compilação" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " ✅ BUILD CONCLUÍDO!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Executável: dist\AtualizadorDrivers_Garrinha.exe" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  Execute como Administrador!" -ForegroundColor Yellow
Write-Host ""
