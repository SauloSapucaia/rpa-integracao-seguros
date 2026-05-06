#%%
import os
from dotenv import load_dotenv

# Descobre a pasta real onde este arquivo config.py está rodando na nuvem
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
caminho_env = os.path.join(DIRETORIO_ATUAL, '.env')

# Carrega o arquivo .env apontando para o caminho exato
load_dotenv(caminho_env)

# =========================================================================
# Conexão com o Microsoft Fabric (SQL Database)
# =========================================================================
FABRIC_SERVER = os.getenv("FABRIC_SERVER")
FABRIC_DATABASE = os.getenv("FABRIC_DATABASE")

# Trava de segurança para avisar se o arquivo .env não for lido
if not FABRIC_SERVER:
    print("!!! ALERTA CRÍTICO: O arquivo .env não foi lido corretamente !!!")

# =========================================================================
# Configurações de Execução do Robô
# =========================================================================
AMBIENTE = os.getenv("AMBIENTE", "PRODUCAO") 
SIMULAR_ENVIO_API = False

#%%