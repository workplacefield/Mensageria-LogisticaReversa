# solicitar_coletas.py

import customtkinter as ctk
from tkinter import filedialog, messagebox
import pandas as pd
from datetime import datetime
import webbrowser

from requests import Session
from zeep import Client
from zeep.transports import Transport
from zeep.helpers import serialize_object  # usado só em erros p/ debug

from config import (
    WSDL_URL,
    COD_ADMIN,
    COD_SERVICO,
    CARTAO,
    USUARIO,
    SENHA,
    DESTINATARIO_FIXO,
    EMBALAGEM_CODIGO,
    EMBALAGEM_TIPO,
    EMBALAGEM_QTD,
    NUMERO_CONTRATO,  # só para exibir na UI
)

# opcional: envio via Digisac (AGORA POR NÚMERO)
try:
    from digisac_client import enviar_whatsapp_por_numero
    TEM_DIGISAC = True
except ImportError:
    TEM_DIGISAC = False


# =========================
# CONFIG VISUAL DO APP
# =========================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


# =========================
# TEMPLATE DA MENSAGEM WHATS (EDITÁVEL NA UI)
# =========================
TEMPLATE_WHATS_DEFAULT = (
    "Olá, *{NOME_COLABORADOR}*\n\n"
    "Por meio deste, informamos que o processo de devolução do(s) seguinte(s) "
    "equipamento(s) foi iniciado:\n\n"
    "*Patrimônio:* {ATIVO}\n"
    "*Equipamento:* {EQUIPAMENTO}\n\n"
    "Para realizar a devolução, dirija-se a uma agência dos Correios e informe o "
    "seguinte código de postagem: *{CODIGO_ETICKET}*.\n\n"
    "Este código é válido por *24 horas* e já inclui a embalagem, que será fornecida no local.\n\n"
    "*Importante:* Caso o equipamento não seja devolvido dentro do período estipulado, "
    "informamos que a falta de retorno do ativo acarretará cobrança extrajudicial.\n\n"
    "*Atenção:* Se você estiver em período de aviso prévio, por favor, nos comunique "
    "para que possamos gerar um novo código de postagem com validade futura.\n\n"
    "*Após a postagem, envie o comprovante com o código de rastreio para este canal "
    "para que possamos acompanhar o retorno do equipamento.*\n\n"
    "Time Gestão de Ativos."
)

TEMPLATE_WHATS = TEMPLATE_WHATS_DEFAULT


# =========================
# FUNÇÕES CORE – CORREIOS
# =========================
def criar_cliente_soap():
    session = Session()
    session.auth = (USUARIO, SENHA)
    transport = Transport(session=session)
    client = Client(WSDL_URL, transport=transport)
    return client


def _extrair_ddd_telefone_de_uma_coluna(tel_raw: str):
    """
    Recebe qualquer coisa em TELEFONE (com ou sem +55, espaços, etc)
    e devolve (ddd, telefone) para o payload dos Correios.

    Regras:
      - Mantém apenas dígitos
      - Se começar com 55, remove o 55
      - Se tiver 10 ou 11 dígitos, assume DDD = 2 primeiros
      - Caso contrário, devolve ("", "") para sinalizar inválido
    """
    s = str(tel_raw or "")
    digits = "".join(ch for ch in s if ch.isdigit())

    if digits.startswith("55"):
        digits = digits[2:]

    if len(digits) in (10, 11):
        ddd = digits[:2]
        telefone = digits[2:]
        return ddd, telefone

    return "", ""


