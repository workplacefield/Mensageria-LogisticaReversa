import os
from dotenv import load_dotenv

load_dotenv()

# config.py
# ==============================
# AMBIENTE DOS CORREIOS
# ==============================

# 👉 PRODUÇÃO:
WSDL_URL = (
    "https://apps.correios.com.br/"
    "logisticaReversaWS/logisticaReversaService/logisticaReversaWS?wsdl"
)

# Se quiser usar HOMOLOGAÇÃO, comente o de cima e descomente este:
# WSDL_URL = (
#     "https://apphom.correios.com.br/"
#     "logisticaReversaWS/logisticaReversaService/logisticaReversaWS?wsdl"
# )

# ==============================
# DADOS DO CONTRATO — CORREIOS
# ==============================
# Preencher com os dados reais do seu contrato de Logística Reversa

USUARIO = os.environ.get("CORREIOS_USUARIO", "")
SENHA = os.environ.get("CORREIOS_SENHA", "")

COD_ADMIN = os.environ.get("CORREIOS_COD_ADMIN", "")
COD_SERVICO = "03247"              # código do serviço logístico
CARTAO = os.environ.get("CORREIOS_CARTAO", "")
NUMERO_CONTRATO = os.environ.get("CORREIOS_NUMERO_CONTRATO", "")

# ==============================
# DESTINATÁRIO — SUA EMPRESA
# ==============================

DESTINATARIO_FIXO = {
    "nome": os.environ.get("DESTINATARIO_NOME", ""),
    "logradouro": os.environ.get("DESTINATARIO_LOGRADOURO", ""),
    "numero": os.environ.get("DESTINATARIO_NUMERO", ""),
    "complemento": os.environ.get("DESTINATARIO_COMPLEMENTO", ""),
    "bairro": os.environ.get("DESTINATARIO_BAIRRO", ""),
    "referencia": "",
    "cidade": os.environ.get("DESTINATARIO_CIDADE", ""),
    "uf": os.environ.get("DESTINATARIO_UF", ""),
    "cep": os.environ.get("DESTINATARIO_CEP", ""),
    "ddd": os.environ.get("DESTINATARIO_DDD", ""),
    "telefone": os.environ.get("DESTINATARIO_TELEFONE", ""),
    "celular": "",
    "ddd_celular": "",
    "email": os.environ.get("DESTINATARIO_EMAIL", ""),
    "identificacao": os.environ.get("DESTINATARIO_CNPJ", ""),
    "ciencia_conteudo_proibido": "S",
}

# ==============================
# EMBALAGEM UNIVERSAL — CAIXA 03
# ==============================
# Caixa Encomenda 03 — maior caixa padrão Correios para encomendas

EMBALAGEM_CODIGO = "116600071"  # código da embalagem
EMBALAGEM_TIPO = "2"            # tipo conforme tabela dos Correios
EMBALAGEM_QTD = 1               # normalmente 1 por devolução
