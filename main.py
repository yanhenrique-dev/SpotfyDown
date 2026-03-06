#!/usr/bin/env python3
"""
Spotify Downloader - Entry Point
Gerencia venv e inicialização.
"""
import sys
import os
import subprocess
from pathlib import Path
import shutil

REQUIRED_PACKAGES = [
    "PyGObject", "spotipy", "yt-dlp", "mutagen", "Pillow", "requests"
]

def check_ffmpeg():
    """Verifica se o FFmpeg está instalado no sistema (Funcionalidade 1)"""
    if not shutil.which("ffmpeg"):
        print("⚠️  AVISO: FFmpeg não encontrado!")
        print("O download funcionará, mas a conversão para MP3 e metadados falharão.")
        print("No Fedora, instale com: sudo dnf install ffmpeg")
        return False
    return True

def ensure_venv():
    project_dir = Path(__file__).parent.absolute()
    venv_dir = project_dir / '.venv'
    
    # Se já estamos no venv, apenas segue
    if os.environ.get('VIRTUAL_ENV') == str(venv_dir):
        return

    # Cria requirements se não existir
    req_file = project_dir / 'src' / 'requirements.txt'
    if not req_file.exists():
        with open(req_file, 'w') as f:
            f.write('\n'.join(REQUIRED_PACKAGES))

    venv_python = venv_dir / 'bin' / 'python'
    
    if not venv_dir.exists():
        print("📦 Criando ambiente virtual...")
        subprocess.check_call([sys.executable, '-m', 'venv', '--system-site-packages', str(venv_dir)])
    
    print("🔧 Verificando bibliotecas Python...")
    try:
        subprocess.check_call([str(venv_python), '-m', 'pip', 'install', '-r', str(req_file), '-q'])
    except:
        print("⚠️ Erro na instalação de dependências via pip.")

    print("🚀 Iniciando aplicação...")
    
    # Re-executa dentro do VENV
    env = os.environ.copy()
    env['VIRTUAL_ENV'] = str(venv_dir)
    env['PATH'] = f"{str(venv_dir / 'bin')}:{env.get('PATH', '')}"
    
    try:
        os.chdir(project_dir)
        os.execve(str(venv_python), [str(venv_python), '-m', 'src.entry'] + sys.argv[1:], env)
    except OSError as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_ffmpeg()
    ensure_venv()