@echo off
chcp 65001 >nul
echo ============================================
echo  Gerando GeradorCertificados.exe
echo ============================================
echo.

py -m pip install --upgrade pip
py -m pip install cryptography pyinstaller

py -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "GeradorCertificados" ^
  --icon "icone.ico" ^
  --add-data "icone.ico;." ^
  --add-data "icone.png;." ^
  gerador_certificados.py

echo.
echo Pronto! O executavel esta em: dist\GeradorCertificados.exe
pause
