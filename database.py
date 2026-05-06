import pandas as pd
import re
import struct
import pyodbc
import json
import warnings
from sqlalchemy import create_engine, text
from funcoes_auxiliares import tratar_valor_fipe
# from azure.identity import InteractiveBrowserCredential               # 09/03/2026 - MOVIDO PARA A FUNÇÃO obter_engine() PARA RODAR NA NUVEM (FABRIC MICROSOFT)
# from azure.identity import DefaultAzureCredential                     # 09/03/2026 - MOVIDO PARA A FUNÇÃO obter_engine() PARA RODAR NA NUVEM (FABRIC MICROSOFT)
from config import FABRIC_SERVER, FABRIC_DATABASE

# Silencia avisos técnicos de segurança do MSAL no terminal
warnings.filterwarnings("ignore", category=UserWarning, module="msal.oauth2cli.oauth2")

# Variável global para guardar a engine e evitar logins repetidos
_engine_cache = None

def obter_engine():
    """Retorna a engine existente ou cria uma nova se for a primeira vez."""
    global _engine_cache
    
    if _engine_cache is not None:
        return _engine_cache

    # =========================================================
    # 1. GERAÇÃO DE TOKEN "AMBIENTE INTELIGENTE" (Nuvem vs Local)
    # =========================================================
    try:
        # TENTA NA NUVEM: Usa o autenticador nativo do Microsoft Fabric
        from notebookutils import mssparkutils
        token_string = mssparkutils.credentials.getToken("https://database.windows.net/")
        print(" -> Token obtido com sucesso via ambiente interno do Fabric.")
    except ImportError:
        # TENTA LOCAL: Se não achar a biblioteca do Fabric, abre o navegador
        from azure.identity import InteractiveBrowserCredential
        print(" -> Ambiente local detectado. Solicitando login via navegador...")
        credential = InteractiveBrowserCredential()
        token_obj = credential.get_token("https://database.windows.net/.default")
        token_string = token_obj.token

    token_bytes = token_string.encode("UTF-16-LE")
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
    
    # Descobre automaticamente a versão do driver instalada (17 no seu PC, 18 no Fabric)
    drivers_disponiveis = [d for d in pyodbc.drivers() if 'ODBC Driver' in d and 'SQL Server' in d]
    driver_instalado = drivers_disponiveis[-1] if drivers_disponiveis else 'ODBC Driver 18 for SQL Server'

    conn_str = (
        f"Driver={{{driver_instalado}}};"
        f"Server=tcp:{FABRIC_SERVER},1433;"
        f"Database={{{FABRIC_DATABASE}}};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=30;"
    )

    def dsn_creator():
        return pyodbc.connect(conn_str, attrs_before={1256: token_struct})

    # Guarda na variável global antes de retornar
    _engine_cache = create_engine(
        "mssql+pyodbc://",
        creator=dsn_creator,
        fast_executemany=True,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30
    )
    return _engine_cache

# =========================================================================
# FUNÇÕES DE CARREGAMENTO (READ)
# =========================================================================

def carregar_credenciais_portal():
    """Busca os logins ativos do Portal Seguradora na tabela tb_config_credenciais."""
    engine = obter_engine()
    query = """
        SELECT tb_config_login_usuario, tb_config_senha_usuario, tb_config_nome_responsavel 
        FROM tb_config_credenciais 
        WHERE tb_config_sistema = 'PortalSeguradora' AND tb_config_is_ativo = 1
    """
    df_creds = pd.read_sql(query, engine)
    
    return {
        row['tb_config_nome_responsavel']: {
            "login": row['tb_config_login_usuario'], 
            "senha": row['tb_config_senha_usuario']
        } for _, row in df_creds.iterrows()
    }

def carregar_mapa_ddd():
    """Busca a tabela de DDDs e UFs do banco para validação no robô."""
    engine = obter_engine()
    query = "SELECT tb_dic_ddd_cod, tb_dic_uf FROM tb_dic_ddd_uf WHERE tb_dic_ativo = 1"
    df_ddd = pd.read_sql(query, engine)
    return dict(zip(df_ddd['tb_dic_ddd_cod'], df_ddd['tb_dic_uf']))

def carregar_parametros_robo():
    """Busca configurações dinâmicas da tabela de parâmetros respeitando a tipagem real do Banco."""
    engine = obter_engine()
    # Puxamos as duas colunas novas do banco
    query = "SELECT tb_config_chave_parametro, tb_config_valor_texto, tb_config_valor_numero FROM tb_config_parametros_robo"
    df_params = pd.read_sql(query, engine)
    
    parametros = {}
    for _, row in df_params.iterrows():
        chave = row['tb_config_chave_parametro']
        
        # Se a coluna numérica não for nula, o Python já absorve como INT (número real)
        if pd.notna(row['tb_config_valor_numero']):
            parametros[chave] = int(row['tb_config_valor_numero'])
        else:
            # Caso contrário, absorve como String (texto)
            parametros[chave] = row['tb_config_valor_texto']
            
    return parametros

def higienizar_telefone(telefone_bruto, ddd_bruto=None):
    """
    Aplica as regras A, B e C para higienizar contatos antes de salvar no banco.
    """
    if pd.isna(telefone_bruto) or str(telefone_bruto).lower() in ['nan', 'none', '']:
        return None, None

    # PASSO A: Remove tudo que NÃO for número (letras, parênteses, traços, espaços)
    tel_limpo = re.sub(r'\D', '', str(telefone_bruto))
    
    # PASSO C: Exclui sujeiras irrecuperáveis (< 8 dígitos)
    if len(tel_limpo) < 8:
        return None, None
        
    # PASSO B: Se tem 10 ou 11 dígitos e não temos DDD separado, fatiamos o número
    if len(tel_limpo) in (10, 11) and not ddd_bruto:
        ddd_final = int(tel_limpo[:2])
        tel_final = tel_limpo[2:]
        return ddd_final, tel_final
        
    # Se já tem DDD, apenas limpa e devolve
    ddd_final = int(str(ddd_bruto).replace('.0', '').strip()) if ddd_bruto and str(ddd_bruto).replace('.0', '').strip().isdigit() else None
    return ddd_final, tel_limpo

def carregar_config_plataforma_gestao():
    """Busca as configurações exclusivas da API da Plataforma de Gestão na tabela dedicada."""
    engine = obter_engine()
    query = """
        SELECT TOP 1 
            tb_config_base_url, 
            tb_config_client_id, 
            tb_config_client_secret, 
            tb_config_timeout 
        FROM tb_config_api_plataforma_gestao 
        WHERE tb_config_ativo = 1
    """
    df_config = pd.read_sql(query, engine)
    
    if not df_config.empty:
        return df_config.iloc[0].to_dict()
    return {}

