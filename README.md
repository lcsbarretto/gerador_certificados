# 🔒 Gerador de Certificados Autoassinados

Aplicativo desktop com interface gráfica (Python + Tkinter) para criar certificados **autoassinados** nos formatos `.key`, `.crt` e `.pfx`, com suporte a múltiplos endereços IP e DNS names.

<p align="center">
  <img src="icone.png" alt="Ícone do aplicativo" width="128">
</p>

## ✨ Funcionalidades

- Geração de `.key` (chave privada, PEM), `.crt` (certificado, PEM) e `.pfx` (PKCS#12) de uma só vez
- Múltiplos **endereços IP** (IPv4 e IPv6) e **DNS names**, incluindo curinga (`*.empresa.local`)
- Senha do PFX **opcional**: deixando o campo em branco, o PFX é gerado sem senha
- Nome dos arquivos, validade (em dias) e pasta de destino configuráveis
- Validação dos campos e confirmação antes de sobrescrever arquivos existentes
- Interface responsiva: a janela pode ser redimensionada, com rolagem quando necessário
- Pode ser empacotado em um único `.exe` para Windows

## 📋 Requisitos

- Python 3.9 ou superior (com Tkinter, que já vem na instalação padrão do Python no Windows e no macOS)
- Biblioteca [`cryptography`](https://pypi.org/project/cryptography/)

No Linux, o Tkinter pode precisar ser instalado à parte, por exemplo:

```bash
sudo apt install python3-tk
```

## 🚀 Como executar

```bash
# 1. Clone o repositório
git clone https://github.com/SEU_USUARIO/gerador-certificados.git
cd gerador-certificados

# 2. (Opcional) Crie um ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Execute
python gerador_certificados.py
```

> O `requirements.txt` inclui o `pyinstaller`, necessário apenas para gerar o `.exe`. Para só rodar o programa, `pip install cryptography` é suficiente.

## 🖥️ Como usar

1. Informe um ou mais **endereços IP** e/ou **DNS names** (é necessário ao menos um dos dois).
2. Defina o **nome dos arquivos** (sem extensão).
3. Informe a **senha do PFX**, ou deixe em branco para gerar sem senha.
4. Ajuste a **validade** e escolha a **pasta de destino**.
5. Clique em **Gerar certificados**.

Serão criados na pasta escolhida:

| Arquivo | Conteúdo |
|---------|----------|
| `nome.key` | Chave privada RSA 2048 (PEM, sem senha) |
| `nome.crt` | Certificado X.509 (PEM) |
| `nome.pfx` | Chave + certificado (PKCS#12), com ou sem senha |

### Detalhes do certificado

- Algoritmo: RSA 2048 bits, assinatura SHA-256
- Subject Alternative Name (SAN): todos os DNS names e IPs informados
- CN: primeiro DNS name informado (ou o primeiro IP, se não houver DNS)
- Uso: autenticação de servidor (`serverAuth`), `CA:FALSE`

## 📦 Gerando o executável (.exe)

No Windows, com o Python instalado (marcando "Add Python to PATH"), basta dar dois cliques no `build.bat`.

Ou, manualmente:

```bat
py -m pip install cryptography pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "GeradorCertificados" ^
  --icon "icone.ico" ^
  --add-data "icone.ico;." ^
  --add-data "icone.png;." ^
  gerador_certificados.py
```

O executável será criado em `dist\GeradorCertificados.exe`.

> Alguns antivírus podem marcar como suspeitos executáveis criados com o PyInstaller em modo de arquivo único (`--onefile`). É um falso positivo comum. Se acontecer, troque `--onefile` por `--onedir`.

## 🔐 Confiando no certificado

Como o certificado é **autoassinado**, navegadores e sistemas exibirão um aviso de segurança até que ele seja marcado como confiável. Para evitar o aviso, instale o `.crt` como autoridade confiável nas máquinas clientes (por exemplo, em "Autoridades de Certificação Raiz Confiáveis" no Windows).

## ⚠️ Segurança

- A chave privada (`.key`) é salva **sem senha**. Proteja o arquivo e não o compartilhe.
- **Nunca** envie arquivos `.key`, `.pfx` ou `.pem` para o repositório. O `.gitignore` deste projeto já os ignora.
- Certificados autoassinados são indicados para testes, desenvolvimento e redes internas. Para produção pública, use uma autoridade certificadora.

## 📁 Estrutura do projeto

```
.
├── gerador_certificados.py   # Aplicativo (interface + geração dos certificados)
├── build.bat                 # Script para gerar o .exe no Windows
├── requirements.txt          # Dependências
├── icone.ico                 # Ícone do executável
├── icone.png                 # Ícone usado na janela
├── .gitignore
└── README.md
```

## 📄 Licença

Defina aqui a licença do projeto (por exemplo, MIT) e adicione o arquivo `LICENSE` ao repositório.