def montar_remetente(row):
    cep_raw = str(row["CEP"])
    cep_numerico = "".join(ch for ch in cep_raw if ch.isdigit()).zfill(8)

    # Agora: UMA coluna TELEFONE (sem coluna DDD)
    ddd_digits, tel_digits = _extrair_ddd_telefone_de_uma_coluna(row.get("TELEFONE", ""))

    remetente = {
        "nome": row["NOME_COLABORADOR"],
        "logradouro": row["LOGRADOURO"],
        "numero": str(row["NUMERO"]),
        "complemento": row.get("COMPLEMENTO", "") or "",
        "bairro": row["BAIRRO"],
        "referencia": "",
        "cidade": row["CIDADE"],
        "uf": row["UF"],
        "cep": cep_numerico,
        "ddd": str(ddd_digits),
        "telefone": str(tel_digits),
        "email": row.get("EMAIL", "") or "",
        "identificacao": str(row.get("CPF", "")) or "",
        "documento_estrangeiro": "",
        "celular": "",
        "ddd_celular": "",
        "sms": "N",
        "restricao_anac": "S",
    }
    return remetente


def montar_coleta(row, remetente):
    VALOR_MINIMO = 25.63
    try:
        valor_planilha = float(row.get("VALOR_DECLARADO", 0) or 0)
    except Exception:
        valor_planilha = 0.0

    valor_declarado = max(VALOR_MINIMO, valor_planilha)

    produtos = []
    if EMBALAGEM_CODIGO and EMBALAGEM_TIPO and EMBALAGEM_QTD:
        produtos.append(
            {
                "codigo": EMBALAGEM_CODIGO,
                "tipo": EMBALAGEM_TIPO,
                "qtd": int(EMBALAGEM_QTD),
            }
        )

    coleta = {
        "tipo": "A",
        "numero": "",
        "id_cliente": str(row["ID_DEVOLUCAO"]),
        "ag": "",
        "cartao": "",
        "valor_declarado": valor_declarado,
        "servico_adicional": "",
        "descricao": "Devolução de equipamento corporativo",
        "ar": "",
        "cklist": "",
        "documento": "",
        "remetente": remetente,
        "produto": produtos,
        "obj_col": [
            {
                "item": 1,
                "id": str(row["ID_DEVOLUCAO"]),
                "desc": "Equipamento corporativo",
                "entrega": "",
                "num": "",
            }
        ],
    }
    return coleta


