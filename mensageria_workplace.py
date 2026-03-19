# mensagens_ativos.py

import customtkinter as ctk
from tkinter import filedialog, messagebox
import pandas as pd
from datetime import datetime, date, time
import numpy as np  # para tratar numpy.datetime64
import webbrowser   # para abrir o LinkedIn

# Mesmo cliente Digisac já testado no outro script
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
# TEMPLATES DE MENSAGEM
# =========================

TEMPLATE_CONF_ENDERECO_DEFAULT = (
    "Olá *{NOME_COLABORADOR}*, tudo bem?\n\n"
    "Nós do Workplace estamos preparando seu equipamento para envio. "
    "Estamos enviando seu *{EQUIPAMENTO}* e precisamos que você confirme seu endereço "
    "para que tudo ocorra da melhor maneira.\n\n"
    "Por favor, verifique se as informações abaixo estão corretas:\n\n"
    "{LOGRADOURO}\n\n"
    "Esse endereço está correto? Se precisar fazer alguma alteração, por favor, "
    "nos envie o endereço atualizado.\n\n"
    "Aguardamos sua confirmação.\n\n"
    "Atenciosamente,\n"
    "Workplace Empresa."
)

TEMPLATE_RASTREIO_DEFAULT = (
    "Olá *{NOME_COLABORADOR}*, seu equipamento está pronto para envio!\n\n"
    "*Patrimônio:* {PATRIMONIO}\n\n"
    "*Código de rastreio:* {RASTREIO}\n\n"
    "Acesse o rastreamento pelo link:\n"
    "https://rastreamento.correios.com.br/app/index.php\n\n"
    "Se aparecer \"Objeto Não Localizado\", aguarde, pois ainda não foi postado.\n\n"
    "O login da rede é: *{USUARIO}* e a senha inicial é: *{SENHA}*.\n\n"
    "IMPORTANTE: Use apenas as credenciais desta mensagem. Não altere a senha antes do primeiro login.\n\n"
    "Para máquinas com padrão da empresa, faça o primeiro login com a senha padrão e, se necessário, "
    "sincronize a nova senha na VPN.\n\n"
    "Para colaboradores com clientes externos, entre em contato com sua Gestão "
    "para as credenciais corretas.\n\n"
    "Aproveitamos para lembrar que é necessário alterar a senha. Acesse o portal da empresa para realizar a alteração.\n\n"
    "Você receberá instruções adicionais no primeiro dia de trabalho para se cadastrar no sistema. "
    "Complete o cadastro dentro do prazo para evitar bloqueio.\n\n"
    "Confirme o recebimento do equipamento enviando um e-mail para "
    "suporte@suaempresa.com e siga as instruções do Termo de Responsabilidade.\n\n"
    "Atenciosamente,\n"
    "Equipe Workplace.\n\n"
    "*Segue em anexo link com vídeo de boas-vindas:*\n"
    "https://link-do-video-de-boas-vindas"
)

TEMPLATE_AGENDAMENTO_DEFAULT = (
    "Olá, *{NOME_COLABORADOR}*!\n\n"
    "Tudo bem com você?\n\n"
    "Estamos muito felizes em ter você conosco! Para que você comece sua jornada da melhor forma, "
    "já preparamos o seu equipamento.\n\n"
    "Aqui estão os detalhes:\n\n"
    "*Patrimônio:* {ATIVO}\n"
    "*Equipamento:* {EQUIPAMENTO}\n\n"
    "Retirada: *Filial Empresa*\n\n"
    "Quando: *{DATA_RETIRADA}*\n\n"
    "Horário: *{HORARIO_RETIRADA}*\n\n"
    "Endereço: Endereço da Empresa, 1000 - Bairro - Cidade.\n\n"
    "Ah, e para garantir que você leve seu equipamento com conforto, sugerimos trazer uma mochila ou bolsa "
    "para transportá-lo com segurança.\n\n"
    "Informações do equipamento:\n\n"
    "Usuário: *{LOGIN_REDE}*\n"
    "Senha: *{SENHA_INICIAL}*\n\n"
    "Aqui valorizamos o feedback para sempre evoluirmos!\n\n"
    "Sua opinião é super importante, então se puder, deixe um comentário sobre o serviço clicando no link do formulário da empresa.\n\n"
    "Para começar a se sentir em casa, também anexamos um vídeo de boas-vindas. Não deixe de conferir!\n\n"
    "Estamos aqui para o que precisar.\n\n"
    "Abraços,\n"
    "Time Workplace."
)

