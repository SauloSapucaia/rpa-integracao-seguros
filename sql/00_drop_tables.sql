-- =====================================================
-- LIMPEZA COMPLETA DO AMBIENTE
-- PROJETO RPA PIPELINE INTEGRAÇÃO SEGUROS
-- =====================================================

-- =====================================================
-- 1. DROP VIEW
-- =====================================================

IF OBJECT_ID('vw_processos_prontos_envio', 'V') IS NOT NULL
DROP VIEW vw_processos_prontos_envio;


-- =====================================================
-- 2. DROP LOG TABLES
-- =====================================================

DROP TABLE IF EXISTS tb_log_notificacao_power_automate;
DROP TABLE IF EXISTS tb_log_transacao_api;
DROP TABLE IF EXISTS tb_log_anomalia_negocio;
DROP TABLE IF EXISTS tb_log_execucao_robo;
DROP TABLE IF EXISTS tb_log_auditoria_credenciais;


-- =====================================================
-- 3. DROP CONFIG TABLES
-- =====================================================

DROP TABLE IF EXISTS tb_config_credenciais;
DROP TABLE IF EXISTS tb_config_parametros_robo;


-- =====================================================
-- 4. DROP FACT TABLES
-- =====================================================

DROP TABLE IF EXISTS tb_fact_transferencia_processo;
DROP TABLE IF EXISTS tb_fact_historico_usuario_processo;
DROP TABLE IF EXISTS tb_fact_sla_processo;
DROP TABLE IF EXISTS tb_fact_documento;
DROP TABLE IF EXISTS tb_fact_workflow_step;
DROP TABLE IF EXISTS tb_fact_workflow_portal;
DROP TABLE IF EXISTS tb_fact_acionamento_plataforma;
DROP TABLE IF EXISTS tb_fact_fila_envio;


-- =====================================================
-- 5. DROP DIMENSION TABLES
-- =====================================================

DROP TABLE IF EXISTS tb_dim_contato;
DROP TABLE IF EXISTS tb_dim_envolvido;
DROP TABLE IF EXISTS tb_dim_veiculo;
DROP TABLE IF EXISTS tb_dim_processo;
DROP TABLE IF EXISTS tb_dim_usuario_robo;


-- =====================================================
-- 6. DROP DOMAIN TABLES
-- =====================================================

DROP TABLE IF EXISTS tb_dom_tipo_contato;
DROP TABLE IF EXISTS tb_dom_status_portal;
DROP TABLE IF EXISTS tb_dom_evento_workflow;
DROP TABLE IF EXISTS tb_dom_tipo_envolvido;

DROP TABLE IF EXISTS tb_dic_status_fila;
DROP TABLE IF EXISTS tb_dic_ddd_uf;
DROP TABLE IF EXISTS tb_dic_tipo_expediente;