def enriquecer_processos_existentes(df_processos, execution_id):
    """
    Faz um 'backfill' (carga histórica) de dados pesados nos processos que já existem.
    Grava o JSON RAW, atualiza Veículo, Status, Fase, Dicionários, SLA, Documentos e Analista da Seguradora.
    """
    if df_processos.empty:
        return 0

    engine = obter_engine()
    
    with engine.begin() as conn:
        for _, row in df_processos.iterrows():
            id_proc = int(row['idProcesso'])
            sinistro = str(row.get('noSinistro', row.get('sinistro', '')))[:50]
            
            # ====================================================
            # 0. GRAVAR O JSON CRU (SNAPSHOT + HISTÓRICO)
            # ====================================================
            json_cru = json.dumps(row.to_dict(), ensure_ascii=False)
            conn.execute(text("""
                -- 1. Mantém a foto atualizada na tabela principal
                IF NOT EXISTS (SELECT 1 FROM tb_raw_processos_portal WHERE tb_raw_id_processo_cod = :id_p)
                BEGIN
                    INSERT INTO tb_raw_processos_portal (tb_raw_id_processo_cod, tb_raw_no_sinistro, tb_raw_json_completo, tb_raw_data_captura)
                    VALUES (:id_p, :sinistro, :json_cru, DATEADD(HOUR, -3, GETDATE()))
                END
                ELSE
                BEGIN
                    UPDATE tb_raw_processos_portal
                    SET tb_raw_json_completo = :json_cru, tb_raw_data_captura = DATEADD(HOUR, -3, GETDATE())
                    WHERE tb_raw_id_processo_cod = :id_p
                END
                
                -- 2. Salva a nova linha no cofre de histórico (Append-only)
                INSERT INTO tb_raw_historico_processos_portal (tb_raw_id_processo_cod, tb_raw_no_sinistro, tb_raw_json_completo, tb_raw_data_captura)
                VALUES (:id_p, :sinistro, :json_cru, DATEADD(HOUR, -3, GETDATE()))
            """), {"id_p": id_proc, "sinistro": sinistro, "json_cru": json_cru})

            # ====================================================
            # 1. DIM_PROCESSO (Datas, Fase, Status, Alerta)
            # ====================================================
            dt_bruta = row.get('data_completa_minima')
            dt_abertura = None if pd.isna(dt_bruta) or str(dt_bruta).strip().lower() in ["", "não informada", "nan", "none", "nat"] else dt_bruta
            
            dt_sinistro_bruta = row.get('data_sinistro')
            dt_sinistro = None if pd.isna(dt_sinistro_bruta) or str(dt_sinistro_bruta).strip().lower() in ["", "nan", "none", "nat"] else dt_sinistro_bruta
            
            fase_val = row.get('status_processo')
            # 19/03/2026 - Melhoria na captura da Fase/Status
            if pd.isna(fase_val) or str(fase_val).strip().lower() in ['nan', 'none', '', 'null']:
                # Se estiver nulo, tenta a coluna de status corrente como backup
                fase_val = row.get('dsStatusCorrente')

            fase_site = str(fase_val).strip()[:150] if pd.notna(fase_val) else "PROCESSO RECEPCIONADO"
            # fase_site = None if pd.isna(fase_val) or str(fase_val).strip().lower() in ['nan', 'none', ''] else str(fase_val).strip()[:150]

            id_status = row.get('idStatusCorrente')
            id_status_portal = int(id_status) if pd.notna(id_status) and str(id_status).strip().lower() not in ['nan', 'none', ''] else None
            
            alerta_str = str(row.get('flAlerta', '')).strip().upper()
            fl_alerta = 1 if alerta_str in ['TRUE', '1', 'S', 'SIM'] else 0

            conn.execute(text("""
                UPDATE tb_dim_processo 
                SET tb_dim_dt_abertura_sinistro = COALESCE(tb_dim_dt_abertura_sinistro, :dt_ab),
                    tb_dim_dt_ocorrencia_sinistro = COALESCE(tb_dim_dt_ocorrencia_sinistro, :dt_sin),
                    tb_dim_fase_processo = COALESCE(:stt_proc, tb_dim_fase_processo),
                    tb_dim_id_status_portal_cod = COALESCE(:id_status, tb_dim_id_status_portal_cod),
                    tb_dim_fl_alerta = :alerta
                WHERE tb_dim_id_processo_cod = :id
            """), {
                "dt_ab": dt_abertura, "dt_sin": dt_sinistro, "stt_proc": fase_site,
                "id_status": id_status_portal, "alerta": fl_alerta, "id": id_proc
            })

            # ====================================================
            # 2. ATUALIZAR VEÍCULO
            # ====================================================
            placa = str(row.get('placa', 'AVI0000'))[:10]
            marca = str(row.get('marca', ''))[:50]
            modelo = str(row.get('modelo', ''))[:100]
            valor_fipe = tratar_valor_fipe(row.get('valor_veiculo'))
            sub_modelo = str(row.get('sub_modelo', '')).strip()[:150]
            is_alienado = int(row.get('flBaixaGravame', 0))
            
            ano_val = row.get('ano_fabricacao', row.get('anoVeiculo'))
            try:
                ano_fab = int(float(str(ano_val))) if pd.notna(ano_val) and str(ano_val).lower() not in ['nan', 'none', ''] else None
            except:
                ano_fab = None

            conn.execute(text("""
                UPDATE tb_dim_veiculo 
                SET tb_dim_placa = :placa, tb_dim_marca = :marca, tb_dim_modelo = :modelo,
                    tb_dim_ano_fabricacao = :ano_fab, tb_dim_valor_fipe = :vlr,
                    tb_dim_sub_modelo = :sub_modelo, tb_dim_is_alienado = :is_alienado
                WHERE tb_dim_id_processo_cod = :id
            """), {
                "placa": placa, "marca": marca, "modelo": modelo, "ano_fab": ano_fab, 
                "vlr": valor_fipe, "sub_modelo": sub_modelo if sub_modelo else None,
                "is_alienado": is_alienado, "id": id_proc
            })

            # ====================================================
            # 3. GARANTIR O SLA 
            # ====================================================
            conn.execute(text("""
                IF NOT EXISTS (SELECT 1 FROM tb_fact_sla_processo WHERE tb_fact_id_processo_cod = :id_check)
                BEGIN
                    INSERT INTO tb_fact_sla_processo (tb_fact_id_processo_cod, tb_fact_data_recepcao_portal, tb_fact_data_captura_robo, tb_fact_status_sla)
                    VALUES (:id_ins, :dt, DATEADD(HOUR, -3, GETDATE()), 'PENDENTE_ENVIO')
                END
            """), {"id_check": id_proc, "id_ins": id_proc, "dt": dt_abertura})

            # ====================================================
            # 4.ALIMENTAR DICIONÁRIOS E WORKFLOW 
            # ====================================================
            if id_status_portal:
                desc_val = row.get('dsStatusCorrente')
                desc_status = "" if pd.isna(desc_val) or str(desc_val).strip().lower() in ['nan', 'none', ''] else str(desc_val).strip()
                desc_st_final = desc_status[:100] if desc_status else f"Status ID: {id_status_portal}"
                
                conn.execute(text("""
                    IF NOT EXISTS (SELECT 1 FROM tb_dom_status_portal WHERE tb_dom_id_status_portal_cod = :id_st)
                    BEGIN
                        INSERT INTO tb_dom_status_portal (tb_dom_id_status_portal_cod, tb_dom_desc_status_portal, tb_dom_is_status_final)
                        VALUES (:id_st, :desc, 0)
                    END
                    ELSE
                    BEGIN
                        UPDATE tb_dom_status_portal SET tb_dom_desc_status_portal = :desc 
                        WHERE tb_dom_id_status_portal_cod = :id_st AND tb_dom_desc_status_portal LIKE 'Status ID:%' AND :desc NOT LIKE 'Status ID:%'
                    END
                """), {"id_st": id_status_portal, "desc": desc_st_final})

            for evento in row.get('workflow', []):
                id_evento = evento.get('idEvento', 0)
                desc_ev_val = str(evento.get('descricao', '')).strip()
                desc_evento = "" if str(desc_ev_val).lower() in ['nan', 'none', ''] else desc_ev_val[:200]
                dt_evento = evento.get('data')
                
                if id_evento > 0:
                    desc_ev_final = desc_evento[:100] if desc_evento else f"Evento ID: {id_evento}"
                    
                    conn.execute(text("""
                        IF NOT EXISTS (SELECT 1 FROM tb_dom_evento_workflow WHERE tb_dom_id_evento_portal_cod = :id_ev)
                        BEGIN
                            INSERT INTO tb_dom_evento_workflow (tb_dom_id_evento_portal_cod, tb_dom_desc_evento, tb_dom_fase_processo)
                            VALUES (:id_ev, :desc, 'Fase a Mapear')
                        END
                        ELSE
                        BEGIN
                            UPDATE tb_dom_evento_workflow SET tb_dom_desc_evento = :desc 
                            WHERE tb_dom_id_evento_portal_cod = :id_ev AND tb_dom_desc_evento LIKE 'Evento ID:%' AND :desc NOT LIKE 'Evento ID:%'
                        END
                    """), {"id_ev": id_evento, "desc": desc_ev_final})
                    
                    if dt_evento:
                        conn.execute(text("""
                            IF NOT EXISTS (SELECT 1 FROM tb_fact_workflow_portal WHERE tb_fact_id_processo_cod = :id_p AND tb_fact_id_evento_portal_cod = :id_e)
                            BEGIN
                                INSERT INTO tb_fact_workflow_portal (tb_fact_id_processo_cod, tb_fact_id_evento_portal_cod, tb_fact_descricao_complementar, tb_fact_data_hora_evento)
                                VALUES (:id_p, :id_e, :desc, :dt)
                            END
                            ELSE IF :desc != ''
                            BEGIN
                                UPDATE tb_fact_workflow_portal SET tb_fact_descricao_complementar = :desc
                                WHERE tb_fact_id_processo_cod = :id_p AND tb_fact_id_evento_portal_cod = :id_e AND (tb_fact_descricao_complementar IS NULL OR tb_fact_descricao_complementar = '')
                            END
                        """), {"id_p": id_proc, "id_e": id_evento, "desc": desc_evento, "dt": dt_evento})

            # ====================================================
            # 5. ANALISTA SEGURADORA (ENVOLVIDO TIPO 4)
            # ====================================================
            nm_analista = str(row.get('analista_nome', '')).strip()
            email_analista = str(row.get('analista_email', '')).strip()

            if nm_analista and nm_analista.lower() not in ['nan', 'none', '']:
                res_ana = conn.execute(text("SELECT TOP 1 tb_dim_id_envolvido_cod FROM tb_dim_envolvido WHERE tb_dim_id_processo_cod = :id AND tb_dim_id_tipo_envolvido_cod = 4"), {"id": id_proc}).fetchone()
                
                if not res_ana:
                    conn.execute(text("""
                        INSERT INTO tb_dim_envolvido (tb_dim_id_processo_cod, tb_dim_id_tipo_envolvido_cod, tb_dim_nome, tb_dim_data_cadastro, tb_dim_ativo) 
                        VALUES (:id, 4, :nome, DATEADD(HOUR, -3, GETDATE()), 1)
                    """), {"id": id_proc, "nome": nm_analista[:150]})
                    
                if email_analista and '@' in email_analista:
                    conn.execute(text("""
                        DECLARE @id_env INT;
                        SELECT TOP 1 @id_env = tb_dim_id_envolvido_cod FROM tb_dim_envolvido WHERE tb_dim_id_processo_cod = :id_p AND tb_dim_id_tipo_envolvido_cod = 4 ORDER BY tb_dim_id_envolvido_cod DESC;
                        
                        IF @id_env IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tb_dim_contato WHERE tb_dim_id_envolvido_cod = @id_env AND tb_dim_id_tipo_contato_cod = 3)
                        BEGIN
                            INSERT INTO tb_dim_contato (tb_dim_id_envolvido_cod, tb_dim_id_tipo_contato_cod, tb_dim_valor_contato, tb_dim_is_principal)
                            VALUES (@id_env, 3, :email, 1)
                        END
                        ELSE IF @id_env IS NOT NULL
                        BEGIN
                            UPDATE tb_dim_contato SET tb_dim_valor_contato = :email WHERE tb_dim_id_envolvido_cod = @id_env AND tb_dim_id_tipo_contato_cod = 3
                        END
                    """), {"id_p": id_proc, "email": email_analista[:150]})

            # ====================================================
            # 6. EXTRAÇÃO DE DOCUMENTOS
            # ====================================================
            lista_docs = row.get('documentos', row.get('listaDocumentos', row.get('documentosProcesso', [])))
            if isinstance(lista_docs, list) and len(lista_docs) > 0:
                for doc in lista_docs:
                    nome_doc_val = doc.get('dsDocumento', doc.get('nomeDocumento', doc.get('descricao', '')))
                    st_doc_val = doc.get('dsStatus', doc.get('statusDocumento', doc.get('status', '')))
                    
                    nome_doc = "" if pd.isna(nome_doc_val) or str(nome_doc_val).strip().lower() in ['nan', 'none', ''] else str(nome_doc_val).strip()[:200]
                    status_doc = "" if pd.isna(st_doc_val) or str(st_doc_val).strip().lower() in ['nan', 'none', ''] else str(st_doc_val).strip()[:50]

                    if nome_doc and nome_doc.lower() not in ['nan', 'none', '']:
                        conn.execute(text("""
                            IF NOT EXISTS (SELECT 1 FROM tb_fact_documento WHERE tb_fact_id_processo_cod = :id_p AND tb_fact_nome_documento = :nome)
                            BEGIN
                                INSERT INTO tb_fact_documento (tb_fact_id_processo_cod, tb_fact_nome_documento, tb_fact_status_documento, tb_fact_data_cadastro)
                                VALUES (:id_p, :nome, :st, DATEADD(HOUR, -3, GETDATE()))
                            END
                            ELSE
                            BEGIN
                                UPDATE tb_fact_documento SET tb_fact_status_documento = :st 
                                WHERE tb_fact_id_processo_cod = :id_p AND tb_fact_nome_documento = :nome
                            END
                        """), {"id_p": id_proc, "nome": nome_doc, "st": status_doc})
            
            # ====================================================
            # 7. HISTÓRICO DE USUÁRIO E SLA
            # ====================================================
            id_usuario = int(row.get('idUsuario', 0)) 
            nm_usuario_origem = str(row.get('usuario_origem', 'SISTEMA'))
            
            if id_usuario > 0:
                conn.execute(text("""
                    IF NOT EXISTS (SELECT 1 FROM tb_dim_usuario_robo WHERE tb_dim_id_usuario_cod = :id_usu)
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM tb_dim_usuario_robo WHERE tb_dim_login_portal = :login)
                        BEGIN
                            INSERT INTO tb_dim_usuario_robo (tb_dim_id_usuario_cod, tb_dim_nome_usuario, tb_dim_login_portal)
                            VALUES (:id_usu, :login, :login);
                        END
                    END
                """), {"id_usu": id_usuario, "login": nm_usuario_origem})

                conn.execute(text("""
                    IF NOT EXISTS (
                        SELECT 1 FROM tb_fact_historico_usuario_processo 
                        WHERE tb_fact_id_processo_cod = :id_proc_sel AND tb_fact_id_usuario_cod = :id_usu_sel
                    )
                    BEGIN
                        INSERT INTO tb_fact_historico_usuario_processo (tb_fact_id_processo_cod, tb_fact_id_usuario_cod, tb_fact_is_responsavel_atual)
                        VALUES (:id_proc_ins, :id_usu_ins, 1);
                    END
                """), {
                    "id_proc_sel": id_proc, "id_usu_sel": id_usuario,
                    "id_proc_ins": id_proc, "id_usu_ins": id_usuario
                })

            conn.execute(text("""
                IF NOT EXISTS (SELECT 1 FROM tb_fact_sla_processo WHERE tb_fact_id_processo_cod = :id_proc_sla_sel)
                BEGIN
                    INSERT INTO tb_fact_sla_processo (tb_fact_id_processo_cod, tb_fact_data_recepcao_portal, tb_fact_data_captura_robo, tb_fact_status_sla)
                    VALUES (:id_proc_sla_ins, :dt_abertura, DATEADD(HOUR, -3, GETDATE()), 'PENDENTE_ENVIO');
                END
            """), {"id_proc_sla_sel": id_proc, "id_proc_sla_ins": id_proc, "dt_abertura": dt_abertura})

    return len(df_processos)