# variáveis editáveis em runtime pela UI
TEMPLATE_CONF_ENDERECO = TEMPLATE_CONF_ENDERECO_DEFAULT
TEMPLATE_RASTREIO = TEMPLATE_RASTREIO_DEFAULT
TEMPLATE_AGENDAMENTO = TEMPLATE_AGENDAMENTO_DEFAULT


# =========================
# HELPERS DE FORMATAÇÃO
# =========================

def formatar_data(valor):
    """Formata datas em DD/MM/AAAA, removendo hora caso venha junto."""
    if pd.isna(valor):
        return ""

    # datetime / Timestamp / numpy.datetime64
    if isinstance(valor, (datetime, pd.Timestamp, np.datetime64)):
        dt = pd.to_datetime(valor)
        return dt.strftime("%d/%m/%Y")

    # date puro
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")

    s = str(valor).strip()
    if not s:
        return ""

    # Tentar com pandas, aceitando vários formatos
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="raise")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        pass

    # Se vier como "2025-12-10 00:00:00"
    if " " in s:
        s = s.split(" ")[0]

    # Se vier como "2025-12-10"
    if "-" in s:
        partes = s.split("-")
        if len(partes) == 3 and len(partes[0]) == 4:
            yyyy, mm, dd = partes
            return f"{dd}/{mm}/{yyyy}"

    # Último caso: devolve como está
    return s


def formatar_horario(valor):
    """Formata horários em HH:MM, removendo segundos se existirem."""
    if pd.isna(valor):
        return ""

    # datetime / Timestamp
    if isinstance(valor, (datetime, pd.Timestamp)):
        return valor.strftime("%H:%M")

    # time puro
    if isinstance(valor, time):
        return valor.strftime("%H:%M")

    s = str(valor).strip()
    if not s:
        return ""

    # Se vier "HH:MM:SS"
    if len(s) >= 8 and s[2] == ":" and s[5] == ":":
        return s[:5]

    # Se vier "HH:MM"
    if len(s) >= 5 and s[2] == ":":
        return s[:5]

    # Número puro (ex: 900 ou 930) – devolve cru
    return s


# =========================
# FUNÇÕES DE TEXTO
# =========================

def montar_texto_confirmacao_endereco(row):
    nome = str(row.get("NOME_COLABORADOR", "")).strip()
    equipamento = str(row.get("EQUIPAMENTO", "")).strip()
    endereco = str(row.get("LOGRADOURO", "")).strip()  # endereço completo

    ctx = {
        "NOME_COLABORADOR": nome,
        "EQUIPAMENTO": equipamento,
        "LOGRADOURO": endereco,
    }

    try:
        return TEMPLATE_CONF_ENDERECO.format(**ctx)
    except Exception:
        texto = (
            f"Olá *{nome}*, tudo bem?\n\n"
            "Nós do Workplace estamos preparando seu equipamento para envio. "
            f"Estamos enviando seu *{equipamento}* e precisamos que você confirme seu endereço "
            "para que tudo ocorra da melhor maneira.\n\n"
            "Por favor, verifique se as informações abaixo estão corretas:\n\n"
            f"{endereco}\n\n"
            "Esse endereço está correto? Se precisar fazer alguma alteração, por favor, "
            "nos envie o endereço atualizado.\n\n"
            "Aguardamos sua confirmação.\n\n"
            "Atenciosamente,\n"
            "Workplace Empresa."
        )
        return texto


