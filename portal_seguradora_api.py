import time
import requests
import pandas as pd
import random
from datetime import datetime

# As URLs reais
BASE_URL = "https://api.portal-seguradora-cliente.com.br/backend/api"
FRONT_URL = "https://portal.seguradora-cliente.com.br"

class PortalSeguradoraAPI:
    """
    Classe de integração com API do Portal da Seguradora Cliente.
    Mantém o controle de limites e tentativas da arquitetura original.
    """
    def __init__(self, login, senha):
        self.session = requests.Session()
        self.login = login
        self.senha = senha
        self.id_usuario = None
        self.token = None
        self.ultima_chamada = time.time()

        # Simula navegador para burlar bloqueios (CORS)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RPA-Sinistros",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": FRONT_URL,
            "Referer": FRONT_URL + "/",
            "X-Requested-With": "XMLHttpRequest"
        })

    def aguardar_limite(self, minimo_intervalo=0.7):
        agora = time.time()
        delta = agora - self.ultima_chamada
        if delta < minimo_intervalo:
            time.sleep(minimo_intervalo - delta)
        self.ultima_chamada = time.time()

    def _request(self, method, url, **kwargs):
        """Wrapper com Rate limit, Retry exponencial e Tratamento de Erro."""
        tentativas = 3
        for tentativa in range(tentativas):
            try:
                self.aguardar_limite(random.uniform(0.6, 1.2))
                response = self.session.request(method, url, timeout=30, **kwargs)

                if response.status_code == 404:
                    print(f" !**! 404 - Dados não encontrados na URL: {url}")
                    return None

                if response.status_code in (429, 500, 502, 503):
                    raise requests.HTTPError(f"HTTP {response.status_code}")

                response.raise_for_status()
                return response

            except Exception as e:
                if tentativa == tentativas - 1:
                    print(f" !! Erro fatal na requisição ({url}): {e}")
                    return None
                espera = 2 ** tentativa
                time.sleep(espera)
        return None

    def autenticar(self):
        """Realiza o login com a estrutura original (Authorization no header)."""
        url = f"{BASE_URL}/login"
        payload = {
            "login": self.login,
            "senha": self.senha,
            "emailTrocarSenha": True
        }
        
        response = self._request("POST", url, json=payload)
        if not response:
            raise Exception("Falha na requisição de login (Sem resposta).")
            
        auth_header = response.headers.get("Authorization")
        if not auth_header:
            raise Exception("Authorization não retornou no login")

        self.token = auth_header
        dados = response.json()
        self.id_usuario = dados["id"]

        self.session.headers.update({
            "Authorization": self.token,
            "idUsuarioLogado": str(self.id_usuario)
        })
        print(f" -> Login realizado com sucesso! Usuário ID: {self.id_usuario}")
        return True

    def buscar_todos_processos(self):
        """Busca inicial de processos paginada."""
        todos = []
        pagina = 1
        while True:
            payload = {
                "filtrarGrupo": False,
                "idStatusCorrente": 1,
                "idUsuarioResponsavel": self.id_usuario,
                "noPagina": pagina,
                "orderByField": "ID",
                "qtdeDataPagina": 50,
                "ascOrder": 1
            }
            url = f"{BASE_URL}/processo"
            response = self._request("POST", url, json=payload)
            if response is None:
                break
                
            dados = response.json()
            processos = dados.get("processos", [])
            
            if not processos:
                break

            print(f" ->> Página {pagina} - {len(processos)} registros encontrados.")
            todos.extend(processos)
            pagina += 1

        return todos

    def consultar_agenda(self, processo):
        """Descobre o número do Expediente usando Força Bruta (Original)."""
        url = f"{BASE_URL}/processo/consultarAgenda"
        sinistro = processo.get("noSinistro")
        tipo = processo.get("tpExpediente")

        payload = {
            "codTramite": "509", "ctpExpediente": tipo, "numCia": 1,
            "numExpediente": None, "numLiquidacao": None, "numSeqTramite": None, "numSinistro": sinistro
        }
        response = self._request("POST", url, json=payload)
        if response is None: return None
        
        try:
            dados = response.json()
        except Exception:
            print(f"   [AVISO] Falha ao ler a agenda do sinistro {sinistro}. Pulando...")
            return None

        if dados.get("codError") == "0" and dados.get("numExpediente"):
            return dados.get("numExpediente")

        if dados.get("codError") == "6":
            for tentativa in range(1, 7):
                payload["numExpediente"] = tentativa
                resp = self._request("POST", url, json=payload)
                if resp:
                    try:
                        dados_teste = resp.json()
                        if dados_teste.get("codError") == "0":
                            return tentativa
                    except Exception:
                        continue # Ignora o erro nesta tentativa e testa o próximo número
        return None

    def buscar_detalhes_processo(self, sinistro, expediente):
        url = f"{BASE_URL}/processo/acompanhamento"
        payload = {"sinistro": str(sinistro), "expediente": str(expediente)}
        response = self._request("POST", url, json=payload)
        if response is None or response.status_code != 200:
            return {}
        try:
            return response.json()
        except:
            return {}

    def buscar_processo_por_id(self, id_processo):
        url = f"{BASE_URL}/processo/{id_processo}"
        response = self._request("GET", url)
        if response is None or response.status_code != 200:
            return {}
        try:
            return response.json()
        except:
            return {}