# =========================================================================
# FUNÇÕES DE LOG E AUDITORIA
# =========================================================================

def iniciar_log_execucao(execution_id):
    """Registra o início de uma nova rodada do robô."""
    engine = obter_engine()
    query = text("""
        INSERT INTO tb_log_execucao_robo (tb_log_execution_id_cod, tb_log_data_inicio, tb_log_status_execucao)
        VALUES (:exec_id, DATEADD(HOUR, -3, GETDATE()), 'RODANDO')
    """)
    with engine.begin() as conn:
        conn.execute(query, {"exec_id": execution_id})

def finalizar_log_execucao(execution_id, status, qtd_lidos, qtd_novos, mensagem):
    """Atualiza o Log da Execução com o resultado e volumetria final."""
    engine = obter_engine()
    query = text("""
        UPDATE tb_log_execucao_robo 
        SET tb_log_data_fim = DATEADD(HOUR, -3, GETDATE()), 
            tb_log_status_execucao = :status, 
            tb_log_qtd_processos_lidos = :lidos, 
            tb_log_qtd_novos_processos = :novos, 
            tb_log_mensagem_geral = :msg
        WHERE tb_log_execution_id_cod = :exec_id
    """)
    with engine.begin() as conn:
        conn.execute(query, {
            "status": status, "lidos": qtd_lidos, "novos": qtd_novos, 
            "msg": str(mensagem)[:4000], "exec_id": execution_id
        })