def montar_texto_rastreio(row):
    nome = str(row.get("NOME_COLABORADOR", "")).strip()

    patrimonio = str(row.get("PATRIMONIO", row.get("ATIVO", ""))).strip()
    cod_rastreio = str(row.get("RASTREIO", row.get("COD_RASTREIO", ""))).strip()
    usuario = str(row.get("USUARIO", row.get("LOGIN_REDE", ""))).strip()
    senha = str(row.get("SENHA", row.get("SENHA_INICIAL", ""))).strip()

    ctx = {
        "NOME_COLABORADOR": nome,
        "PATRIMONIO": patrimonio,
        "RASTREIO": cod_rastreio,
        "USUARIO": usuario,
        "SENHA": senha,
    }

    try:
        return TEMPLATE_RASTREIO.format(**ctx)
    except Exception:
        texto = (
            f"Olá *{nome}*, seu equipamento está pronto para envio!\n\n"
            f"*Patrimônio:* {patrimonio}\n"
            f"*Código de rastreio:* `{cod_rastreio}`\n\n"
            "Acesse o rastreamento pelo link:\n"
            "https://rastreamento.correios.com.br/app/index.php\n\n"
            "Se aparecer *\"Objeto Não Localizado\"*, aguarde, pois ainda não foi postado.\n\n"
            f"O login da rede é: *{usuario}* e a senha inicial é: *{senha}*.\n\n"
            "IMPORTANTE: Use apenas as credenciais desta mensagem. Não altere a senha antes do primeiro login.\n\n"
            "Para máquinas padrão, faça o primeiro login com a senha inicial e, se necessário, "
            "sincronize a nova senha na VPN.\n\n"
            "Para colaboradores em clientes específicos, entre em contato com sua Gestão "
            "para as credenciais corretas.\n\n"
            "Aproveitamos para lembrar que é necessário alterar a senha. Acesse o portal da empresa para realizar a alteração.\n\n"
            "Você receberá mais instruções no primeiro dia de trabalho para se cadastrar no sistema. "
            "Complete o cadastro dentro do prazo para evitar bloqueio.\n\n"
            "Confirme o recebimento do equipamento enviando um e-mail para "
            "suporte@suaempresa.com e siga as instruções do Termo de Responsabilidade.\n\n"
            "Atenciosamente,\n"
            "Equipe Workplace.\n\n"
            "*Segue em anexo link com vídeo de boas-vindas:*\n"
            "https://link-do-video-de-boas-vindas"
        )
        return texto


def montar_texto_agendamento_filial(row):
    nome = str(row.get("NOME_COLABORADOR", "")).strip()
    patrimonio = str(row.get("ATIVO", "")).strip()
    equipamento = str(row.get("EQUIPAMENTO", "")).strip()

    data_raw = row.get("DATA_RETIRADA", "")
    horario_raw = row.get("HORARIO_RETIRADA", "")

    data_retirada = formatar_data(data_raw)
    horario_retirada = formatar_horario(horario_raw)

    if not data_retirada:
        data_retirada = "a definir"
    if not horario_retirada:
        horario_retirada = "a definir"

    login_rede = str(row.get("LOGIN_REDE", "")).strip()
    senha_inicial = str(row.get("SENHA_INICIAL", "")).strip()

    ctx = {
        "NOME_COLABORADOR": nome,
        "ATIVO": patrimonio,
        "EQUIPAMENTO": equipamento,
        "DATA_RETIRADA": data_retirada,
        "HORARIO_RETIRADA": horario_retirada,
        "LOGIN_REDE": login_rede,
        "SENHA_INICIAL": senha_inicial,
    }

    try:
        return TEMPLATE_AGENDAMENTO.format(**ctx)
    except Exception:
        texto = (
            f"Olá, *{nome}*!\n\n"
            "Tudo bem com você?\n\n"
            "Estamos muito felizes em ter você conosco! Para que você comece sua jornada da melhor forma, "
            "já preparamos o seu equipamento.\n\n"
            "Aqui estão os detalhes:\n\n"
            f"*Patrimônio:* {patrimonio}\n"
            f"*Equipamento:* {equipamento}\n\n"
            "Retirada: *Filial Empresa*\n\n"
            f"Quando: *{data_retirada}*\n\n"
            f"Horário: *{horario_retirada}*\n\n"
            "Endereço: Endereço da Empresa, 1000 - Bairro - Cidade.\n\n"
            "Ah, e para garantir que você leve seu equipamento com conforto, sugerimos trazer uma mochila ou bolsa "
            "para transportá-lo com segurança.\n\n"
            "Informações do equipamento:\n\n"
            f"Usuário: *{login_rede}*\n"
            f"Senha: *{senha_inicial}*\n\n"
            "Aqui valorizamos o feedback para sempre evoluirmos!\n\n"
            "Sua opinião é super importante, então se puder, deixe um comentário sobre o serviço acessando o formulário.\n\n"
            "Para começar a se sentir em casa, também anexamos um vídeo de boas-vindas. Não deixe de conferir!\n\n"
            "Estamos aqui para o que precisar.\n\n"
            "Abraços,\n"
            "Time Workplace."
        )
        return texto