# =========================
# INTERFACE TKINTER
# =========================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Logística Reversa - Correios")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        self.excel_path = None

        # layout estilo RPA: coluna 0 fixa (sidebar), coluna 1 expansiva
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar (mesma cor do RPA)
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color="#111827")
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        # Main container com cantos arredondados e fundo escuro
        self.main_frame = ctk.CTkFrame(self, corner_radius=16, fg_color="#020617")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self._montar_sidebar()
        self._montar_logs()

    # -----------------------------------
    # SIDEBAR
    # -----------------------------------
    def _montar_sidebar(self):
        titulo = ctk.CTkLabel(
            self.sidebar,
            text="Logística Reversa",
            font=("Segoe UI", 24, "bold"),
        )
        titulo.pack(pady=(25, 4), padx=20, anchor="w")

        subt = ctk.CTkLabel(
            self.sidebar,
            text="Geração de código Correios\nWorkplace Empresa",
            font=("Segoe UI", 11),
            text_color="#9CA3AF",
            justify="left",
        )
        subt.pack(pady=(0, 18), padx=20, anchor="w")

        def label(text):
            return ctk.CTkLabel(self.sidebar, text=text, anchor="w", font=("Segoe UI", 11))

        # Código administrativo
        label("Código Administrativo").pack(pady=(4, 0), padx=24, anchor="w")
        self.entry_cod_admin = ctk.CTkEntry(
            self.sidebar,
            state="disabled",
            fg_color="#020617",
            text_color="#E5E7EB",
            border_color="#4B5563",
        )
        self.entry_cod_admin.pack(pady=(6, 10), padx=24, fill="x")
        self.entry_cod_admin.configure(state="normal")
        self.entry_cod_admin.insert(0, COD_ADMIN)
        self.entry_cod_admin.configure(state="disabled")

        # Cartão
        label("Cartão de Postagem").pack(pady=(0, 0), padx=24, anchor="w")
        self.entry_cartao = ctk.CTkEntry(
            self.sidebar,
            state="disabled",
            fg_color="#020617",
            text_color="#E5E7EB",
            border_color="#4B5563",
        )
        self.entry_cartao.pack(pady=(6, 10), padx=24, fill="x")
        self.entry_cartao.configure(state="normal")
        self.entry_cartao.insert(0, CARTAO)
        self.entry_cartao.configure(state="disabled")

        # Contrato
        label("Contrato").pack(pady=(0, 0), padx=24, anchor="w")
        self.entry_contrato = ctk.CTkEntry(
            self.sidebar,
            state="disabled",
            fg_color="#020617",
            text_color="#E5E7EB",
            border_color="#4B5563",
        )
        self.entry_contrato.pack(pady=(6, 10), padx=24, fill="x")
        self.entry_contrato.configure(state="normal")
        self.entry_contrato.insert(0, NUMERO_CONTRATO)
        self.entry_contrato.configure(state="disabled")

        # Destino
        label("Endereço de Destino").pack(pady=(0, 0), padx=24, anchor="w")
        self.destino_box = ctk.CTkTextbox(
            self.sidebar,
            height=92,
            fg_color="#020617",
            text_color="#E5E7EB",
            corner_radius=10,
        )
        self.destino_box.pack(pady=(6, 12), padx=24, fill="x")
        self._preencher_destino()

        # Botão selecionar planilha
        self.btn_excel = ctk.CTkButton(
            self.sidebar,
            text="Selecionar Planilha",
            fg_color="#4C1D95",
            hover_color="#7C3AED",
            height=34,
            font=("Segoe UI", 11),
            command=self.selecionar_excel,
        )
        self.btn_excel.pack(pady=(6, 4), padx=24, fill="x")

        self.lbl_excel = ctk.CTkLabel(
            self.sidebar,
            text="Nenhuma planilha selecionada",
            font=("Segoe UI", 10),
            text_color="#9CA3AF",
        )
        self.lbl_excel.pack(pady=(0, 10), padx=24, anchor="w")

        # Botão editar modelo (mesma cor do Selecionar Planilha)
        self.btn_editar_modelo = ctk.CTkButton(
            self.sidebar,
            text="Editar modelo...",
            fg_color="#4C1D95",
            hover_color="#7C3AED",
            height=34,
            font=("Segoe UI", 11),
            command=self.abrir_editor_modelo,
        )
        self.btn_editar_modelo.pack(pady=(8, 12), padx=24, fill="x")

        # Iniciar
        self.btn_iniciar = ctk.CTkButton(
            self.sidebar,
            text="🚀 Iniciar Geração",
            fg_color="#A855F7",
            hover_color="#7C3AED",
            height=46,
            font=("Segoe UI", 14, "bold"),
            command=self.iniciar_automacao,
        )
        self.btn_iniciar.pack(pady=(10, 10), padx=24, fill="x")

        self.lbl_status = ctk.CTkLabel(
            self.sidebar,
            text="Status: aguardando início",
            font=("Segoe UI", 9),
            text_color="#6B7280",
        )
        self.lbl_status.pack(side="bottom", pady=(4, 2), padx=20, anchor="w")

        if not TEM_DIGISAC:
            aviso = ctk.CTkLabel(
                self.sidebar,
                text="⚠ Módulo Digisac não encontrado.\nEnvio de WhatsApp desativado.",
                text_color="orange",
                font=("Segoe UI", 10),
                justify="left",
            )
            aviso.pack(side="bottom", pady=(0, 8), padx=20, anchor="w")

        # Marca d'água + LinkedIn (igual ao RPA)
        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.pack(side="bottom", pady=(2, 8), padx=16, anchor="w")

        watermark = ctk.CTkLabel(
            footer,
            text="Criado por Gustavo Alves - Workplace",
            font=("Segoe UI", 9),
            text_color="#6B7280",
        )
        watermark.pack(side="left")

        linkedin_btn = ctk.CTkButton(
            footer,
            text="in",
            width=26,
            height=22,
            corner_radius=6,
            fg_color="#0A66C2",
            hover_color="#004182",
            font=("Segoe UI", 11, "bold"),
            command=lambda: webbrowser.open_new_tab(
                "https://www.linkedin.com/in/gustavo-alves-7971a9156/"
            ),
        )
        linkedin_btn.pack(side="left", padx=(6, 0))

    def _preencher_destino(self):
        texto = (
            f"{DESTINATARIO_FIXO['nome']}\n"
            f"{DESTINATARIO_FIXO['logradouro']}, {DESTINATARIO_FIXO['numero']} "
            f"{DESTINATARIO_FIXO.get('complemento', '')}\n"
            f"{DESTINATARIO_FIXO['bairro']} - "
            f"{DESTINATARIO_FIXO['cidade']}/{DESTINATARIO_FIXO['uf']}\n"
            f"CEP: {DESTINATARIO_FIXO['cep']}"
        )
        self.destino_box.configure(state="normal")
        self.destino_box.delete("1.0", "end")
        self.destino_box.insert("1.0", texto)
        self.destino_box.configure(state="disabled")

    # -----------------------------------
    # EDITOR DE MODELO
    # -----------------------------------
    def abrir_editor_modelo(self):
        editor = ctk.CTkToplevel(self)
        editor.title("Editar modelo de mensagem (WhatsApp)")
        editor.geometry("820x620")
        editor.grab_set()
        editor.configure(fg_color="#020617")

        ctk.CTkLabel(
            editor,
            text=(
                "Edite o texto da mensagem enviada via WhatsApp (Digisac).\n"
                "Placeholders disponíveis: {NOME_COLABORADOR}, {ATIVO}, {EQUIPAMENTO}, {CODIGO_ETICKET}"
            ),
            font=("Segoe UI", 11),
            justify="left",
        ).pack(pady=(12, 8), padx=12, anchor="w")

        textbox = ctk.CTkTextbox(
            editor,
            wrap="word",
            fg_color="#111827",
            text_color="#E5E7EB",
            font=("Consolas", 11),
            corner_radius=12,
        )
        textbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        textbox.insert("1.0", TEMPLATE_WHATS)

        btn_frame = ctk.CTkFrame(editor, fg_color="#020617")
        btn_frame.pack(pady=(0, 14))

        def salvar():
            global TEMPLATE_WHATS
            novo = textbox.get("1.0", "end").rstrip("\n")
            TEMPLATE_WHATS = novo or TEMPLATE_WHATS_DEFAULT
            self.log("Modelo de WhatsApp atualizado na sessão atual.")
            editor.destroy()

        def restaurar():
            global TEMPLATE_WHATS
            TEMPLATE_WHATS = TEMPLATE_WHATS_DEFAULT
            textbox.delete("1.0", "end")
            textbox.insert("1.0", TEMPLATE_WHATS)
            self.log("Modelo de WhatsApp restaurado para o padrão.")

        btn_salvar = ctk.CTkButton(
            btn_frame,
            text="Salvar",
            fg_color="#22C55E",
            hover_color="#16A34A",
            font=("Segoe UI", 11, "bold"),
            command=salvar,
        )
        btn_salvar.pack(side="left", padx=6)

        btn_reset = ctk.CTkButton(
            btn_frame,
            text="Restaurar padrão",
            fg_color="#6B7280",
            hover_color="#4B5563",
            font=("Segoe UI", 11),
            command=restaurar,
        )
        btn_reset.pack(side="left", padx=6)

    # -----------------------------------
    # LOGS E PROGRESSO
    # -----------------------------------
    def _montar_logs(self):
        titulo_logs = ctk.CTkLabel(
            self.main_frame,
            text="Logs da Execução",
            font=("Segoe UI", 20, "bold"),
        )
        titulo_logs.grid(row=0, column=0, padx=20, pady=(16, 4), sticky="w")

        progress_container = ctk.CTkFrame(self.main_frame, fg_color="#020617")
        progress_container.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        progress_container.grid_columnconfigure(0, weight=1)

        self.progressbar = ctk.CTkProgressBar(
            progress_container,
            height=10,
            fg_color="#111827",
            progress_color="#A855F7",
        )
        self.progressbar.grid(row=0, column=0, sticky="ew", padx=4, pady=(8, 0))
        self.progressbar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_container,
            text="0% concluído",
            font=("Segoe UI", 11),
        )
        self.progress_label.grid(row=1, column=0, sticky="w", padx=4, pady=(2, 8))

        self.log_box = ctk.CTkTextbox(
            self.main_frame,
            fg_color="#111827",
            text_color="#E5E7EB",
            font=("Consolas", 11),
            corner_radius=12,
        )
        self.log_box.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log("Interface pronta. Selecione a planilha para iniciar.")

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"• {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def set_status(self, msg):
        self.lbl_status.configure(text=f"Status: {msg}")
        self.update_idletasks()

    def set_progress(self, value, total):
        frac = value / total if total else 0
        self.progressbar.set(frac)
        self.progress_label.configure(text=f"{int(frac * 100)}% concluído")
        self.update_idletasks()

    # -----------------------------------
    # BOTÕES
    # -----------------------------------
    def selecionar_excel(self):
        path = filedialog.askopenfilename(
            title="Selecione a planilha (.xlsx)",
            filetypes=[("Excel", "*.xlsx")],
        )
        if path:
            self.excel_path = path
            self.lbl_excel.configure(text=path)
            self.log(f"Planilha selecionada: {path}")
        else:
            self.log("Nenhum arquivo selecionado.")

    def iniciar_automacao(self):
        if not self.excel_path:
            messagebox.showwarning("Atenção", "Selecione uma planilha primeiro.")
            return

        try:
            self.rodar_logistica()
        except Exception as e:
            self.log(f"Erro inesperado: {e}")
            messagebox.showerror("Erro", str(e))

    # -----------------------------------
    # PROCESSAMENTO PRINCIPAL
    # -----------------------------------
    def rodar_logistica(self):
        self.set_status("lendo planilha...")
        df = pd.read_excel(self.excel_path)

        # (novo) colunas de status do WhatsApp
        if "STATUS_WHATS" not in df.columns:
            df["STATUS_WHATS"] = ""
        if "DATA_WHATS" not in df.columns:
            df["DATA_WHATS"] = ""

        pendentes = df[df["COD_E_TICKET"].isna() | (df["COD_E_TICKET"] == "")]
        total = len(pendentes)

        if total == 0:
            self.log("Nenhuma devolução pendente.")
            self.set_status("nenhuma pendência")
            return

        self.log(f"{total} devoluções pendentes encontradas.")
        self.set_status("conectando aos Correios...")

        client = criar_cliente_soap()
        self.set_status("processando solicitações...")

        processados = 0

        for idx, row in pendentes.iterrows():
            self.log(
                f"Processando ID {row['ID_DEVOLUCAO']} ({row['NOME_COLABORADOR']})..."
            )

            remetente = montar_remetente(row)
            coleta = montar_coleta(row, remetente)

            payload = {
                "codAdministrativo": COD_ADMIN,
                "codigo_servico": COD_SERVICO,
                "cartao": CARTAO,
                "destinatario": DESTINATARIO_FIXO,
                "coletas_solicitadas": [coleta],
            }

            try:
                resposta = client.service.solicitarPostagemReversa(**payload)
                resultado_list = getattr(resposta, "resultado_solicitacao", None)

                if not resultado_list:
                    resp_dict = serialize_object(resposta)
                    self.log(
                        f"⚠ Correios não retornaram 'resultado_solicitacao'. "
                        f"Debug: {resp_dict}"
                    )
                    continue

                if isinstance(resultado_list, list):
                    resultado = resultado_list[0]
                else:
                    resultado = resultado_list

                codigo_erro = int(getattr(resultado, "codigo_erro", 0) or 0)
                descricao_erro = getattr(resultado, "descricao_erro", "")

                if codigo_erro != 0:
                    resp_dict = serialize_object(resposta)
                    self.log(
                        f"⚠ Erro Correios: {codigo_erro} - {descricao_erro} "
                        f"(debug: {resp_dict})"
                    )
                    continue

                codigo_eticket = (
                    getattr(resultado, "numero_coleta", None)
                    or getattr(resultado, "numero_etiqueta", None)
                )

                if not codigo_eticket:
                    resp_dict = serialize_object(resposta)
                    self.log(
                        "⚠ Chamada OK, mas nenhum código retornado em "
                        "'numero_coleta/numero_etiqueta'. "
                        f"Debug: {resp_dict}"
                    )
                    continue

                # Atualiza planilha (Correios OK)
                df.at[idx, "COD_E_TICKET"] = codigo_eticket
                df.at[idx, "STATUS"] = "CODIGO_GERADO"
                df.at[idx, "DATA_CODIGO"] = datetime.today().strftime("%Y-%m-%d")

                self.log(f"✅ Código gerado: {codigo_eticket}")

                # ============================
                # ENVIO OPCIONAL VIA DIGISAC (POR TELEFONE)
                # - STATUS_WHATS:
                #   - NUMERO_INEXISTENTE  (telefone inválido)
                #   - VERIFICAR_ENVIO     (erro HTTP / API / pode ter enviado ou não)
                #   - WHATS_ENVIADO       (sucesso)
                # ============================
                if TEM_DIGISAC:
                    tel_raw = str(row.get("TELEFONE", "") or "")
                    tel_digits = "".join(ch for ch in tel_raw if ch.isdigit())

                    # valida mínimo (com DDD)
                    if len(tel_digits) < 10:
                        self.log("ℹ TELEFONE inválido ou inexistente; WhatsApp não enviado.")
                        df.at[idx, "STATUS_WHATS"] = "NUMERO_INEXISTENTE"
                        df.at[idx, "DATA_WHATS"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        # E.164
                        if tel_digits.startswith("55"):
                            numero_e164 = tel_digits
                        else:
                            numero_e164 = f"55{tel_digits}"

                        nome_colab = str(row.get("NOME_COLABORADOR", "")).strip()
                        patrimonio = str(row.get("ATIVO", "")).strip()
                        equipamento = str(row.get("EQUIPAMENTO", "")).strip()

                        ctx = {
                            "NOME_COLABORADOR": nome_colab,
                            "ATIVO": patrimonio,
                            "EQUIPAMENTO": equipamento,
                            "CODIGO_ETICKET": codigo_eticket,
                        }

                        try:
                            texto_whats = TEMPLATE_WHATS.format(**ctx)
                        except Exception:
                            texto_whats = TEMPLATE_WHATS_DEFAULT.format(**ctx)

                        try:
                            ok, resp = enviar_whatsapp_por_numero(numero_e164, texto_whats)
                            if ok:
                                self.log(f"📲 WhatsApp enviado via Digisac (número={numero_e164}).")
                                df.at[idx, "STATUS_WHATS"] = "WHATS_ENVIADO"
                            else:
                                self.log(f"⚠ Falha ao enviar WhatsApp via Digisac para {numero_e164}: {resp}")
                                df.at[idx, "STATUS_WHATS"] = "VERIFICAR_ENVIO"
                        except Exception as e:
                            self.log(f"⚠ Erro HTTP / conexão ao enviar WhatsApp para {numero_e164}: {e}")
                            df.at[idx, "STATUS_WHATS"] = "VERIFICAR_ENVIO"

                        df.at[idx, "DATA_WHATS"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

            except Exception as e:
                try:
                    resp_dict = serialize_object(resposta)  # pode não existir
                    self.log(f"❌ Erro na solicitação: {e} | Debug: {resp_dict}")
                except Exception:
                    self.log(f"❌ Erro na solicitação: {e}")

            processados += 1
            self.set_progress(processados, total)

        try:
            df.to_excel(self.excel_path, index=False)
            self.log("Planilha atualizada com sucesso!")
            self.set_status("concluído")
        except PermissionError:
            self.log("⚠ Não foi possível salvar. Feche o Excel e tente novamente.")
            self.set_status("erro ao salvar")


if __name__ == "__main__":
    app = App()
    app.mainloop()