# =========================================================================
# MOTOR PRINCIPAL DE INGESTÃO (GRAVAÇÃO DE PROCESSOS)
# =========================================================================

def registrar_processos_no_banco(df_processos, execution_id):
    """
    Insere processos novos e distribui os dados nas tabelas satélites.
    Alimentando Dicionários, Documentos e protegendo contra nulos do Pandas.
    """
    if df_processos.empty:
        return 0
        
    engine = obter_engine()
    mapa_ddd = carregar_mapa_ddd()
    
    df_existentes = pd.read_sql("SELECT tb_dim_id_processo_cod FROM tb_dim_processo", engine)
    ids_existentes = df_existentes['tb_dim_id_processo_cod'].tolist()
    
    df_novos = df_processos[~df_processos['idProcesso'].isin(ids_existentes)].copy()
    if df_novos.empty:
        return 0

    with engine.begin() as conn:
        for _, row in df_novos.iterrows():
            id_proc = int(row['idProcesso'])
            sinistro = str(row['noSinistro'])
            
            # --- TRATAMENTO DE UF ---
            ddd_bruto = str(row.get('ddd', '')).replace('.0', '').strip()
            ddd_segurado = int(ddd_bruto) if ddd_bruto.isdigit() else None
            uf_processo = mapa_ddd.get(ddd_segurado, str(row.get('dsUF', 'SP')).strip()[:2].upper())
            
            # ====================================================
            # 0. GRAVAR O JSON CRU (SNAPSHOT + HISTÓRICO)
            # ====================================================
            json_cru = json.dumps(row.to_dict(), ensure_ascii=False)
            conn.execute(text("""
                -- 1. Cria a foto inicial na tabela principal
                IF NOT EXISTS (SELECT 1 FROM tb_raw_processos_portal WHERE tb_raw_id_processo_cod = :id_proc)
                BEGIN
                    INSERT INTO tb_raw_processos_portal (tb_raw_id_processo_cod, tb_raw_no_sinistro, tb_raw_json_completo, tb_raw_data_captura)
                    VALUES (:id_proc, :sinistro, :json_cru, DATEADD(HOUR, -3, GETDATE()))
                END

                -- 2. Salva a primeira linha no cofre de histórico
                INSERT INTO tb_raw_historico_processos_portal (tb_raw_id_processo_cod, tb_raw_no_sinistro, tb_raw_json_completo, tb_raw_data_captura)
                VALUES (:id_proc, :sinistro, :json_cru, DATEADD(HOUR, -3, GETDATE()))
            """), {"id_proc": id_proc, "sinistro": sinistro, "json_cru": json_cru})

            # ====================================================
            # 1. DIM_PROCESSO (Datas, Fase, Status, Alerta)
            # ====================================================
            dt_bruta = row.get('data_completa_minima')
            dt_abertura = None if pd.isna(dt_bruta) or str(dt_bruta).strip().lower() in ["", "não informada", "nan", "none", "nat"] else dt_bruta
            
            dt_sinistro_bruta = row.get('data_sinistro')
            dt_sinistro = None if pd.isna(dt_sinistro_bruta) or str(dt_sinistro_bruta).strip().lower() in ["", "nan", "none", "nat"] else dt_sinistro_bruta
            
            tp_exp = str(row.get('tpExpediente', '')).strip().upper()
            id_expediente = 1 if tp_exp == 'DPA' else (2 if tp_exp == 'TRC' else 0)
            
            fase_val = row.get('status_processo') 
            # 19/03/2026 - Melhoria na captura da Fase/Status
            if pd.isna(fase_val) or str(fase_val).strip().lower() in ['nan', 'none', '', 'null']:
                # Se estiver nulo, tenta a coluna de status corrente como backup
                fase_val = row.get('dsStatusCorrente')

            fase_site = str(fase_val).strip()[:150] if pd.notna(fase_val) else "PROCESSO RECEPCIONADO"
            # fase_site = None if pd.isna(fase_val) or str(fase_val).strip().lower() in ['nan', 'none', ''] else str(fase_val).strip()[:150]

            id_status = row.get('idStatusCorrente')
            id_status_portal = int(id_status) if pd.notna(id_status) and str(id_status).strip().lower() not in ['nan', 'none', ''] else None
            
            alerta_str = str(row.get('flAlerta', '')).strip().upper()
            fl_alerta = 1 if alerta_str in ['TRUE', '1', 'S', 'SIM'] else 0

            conn.execute(text("""
                INSERT INTO tb_dim_processo (
                    tb_dim_id_processo_cod, tb_dim_no_sinistro, tb_dim_dt_abertura_sinistro, 
                    tb_dim_uf_processo, tb_dim_id_tipo_expediente_cod, tb_dim_id_status_portal_cod, 
                    tb_dim_nm_cia, tb_dim_data_cadastro, tb_dim_ativo, tb_dim_dt_ocorrencia_sinistro,
                    tb_dim_fase_processo, tb_dim_fl_alerta
                ) VALUES (
                    :id_proc, :sinistro, :dt_abertura, :uf, :id_exp, :id_status, 'SEGURADORA CLIENTE', DATEADD(HOUR, -3, GETDATE()), 1, :dt_sinistro,
                    :fase_site, :alerta
                )
            """), {
                "id_proc": id_proc, "sinistro": sinistro, "dt_abertura": dt_abertura, 
                "uf": uf_processo, "id_exp": id_expediente, "id_status": id_status_portal,
                "dt_sinistro": dt_sinistro, "fase_site": fase_site, "alerta": fl_alerta
            })
            
            # ====================================================
            # 2. FILA DE TRABALHO
            # ====================================================
            conn.execute(text("""
                INSERT INTO tb_fact_fila_envio (tb_fact_id_processo_cod, tb_fact_id_status_fila_cod, tb_fact_tentativas, tb_fact_data_cadastro, tb_fact_ativo) 
                VALUES (:id_proc, 1, 0, DATEADD(HOUR, -3, GETDATE()), 1)
            """), {"id_proc": id_proc})
            
            # ====================================================
            # 3. VEÍCULO
            # ====================================================
            placa = str(row.get('placa', 'AVI0000')).strip().upper()
            if not placa or placa in ['NAN', 'NONE', '']: placa = 'AVI0000'

            marca = str(row.get('marca', '')).strip()
            modelo = str(row.get('modelo', '')).strip()
            chassi = str(row.get('chassi', '')).strip()
            ano_val = row.get('ano_fabricacao', row.get('anoVeiculo'))
            valor_fipe = tratar_valor_fipe(row.get('valor_veiculo'))
            sub_modelo = str(row.get('sub_modelo', '')).strip()[:150]
            is_alienado = int(row.get('flBaixaGravame', 0))
            
            try:
                ano_fab = int(float(str(ano_val))) if pd.notna(ano_val) and str(ano_val).lower() not in ['nan', 'none', ''] else None
            except:
                ano_fab = None

            conn.execute(text("""
                INSERT INTO tb_dim_veiculo (
                    tb_dim_id_processo_cod, tb_dim_placa, tb_dim_chassi, 
                    tb_dim_marca, tb_dim_modelo, tb_dim_ano_fabricacao, 
                    tb_dim_valor_fipe, tb_dim_data_cadastro, tb_dim_ativo,
                    tb_dim_sub_modelo, tb_dim_is_alienado
                ) VALUES (
                    :id_proc, :placa, :chassi, :marca, :modelo, :ano_fab, :vlr_fipe, DATEADD(HOUR, -3, GETDATE()), 1,
                    :sub_modelo, :is_alienado
                )
            """), {
                "id_proc": id_proc, "placa": placa, "chassi": chassi if chassi else None,
                "marca": marca if marca else None, "modelo": modelo if modelo else None,
                "ano_fab": ano_fab, "vlr_fipe": valor_fipe,
                "sub_modelo": sub_modelo if sub_modelo else None, "is_alienado": is_alienado
            })

            # ====================================================
            # 4. ENVOLVIDOS (SEGURADO, CORRETOR E ANALISTA)
            # ====================================================
            # A) SEGURADO
            nome_envolvido = str(row.get('nomeSegurado', '')).strip()
            cpf = str(row.get('cpfSegurado', '')).strip()
            id_tipo_env = 1 if tp_exp == 'DPA' else (2 if tp_exp == 'TRC' else 1)
            
            conn.execute(text("""
                INSERT INTO tb_dim_envolvido (tb_dim_id_processo_cod, tb_dim_id_tipo_envolvido_cod, tb_dim_nome, tb_dim_cpf_cnpj, tb_dim_data_cadastro, tb_dim_ativo) 
                VALUES (:id_proc, :id_tipo, :nome, :cpf, DATEADD(HOUR, -3, GETDATE()), 1)
            """), {"id_proc": id_proc, "id_tipo": id_tipo_env, "nome": nome_envolvido[:150], "cpf": cpf[:20]})
            
            res_seg = conn.execute(text("SELECT TOP 1 tb_dim_id_envolvido_cod FROM tb_dim_envolvido WHERE tb_dim_id_processo_cod = :id_proc AND tb_dim_id_tipo_envolvido_cod = :id_tipo ORDER BY tb_dim_id_envolvido_cod DESC"), {"id_proc": id_proc, "id_tipo": id_tipo_env})
            id_env_seg = res_seg.fetchone()[0]

            emails_brutos = str(row.get('emailSegurado', '')).replace(',', ';')
            for email in [e.strip() for e in emails_brutos.split(';') if '@' in e]:
                conn.execute(text("""
                    INSERT INTO tb_dim_contato (tb_dim_id_envolvido_cod, tb_dim_id_tipo_contato_cod, tb_dim_valor_contato, tb_dim_is_principal, tb_dim_data_cadastro, tb_dim_ativo) 
                    VALUES (:id_env, 3, :email, 1, DATEADD(HOUR, -3, GETDATE()), 1)
                """), {"id_env": id_env_seg, "email": email[:150]})

            ddd_seg_final, tel_seg_limpo = higienizar_telefone(row.get('telefoneBeneficiario'), row.get('ddd'))
            if tel_seg_limpo:
                conn.execute(text("""
                    INSERT INTO tb_dim_contato (tb_dim_id_envolvido_cod, tb_dim_id_tipo_contato_cod, tb_dim_ddd_cod, tb_dim_valor_contato, tb_dim_is_principal, tb_dim_data_cadastro, tb_dim_ativo) 
                    VALUES (:id_env, 2, :ddd, :tel, 1, DATEADD(HOUR, -3, GETDATE()), 1)
                """), {"id_env": id_env_seg, "ddd": ddd_seg_final, "tel": tel_seg_limpo[:150]})

            # B) CORRETOR
            nm_corretor = str(row.get('nmCorretor', '')).strip()
            if nm_corretor and nm_corretor.lower() not in ['nan', 'none', '']:
                conn.execute(text("""
                    INSERT INTO tb_dim_envolvido (tb_dim_id_processo_cod, tb_dim_id_tipo_envolvido_cod, tb_dim_nome, tb_dim_data_cadastro, tb_dim_ativo) 
                    VALUES (:id_proc, 3, :nome, DATEADD(HOUR, -3, GETDATE()), 1)
                """), {"id_proc": id_proc, "nome": nm_corretor[:150]})

                res_corr = conn.execute(text("SELECT TOP 1 tb_dim_id_envolvido_cod FROM tb_dim_envolvido WHERE tb_dim_id_processo_cod = :id_proc AND tb_dim_id_tipo_envolvido_cod = 3 ORDER BY tb_dim_id_envolvido_cod DESC"), {"id_proc": id_proc})
                id_env_corr = res_corr.fetchone()[0]

                email_corr = str(row.get('emailCorretor', '')).strip()
                if email_corr and '@' in email_corr:
                    conn.execute(text("""
                        INSERT INTO tb_dim_contato (tb_dim_id_envolvido_cod, tb_dim_id_tipo_contato_cod, tb_dim_valor_contato, tb_dim_is_principal, tb_dim_data_cadastro, tb_dim_ativo) 
                        VALUES (:id_env, 3, :email, 1, DATEADD(HOUR, -3, GETDATE()), 1)
                    """), {"id_env": id_env_corr, "email": email_corr[:150]})

                ddd_corr_final, tel_corr_limpo = higienizar_telefone(row.get('telefoneCorretor'), row.get('dddCorr'))
                if tel_corr_limpo:
                    conn.execute(text("""
                        INSERT INTO tb_dim_contato (tb_dim_id_envolvido_cod, tb_dim_id_tipo_contato_cod, tb_dim_ddd_cod, tb_dim_valor_contato, tb_dim_is_principal, tb_dim_data_cadastro, tb_dim_ativo) 
                        VALUES (:id_env, 2, :ddd, :tel, 1, DATEADD(HOUR, -3, GETDATE()), 1)
                    """), {"id_env": id_env_corr, "ddd": ddd_corr_final, "tel": tel_corr_limpo[:150]})

            # C) ANALISTA SEGURADORA
            nm_analista = str(row.get('analista_nome', '')).strip()
            email_analista = str(row.get('analista_email', '')).strip()

            if nm_analista and nm_analista.lower() not in ['nan', 'none', '']:
                conn.execute(text("""
                    INSERT INTO tb_dim_envolvido (tb_dim_id_processo_cod, tb_dim_id_tipo_envolvido_cod, tb_dim_nome, tb_dim_data_cadastro, tb_dim_ativo) 
                    VALUES (:id_proc, 4, :nome, DATEADD(HOUR, -3, GETDATE()), 1)
                """), {"id_proc": id_proc, "nome": nm_analista[:150]})
                
                res_ana = conn.execute(text("SELECT TOP 1 tb_dim_id_envolvido_cod FROM tb_dim_envolvido WHERE tb_dim_id_processo_cod = :id_proc AND tb_dim_id_tipo_envolvido_cod = 4 ORDER BY tb_dim_id_envolvido_cod DESC"), {"id_proc": id_proc})
                id_env_ana = res_ana.fetchone()[0]
                
                if email_analista and '@' in email_analista:
                    conn.execute(text("""
                        INSERT INTO tb_dim_contato (tb_dim_id_envolvido_cod, tb_dim_id_tipo_contato_cod, tb_dim_valor_contato, tb_dim_is_principal, tb_dim_data_cadastro, tb_dim_ativo) 
                        VALUES (:id_env, 3, :email, 1, DATEADD(HOUR, -3, GETDATE()), 1)
                    """), {"id_env": id_env_ana, "email": email_analista[:150]})

            # ====================================================
            # 5. DICIONÁRIOS E WORKFLOW
            # ====================================================
            if id_status_portal:
                desc_val = row.get('dsStatusCorrente')
                desc_status = "" if pd.isna(desc_val) or str(desc_val).strip().lower() in ['nan', 'none', ''] else str(desc_val).strip()
                desc_st_final = desc_status[:100] if desc_status else f"Status ID: {id_status_portal}"
                
                conn.execute(text("""
                    IF NOT EXISTS (SELECT 1 FROM tb_dom_status_portal WHERE tb_dom_id_status_portal_cod = :id_st)
                    BEGIN
                        INSERT INTO tb_dom_status_portal (tb_dom_id_status_portal_cod, tb_dom_desc_status_portal, tb_dom_is_status_final)
                        VALUES (:id_st, :desc, 0)
                    END
                """), {"id_st": id_status_portal, "desc": desc_st_final})

            for evento in row.get('workflow', []):
                id_evento = evento.get('idEvento', 0)
                desc_ev_val = str(evento.get('descricao', '')).strip()
                desc_evento = "" if str(desc_ev_val).lower() in ['nan', 'none', ''] else desc_ev_val[:200]
                dt_evento = evento.get('data')
                
                if id_evento > 0:
                    desc_ev_final = desc_evento[:100] if desc_evento else f"Evento ID: {id_evento}"
                    conn.execute(text("""
                        IF NOT EXISTS (SELECT 1 FROM tb_dom_evento_workflow WHERE tb_dom_id_evento_portal_cod = :id_ev)
                        BEGIN
                            INSERT INTO tb_dom_evento_workflow (tb_dom_id_evento_portal_cod, tb_dom_desc_evento, tb_dom_fase_processo)
                            VALUES (:id_ev, :desc, 'Fase a Mapear')
                        END
                    """), {"id_ev": id_evento, "desc": desc_ev_final})
                    
                if dt_evento:
                    conn.execute(text("""
                        INSERT INTO tb_fact_workflow_portal (tb_fact_id_processo_cod, tb_fact_id_evento_portal_cod, tb_fact_descricao_complementar, tb_fact_data_hora_evento, tb_fact_data_cadastro)
                        VALUES (:id_proc, :id_e, :desc, :dt, DATEADD(HOUR, -3, GETDATE()))
                    """), {"id_proc": id_proc, "id_e": id_evento, "desc": desc_evento, "dt": dt_evento})

            id_ciclo = row.get('idCicloCorrente')
            ds_status_proc = str(row.get('dsStatusCorrenteProcesso', '')).strip()[:200]
            ds_status = str(row.get('dsStatus', '')).strip()[:50]
            
            if pd.notna(id_ciclo) and int(id_ciclo) > 0:
                conn.execute(text("""
                    INSERT INTO tb_fact_workflow_step (tb_fact_id_processo_cod, tb_fact_id_tarefa_cod, tb_fact_nome_tarefa, tb_fact_status_tarefa, tb_fact_data_hora_step, tb_fact_data_cadastro)
                    VALUES (:id_p, :id_c, :nome, :status, DATEADD(HOUR, -3, GETDATE()), DATEADD(HOUR, -3, GETDATE()))
                """), {"id_p": id_proc, "id_c": int(id_ciclo), "nome": ds_status_proc, "status": ds_status})

            # ====================================================
            # 6. DOCUMENTOS
            # ====================================================
            lista_docs = row.get('documentos', row.get('listaDocumentos', row.get('documentosProcesso', [])))
            if isinstance(lista_docs, list) and len(lista_docs) > 0:
                for doc in lista_docs:
                    nome_doc_val = doc.get('dsDocumento', doc.get('nomeDocumento', doc.get('descricao', '')))
                    st_doc_val = doc.get('dsStatus', doc.get('statusDocumento', doc.get('status', '')))
                    
                    nome_doc = "" if pd.isna(nome_doc_val) or str(nome_doc_val).strip().lower() in ['nan', 'none', ''] else str(nome_doc_val).strip()[:200]
                    status_doc = "" if pd.isna(st_doc_val) or str(st_doc_val).strip().lower() in ['nan', 'none', ''] else str(st_doc_val).strip()[:50]

                    if nome_doc and nome_doc.lower() not in ['nan', 'none', '']:
                        conn.execute(text("""
                            IF NOT EXISTS (SELECT 1 FROM tb_fact_documento WHERE tb_fact_id_processo_cod = :id_p AND tb_fact_nome_documento = :nome)
                            BEGIN
                                INSERT INTO tb_fact_documento (tb_fact_id_processo_cod, tb_fact_nome_documento, tb_fact_status_documento, tb_fact_data_cadastro)
                                VALUES (:id_p, :nome, :st, DATEADD(HOUR, -3, GETDATE()))
                            END
                            ELSE
                            BEGIN
                                UPDATE tb_fact_documento SET tb_fact_status_documento = :st 
                                WHERE tb_fact_id_processo_cod = :id_p AND tb_fact_nome_documento = :nome
                            END
                        """), {"id_p": id_proc, "nome": nome_doc, "st": status_doc})

            # ====================================================
            # 7. HISTÓRICO DE USUÁRIO E SLA
            # ====================================================
            id_usuario = int(row.get('idUsuario', 0)) 
            nm_usuario_origem = str(row.get('usuario_origem', 'SISTEMA'))
            
            if id_usuario > 0:
                conn.execute(text("""
                    IF NOT EXISTS (SELECT 1 FROM tb_dim_usuario_robo WHERE tb_dim_id_usuario_cod = :id_usu)
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM tb_dim_usuario_robo WHERE tb_dim_login_portal = :login)
                        BEGIN
                            INSERT INTO tb_dim_usuario_robo (tb_dim_id_usuario_cod, tb_dim_nome_usuario, tb_dim_login_portal)
                            VALUES (:id_usu, :login, :login);
                        END
                    END
                """), {"id_usu": id_usuario, "login": nm_usuario_origem})

                conn.execute(text("""
                    IF NOT EXISTS (
                        SELECT 1 FROM tb_fact_historico_usuario_processo 
                        WHERE tb_fact_id_processo_cod = :id_proc_sel AND tb_fact_id_usuario_cod = :id_usu_sel
                    )
                    BEGIN
                        INSERT INTO tb_fact_historico_usuario_processo (tb_fact_id_processo_cod, tb_fact_id_usuario_cod, tb_fact_is_responsavel_atual)
                        VALUES (:id_proc_ins, :id_usu_ins, 1);
                    END
                """), {
                    "id_proc_sel": id_proc, "id_usu_sel": id_usuario,
                    "id_proc_ins": id_proc, "id_usu_ins": id_usuario
                })

            conn.execute(text("""
                IF NOT EXISTS (SELECT 1 FROM tb_fact_sla_processo WHERE tb_fact_id_processo_cod = :id_proc_sla_sel)
                BEGIN
                    INSERT INTO tb_fact_sla_processo (tb_fact_id_processo_cod, tb_fact_data_recepcao_portal, tb_fact_data_captura_robo, tb_fact_status_sla)
                    VALUES (:id_proc_sla_ins, :dt_abertura, DATEADD(HOUR, -3, GETDATE()), 'PENDENTE_ENVIO');
                END
            """), {"id_proc_sla_sel": id_proc, "id_proc_sla_ins": id_proc, "dt_abertura": dt_abertura})

    return len(df_novos)


