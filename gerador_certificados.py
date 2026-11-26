import datetime
import ipaddress
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

APP_NAME = "Gerador de Certificados"
COR_PRIMARIA = "#13347d"
COR_ACENTO = "#2563eb"
COR_ACENTO_HOVER = "#1d4ed8"
COR_FUNDO = "#f3f4f6"
COR_TEXTO_SUAVE = "#6b7280"
FONTE = "Segoe UI"

# Hostname válido (aceita curinga no início, ex.: *.empresa.local)
REGEX_DNS = re.compile(
    r"^(\*\.)?[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$"
)


def resource_path(rel):
    """Caminho de recursos, funciona no script e no .exe do PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# ----------------------------------------------------------------------
# Geração dos certificados
# ----------------------------------------------------------------------
def gerar_certificado(ips, dns_names, senha_pfx, nome_base, pasta, dias):
    """Gera .key, .crt e .pfx na pasta indicada."""
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # SAN: DNS names primeiro, depois IPs
    san = [x509.DNSName(d) for d in dns_names] + [x509.IPAddress(ip) for ip in ips]

    # CN = primeiro DNS name, ou primeiro IP se não houver DNS
    cn = dns_names[0] if dns_names else str(ips[0])
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])

    agora = datetime.datetime.now(datetime.timezone.utc)

    cert = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - datetime.timedelta(minutes=5))
        .not_valid_after(agora + datetime.timedelta(days=dias))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(chave, hashes.SHA256())
    )

    caminho_key = os.path.join(pasta, f"{nome_base}.key")
    caminho_crt = os.path.join(pasta, f"{nome_base}.crt")
    caminho_pfx = os.path.join(pasta, f"{nome_base}.pfx")

    # .key (PEM, sem senha)
    with open(caminho_key, "wb") as f:
        f.write(
            chave.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # .crt (PEM)
    with open(caminho_crt, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # .pfx (com senha ou sem senha, se o campo estiver em branco)
    if senha_pfx:
        enc = serialization.BestAvailableEncryption(senha_pfx.encode("utf-8"))
    else:
        enc = serialization.NoEncryption()

    with open(caminho_pfx, "wb") as f:
        f.write(
            pkcs12.serialize_key_and_certificates(
                name=nome_base.encode("utf-8"),
                key=chave,
                cert=cert,
                cas=None,
                encryption_algorithm=enc,
            )
        )

    return caminho_key, caminho_crt, caminho_pfx


# ----------------------------------------------------------------------
# Interface
# ----------------------------------------------------------------------
class ListaCampos(ttk.LabelFrame):
    """Lista dinâmica de campos de texto com botões + e –."""

    def __init__(self, parent, titulo, dica, texto_botao, valor_inicial=""):
        super().__init__(parent, text=f" {titulo} ", padding=(10, 6, 10, 8))
        ttk.Label(self, text=dica, style="Hint.TLabel").pack(anchor="w", pady=(0, 4))
        self.linhas = []
        self.container = ttk.Frame(self)
        self.container.pack(fill="x")
        ttk.Button(self, text=texto_botao, style="Link.TButton", command=self.adicionar).pack(
            anchor="w", pady=(6, 0)
        )
        self.adicionar(valor_inicial)

    def adicionar(self, valor=""):
        if not isinstance(valor, str):
            valor = ""
        frame = ttk.Frame(self.container)
        frame.pack(fill="x", pady=2)
        var = tk.StringVar(value=valor)
        entry = ttk.Entry(frame, textvariable=var, width=18)
        entry.pack(side="left", fill="x", expand=True)
        item = (frame, var)
        ttk.Button(frame, text="✕", width=3, style="Small.TButton",
                   command=lambda: self.remover(item)).pack(side="left", padx=(6, 0))
        self.linhas.append(item)
        if not valor:
            entry.focus_set()

    def remover(self, item):
        if len(self.linhas) <= 1:
            item[1].set("")  # mantém uma linha vazia
            return
        item[0].destroy()
        self.linhas.remove(item)

    def valores(self):
        """Valores preenchidos (sem espaços e sem campos vazios)."""
        return [v.get().strip() for _, v in self.linhas if v.get().strip()]


class ScrollFrame(ttk.Frame):
    """Área com rolagem vertical (a barra só aparece quando necessário)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=COR_FUNDO)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")

        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._ao_mudar_conteudo)
        self.canvas.bind("<Configure>", self._ao_mudar_canvas)

        # Roda do mouse (Windows/macOS e Linux)
        self.bind_all("<MouseWheel>", self._roda)
        self.bind_all("<Button-4>", lambda e: self._roda(e, 1))
        self.bind_all("<Button-5>", lambda e: self._roda(e, -1))

    def _ao_mudar_conteudo(self, _e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._atualizar_barra()

    def _ao_mudar_canvas(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)
        self._atualizar_barra()

    def _atualizar_barra(self):
        precisa = self.inner.winfo_reqheight() > self.canvas.winfo_height()
        if precisa:
            self.vsb.grid()
        else:
            self.vsb.grid_remove()
            self.canvas.yview_moveto(0)

    def _roda(self, e, direcao=None):
        if not self.vsb.winfo_ismapped():
            return
        if direcao is None:
            direcao = 1 if e.delta > 0 else -1
        self.canvas.yview_scroll(-direcao, "units")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.resizable(True, True)
        self.configure(bg=COR_FUNDO)
        self._definir_icone()
        self._estilos()

        self.var_senha = tk.StringVar()
        self.var_nome = tk.StringVar(value="certificado")
        self.var_pasta = tk.StringVar(value=os.path.expanduser("~"))
        self.var_dias = tk.StringVar(value="365")
        self.var_mostrar = tk.BooleanVar(value=False)
        self.var_status = tk.StringVar(value="Pronto para gerar.")

        self._montar_ui()
        self._ajustar_tamanho()
        self._centralizar()

    # ---------- aparência ----------
    def _definir_icone(self):
        # Ícone da barra de título / barra de tarefas
        if sys.platform.startswith("win"):
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "gerador.certificados.app"
                )
            except Exception:  # noqa: BLE001
                pass
            try:
                self.iconbitmap(resource_path("icone.ico"))
            except Exception:  # noqa: BLE001
                pass
        self._img_header = None
        try:
            img = tk.PhotoImage(file=resource_path("icone.png"))
            self._img_header = img.subsample(5, 5)  # ~51px no cabeçalho
            if not sys.platform.startswith("win"):
                self.iconphoto(True, img)
        except Exception:  # noqa: BLE001
            pass

    def _estilos(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=COR_FUNDO, font=(FONTE, 10))
        s.configure("TLabel", background=COR_FUNDO)
        s.configure("TCheckbutton", background=COR_FUNDO)
        s.configure("Hint.TLabel", foreground=COR_TEXTO_SUAVE, font=(FONTE, 9))
        s.configure("TLabelframe", background=COR_FUNDO, bordercolor="#d1d5db")
        s.configure("TLabelframe.Label", background=COR_FUNDO,
                    foreground=COR_PRIMARIA, font=(FONTE, 10, "bold"))
        s.configure("TEntry", padding=5, fieldbackground="white", bordercolor="#d1d5db")
        s.map("TEntry", bordercolor=[("focus", COR_ACENTO)])
        s.configure("TButton", padding=(10, 5))
        s.configure("Small.TButton", padding=(2, 4))
        s.configure("Link.TButton", background=COR_FUNDO, foreground=COR_ACENTO,
                    borderwidth=0, padding=(0, 2), font=(FONTE, 9, "bold"))
        s.map("Link.TButton", foreground=[("active", COR_ACENTO_HOVER)],
              background=[("active", COR_FUNDO)])
        s.configure("Accent.TButton", background=COR_ACENTO, foreground="white",
                    font=(FONTE, 11, "bold"), padding=(16, 10), borderwidth=0)
        s.map("Accent.TButton", background=[("active", COR_ACENTO_HOVER),
                                            ("pressed", COR_ACENTO_HOVER)])
        s.configure("Status.TLabel", background="#e5e7eb", foreground="#374151",
                    font=(FONTE, 9), padding=(12, 5))

    def _ajustar_tamanho(self):
        """Tamanho inicial = tamanho do conteúdo; depois a janela pode crescer/encolher."""
        self.update_idletasks()
        w = self.scroll.inner.winfo_reqwidth()
        h = self.scroll.inner.winfo_reqheight()
        altura_max = max(300, self.winfo_screenheight() - 220)
        self.scroll.canvas.configure(width=w, height=min(h, altura_max))
        self.update_idletasks()
        self.minsize(460, 400)

    def _centralizar(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = max(0, (self.winfo_screenheight() - h) // 2 - 30)
        self.geometry(f"+{x}+{y}")

    # ---------- layout ----------
    def _montar_ui(self):
        # Cabeçalho
        header = tk.Frame(self, bg=COR_PRIMARIA)
        header.pack(fill="x")
        if self._img_header:
            tk.Label(header, image=self._img_header, bg=COR_PRIMARIA).pack(
                side="left", padx=(16, 8), pady=10
            )
        textos = tk.Frame(header, bg=COR_PRIMARIA)
        textos.pack(side="left", pady=10)
        tk.Label(textos, text=APP_NAME, bg=COR_PRIMARIA, fg="white",
                 font=(FONTE, 15, "bold")).pack(anchor="w")
        tk.Label(textos, text="Crie arquivos .key, .crt e .pfx autoassinados",
                 bg=COR_PRIMARIA, fg="#bfdbfe", font=(FONTE, 9)).pack(anchor="w")

        # Barra de status e botão principal ficam fixos no rodapé
        ttk.Label(self, textvariable=self.var_status, style="Status.TLabel",
                  anchor="w").pack(fill="x", side="bottom")
        rodape = ttk.Frame(self, padding=(16, 8, 16, 10))
        rodape.pack(fill="x", side="bottom")
        ttk.Button(rodape, text="🔒  Gerar certificados", style="Accent.TButton",
                   command=self.gerar).pack(fill="x")

        # Conteúdo com rolagem
        self.scroll = ScrollFrame(self)
        self.scroll.pack(fill="both", expand=True)
        corpo = ttk.Frame(self.scroll.inner, padding=(16, 14, 16, 6))
        corpo.pack(fill="both", expand=True)

        # Identificação (IPs e DNS lado a lado)
        ident = ttk.Frame(corpo)
        ident.pack(fill="x")
        ident.columnconfigure((0, 1), weight=1, uniform="col")

        self.lista_ips = ListaCampos(
            ident, "Endereços IP", "Ex.: 192.168.0.10", "+ Adicionar IP", "127.0.0.1"
        )
        self.lista_ips.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.lista_dns = ListaCampos(
            ident, "DNS names", "Ex.: servidor.local ou *.empresa.local",
            "+ Adicionar DNS", "localhost"
        )
        self.lista_dns.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._ident = ident
        self._empilhado = False
        ident.bind("<Configure>", self._reflow_ident)

        # Arquivos de saída
        saida = ttk.LabelFrame(corpo, text=" Arquivos de saída ", padding=(10, 8, 10, 10))
        saida.pack(fill="x", pady=(12, 0))
        saida.columnconfigure(1, weight=1)

        ttk.Label(saida, text="Nome dos arquivos").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(saida, textvariable=self.var_nome).grid(
            row=0, column=1, sticky="ew", padx=(10, 0), pady=4
        )
        ttk.Label(saida, text=".key  .crt  .pfx", style="Hint.TLabel").grid(
            row=0, column=2, padx=(10, 0)
        )

        ttk.Label(saida, text="Senha do PFX").grid(row=1, column=0, sticky="w", pady=4)
        self.entry_senha = ttk.Entry(saida, textvariable=self.var_senha, show="•")
        self.entry_senha.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=4)
        ttk.Checkbutton(saida, text="Mostrar", variable=self.var_mostrar,
                        command=self._toggle_senha).grid(row=1, column=2, padx=(10, 0))
        ttk.Label(saida, text="Deixe em branco para gerar o PFX sem senha",
                  style="Hint.TLabel").grid(row=2, column=1, columnspan=2,
                                            sticky="w", padx=(10, 0))

        ttk.Label(saida, text="Validade (dias)").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(saida, textvariable=self.var_dias, width=10).grid(
            row=3, column=1, sticky="w", padx=(10, 0), pady=4
        )

        ttk.Label(saida, text="Pasta de destino").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(saida, textvariable=self.var_pasta).grid(
            row=4, column=1, sticky="ew", padx=(10, 0), pady=4
        )
        ttk.Button(saida, text="Procurar…", command=self.escolher_pasta).grid(
            row=4, column=2, padx=(10, 0)
        )


    def _reflow_ident(self, event):
        """Em janelas estreitas, coloca IPs e DNS um abaixo do outro."""
        necessario = self.lista_ips.winfo_reqwidth() + self.lista_dns.winfo_reqwidth() + 16
        empilhar = self._empilhado
        if not empilhar and event.width < necessario:
            empilhar = True
        elif empilhar and event.width >= necessario + 30:
            empilhar = False
        if empilhar == self._empilhado:
            return
        self._empilhado = empilhar
        if empilhar:
            self._ident.columnconfigure(0, weight=1, uniform="")
            self._ident.columnconfigure(1, weight=0, uniform="")
            self.lista_ips.grid_configure(row=0, column=0, padx=0, pady=(0, 10))
            self.lista_dns.grid_configure(row=1, column=0, padx=0, pady=0)
        else:
            self._ident.columnconfigure((0, 1), weight=1, uniform="col")
            self.lista_ips.grid_configure(row=0, column=0, padx=(0, 8), pady=0)
            self.lista_dns.grid_configure(row=0, column=1, padx=(8, 0), pady=0)

    # ---------- ações ----------
    def _toggle_senha(self):
        self.entry_senha.config(show="" if self.var_mostrar.get() else "•")

    def escolher_pasta(self):
        pasta = filedialog.askdirectory(initialdir=self.var_pasta.get() or os.getcwd())
        if pasta:
            self.var_pasta.set(os.path.normpath(pasta))

    def _erro(self, titulo, msg):
        self.var_status.set(f"✖ {msg}")
        messagebox.showerror(titulo, msg)

    def gerar(self):
        # IPs
        ips = []
        for texto in self.lista_ips.valores():
            try:
                ip = ipaddress.ip_address(texto)
            except ValueError:
                return self._erro("IP inválido", f"'{texto}' não é um endereço IP válido.")
            if ip not in ips:
                ips.append(ip)

        # DNS names
        dns_names = []
        for texto in self.lista_dns.valores():
            d = texto.lower().rstrip(".")
            if len(d) > 253 or not REGEX_DNS.match(d):
                return self._erro("DNS inválido", f"'{texto}' não é um nome DNS válido.")
            if d not in dns_names:
                dns_names.append(d)

        if not ips and not dns_names:
            return self._erro("Erro", "Informe ao menos um endereço IP ou um DNS name.")

        # Nome dos arquivos
        nome = self.var_nome.get().strip()
        if not nome:
            return self._erro("Erro", "Informe o nome dos arquivos.")
        if re.search(r'[\\/:*?"<>|]', nome):
            return self._erro("Erro", 'O nome não pode conter \\ / : * ? " < > |')

        # Validade
        try:
            dias = int(self.var_dias.get())
            if dias <= 0:
                raise ValueError
        except ValueError:
            return self._erro("Erro", "Validade deve ser um número inteiro positivo.")

        # Pasta
        pasta = self.var_pasta.get().strip()
        if not pasta or not os.path.isdir(pasta):
            return self._erro("Erro", "Selecione uma pasta de destino válida.")

        # Confirmar sobrescrita
        existentes = [
            f"{nome}{ext}"
            for ext in (".key", ".crt", ".pfx")
            if os.path.exists(os.path.join(pasta, f"{nome}{ext}"))
        ]
        if existentes and not messagebox.askyesno(
            "Sobrescrever?",
            "Os arquivos abaixo já existem:\n\n" + "\n".join(existentes) + "\n\nSobrescrever?",
        ):
            return

        self.var_status.set("Gerando certificados…")
        self.update_idletasks()
        try:
            gerar_certificado(ips, dns_names, self.var_senha.get(), nome, pasta, dias)
        except Exception as e:  # noqa: BLE001
            return self._erro("Erro ao gerar", str(e))

        senha_info = "com senha" if self.var_senha.get() else "sem senha"
        self.var_status.set(f"✔ Certificados gerados em {pasta} (PFX {senha_info})")
        if messagebox.askyesno(
            "Sucesso",
            f"Certificados gerados com sucesso!\n\n"
            f"  {nome}.key\n  {nome}.crt\n  {nome}.pfx\n\n"
            f"PFX {senha_info}.\n\nDeseja abrir a pasta?",
        ):
            self._abrir_pasta(pasta)

    @staticmethod
    def _abrir_pasta(pasta):
        try:
            if sys.platform.startswith("win"):
                os.startfile(pasta)  # noqa: S606
            elif sys.platform == "darwin":
                os.system(f'open "{pasta}"')
            else:
                os.system(f'xdg-open "{pasta}"')
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    App().mainloop()
