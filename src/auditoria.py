import time
import sys
from sqlalchemy import text
from . import database
from .database import obter_engine
from .portal_seguradora_api import PortalSeguradoraAPI

def executar_auditoria_semanal():
    print("\n[MODO AUDITORIA] Iniciando varredura de processos antigos e ociosos...")
    engine = obter_engine()
    
    # Busca credenciais do banco
    credenciais = database.carregar_credenciais_portal()
    
    if not credenciais:
        print(" !! Erro: Nenhuma credencial ativa encontrada no banco para auditoria.")
        return

    # Pega a primeira conta disponível
    nome_conta = list(credenciais.keys())[0]
    dados_conta = credenciais[nome_conta]
    
    login_portal = dados_conta.get("login")
    senha_portal = dados_conta.get("senha")
    
    print(f" -> Usando a conta de {nome_conta.upper()} para realizar a auditoria...")
    
    api_portal = PortalSeguradoraAPI(login_portal, senha_portal)
    
    try:
        api_portal.autenticar() 
    except Exception as e:
        print(f" !! Falha ao autenticar no Portal para a Auditoria: {e}")
        return
    
    with engine.begin() as conn:
        # Puxa processos abertos que estão há mais de 15 dias na base
        query = text("""
            SELECT tb_dim_id_processo_cod, tb_dim_no_sinistro 
            FROM tb_dim_processo 
            WHERE tb_dim_id_status_portal_cod NOT IN (22, 98)
              AND DATEDIFF(DAY, tb_dim_dt_abertura_sinistro, GETDATE()) > 15
        """)
        processos_suspeitos = conn.execute(query).fetchall()
        
        total_processos = len(processos_suspeitos)
        
        if total_processos == 0:
            print(" -> Nenhum processo antigo pendente de auditoria.")
            return

        print(f" -> {total_processos} processos suspeitos encontrados. Validando de forma silenciosa...")
        
        qtd_baixados = 0
        qtd_ainda_abertos = 0
        
        for index, (id_proc, sinistro) in enumerate(processos_suspeitos, 1):
            
            # MÁGICA DO TERMINAL LIMPO: Sobrescreve a mesma linha mostrando o progresso
            print(f"    [*] Progresso da varredura: {index}/{total_processos} processos analisados...", end="\r")
            
            # 1. Tenta buscar pelo ID direto (mais rápido)
            dados_portal = api_portal.buscar_processo_por_id(id_proc)
            status_real_portal = dados_portal.get("idStatusCorrente")
            
            # 2. Se falhar, tenta pela nova função de Sinistro
            if not status_real_portal:
                dados_portal = api_portal.consultar_por_sinistro(sinistro)
                status_real_portal = dados_portal.get("idStatusCorrente")
            
            # 3. Tratamento de segurança
            if not status_real_portal:
                texto_status = str(dados_portal.get("dsStatusCorrenteProcesso", "")).upper()
                if "FINALIZADO" in texto_status or "CONCLU" in texto_status:
                    status_real_portal = 22
                elif "CANCELADO" in texto_status:
                    status_real_portal = 98

            # 4. Faz a avaliação final
            if status_real_portal in [22, 98]:
                # Como usou \r antes, a gente quebra a linha (\n) para a mensagem de sucesso não apagar
                print(f"\n    [✓] SUCESSO! Processo {id_proc} (Sinistro {sinistro}) finalizado no Portal. Atualizando o banco...")
                fase_visual = 'PROCESSO FINALIZADO (Auditoria Automática)' if status_real_portal == 22 else 'PROCESSO CANCELADO (Auditoria Automática)'
                
                # =========================================================
                # ATUALIZA O BANCO DE DADOS
                # =========================================================
                # 1. Atualiza a Dimensão
                conn.execute(text("""
                    UPDATE tb_dim_processo
                    SET tb_dim_fase_processo = :fase,
                        tb_dim_id_status_portal_cod = :id_portal,
                        tb_dim_fl_alerta = 0
                    WHERE tb_dim_id_processo_cod = :id_proc
                """), {
                    "fase": fase_visual,
                    "id_portal": status_real_portal,
                    "id_proc": id_proc
                })
                
                # 2. Desativa da Fila
                conn.execute(text("UPDATE tb_fact_fila_envio SET tb_fact_ativo = 0 WHERE tb_fact_id_processo_cod = :id_proc"), {"id_proc": id_proc})
                
                # 3. NOVO: Registra a Data de Saída do Analista
                conn.execute(text("""
                    UPDATE tb_fact_historico_usuario_processo
                    SET tb_fact_data_saida = DATEADD(HOUR, -3, GETDATE()),
                        tb_fact_is_responsavel_atual = 0
                    WHERE tb_fact_id_processo_cod = :id_proc
                      AND tb_fact_is_responsavel_atual = 1
                """), {"id_proc": id_proc})
                
                qtd_baixados += 1
            else:
                # O processo estava aberto mesmo. Não 'printa' nada, só soma no contador invisível.
                qtd_ainda_abertos += 1
                
            time.sleep(0.5) # Pausa de rate-limiting para a API do Portal

        # Pula uma linha no final para não sobrescrever o contador de progresso
        print(f"\n -> [AUDITORIA CONCLUÍDA] {qtd_baixados} processos foram baixados sozinhos e {qtd_ainda_abertos} continuam abertos legitimamente!")

        