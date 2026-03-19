# digisac_client.py

import requests
from requests.exceptions import ReadTimeout, RequestException

from digisac_config import (
    DIGISAC_API_BASE,
    DIGISAC_API_TOKEN,
    DIGISAC_WHATSAPP_SERVICE_ID,
    DIGISAC_WHATSAPP_USER_ID,
)


def enviar_whatsapp_por_numero(numero_e164: str, mensagem: str):
    """
    Envia mensagem de WhatsApp para um número diretamente via Digisac.
    numero_e164 deve estar no formato E.164: 55DDDNUMERO
    Retorna (ok: bool, detalhe: str|dict)
    """

    numero_e164 = (numero_e164 or "").strip()
    if not numero_e164:
        return False, "número vazio"

    base = DIGISAC_API_BASE.rstrip("/")
    url = f"{base}/messages"

    headers = {
        "Authorization": f"Bearer {DIGISAC_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "serviceId": DIGISAC_WHATSAPP_SERVICE_ID,
        "userId": DIGISAC_WHATSAPP_USER_ID,
        "number": numero_e164,
        "text": mensagem,
        "origin": "bot",
        "dontOpenTicket": True,
    }

    try:
        # timeout=(conexão, leitura)
        resp = requests.post(url, json=payload, headers=headers, timeout=(10, 40))

        try:
            data = resp.json()
        except Exception:
            data = resp.text

        if 200 <= resp.status_code < 300:
            return True, data
        else:
            return False, data

    except ReadTimeout:
        # Nesse caso a mensagem MUITO provavelmente foi enviada,
        # só não tivemos resposta a tempo.
        return True, "ReadTimeout ao aguardar resposta da Digisac, mas o envio provavelmente foi concluído (verifique no painel/logs)."

    except RequestException as e:
        # Outros erros reais de rede/DNS/etc.
        return False, f"Erro de rede/conexão ao chamar Digisac: {e}"