# =========================================================================
# FUNÇÕES DE GESTÃO DA FILA (API)
# =========================================================================

def obter_fila_pendente():
    """Lê os dados já tratados diretamente da View no banco."""
    engine = obter_engine()
    # A ordenação agora é feita pela data_portal (antiga dt_abertura_original)
    query = "SELECT * FROM vw_processos_prontos_envio ORDER BY data_portal ASC"
    return pd.read_sql(query, engine)

def atualizar_status_fila(id_fila, id_processo, status_id, acionamento_id, mensagem, dt_agendamento=None):
    """Atualiza a fila após tentativa de envio e registra o ID de acionamento se sucesso."""
    engine = obter_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE tb_fact_fila_envio 
            SET tb_fact_id_status_fila_cod = :status_id, 
                tb_fact_tentativas = tb_fact_tentativas + 1, 
                tb_fact_data_ultima_tentativa = DATEADD(HOUR, -3, GETDATE()),
                tb_fact_mensagem_erro = :msg, 
                tb_fact_data_hora_agendamento = :dt_agendamento
            WHERE tb_fact_id_fila_cod = :id_fila
        """), {"status_id": status_id, "msg": mensagem, "dt_agendamento": dt_agendamento, "id_fila": id_fila})
        
        if status_id == 2:
            conn.execute(text("""
                UPDATE tb_fact_sla_processo 
                SET tb_fact_data_envio_plataforma = DATEADD(HOUR, -3, GETDATE()),
                    tb_fact_tempo_fila_minutos = DATEDIFF(MINUTE, tb_fact_data_captura_robo, DATEADD(HOUR, -3, GETDATE()))
                WHERE tb_fact_id_processo_cod = :id_proc 
                  AND tb_fact_data_envio_plataforma IS NULL
            """), {"id_proc": id_processo})

def registrar_log_api(execution_id, id_processo, destino, acao, status_code, payload, resposta):
    """Log técnico detalhado das requisições HTTP."""
    engine = obter_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO tb_log_transacao_api (tb_log_execution_id_cod, tb_log_id_processo_cod, tb_log_sistema_destino, tb_log_tipo_acao, tb_log_status_code, tb_log_payload_enviado, tb_log_resposta_recebida, tb_log_data_hora_transacao)
            VALUES (:exec_id, :id_proc, :dest, :acao, :status, :pay, :resp, DATEADD(HOUR, -3, GETDATE()))
        """), {"exec_id": execution_id, "id_proc": id_processo, "dest": destino, "acao": acao, "status": status_code, "pay": str(payload)[:4000], "resp": str(resposta)[:4000]})

