import pandas as pd
import requests
from . import database
from .funcoes_auxiliares import obter_agora_br
import re

class PlataformaGestaoAPI:
    """
    Classe de integração com a API da Plataforma de Gestão e Webhooks do Power Automate.
    Utiliza parâmetros dinâmicos vindos da tabela dedicada tb_config_api_plataforma_gestao.
    """
    def __init__(self, id_solicitante, id_servico, natureza):
        # 1. Carrega as configurações exclusivas da nova tabela
        config_sinistro = database.carregar_config_plataforma_gestao()
        
        self.url_base = config_sinistro.get('tb_config_base_url', 'https://api.plataforma-gestao.com.br/api')
        self.login_api = config_sinistro.get('tb_config_client_id')
        self.senha_api = config_sinistro.get('tb_config_client_secret')
        self.timeout_api = int(config_sinistro.get('tb_config_timeout', 30))

        # (Opcional) Busca a URL do Power Automate da tabela geral, se ainda estiver usando
        parametros_gerais = database.carregar_parametros_robo()
        self.webhook_url = parametros_gerais.get('WEBHOOK_POWER_AUTOMATE')
        
        # Inicia a sessão com os dados do banco
        self.headers = {
            "Content-Type": "application/json"
        }
        
        self.id_solicitante = id_solicitante
        self.id_servico = id_servico
        self.natureza = natureza
        self._token = None

    def autenticar_v2(self):
        """Nova função de autenticação usando os dados do banco."""
        url_login = f"{self.url_base}/login"
        payload = {
            "login": self.login_api,
            "password": self.senha_api
        }
        
        response = requests.post(url_login, json=payload, timeout=self.timeout_api)
        if response.status_code == 200:
            token = response.json().get("token")
            self._token = token
            self.headers["Authorization"] = f"Bearer {token}"
            return True
        else:
            print(f" -> Erro de autenticação: {response.text}")
            return False

    @staticmethod
    def _extrair_primeiro_email(texto_bruto):
        """Extrai estritamente o PRIMEIRO e-mail válido de uma string bagunçada."""
        if not texto_bruto or pd.isna(texto_bruto):
            return ""
        # Regex que captura apenas o formato exato de um e-mail
        emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(texto_bruto))
        return emails[0] if emails else ""
    

    def montar_payload(self, linha_view):
        """
        Usa as colunas ricas já tratadas pela View do SQL.
        As chaves do dicionário batem exatamente com o manual da API da Plataforma de Gestão.
        """
        # 1. Trata Valor FIPE
        vlr_fipe = linha_view.get('valor_fipe')
        vlr_fipe_float = float(vlr_fipe) if pd.notna(vlr_fipe) else None

        # 2. Trata a nova Data do Sinistro
        dt_sin = linha_view.get('dt_sinistro')
        
        # Se for string, já está no formato certo. Se for objeto de data, formata.
        if isinstance(dt_sin, str):
            # Formata para o padrão ISO exigido: YYYY-MM-DDTHH:MM:SS
            dt_sin_str = dt_sin.replace(" ", "T")[:19]
        elif pd.notna(dt_sin):
            dt_sin_str = dt_sin.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            # Se for null, a API grava a "Data Mínima" do sistema deles
            dt_sin_str = None

        # Puxa a data agendada (horário de Brasília calculado pelo nosso robô)
        dt_ag = linha_view.get('data_agendada')
        
        if isinstance(dt_ag, str):
            # Se for string, garante o formato T (Ex: 2026-03-10T12:55:05)
            dt_ag_str = dt_ag.replace(" ", "T")[:19]
        elif pd.notna(dt_ag):
            dt_ag_str = dt_ag.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            dt_ag_str = obter_agora_br().strftime("%Y-%m-%dT%H:%M:%S")

        email_seg_limpo = self._extrair_primeiro_email(linha_view.get('email_segurado', ''))

        # 3. Monta a Base e o Envolvido Obrigatório (Segurado/Terceiro)
        payload = {
            "solicitanteId": self.id_solicitante,
            "servicoId": self.id_servico,
            "naturezaId": self.natureza,
            "sinistro": str(linha_view.get('sinistro_tratado', '')),
            "sinistroDataHora": dt_sin_str, # Nova chave de Data
            "dataHora": dt_ag_str,
            "placa": str(linha_view.get('placa_veiculo', 'AVI0000')),
            "uf": str(linha_view.get('uf_processo', 'SP')),
            "chassi": str(linha_view.get('chassi_veiculo', '')),
            "fipeValue": vlr_fipe_float,
            "detalhes": f"Capturado via RPA Portal Seguradora - {obter_agora_br().strftime('%d/%m/%Y')}",
            
            "envolvido": {
                "typeId": int(linha_view.get('tipo_envolvido_id', 1)), 
                "name": str(linha_view.get('nome_segurado', '')),
                "email": email_seg_limpo, 
                "document": {
                    "type": int(linha_view.get('tipo_doc_id', 1)),
                    "value": str(linha_view.get('doc_formatado', ''))
                }
            }
        }

        # 4. Adiciona o Telefone do Segurado/Terceiro (Array exigido pela API)
        tel_seg = str(linha_view.get('tel_segurado', '')).strip()
        ddd_seg = str(linha_view.get('ddd_segurado', '')).replace('.0', '').strip()
        if tel_seg and tel_seg.lower() not in ['none', 'nan', '']:
            numero_completo = f"{ddd_seg}{tel_seg}" if ddd_seg and ddd_seg.lower() != 'none' else tel_seg
            
            # Só envia se o número tiver tamanho válido (evita warning da API)
            num_apenas_digitos = re.sub(r'\D', '', numero_completo)
            if len(num_apenas_digitos) in [10, 11]:
                payload["envolvido"]["phones"] = [
                    {"number": numero_completo, "typeId": 1}
                ]

        # 5. Adiciona o Corretor (Apenas se tiver Nome e E-mail Válido)
        nome_corr = str(linha_view.get('nome_corretor', '')).strip()
        email_corr = self._extrair_primeiro_email(linha_view.get('email_corretor', ''))
        
        if nome_corr and nome_corr.lower() not in ['none', 'nan', ''] and '@' in email_corr:
            payload["corretor"] = {
                "typeId": 3, # Tipo 3 = Corretor
                "name": nome_corr,
                "email": email_corr
            }
            # Telefone do Corretor
            tel_corr = str(linha_view.get('tel_corretor', '')).strip()
            if tel_corr and tel_corr.lower() not in ['none', 'nan', '']:
                num_corr_digitos = re.sub(r'\D', '', tel_corr)
                if len(num_corr_digitos) in [10, 11]:
                    payload["corretor"]["phones"] = [
                        {"number": tel_corr, "typeId": 1}
                    ]

        # 6. Adiciona o Analista da Operadora e Analista da Seguradora Cliente (Se tiver E-mail Válido, senão só o Nome nos Detalhes)
        nome_ana = str(linha_view.get('nome_analista_operadora', '')).strip()
        email_ana = str(linha_view.get('email_analista_operadora', '')).strip()
        nome_seguradora = str(linha_view.get('nome_analista_seguradora', '')).strip()
        email_seguradora = self._extrair_primeiro_email(linha_view.get('email_analista_seguradora', ''))
        
        if nome_seguradora and '@' in email_seguradora:
            payload["analista"] = {
                "typeId": 4, 
                "name": nome_seguradora,
                "email": email_seguradora
            }
        else:
            # Caso não tenha e-mail do analista Seguradora, enviamos apenas o Nome nos Detalhes
            payload["detalhes"] += f" | Analista Seguradora: {nome_seguradora}"

        return payload

    def abrir_acionamento(self, execution_id, id_processo, payload):
        """Envia o processo para a Plataforma de Gestão após garantir o token."""
        # Garante que tem o token antes de enviar
        if not self._token:
            sucesso_login = self.autenticar_v2()
            if not sucesso_login:
                return {"status_code": 401, "message": "Falha de autenticação na API."}

        endpoint = "/acionamento"
        print(f" -> Enviando Processo {id_processo} para PlataformaGestao...")
        
        try:
            response = requests.post(
                f"{self.url_base}{endpoint}", 
                headers=self.headers, 
                json=payload,
                timeout=self.timeout_api
            )
            
            # (Mantém o resto da sua lógica original de tratamento de resposta e log)
            status_code = response.status_code
            resposta_json = response.json() if status_code != 204 else {"message": "Sucesso sem conteúdo"}
            
            database.registrar_log_api(
                execution_id=execution_id,
                id_processo=id_processo,
                destino="PlataformaGestao",
                acao="POST_ACIONAMENTO",
                status_code=status_code,
                payload=payload,
                resposta=resposta_json
            )
            
            return {
                "status_code": status_code,
                "acionamentoId": resposta_json.get("id") or resposta_json.get("acionamentoId"),
                "message": resposta_json.get("message") or str(resposta_json)
            }

        except Exception as e:
            error_msg = f"Erro de conexão com PlataformaGestao: {str(e)}"
            database.registrar_log_api(execution_id, id_processo, "PlataformaGestao", "ERRO_CONEXAO", 500, payload, error_msg)
            return {"status_code": 500, "message": error_msg}

    @staticmethod
    def _limpar_emails_duplicados(texto_bruto):
        """Varre o texto, encontra e-mails colados, remove duplicatas e separa por vírgula."""
        if not texto_bruto or texto_bruto == 'Não informado':
            return 'Não informado'
        
        # Encontra tudo que tem formato de e-mail (separando os colados)
        emails_encontrados = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(texto_bruto))
        
        if emails_encontrados:
            # Remove duplicatas mantendo a ordem
            emails_unicos = list(dict.fromkeys(emails_encontrados))
            return ", ".join(emails_unicos)
        
        return str(texto_bruto)


    def enviar_notificacao_email(self, execution_id, id_processo, linha_view, acionamento_id, sucesso, mensagem_api):
        """
        Recria o dicionário rico (dados_para_flow) do seu código antigo com dados da View.
        """
        agora = obter_agora_br()
        
        # Montagem do payload idêntica ao seu código original
        payload_flow = {
            "email_destino": "analista@empresa-operadora.com.br, gestao1@empresa-operadora.com.br, gestao2@empresa-operadora.com.br",
            "sucesso": sucesso,
            "cia": str(linha_view.get('cia', 'SEGURADORA CLIENTE')),
            "data": agora.strftime("%d/%m/%Y"),
            "hora": agora.strftime("%H:%M"),
            "data_portal": str(linha_view.get('data_portal', 'Não informada')),
            "placa": str(linha_view.get('placa_veiculo', 'Não informada')),
            "uf": str(linha_view.get('uf_processo', 'SP')), # Agora vindo da View
            "chassi": str(linha_view.get('chassi_veiculo', 'Não informada')),
            "sinistro": str(linha_view.get('sinistro_tratado', 'Não informada')),
            "acionamentoId": int(acionamento_id) if acionamento_id else 0,
            "mensagem_api": str(mensagem_api),
            
            # Campos de rastreabilidade e contatos
            "usuario_portal": str(linha_view.get('usuario_portal', 'Não informado')),
            "nome_segurado": str(linha_view.get('nome_segurado', 'Não informado')),
            # "email_segurado": str(linha_view.get('email_segurado', 'Não informado')),   # 09/03/2026 - Substituído pela função de limpeza de e-mails colados
            "email_segurado": self._limpar_emails_duplicados(linha_view.get('email_segurado', 'Não informado')),
            "telefone_segurado": f"{linha_view.get('ddd_segurado', '')}{linha_view.get('tel_segurado', '')}",
            "nome_corretor": str(linha_view.get('nome_corretor', 'Não informado')),
            # "email_corretor": str(linha_view.get('email_corretor', 'Não informado')),  # 09/03/2026 - Substituído pela função de limpeza de e-mails colados
            "email_corretor": self._limpar_emails_duplicados(linha_view.get('email_corretor', 'Não informado')),
            "telefone_corretor": str(linha_view.get('tel_corretor', 'Não informado')),
            # "email_analista": quem capturou o processo para o corpo do E-mail (Nome Completo)
            "nome_analista_operadora": str(linha_view.get('nome_analista_operadora', 'SISTEMA')).upper(),
            "email_analista_operadora": str(linha_view.get('email_analista_operadora', ''))
        }
        
        
        try:
            # CORREÇÃO: Usando a variável correta payload_flow
            # response = requests.post(webhook_url, json=payload_flow, timeout=20)          # 09/03/2026 - LINHA ORIGINAL COM ERRO
            response = requests.post(self.webhook_url, json=payload_flow, timeout=20)
            status_code = response.status_code
            
            try:
                resposta_texto = response.json()
            except:
                resposta_texto = response.text

            # Registro de auditoria conforme nossa nova governança
            database.registrar_log_notificacao(
                execution_id=execution_id,
                id_processo=id_processo,
                status_code=status_code,
                mensagem=resposta_texto
            )
            
            return status_code in [200, 202]

        except Exception as e:
            database.registrar_log_notificacao(execution_id, id_processo, 500, f"Falha no Webhook: {e}")
            return False