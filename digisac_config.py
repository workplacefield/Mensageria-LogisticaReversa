import os
from dotenv import load_dotenv

load_dotenv()

# digisac_config.py

# BASE DA API (igual no código Node)
DIGISAC_API_BASE = os.environ.get("DIGISAC_API_BASE", "https://suaempresa.digisac.co/api/v1")

# === Você precisa pedir esses 3 valores para o pessoal que já integrou ===
# normalmente são as variáveis:
#   WHATSAPP_API_TOKEN
#   WHATSAPP_SERVICE_ID
#   WHATSAPP_USER_ID

# 1) Token Bearer de API (mesmo que o código Node usa em WHATSAPP_API_TOKEN)
DIGISAC_API_TOKEN = os.environ.get("DIGISAC_API_TOKEN", "")

# 2) ID do serviço/conexão WhatsApp (WHATSAPP_SERVICE_ID)
DIGISAC_WHATSAPP_SERVICE_ID = os.environ.get("DIGISAC_WHATSAPP_SERVICE_ID", "")

# 3) ID do usuário/bot que envia a mensagem (WHATSAPP_USER_ID)
DIGISAC_WHATSAPP_USER_ID = os.environ.get("DIGISAC_WHATSAPP_USER_ID", "")