# =========================
# INTERFACE TKINTER
# =========================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gestão de Ativos - Mensagens WhatsApp")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        # layout estilo RPA: coluna 0 (sidebar) fixa, coluna 1 expansiva
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.excel_path = None

        # Sidebar com mesma cor do exemplo
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
        self._montar_watermark()

    # -----------------------------------
    # SIDEBAR
    # -----------------------------------
    def _montar_sidebar(self):
        titulo = ctk.CTkLabel(
            self.sidebar,
            text="Mensagens WhatsApp",
            font=("Segoe UI", 24, "bold"),
        )
        titulo.pack(pady=(25, 4), padx=20, anchor="w")

        subt = ctk.CTkLabel(
            self.sidebar,
            text="Gestão de Ativos\nWorkplace",
            font=("Segoe UI", 11),
            text_color="#9CA3AF",
            justify="left",
        )
        subt.pack(pady=(0, 18), padx=20, anchor="w")

        lbl_tipo = ctk.CTkLabel(
            self.sidebar,
            text="Tipo de mensagem",
            anchor="w",
            font=("Segoe UI", 11),
        )
        lbl_tipo.pack(pady=(4, 0), padx=24, anchor="w")

        self.tipo_msg_var = ctk.StringVar(value="AGENDAMENTO_FILIAL")
        self.combo_tipo_msg = ctk.CTkOptionMenu(
            self.sidebar,
            variable=self.tipo_msg_var,
            values=[
                "CONF_ENDERECO",
                "ENVIO_RASTREIO",
                "AGENDAMENTO_FILIAL",
            ],
            fg_color="#020617",
            button_color="#4C1D95",
            button_hover_color="#7C3AED",
            font=("Segoe UI", 11),
        )
        self.combo_tipo_msg.pack(pady=8, padx=24, fill="x")

        self.btn_excel = ctk.CTkButton(
            self.sidebar,
            text="Selecionar Planilha",
            fg_color="#4C1D95",
            hover_color="#7C3AED",
            height=34,
            font=("Segoe UI", 11),
            command=self.selecionar_excel,
        )
        self.btn_excel.pack(pady=(14, 4), padx=24, fill="x")

        self.lbl_excel = ctk.CTkLabel(
            self.sidebar,
            text="Nenhuma planilha selecionada",
            font=("Segoe UI", 10),
            text_color="#9CA3AF",
        )
        self.lbl_excel.pack(pady=(0, 10), padx=24, anchor="w")

        self.btn_iniciar = ctk.CTkButton(
            self.sidebar,
            text="📲 Enviar Mensagens",
            fg_color="#22C55E",
            hover_color="#16A34A",
            height=44,
            font=("Segoe UI", 13, "bold"),
            command=self.iniciar_envio,
        )
        self.btn_iniciar.pack(pady=(14, 8), padx=24, fill="x")

        # Botão editor de modelos
        self.btn_editar_modelos = ctk.CTkButton(
            self.sidebar,
            text="Editar modelos...",
            # 🔹 Mesmas cores do botão Selecionar Planilha
            fg_color="#4C1D95",
            hover_color="#7C3AED",
            height=34,
            font=("Segoe UI", 11),
            command=self.abrir_editor_modelos,
        )
        self.btn_editar_modelos.pack(pady=(4, 20), padx=24, fill="x")

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

    # -----------------------------------
    # EDITOR DE MODELOS
    # -----------------------------------
    def abrir_editor_modelos(self):
        editor = ctk.CTkToplevel(self)
        editor.title("Editar modelos de mensagem")
        editor.geometry("800x600")
        editor.grab_set()
        editor.configure(fg_color="#020617")

        ctk.CTkLabel(
            editor,
            text=(
                "Selecione o tipo de mensagem e edite o texto.\n"
                "Use os placeholders indicados para inserir dados dinâmicos."
            ),
            font=("Segoe UI", 11),
        ).pack(pady=(10, 5))

        frame_top = ctk.CTkFrame(editor, fg_color="#020617")
        frame_top.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            frame_top,
            text="Tipo:",
            font=("Segoe UI", 11),
        ).pack(side="left", padx=(5, 5))

        tipo_var = ctk.StringVar(value="CONF_ENDERECO")

        lbl_tips = ctk.CTkLabel(
            editor,
            text="",
            font=("Segoe UI", 10),
            text_color="#9CA3AF",
        )
        lbl_tips.pack(pady=(0, 5))

        textbox = ctk.CTkTextbox(
            editor,
            wrap="word",
            fg_color="#111827",
            text_color="#E5E7EB",
            font=("Consolas", 11),
            corner_radius=10,
        )
        textbox.pack(fill="both", expand=True, padx=10, pady=10)

        def carregar_template(*_):
            tipo = tipo_var.get()
            if tipo == "CONF_ENDERECO":
                texto = TEMPLATE_CONF_ENDERECO
                tips = "Placeholders: {NOME_COLABORADOR}, {EQUIPAMENTO}, {LOGRADOURO}"
            elif tipo == "ENVIO_RASTREIO":
                texto = TEMPLATE_RASTREIO
                tips = "Placeholders: {NOME_COLABORADOR}, {PATRIMONIO}, {RASTREIO}, {USUARIO}, {SENHA}"
            else:  # AGENDAMENTO_FILIAL
                texto = TEMPLATE_AGENDAMENTO
                tips = (
                    "Placeholders: {NOME_COLABORADOR}, {ATIVO}, {EQUIPAMENTO}, "
                    "{DATA_RETIRADA}, {HORARIO_RETIRADA}, {LOGIN_REDE}, {SENHA_INICIAL}"
                )

            lbl_tips.configure(text=tips)
            textbox.configure(state="normal")
            textbox.delete("1.0", "end")
            textbox.insert("1.0", texto)
            textbox.configure(state="normal")

        tipo_menu = ctk.CTkOptionMenu(
            frame_top,
            variable=tipo_var,
            values=["CONF_ENDERECO", "ENVIO_RASTREIO", "AGENDAMENTO_FILIAL"],
            fg_color="#020617",
            button_color="#4C1D95",
            button_hover_color="#7C3AED",
            font=("Segoe UI", 11),
            command=carregar_template,
        )
        tipo_menu.pack(side="left", padx=(0, 10))

        btn_frame = ctk.CTkFrame(editor, fg_color="#020617")
        btn_frame.pack(pady=(0, 10))

        def salvar_template():
            global TEMPLATE_CONF_ENDERECO, TEMPLATE_RASTREIO, TEMPLATE_AGENDAMENTO
            novo_texto = textbox.get("1.0", "end").rstrip("\n")
            tipo = tipo_var.get()

            if tipo == "CONF_ENDERECO":
                TEMPLATE_CONF_ENDERECO = novo_texto or TEMPLATE_CONF_ENDERECO_DEFAULT
            elif tipo == "ENVIO_RASTREIO":
                TEMPLATE_RASTREIO = novo_texto or TEMPLATE_RASTREIO_DEFAULT
            else:
                TEMPLATE_AGENDAMENTO = novo_texto or TEMPLATE_AGENDAMENTO_DEFAULT

            self.log(f"Modelo '{tipo}' atualizado na sessão atual.")
            editor.destroy()

        def restaurar_padroes():
            global TEMPLATE_CONF_ENDERECO, TEMPLATE_RASTREIO, TEMPLATE_AGENDAMENTO
            TEMPLATE_CONF_ENDERECO = TEMPLATE_CONF_ENDERECO_DEFAULT
            TEMPLATE_RASTREIO = TEMPLATE_RASTREIO_DEFAULT
            TEMPLATE_AGENDAMENTO = TEMPLATE_AGENDAMENTO_DEFAULT
            self.log("Todos os modelos foram restaurados para o padrão.")
            carregar_template()

        btn_salvar = ctk.CTkButton(
            btn_frame,
            text="Salvar",
            fg_color="#22C55E",
            hover_color="#16A34A",
            font=("Segoe UI", 11, "bold"),
            command=salvar_template,
        )
        btn_salvar.pack(side="left", padx=5)

        btn_reset = ctk.CTkButton(
            btn_frame,
            text="Restaurar padrões",
            fg_color="#6B7280",
            hover_color="#4B5563",
            font=("Segoe UI", 11),
            command=restaurar_padroes,
        )
        btn_reset.pack(side="left", padx=5)

        carregar_template()

    # -----------------------------------
    # LOGS / MAIN
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
        self.log("Interface pronta. Selecione a planilha e o tipo de mensagem.")

    # -----------------------------------
    # WATERMARK / MARCA D'ÁGUA
    # -----------------------------------
    def _abrir_linkedin(self, event=None):
        url = "https://www.linkedin.com/in/gustavo-alves-7971a9156/"
        webbrowser.open(url)

    def _montar_watermark(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        # canto inferior esquerdo da área principal
        frame.place(relx=0.01, rely=0.99, anchor="sw")

        lbl_autor = ctk.CTkLabel(
            frame,
            text="Criado por Gustavo Alves -",
            font=("Segoe UI", 9),
            text_color="#6B7280",
        )
        lbl_autor.pack(side="left")

        lbl_linkedin_logo = ctk.CTkLabel(
            frame,
            text="in",
            font=("Segoe UI", 11, "bold"),
            text_color="#0A66C2",
        )
        lbl_linkedin_logo.pack(side="left", padx=(4, 0))

        lbl_linkedin = ctk.CTkLabel(
            frame,
            text="LinkedIn",
            font=("Segoe UI", 9, "underline"),
            text_color="#0EA5E9",
        )
        lbl_linkedin.pack(side="left", padx=(2, 0))

        lbl_linkedin.bind("<Button-1>", self._abrir_linkedin)
        lbl_linkedin_logo.bind("<Button-1>", self._abrir_linkedin)

    # -----------------------------------
    # HELPERS
    # -----------------------------------
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
    # SELEÇÃO DE PLANILHA
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

    # -----------------------------------
    # FLUXO DE ENVIO
    # -----------------------------------
    def iniciar_envio(self):
        if not self.excel_path:
            messagebox.showwarning("Atenção", "Selecione uma planilha primeiro.")
            return

        if not TEM_DIGISAC:
            messagebox.showerror(
                "Erro",
                "Módulo Digisac não está disponível. Verifique o arquivo digisac_client.py.",
            )
            return

        try:
            self.enviar_mensagens()
        except Exception as e:
            self.log(f"Erro inesperado: {e}")
            messagebox.showerror("Erro", str(e))

    # -----------------------------------
    # ENVIO DE MENSAGENS
    # -----------------------------------
    def enviar_mensagens(self):
        self.set_status("lendo planilha...")
        df = pd.read_excel(self.excel_path)

        # Considera pendente quem não tem STATUS_MSG ou está vazio
        if "STATUS_MSG" in df.columns:
            pendentes = df[df["STATUS_MSG"].isna() | (df["STATUS_MSG"] == "")]
        else:
            df["STATUS_MSG"] = ""
            pendentes = df

        total = len(pendentes)
        if total == 0:
            self.log("Nenhuma linha pendente para envio de mensagem.")
            self.set_status("nenhuma pendência")
            return

        tipo_msg = self.tipo_msg_var.get()
        self.log(f"{total} registros pendentes. Tipo de mensagem: {tipo_msg}")
        self.set_status("enviando mensagens...")

        processados = 0

        for idx, row in pendentes.iterrows():
            nome = str(row.get("NOME_COLABORADOR", "")).strip()
            self.log(f"Processando linha {idx} - {nome}...")

            # TELEFONE — apenas uma coluna
            tel_raw = str(row.get("TELEFONE", "") or "")
            tel_digits = "".join(ch for ch in tel_raw if ch.isdigit())

            # Deve ter ao menos 10 dígitos (ex.: 11999998888)
            if len(tel_digits) < 10:
                self.log(
                    f"ℹ TELEFONE inválido para linha {idx}: {tel_raw}; "
                    "não enviei WhatsApp."
                )
                processados += 1
                self.set_progress(processados, total)
                continue

            # Garante formato E.164 → 55 + número (se ainda não tiver)
            if tel_digits.startswith("55"):
                numero_e164 = tel_digits
            else:
                numero_e164 = f"55{tel_digits}"

            # Monta texto conforme tipo selecionado
            if tipo_msg == "CONF_ENDERECO":
                texto = montar_texto_confirmacao_endereco(row)
                status_novo = "ENVIADA_CONF_END"
            elif tipo_msg == "ENVIO_RASTREIO":
                texto = montar_texto_rastreio(row)
                status_novo = "ENVIADA_RASTREIO"
            elif tipo_msg == "AGENDAMENTO_FILIAL":
                texto = montar_texto_agendamento_filial(row)
                status_novo = "ENVIADA_AG_FILIAL"
            else:
                self.log(f"⚠ Tipo de mensagem desconhecido: {tipo_msg}")
                processados += 1
                self.set_progress(processados, total)
                continue

            # Envio via Digisac
            try:
                ok, resp = enviar_whatsapp_por_numero(numero_e164, texto)
            except Exception as e:
                ok = False
                resp = f"Exceção ao chamar Digisac: {e}"

            if ok:
                self.log(
                    f"📲 WhatsApp enviado para {numero_e164} ({nome})."
                )
                df.at[idx, "STATUS_MSG"] = status_novo
                df.at[idx, "DATA_MSG"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
            else:
                self.log(
                    f"⚠ Falha ao enviar WhatsApp para {numero_e164} ({nome}): {resp}"
                )

            processados += 1
            self.set_progress(processados, total)

        # Salva planilha de volta
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