def tratar_datas_abertura_banco():
    """
    Usa o banco para extrair a data mínima do Workflow (ELT Puro).
    CORREÇÃO: Garante que a data de abertura seja extraída estritamente do 
    histórico individual de cada idProcesso, evitando contaminação entre placas.
    """
    engine = obter_engine()
    query = text("""
        UPDATE p
        SET p.tb_dim_dt_abertura_sinistro = w.DataMinima
        FROM tb_dim_processo p
        INNER JOIN (
            SELECT tb_fact_id_processo_cod, MIN(tb_fact_data_hora_evento) AS DataMinima
            FROM tb_fact_workflow_portal
            -- [TRAVA] Ignora qualquer evento de workflow anterior a 2026
            WHERE tb_fact_data_hora_evento >= '2026-01-01'
            GROUP BY tb_fact_id_processo_cod
        ) w ON p.tb_dim_id_processo_cod = w.tb_fact_id_processo_cod
        WHERE p.tb_dim_dt_abertura_sinistro IS NULL 
          OR p.tb_dim_dt_abertura_sinistro < '2026-01-01';
    """)
    with engine.begin() as conn:
        conn.execute(query)

def conciliar_fila_com_plataforma_gestao():
    """Cruza a fila com a tabela de staging local do Fabric."""
    engine = obter_engine()
    query = text("""
        UPDATE f
        SET f.tb_fact_id_status_fila_cod = 2,
            f.tb_fact_mensagem_erro = 'Conciliado via Snapshot D-1 (Fabric)',
            f.tb_fact_data_ultima_tentativa = DATEADD(HOUR, -3, GETDATE())
        FROM tb_fact_fila_envio f
        INNER JOIN vw_processos_prontos_envio vw ON f.tb_fact_id_processo_cod = vw.id_processo
        INNER JOIN stg_asinistro_estoque d1 ON vw.sinistro_tratado = d1.Sinistro
        WHERE f.tb_fact_id_status_fila_cod = 1;
    """)
    try:
        with engine.begin() as conn:
            res = conn.execute(query)
            print(f" -> {res.rowcount} duplicidades D-1 removidas da fila.")
    except Exception:
        print(" -> Aviso: Tabela de conciliação ainda não existe. Pulando limpeza...")

