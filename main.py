#%%
import uuid
import time
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import datetime
import logging
from src import config
from src import database
from src import auditoria
from src.portal_seguradora_api import extrair_portal_seguradora
from src.sinistro_api import PlataformaGestaoAPI
from src.funcoes_auxiliares import calcular_data_agendamento, consertar_uf_linha, obter_agora_br

#%%
def executar_robo():
    # Mude para True para preencher os dados em branco no banco. 
    # Mude para False para o fluxo normal do dia a dia.
    # MODO_ENRIQUECIMENTO = False

    hora_atual = obter_agora_br().hour
    dia_da_semana = obter_agora_br().weekday() # 0 = Segunda, 4 = Sexta, 5 = Sábado

    # --- 19/03/2026: MODO AUDITORIA (Exemplo: Sexta-feira às 18h) ---
    if dia_da_semana == 4 and hora_atual == 18:
        logging.info("🕒 Horário atual: 18h de Sexta-feira -> Iniciando MODO AUDITORIA DE LIMPEZA")
        from auditoria import executar_auditoria_semanal # Importa a função que criamos acima
        executar_auditoria_semanal()
        return # Encerra o robô aqui, pois a sexta 18h é só pra faxina
    
    if hora_atual in (8, 13):
        MODO_ENRIQUECIMENTO = True
        logging.info(f"🕒 Horário atual: {hora_atual}h -> Iniciando no MODO ENRIQUECIMENTO")
    else:
        MODO_ENRIQUECIMENTO = False
        logging.info(f"🕒 Horário atual: {hora_atual}h -> Iniciando no MODO CAPTURA")

    # =========================================================================
    # 1. INICIALIZAÇÃO E IDENTIDADE DA EXECUÇÃO
    inicio_execucao = obter_agora_br()
    execution_id = str(uuid.uuid4())
    
    status_final = "SUCESSO"
    msg_erro = "Execução concluída com êxito."
    lidos = 0
    novos = 0

    print(f"=== INICIANDO ROBÔ RPA PORTAL SEGURADORA (UUID: {execution_id}) ===")
    
    try:
        # 2. REGISTRO DE LOG E CARGA DE PARÂMETROS
        database.iniciar_log_execucao(execution_id)
        
        print("\n[PASSO 1] Carregando configurações e credenciais do banco...")
        credenciais = database.carregar_credenciais_portal()
        mapa_ddd = database.carregar_mapa_ddd()
        params = database.carregar_parametros_robo()

        if not credenciais:
            raise Exception("Nenhuma conta ativa encontrada na tb_config_credenciais!")

        # 3. EXTRAÇÃO DO PORTAL SEGURADORA (ETL - EXTRACT)
        print("\n[PASSO 2] Iniciando varredura no Portal da Seguradora...")

        if MODO_ENRIQUECIMENTO:
            print(" -> MODO ENRIQUECIMENTO ATIVO: Ignorando filtro de IDs existentes para atualizar o banco.")
            ids_filtro = set() # Passa um set vazio para ele extrair TUDO do portal
        else:
            ids_filtro = database.obter_ids_processos_existentes()

        df_portal = extrair_portal_seguradora(credenciais, ids_filtro) 
        lidos = len(df_portal)

        # 4. PERSISTÊNCIA E ENRIQUECIMENTO (ETL - LOAD & TRANSFORM)
        print("\n[PASSO 3] Gravando processos e satélites no Fabric...")
        if MODO_ENRIQUECIMENTO:
            ids_ja_no_banco = database.obter_ids_processos_existentes()
            df_portal['idProcesso'] = df_portal['idProcesso'].astype(int)
            
            df_novos_surgidos = df_portal[~df_portal['idProcesso'].isin(ids_ja_no_banco)]
            df_antigos = df_portal[df_portal['idProcesso'].isin(ids_ja_no_banco)]
            
            if not df_novos_surgidos.empty:
                print(f" -> Salvando {len(df_novos_surgidos)} processos INÉDITOS que caíram na fila enquanto o robô lia...")
                database.registrar_processos_no_banco(df_novos_surgidos, execution_id)
                
            if not df_antigos.empty:
                print(f" -> Enriquecendo {len(df_antigos)} processos antigos do estoque...")
                database.enriquecer_processos_existentes(df_antigos, execution_id)
            
            print("\n[MANUTENÇÃO] Finalizando execução antes das etapas 4 e 5 por segurança.")
            return 
            
        else:
            # Fluxo normal: Só grava o que é inédito
            novos = database.registrar_processos_no_banco(df_portal, execution_id)

            if not df_portal.empty:
                # 2. Sincroniza as atualizações (Fase, Status, Workflow) de quem já estava no banco
                qtd_sinc = database.sincronizar_processos_existentes(df_portal, execution_id)
                if qtd_sinc > 0:
                    print(f" -> [SINCRONIZAÇÃO] {qtd_sinc} processos verificados e atualizados.")

                # 3. CONCILIAÇÃO (Baixa de quem sumiu da fila)
                if 'idUsuario' in df_portal.columns:
                    for id_usu in df_portal['idUsuario'].dropna().unique():
                        df_usu_filtrado = df_portal[df_portal['idUsuario'] == id_usu]
                        qtd_baixa = database.registrar_saidas_processos(df_usu_filtrado, int(id_usu))
                        if qtd_baixa > 0:
                            print(f" -> [BAIXA] {qtd_baixa} processos do usuário {int(id_usu)} saíram da fila.")
            
            # ELT: O banco calcula a data mínima de abertura baseado no workflow inserido
            database.tratar_datas_abertura_banco()
            print(f" -> {novos} novos processos registrados e enriquecidos via SQL.")

            # print("\n[PASSO 4] Conciliação de Duplicidades (Base Azure D-1)...")
            # database.conciliar_fila_com_plataforma_gestao()

        # Adicione este comando para PARAR o robô aqui!
        # print(" -> [CARGA INICIAL] Parando execução antes do envio da API para evitar duplicidade.")
        # return

        print("\n[PASSO 4] Processando Fila de SLA para PlataformaGestao...")
        fila_pendente = database.obter_fila_pendente()
        if not fila_pendente.empty:
            api_plataforma = PlataformaGestaoAPI(params.get('ID_SOLICITANTE'), params.get('ID_SERVICO'), params.get('ID_NATUREZA'))

            ultimo_horario = None
            
            for _, proc in fila_pendente.iterrows():
                # Blindagem: Tenta nome novo ou antigo e garante conversão numérica para o banco
                id_fila = int(proc.get('id_fila') or proc.get('idFila') or 0)
                id_proc = int(proc.get('id_processo') or proc.get('idProcesso') or 0)
                dt_abertura_bruta = proc.get('data_portal') or proc.get('dtAberturaSinistro')

                hoje = obter_agora_br()
                limite_data = hoje - relativedelta(days=5) # Limite de 05 dias para abertura

                if pd.isna(dt_abertura_bruta) or dt_abertura_bruta < limite_data:
                    dt_abertura = obter_agora_br()
                else:
                    dt_abertura = dt_abertura_bruta

                no_sinistro = proc.get('sinistro_tratado', 'SemNumero')
                dt_ag = calcular_data_agendamento(dt_abertura, ultimo_horario)
                ultimo_horario = dt_ag
                dt_agendada_str = dt_ag.strftime("%Y-%m-%dT%H:%M:%S")
                
                print(f" -> {no_sinistro}: Agendado para {dt_agendada_str}")
                
                linha_dict = proc.to_dict()
                payload = api_plataforma.montar_payload({**linha_dict, 'data_agendada': dt_agendada_str})
                
                # Simulação ou Real (CORRIGIDO O ERRO DE TIPAGEM AQUI)
                if config.SIMULAR_ENVIO_API:
                    # Removido o "SIM-" para que o acionamentoId seja um número inteiro válido
                    res_api = {"status_code": 201, "acionamentoId": int(time.time()), "message": "Simulado"}
                    time.sleep(0.5)
                else:
                    res_api = api_plataforma.abrir_acionamento(execution_id, id_proc, payload)
                
                # 09/03/2026 - Correção na lógica de status para evitar que erros 409 (conflito) fiquem presos na fila
                # st_id = 2 if res_api["status_code"] in [200, 201] else 3

                # 09/03/2026 - Nova lógica de status:
                # 2 = Sucesso (200, 201) -> Sai da fila
                if res_api["status_code"] in [200, 201]:
                    st_id = 2 # SUCESSO (Sai da fila)
                elif res_api["status_code"] == 409:
                    st_id = 4 # CONFLITO (Já existe na API, sai da fila)
                else:
                    st_id = 3 # ERRO GERAL (Status 500, Timeout, etc -> Continua na fila tentando)

                if st_id == 3:
                    print(f"    [ERRO API] HTTP {res_api.get('status_code')} - Motivo: {res_api.get('message')}")
                
                msg_retorno = str(res_api.get("message", ""))

                # Se a API devolveu avisos de contacto (warnings), anexa-os à mensagem do log
                api_warnings = res_api.get("contactWarnings")
                if api_warnings and isinstance(api_warnings, list):
                    msg_retorno += " | Detalhes: " + ", ".join(api_warnings)
                
                # Se a mensagem estiver vazia ou for None (sucesso total)
                if not msg_retorno.strip() or msg_retorno == "None":
                    msg_retorno = "Cadastrado com Sucesso (Dados Completos)"

                # Atualiza o status no banco com o detalhamento real
                database.atualizar_status_fila(
                    id_fila=id_fila,
                    id_processo=id_proc,
                    status_id=st_id,
                    acionamento_id=res_api.get("acionamentoId"),
                    mensagem=msg_retorno,
                    dt_agendamento=dt_agendada_str
                )

                # O GATILHO DO E-MAIL (SUCESSO OU ERROS REAIS)
                status_real_api = res_api.get("status_code")
                
                # A REGRA: Dispara se for Sucesso (2) OU se for um Erro (3) que NÃO seja 409
                if st_id == 2 or (st_id == 3 and status_real_api != 409):
                    print("    -> Disparando E-mail no Power Automate...")
                    
                    # Avalia dinamicamente se foi sucesso (True) ou erro (False)
                    sucesso_envio = (st_id == 2)
                    
                    api_plataforma.enviar_notificacao_email(
                        execution_id=execution_id, 
                        id_processo=id_proc, 
                        linha_view=proc, 
                        acionamento_id=res_api.get("acionamentoId"), 
                        sucesso=sucesso_envio, 
                        mensagem_api=msg_retorno
                    )

    except Exception as e:
        status_final = "ERRO"
        msg_erro = f"Falha Crítica: {str(e)}"
        print(f"\n!!! ERRO NO ORQUESTRADOR: {e}")

    finally:
        # 6. ENCERRAMENTO E MÉTRICAS
        database.finalizar_log_execucao(execution_id, status_final, lidos, novos, msg_erro)
        
        duracao = obter_agora_br() - inicio_execucao
        print(f"\n=== EXECUÇÃO FINALIZADA EM {duracao} ===")
        print(f"Lidos: {lidos} | Novos: {novos} | Status: {status_final}")

if __name__ == "__main__":
    executar_robo()

#%%