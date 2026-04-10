import subprocess
import hashlib
import sys
from datetime import datetime
from tkinter import messagebox
import os


# ==================================
# CONFIGURAÇÃO
# ==================================

ARQUIVO_DATA = "ultima_execucao.dat"

CLIENTE = "Padaria Central"
MAQUINA = "A2FFC922-D182-480C-BCA7-F95935D2A6A1"
EXPIRA = "2026-12-31"

SECRET = "CONFEITARIA_DOCE_SUSPIRO_ERP_2026"


# ==================================
# PEGAR UUID DA PLACA MÃE
# ==================================

def obter_uuid():

    try:

        comando = [
            "powershell",
            "-Command",
            "(Get-CimInstance Win32_ComputerSystemProduct).UUID"
        ]

        resultado = subprocess.check_output(comando).decode().strip()

        return resultado

    except:
        return None


# ==================================
# GERAR HASH
# ==================================

def gerar_hash():

    base = f"{CLIENTE}{MAQUINA}{EXPIRA}{SECRET}"

    return hashlib.sha256(base.encode()).hexdigest()


LICENCA_HASH = gerar_hash()


# ==================================
# VERIFICAR LICENÇA
# ==================================

def verificar_licenca():

    maquina_atual = obter_uuid()

    if maquina_atual != MAQUINA:

        messagebox.showerror(
            "Licença inválida",
            "Este software não está autorizado para este computador."
        )
        sys.exit()

    data_exp = datetime.strptime(EXPIRA, "%Y-%m-%d")

    if datetime.now() > data_exp:

        messagebox.showerror(
            "Licença expirada",
            "A licença deste software expirou."
        )
        sys.exit()


# ==================================
# PROTEÇÃO CONTRA VOLTAR DATA
# ==================================

def verificar_data():

    hoje = datetime.now()

    if os.path.exists(ARQUIVO_DATA):

        with open(ARQUIVO_DATA,"r") as f:

            ultima = datetime.fromisoformat(f.read())

        if hoje < ultima:

            messagebox.showerror(
                "Erro de segurança",
                "Data do sistema inválida."
            )
            sys.exit()

    with open(ARQUIVO_DATA,"w") as f:

        f.write(hoje.isoformat())