def obter_ids_processos_existentes():
    """Retorna um set com todos os IDs que já estão salvos no banco de dados."""
    engine = obter_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT tb_dim_id_processo_cod FROM tb_dim_processo"))
            return {row[0] for row in result}
    except Exception:
        return set()

def registrar_log_notificacao(execution_id, id_processo, status_code, mensagem):
    """Registra o log de disparo do webhook do Power Automate."""
    engine = obter_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO tb_log_notificacao_power_automate 
            (tb_log_execution_id_cod, tb_log_id_processo_cod, tb_log_status_code, tb_log_mensagem_retorno, tb_log_data_hora_disparo)
            VALUES (:exec_id, :id_proc, :status, :msg, DATEADD(HOUR, -3, GETDATE()))
        """), {
            "exec_id": execution_id, 
            "id_proc": id_processo, 
            "status": status_code, 
            "msg": str(mensagem)[:4000]
        })

def registrar_saidas_processos(df_processos_capturados, id_usuario_robo):
    """
    Compara a fila atual do Portal com o banco de dados.
    Se um processo estava no banco para este usuário e sumiu da tela, registra a Data de Saída.
    """
    if df_processos_capturados.empty:
        return 0
        
    engine = obter_engine()
    
    # 1. Pega os IDs que o robô acabou de ver no Portal
    ids_na_tela = df_processos_capturados['idProcesso'].astype(int).tolist()
    
    with engine.begin() as conn:
        # 2. Pega os IDs que estão "ativos" (sem data de saída) no nosso banco para este usuário
        query = text("""
            SELECT tb_fact_id_processo_cod 
            FROM tb_fact_historico_usuario_processo 
            WHERE tb_fact_id_usuario_cod = :id_usu 
              AND tb_fact_is_responsavel_atual = 1
        """)
        df_banco = pd.read_sql(query, conn, params={"id_usu": id_usuario_robo})
        
        if df_banco.empty:
            return 0
            
        ids_no_banco = df_banco['tb_fact_id_processo_cod'].tolist()
        
        # 3. A Mágica da Conciliação (O que tem no banco mas NÃO tem na tela)
        ids_saida = list(set(ids_no_banco) - set(ids_na_tela))
        
        if not ids_saida:
            return 0 # Ninguém saiu da fila
            
        # 4. Processa as baixas em lotes para evitar travar o SQL Server
        for i in range(0, len(ids_saida), 100):
            lote_ids = ids_saida[i:i+100]
            placeholders = ', '.join([str(x) for x in lote_ids])
            
            # A) Registra a saída no Histórico do Usuário
            conn.execute(text(f"""
                UPDATE tb_fact_historico_usuario_processo
                SET tb_fact_data_saida = DATEADD(HOUR, -3, GETDATE()),
                    tb_fact_is_responsavel_atual = 0
                WHERE tb_fact_id_usuario_cod = {id_usuario_robo}
                  AND tb_fact_id_processo_cod IN ({placeholders})
            """))
            
            # B) Retira do "Estoque" (Fila de Envio) se o processo saiu antes de ser enviado
            conn.execute(text(f"""
                UPDATE tb_fact_fila_envio
                SET tb_fact_id_status_fila_cod = 2, 
                    tb_fact_mensagem_erro = 'Processo finalizado/transferido no Portal (Baixa Automática)',
                    tb_fact_data_ultima_tentativa = DATEADD(HOUR, -3, GETDATE())
                WHERE tb_fact_id_status_fila_cod = 1
                  AND tb_fact_id_processo_cod IN ({placeholders})
            """))
            
    return len(ids_saida)

def sincronizar_processos_existentes(df_processos_capturados, execution_id):
    """
    Escuta alterações em processos que já estão no banco e sincroniza os dados dinâmicos:
    dsStatus, idCicloCorrente, idEvento, fase_processo e flAlerta.
    """
    if df_processos_capturados.empty:
        return 0
        
    engine = obter_engine()
    
    # 1. Identifica quem já está no banco
    df_banco = pd.read_sql("SELECT tb_dim_id_processo_cod FROM tb_dim_processo", engine)
    ids_existentes = df_banco['tb_dim_id_processo_cod'].tolist()
    
    # 2. Separa APENAS os processos que já existem para atualizar
    df_existentes = df_processos_capturados[df_processos_capturados['idProcesso'].isin(ids_existentes)].copy()
    
    if df_existentes.empty:
        return 0
        
    with engine.begin() as conn:
        for _, row in df_existentes.iterrows():
            id_proc = int(row['idProcesso'])
            
            # ====================================================
            # A) ATUALIZA AS COLUNAS DA TABELA MESTRE (DIMENSÃO)
            # ====================================================
            fase_site = str(row.get('fase_processo', '')).strip()[:150]
            status_portal_raw = row.get('idStatusCorrente')
            id_status_portal = int(status_portal_raw) if pd.notna(status_portal_raw) else None
            
            # Tratamento booleano para o flAlerta
            alerta_str = str(row.get('flAlerta', '')).strip().upper()
            fl_alerta = 1 if alerta_str in ['TRUE', '1', 'S', 'SIM', 'TRUE'] else 0
            
            conn.execute(text("""
                UPDATE tb_dim_processo 
                SET tb_dim_fase_processo = COALESCE(:fase, tb_dim_fase_processo),
                    tb_dim_id_status_portal_cod = COALESCE(:id_status, tb_dim_id_status_portal_cod),
                    tb_dim_fl_alerta = :alerta
                WHERE tb_dim_id_processo_cod = :id
            """), {"fase": fase_site if fase_site else None, "id_status": id_status_portal, "alerta": fl_alerta, "id": id_proc})
            
            # ====================================================
            # B) EMPILHA NOVOS EVENTOS DE WORKFLOW (FATO)
            # ====================================================
            for evento in row.get('workflow', []):
                id_evento = evento.get('idEvento', 0)
                dt_evento = evento.get('data')
                
                if dt_evento:
                    # O "IF NOT EXISTS" faz o papel do <> (só insere se for alteração/novo)
                    conn.execute(text("""
                        IF NOT EXISTS (SELECT 1 FROM tb_fact_workflow_portal WHERE tb_fact_id_processo_cod = :id_p AND tb_fact_id_evento_portal_cod = :id_e)
                        BEGIN
                            INSERT INTO tb_fact_workflow_portal (tb_fact_id_processo_cod, tb_fact_id_evento_portal_cod, tb_fact_descricao_complementar, tb_fact_data_hora_evento, tb_fact_data_cadastro)
                            VALUES (:id_p, :id_e, :desc, :dt, DATEADD(HOUR, -3, GETDATE()))
                        END
                    """), {"id_p": id_proc, "id_e": id_evento, "desc": str(evento.get('descricao', ''))[:200], "dt": dt_evento})
            
            # ====================================================
            # C) EMPILHA MUDANÇAS DE CICLO E STATUS (STEPS)
            # ====================================================
            id_ciclo = row.get('idCicloCorrente')
            ds_status_proc = str(row.get('dsStatusCorrenteProcesso', '')).strip()[:200]
            ds_status = str(row.get('dsStatus', '')).strip()[:50]
            
            if pd.notna(id_ciclo) and int(id_ciclo) > 0:
                conn.execute(text("""
                    IF NOT EXISTS (SELECT 1 FROM tb_fact_workflow_step WHERE tb_fact_id_processo_cod = :id_p AND tb_fact_id_tarefa_cod = :id_c)
                    BEGIN
                        INSERT INTO tb_fact_workflow_step (tb_fact_id_processo_cod, tb_fact_id_tarefa_cod, tb_fact_nome_tarefa, tb_fact_status_tarefa, tb_fact_data_hora_step, tb_fact_data_cadastro)
                        VALUES (:id_p, :id_c, :nome, :status, DATEADD(HOUR, -3, GETDATE()), DATEADD(HOUR, -3, GETDATE()))
                    END
                """), {"id_p": id_proc, "id_c": int(id_ciclo), "nome": ds_status_proc, "status": ds_status})
                
    return len(df_existentes)
    