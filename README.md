# Backup OLT Script

Este projeto é um script Python para realizar o backup dos dispositivos OLT (Huawei, ZTE, Datacom), gerando relatórios, enviando notificações por e-mail, e inserindo registros em um banco de dados MySQL.

## Estrutura do Projeto

- **backup_olt.py**: Script principal que realiza a execução do backup.
- **credentials.py**: Contém as credenciais criptografadas para SSH.
- **equipamentos.py**: Contém as informações dos dispositivos OLT.

## Funcionalidades

- Realiza conexão SSH com os dispositivos, coleta a configuração e salva em arquivos `.txt`.
- Gera relatórios HTML e envia por e-mail.
- Insere informações sobre o processo de backup no banco de dados MySQL.

## Requisitos

- Python 3.8+
- Acesso SSH aos dispositivos
- Conexão com um banco de dados MySQL

## Como Utilizar

1. Clone este repositório.
2. Instale as dependências usando o `requirements.txt`.
   ```bash
   pip install -r requirements.txt