def extrair_portal_seguradora(credenciais, ids_existentes=None):
    """
    Função Maestro: Orquestra a extração do Portal da Seguradora e persiste no Microsoft Fabric.
    """
    if ids_existentes is None:
        ids_existentes = set()
        
    todos_processos = []
    
    for nome_analista, creds in credenciais.items():
        print(f"\n--- Iniciando captura: {nome_analista.upper()} ---")
        api = PortalSeguradoraAPI(creds["login"], creds["senha"])
        
        try:
            api.autenticar()
        except Exception as e:
            print(f" !! Falha ao autenticar {nome_analista}: {e}")
            continue
        
        lista_inicial = api.buscar_todos_processos()
        print(f" -> Total na fila de {nome_analista}: {len(lista_inicial)} processos.")
        
        # Conta para exibir no log corretamente
        qtd_existentes = len([p for p in lista_inicial if p.get("idProcesso") in ids_existentes])
        qtd_novos = len([p for p in lista_inicial if p.get("idProcesso") not in ids_existentes])
        
        print(f" -> Processos já existentes (na tela): {qtd_existentes}")
        print(f" -> Processos INÉDITOS para detalhar: {qtd_novos}")

            
        for p_basico in lista_inicial:
            id_proc = p_basico.get("idProcesso")
            sinistro = p_basico.get("noSinistro")
            if not id_proc: continue
            
            processo_completo = {**p_basico}

            if id_proc not in ids_existentes:
                print(f"   -> Detalhando ID: {id_proc} / Sinistro: {sinistro}...")
                detalhe_id = api.buscar_processo_por_id(id_proc) or {}
                
                expediente = api.consultar_agenda(p_basico)
                detalhe_acomp = {}
                if expediente:
                    detalhe_acomp = api.buscar_detalhes_processo(sinistro, expediente) or {}
                
                # Mescla os detalhes pesados apenas para os novos
                processo_completo.update(detalhe_id)
                processo_completo.update(detalhe_acomp)

            # --- Tratamento Universal (Serve para Novos e Existentes) ---
            processo_completo["usuario_origem"] = nome_analista
            processo_completo["idUsuario"] = api.id_usuario

            # CORREÇÃO: Busca exaustiva pela fase/status para não salvar NULL
            fase_extraida = (
                p_basico.get("status_processo") or 
                p_basico.get("dsStatusCorrenteProcesso") or 
                p_basico.get("dsStatus") or 
                detalhe_id.get("status_processo") or
                "PROCESSO RECEPCIONADO" # Valor padrão caso a API não mande nada
            )
            processo_completo["status_processo"] = fase_extraida
            processo_completo["dsStatusCorrente"] = fase_extraida
            
            # Tratamento do Workflow para inserção no banco SQL
            processo_completo["workflow"] = []
            min_data_workflow = None  # Variável para rastrear a data real de abertura
            
            for wf in processo_completo.get("logWorkFlow", []):
                dt_val = wf.get("dataHoraEvento")
                if dt_val:
                    try:
                        # Converte milissegundos e ajusta para o fuso horário BR
                        dt_obj = pd.to_datetime(dt_val, unit='ms') - pd.Timedelta(hours=3)
                        dt_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Salva a data mais antiga (Momento zero do Portal)
                        if min_data_workflow is None or dt_obj < min_data_workflow:
                            min_data_workflow = dt_obj
                    except:
                        continue
                        
                processo_completo["workflow"].append({
                    "idEvento": wf.get("idEvento", 0),
                    "descricao": wf.get("evento", wf.get("statusProcesso", wf.get("observacao", ""))),
                    "data": dt_str
                })
            
            # 09/03/2026: Salva a data real de abertura
            processo_completo["data_completa_minima"] = min_data_workflow.strftime("%Y-%m-%d %H:%M:%S") if min_data_workflow else None
            
            # 10/03/2026: Padronização de chaves da API
            processo_completo["nomeSegurado"] = processo_completo.get("nmBeneficiario", processo_completo.get("nomeSegurado"))
            processo_completo["cpfSegurado"] = processo_completo.get("cpfCnpj", processo_completo.get("cpfSegurado"))
            processo_completo["emailSegurado"] = processo_completo.get("emailBeneficiario", processo_completo.get("emailSegurado"))
            processo_completo["placa"] = processo_completo.get("placaVeiculo", processo_completo.get("placa"))
            processo_completo["marca"] = processo_completo.get("nmMarca", processo_completo.get("dsMarca", processo_completo.get("marca", "")))
            processo_completo["modelo"] = processo_completo.get("nmModelo", processo_completo.get("dsModelo", processo_completo.get("modelo", "")))
            processo_completo["chassi"] = processo_completo.get("chassi", processo_completo.get("nrChassi", ""))
            processo_completo["valor_veiculo"] = processo_completo.get("vrFipe", processo_completo.get("valorFipe", processo_completo.get("valorMercado", None)))
            processo_completo["sub_modelo"] = processo_completo.get("subModeloVeiculo", processo_completo.get("subModelo", ""))
            processo_completo["ano_fabricacao"] = processo_completo.get("anoVeiculo", 
                                                  processo_completo.get("nrAnoFabricacao", 
                                                  processo_completo.get("anoFabricacao", 
                                                  processo_completo.get("ano", None))))
            processo_completo["data_sinistro"] = processo_completo.get("dtSinistro", p_basico.get("dtAberturaSinistro", ""))
            processo_completo["analista_nome"] = p_basico.get("nmAnalista", "")
            processo_completo["analista_email"] = p_basico.get("emailAnalistaTw", "")

            alienado_str = str(processo_completo.get("flBaixaGravame", "")).strip().upper()
            processo_completo["flBaixaGravame"] = 1 if alienado_str in ['S', 'SIM', 'TRUE', '1'] else 0
            processo_completo["dsTpFinanciamento"] = processo_completo.get("dsTpFinanciamento", "")
            processo_completo["status_processo"] = processo_completo.get("dsStatusCorrente", processo_completo.get("status_processo", ""))
            
            todos_processos.append(processo_completo)         
            
    df_final = pd.DataFrame(todos_processos)
    
    if df_final.empty:
        return pd.DataFrame()

    df_final = df_final.drop_duplicates(subset=["idProcesso"], keep="first")
    return df_final