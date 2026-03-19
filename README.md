# Logística Reversa e Mensageria

Este é um projeto com automações para Logística Reversa (Correios) e Mensageria (integração do WhatsApp via plataforma Digisac), focado em processos de gestão de ativos e suporte a colaboradores.

## Funcionalidades

- Integração com Web Services Correios (CWS) para geração de logística reversa.
- Envio de mensagens no WhatsApp através da API Digisac.
- Interfaces em `CustomTkinter` para manipulação em massa através de planilhas.

## Configuração

Antes de rodar a aplicação, você precisa configurar os segredos e chaves de acesso no arquivo `.env`.

1. Duplique o arquivo `.env.example` e renomeie-o para `.env`.
   ```bash
   cp .env.example .env
   ```
2. Abra o recém-criado arquivo `.env` com um editor de texto de sua preferência e preencha com as credenciais válidas da sua empresa (Correios / Destinatário / Digisac).

> **Atenção:** Nunca comite ou envie o arquivo `.env` para repositórios públicos ou Github. Suas credenciais devem se manter seguras.

## Requisitos

Garanta que as bibliotecas necessárias estejam instaladas. Você também precisará da biblioteca `python-dotenv` para facilitar a leitura das variáveis de ambiente.

```bash
pip install -r requirements.txt
pip install python-dotenv customtkinter pandas requests
```

## Utilização

Inicie a aplicação de leitura da planilha e mensageria rodando:

```bash
python mensageria_workplace.py
```

Ou execute a interface de Correios, conforme o script adequado da automação da logística.
