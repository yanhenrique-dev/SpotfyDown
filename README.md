<div align="center">

# 🎵 Spotify Downloader

**Baixe músicas, álbuns, playlists e discografias completas do Spotify**  
com qualidade de MP3 ou FLAC, metadados automáticos e capa do álbum.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![GTK4](https://img.shields.io/badge/GTK-4%20%2B%20libadwaita-green?logo=gnome)
![License](https://img.shields.io/badge/license-GPL--3.0-blue)
![Tests](https://img.shields.io/badge/tests-23%20passed-brightgreen)

</div>

---

## ✨ Funcionalidades

- 🔗 **Cole qualquer link do Spotify** — faixa, álbum, playlist ou artista
- 🎤 **Discografia completa** — baixe todos os álbuns e singles de um artista de uma vez
- 🎧 **MP3 e FLAC** — escolha o formato e qualidade nas configurações
- 🏷️ **Metadados automáticos** — título, artista, álbum, ano, faixa e capa incorporados
- 🔍 **Filtro em tempo real** — pesquise entre as faixas carregadas antes de baixar
- ✅ **Seleção granular** — escolha quais faixas baixar, não precisa baixar tudo
- ⏩ **Downloads paralelos** — múltiplas faixas baixadas simultaneamente (configurável)
- 💾 **Skip inteligente** — pula faixas que já existem na pasta de destino
- 🔐 **Credenciais seguras** — segredo armazenado com `keyring` do sistema

---

## 📸 Interface

> App GTK4/libadwaita — segue o design do GNOME, com suporte a tema escuro automático.

---

## 🚀 Instalação

### Pré-requisitos

| Dependência | Versão | Como instalar |
|-------------|--------|---------------|
| Python | 3.11+ | Geralmente já incluso |
| FFmpeg | qualquer | `sudo dnf install ffmpeg` / `sudo apt install ffmpeg` |
| GTK4 + libadwaita | — | `sudo dnf install python3-gobject libadwaita` |

### Clonar e executar

```bash
git clone https://github.com/yanhenrique-dev/SpotifyDownloader.git
cd SpotifyDownloader
python main.py
```

Na primeira execução, o `main.py` cria automaticamente o `.venv` e instala as dependências Python.

---

## ⚙️ Configuração (obrigatória)

Para usar a API do Spotify você precisa de credenciais gratuitas:

1. Acesse [Developer Dashboard](https://developer.spotify.com/dashboard) e crie um app
2. Defina o **Redirect URI** como `http://localhost:8080`
3. Copie o **Client ID** e o **Client Secret**
4. Abra ⚙️ Configurações dentro do app e cole as credenciais

> O **Client Secret** é armazenado com segurança pelo `keyring` do sistema operacional — nunca em texto puro.

---

## 📁 Estrutura do Projeto

```
SpotifyDownloader/
├── main.py                  # Entry point — cria venv e inicia o app
└── src/
    ├── config.py            # Configurações + keyring
    ├── entry.py             # Inicializa GTK e Adw.Application
    ├── requirements.txt
    ├── core/
    │   ├── spotify.py       # Wrapper da API Spotify (faixa/álbum/playlist/artista)
    │   ├── downloader.py    # Download via yt-dlp + metadados (MP3/FLAC)
    │   └── download_manager.py  # Fila de downloads paralelos (ThreadPoolExecutor)
    └── ui/
        ├── app.py           # Orquestrador principal (GTK ApplicationWindow)
        ├── search_page.py   # Página de busca (URL entry + chip de tipo)
        ├── results_page.py  # Lista de faixas + filtro + toolbar
        ├── settings_dialog.py  # Janela de preferências
        └── components.py    # Widgets reutilizáveis (TrackRow, etc.)
```

---

## 🧪 Testes

```bash
# Instalar dependências de teste
.venv/bin/pip install pytest pytest-mock

# Executar
.venv/bin/python -m pytest tests/ -v
```

```
23 passed in 0.79s ✅
```

---

## 🛠️ Dependências Python

| Pacote | Uso |
|--------|-----|
| `spotipy` | API do Spotify |
| `yt-dlp` | Download de áudio |
| `mutagen` | Tags ID3 / FLAC |
| `Pillow` | Processamento da capa do álbum |
| `PyGObject` | GTK4 + libadwaita |
| `keyring` | Armazenamento seguro de credenciais |
| `requests` | Download da imagem de capa |

---

## ⚖️ Aviso Legal

Este projeto é para **uso pessoal e educacional**. Certifique-se de ter direito de acesso ao conteúdo que baixar. O uso comercial do conteúdo do Spotify é proibido pelos [Termos de Serviço](https://www.spotify.com/legal/end-user-agreement/) da plataforma.

---

## 📝 Licença

Lançado sob a licença **GNU GPLv3**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
