-- =========================================================================
-- PROJETO: Pipeline RPA Integração Portal Seguradora -> Plataforma de Gestão
-- BANCO DE DADOS: Microsoft Fabric (SQL Database - OLTP)
-- PADRÃO: Minúsculo, prefixo tb_ e identificadores _cod
-- =========================================================================

-- =========================================================================
-- 0. CAMADA RAW (DADOS CRUS DO PORTAL SEGURADORA)
-- =========================================================================
CREATE TABLE tb_raw_processos_portal (
    tb_raw_id_processo_cod BIGINT PRIMARY KEY,
    tb_raw_no_sinistro VARCHAR(50),
    tb_raw_json_completo VARCHAR(MAX) NOT NULL, 
    tb_raw_data_captura DATETIME DEFAULT GETDATE()
);
GO
CREATE TABLE tb_raw_historico_processos_portal (
    id_historico INT IDENTITY(1,1) PRIMARY KEY,
    tb_raw_id_processo_cod INT NOT NULL,
    tb_raw_no_sinistro VARCHAR(50),
    tb_raw_json_completo NVARCHAR(MAX),
    tb_raw_data_captura DATETIME DEFAULT DATEADD(HOUR, -3, GETDATE())
);
GO
-- =========================================================================
-- 1. TABELAS DE DOMÍNIO (DICIONÁRIOS)
-- =========================================================================
CREATE TABLE tb_dic_tipo_expediente (
    tb_dic_id_tipo_expediente_cod INT PRIMARY KEY,
    tb_dic_sigla_expediente VARCHAR(5),
    tb_dic_desc_expediente VARCHAR(50),
    tb_dic_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dic_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_dic_ddd_uf (
    tb_dic_ddd_cod INT PRIMARY KEY,
    tb_dic_uf VARCHAR(2),
    tb_dic_nome_estado VARCHAR(50),
    tb_dic_regiao VARCHAR(20),
    tb_dic_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dic_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_dic_status_fila (
    tb_dic_status_fila_cod INT PRIMARY KEY,
    tb_dic_codigo_status VARCHAR(30),
    tb_dic_desc_status VARCHAR(100),
    tb_dic_requer_atencao BIT,
    tb_dic_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dic_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_dom_tipo_envolvido (
    tb_dom_id_tipo_envolvido_cod INT PRIMARY KEY,
    tb_dom_desc_tipo_envolvido VARCHAR(50),
    tb_dom_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dom_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_dom_evento_workflow (
    tb_dom_id_evento_portal_cod BIGINT PRIMARY KEY,
    tb_dom_desc_evento VARCHAR(200),
    tb_dom_fase_processo VARCHAR(50),
    tb_dom_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dom_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_dom_status_portal (
    tb_dom_id_status_portal_cod INT PRIMARY KEY,
    tb_dom_desc_status_portal VARCHAR(100),
    tb_dom_is_status_final BIT,
    tb_dom_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dom_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_dom_tipo_contato (
    tb_dom_id_tipo_contato_cod INT PRIMARY KEY,
    tb_dom_desc_tipo_contato VARCHAR(20),
    tb_dom_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dom_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_dom_status_operadora (
    tb_dom_id_status_operadora_cod INT PRIMARY KEY,
    tb_dom_desc_status_operadora VARCHAR(100) NOT NULL,
    tb_dom_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dom_ativo BIT DEFAULT 1
);
GO

-- =========================================================================
-- 2. TABELAS DE DIMENSÃO (CADASTROS BASE)
-- =========================================================================
CREATE TABLE tb_dim_usuario_robo (
    tb_dim_id_usuario_cod INT PRIMARY KEY,
    tb_dim_nome_usuario VARCHAR(50),
    tb_dim_login_portal VARCHAR(100),
    tb_dim_email_usuario VARCHAR(150), 
    tb_dim_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dim_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_dim_processo (
    tb_dim_id_processo_cod BIGINT PRIMARY KEY,
    tb_dim_no_sinistro VARCHAR(50) NOT NULL,
    tb_dim_id_tipo_expediente_cod INT, 
    tb_dim_id_status_portal_cod INT,     
    tb_dim_uf_processo VARCHAR(2),
    tb_dim_nm_cia VARCHAR(100),
    tb_dim_dt_abertura_sinistro DATETIME,
    tb_dim_dt_ocorrencia_sinistro DATETIME, 
    tb_dim_fase_processo VARCHAR(150), 
    tb_dim_fl_alerta BIT, 
    tb_dim_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dim_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_dim_veiculo (
    tb_dim_id_veiculo_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_dim_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_dim_placa VARCHAR(10),
    tb_dim_chassi VARCHAR(50),
    tb_dim_marca VARCHAR(50),
    tb_dim_modelo VARCHAR(100),
    tb_dim_sub_modelo VARCHAR(150), 
    tb_dim_ano_fabricacao INT,
    tb_dim_valor_fipe DECIMAL(18,2),
    tb_dim_is_alienado BIT, 
    tb_dim_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dim_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_dim_envolvido (
    tb_dim_id_envolvido_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_dim_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_dim_id_tipo_envolvido_cod INT, 
    tb_dim_nome VARCHAR(150),
    tb_dim_cpf_cnpj VARCHAR(20),
    tb_dim_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dim_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_dim_contato (
    tb_dim_id_contato_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_dim_id_envolvido_cod INT FOREIGN KEY REFERENCES tb_dim_envolvido(tb_dim_id_envolvido_cod),
    tb_dim_id_tipo_contato_cod INT, 
    tb_dim_ddd_cod INT,             
    tb_dim_valor_contato VARCHAR(150),
    tb_dim_is_principal BIT,
    tb_dim_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_dim_ativo BIT DEFAULT 1
);
GO

-- =========================================================================
-- 3. TABELAS DE FATO (MOVIMENTAÇÕES, FILA E EVENTOS)
-- =========================================================================
CREATE TABLE tb_fact_fila_envio (
    tb_fact_id_fila_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_fact_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_fact_id_status_fila_cod INT FOREIGN KEY REFERENCES tb_dic_status_fila(tb_dic_status_fila_cod), 
    tb_fact_tentativas INT DEFAULT 0,
    tb_fact_data_hora_agendamento DATETIME,
    tb_fact_data_ultima_tentativa DATETIME,
    tb_fact_mensagem_erro VARCHAR(MAX),
    tb_fact_data_cadastro DATETIME DEFAULT GETDATE(),
    tb_fact_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_fact_acionamento_plataforma (
    tb_fact_id_acionamento_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_fact_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_fact_acionamento_id_api VARCHAR(100),
    tb_fact_status_plataforma VARCHAR(50),
    tb_fact_hash_dados_processo VARCHAR(256),
    tb_fact_data_ultima_sincronizacao DATETIME,
    tb_fact_data_cadastro DATETIME DEFAULT GETDATE()
);
GO
CREATE TABLE tb_fact_workflow_portal (
    tb_fact_id_workflow_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_fact_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_fact_id_evento_portal_cod BIGINT, 
    tb_fact_descricao_complementar VARCHAR(MAX),
    tb_fact_data_hora_evento DATETIME,
    tb_fact_data_cadastro DATETIME DEFAULT GETDATE()
);
GO
CREATE TABLE tb_fact_workflow_step (
    tb_fact_id_workflow_step_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_fact_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_fact_id_tarefa_cod BIGINT,
    tb_fact_nome_tarefa VARCHAR(200),
    tb_fact_status_tarefa VARCHAR(50),
    tb_fact_data_hora_step DATETIME,
    tb_fact_data_cadastro DATETIME DEFAULT GETDATE()
);
GO
CREATE TABLE tb_fact_documento (
    tb_fact_id_doc_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_fact_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_fact_nome_documento VARCHAR(200),
    tb_fact_status_documento VARCHAR(50),
    tb_fact_data_saida DATETIME NULL,
    tb_fact_data_cadastro DATETIME DEFAULT GETDATE()
);
GO
CREATE TABLE tb_fact_sla_processo (
    tb_fact_id_sla_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_fact_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_fact_data_recepcao_portal DATETIME,
    tb_fact_data_captura_robo DATETIME,
    tb_fact_data_envio_plataforma DATETIME,
    tb_fact_tempo_fila_minutos INT,
    tb_fact_status_sla VARCHAR(50),
    tb_fact_data_cadastro DATETIME DEFAULT GETDATE()
);
GO
CREATE TABLE tb_fact_historico_usuario_processo (
    tb_fact_id_historico_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_fact_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_fact_id_usuario_cod INT FOREIGN KEY REFERENCES tb_dim_usuario_robo(tb_dim_id_usuario_cod),
    tb_fact_data_entrada DATETIME NOT NULL DEFAULT GETDATE(),
    tb_fact_data_saida DATETIME NULL, 
    tb_fact_is_responsavel_atual BIT DEFAULT 1 
);
GO
CREATE TABLE tb_fact_transferencia_processo (
    tb_fact_id_transferencia_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_fact_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_fact_id_usuario_origem_cod INT FOREIGN KEY REFERENCES tb_dim_usuario_robo(tb_dim_id_usuario_cod), 
    tb_fact_id_usuario_destino_cod INT FOREIGN KEY REFERENCES tb_dim_usuario_robo(tb_dim_id_usuario_cod), 
    tb_fact_data_hora_transferencia DATETIME DEFAULT GETDATE(),
    tb_fact_tipo_movimentacao VARCHAR(50) 
);
GO

-- =========================================================================
-- 4. CONFIGURAÇÕES GLOBAIS E LOGS (GOVERNANÇA)
-- =========================================================================
CREATE TABLE tb_config_parametros_robo (
    tb_config_id_parametro_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_config_chave_parametro VARCHAR(100) UNIQUE,
    tb_config_valor_parametro VARCHAR(200),
    tb_config_tipo_dado VARCHAR(20),
    tb_config_descricao VARCHAR(255),
    tb_config_data_ultima_alteracao DATETIME DEFAULT GETDATE(),
    tb_config_usuario_alteracao VARCHAR(50)
);
GO
CREATE TABLE tb_config_credenciais (
    tb_config_id_credencial_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_config_sistema VARCHAR(50),
    tb_config_login_usuario VARCHAR(100) NOT NULL,
    tb_config_senha_usuario VARCHAR(255) NOT NULL,
    tb_config_nome_responsavel VARCHAR(100),
    tb_config_data_ultima_atualizacao DATETIME DEFAULT GETDATE(),
    tb_config_atualizado_por VARCHAR(100),
    tb_config_is_ativo BIT DEFAULT 1
);
GO
CREATE TABLE tb_log_auditoria_credenciais (
    tb_log_id_log_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_log_sistema VARCHAR(50),
    tb_log_login_usuario VARCHAR(100),
    tb_log_acao_realizada VARCHAR(50),
    tb_log_quem_alterou VARCHAR(100),
    tb_log_data_hora_alteracao DATETIME DEFAULT GETDATE()
);
GO
CREATE TABLE tb_log_execucao_robo (
    tb_log_execution_id_cod VARCHAR(50) PRIMARY KEY,
    tb_log_data_inicio DATETIME,
    tb_log_data_fim DATETIME,
    tb_log_status_execucao VARCHAR(20),
    tb_log_qtd_processos_lidos INT,
    tb_log_qtd_novos_processos INT,
    tb_log_mensagem_geral VARCHAR(MAX)
);
GO
CREATE TABLE tb_log_transacao_api (
    tb_log_id_transacao_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_log_execution_id_cod VARCHAR(50) FOREIGN KEY REFERENCES tb_log_execucao_robo(tb_log_execution_id_cod),
    tb_log_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_log_sistema_destino VARCHAR(50),
    tb_log_tipo_acao VARCHAR(50),
    tb_log_status_code INT,
    tb_log_payload_enviado VARCHAR(MAX),
    tb_log_resposta_recebida VARCHAR(MAX),
    tb_log_data_hora_transacao DATETIME DEFAULT GETDATE()
);
GO
CREATE TABLE tb_log_notificacao_power_automate (
    tb_log_id_notificacao_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_log_execution_id_cod VARCHAR(50) FOREIGN KEY REFERENCES tb_log_execucao_robo(tb_log_execution_id_cod),
    tb_log_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_log_tipo_notificacao VARCHAR(50) DEFAULT 'email_acionamento',
    tb_log_status_code INT,
    tb_log_payload_enviado VARCHAR(MAX),
    tb_log_mensagem_retorno VARCHAR(MAX),
    tb_log_data_hora_disparo DATETIME DEFAULT GETDATE()
);
GO
CREATE TABLE tb_log_anomalia_negocio (
    tb_log_id_anomalia_cod INT IDENTITY(1,1) PRIMARY KEY,
    tb_log_execution_id_cod VARCHAR(50) FOREIGN KEY REFERENCES tb_log_execucao_robo(tb_log_execution_id_cod),
    tb_log_id_processo_cod BIGINT FOREIGN KEY REFERENCES tb_dim_processo(tb_dim_id_processo_cod),
    tb_log_tipo_anomalia VARCHAR(100),
    tb_log_descricao_detalhada VARCHAR(MAX),
    tb_log_nivel_gravidade VARCHAR(20),
    tb_log_data_detecao DATETIME DEFAULT GETDATE(),
    tb_log_resolvido BIT DEFAULT 0
);
GO

-- =========================================================================
-- 1. CORRIGINDO A VIEW DE ENVIO (Tirando o espaço do 'T')
-- =========================================================================
CREATE OR ALTER VIEW vw_processos_prontos_envio AS
SELECT 
    f.tb_fact_id_fila_cod AS id_fila,
    p.tb_dim_id_processo_cod AS id_processo,
    p.tb_dim_nm_cia AS cia,
    p.tb_dim_uf_processo AS uf_processo, 
    CASE WHEN de.tb_dic_sigla_expediente = 'TRC' THEN p.tb_dim_no_sinistro + 'T' ELSE p.tb_dim_no_sinistro END AS sinistro_tratado,
    
    p.tb_dim_fase_processo AS fase_processo_site,
    se.tb_dom_id_status_operadora_cod AS id_status_operadora,
    se.tb_dom_desc_status_operadora AS desc_status_oficial_operadora,
    p.tb_dim_id_status_portal_cod AS id_status_portal_original,
    sm.tb_dom_desc_status_portal AS desc_status_portal_original,
    sm.tb_dom_contexto_portal AS contexto_portal,
    p.tb_dim_fl_alerta AS alerta_processo,
    env.tb_dim_id_tipo_envolvido_cod AS tipo_envolvido_id,
    LTRIM(RTRIM(REPLACE(REPLACE(REPLACE(env.tb_dim_nome, '  ', ' ' + CHAR(7)), CHAR(7) + ' ', ''), CHAR(7), ''))) AS nome_segurado,
    COALESCE(NULLIF(con_email.tb_dim_valor_contato, ''), 'nao_informado@segurado.com') AS email_segurado,
    con_tel.tb_dim_ddd_cod AS ddd_segurado,
    con_tel.tb_dim_valor_contato AS tel_segurado,
    CASE WHEN LEN(REPLACE(env.tb_dim_cpf_cnpj, '.0', '')) <= 11 THEN 1 ELSE 2 END AS tipo_doc_id,
    CASE WHEN LEN(REPLACE(env.tb_dim_cpf_cnpj, '.0', '')) <= 11 
         THEN RIGHT('00000000000' + REPLACE(env.tb_dim_cpf_cnpj, '.0', ''), 11)
         ELSE RIGHT('00000000000000' + REPLACE(env.tb_dim_cpf_cnpj, '.0', ''), 14)
    END AS doc_formatado,
    env_corr.tb_dim_nome AS nome_corretor,
    con_corr_email.tb_dim_valor_contato AS email_corretor,
    con_corr_tel.tb_dim_valor_contato AS tel_corretor,
    env_ana_seguradora.tb_dim_nome AS nome_analista_seguradora,
    con_ana_email.tb_dim_valor_contato AS email_analista_seguradora,
    u.tb_dim_nome_usuario AS nome_analista_operadora,
    u.tb_dim_email_usuario AS email_analista_operadora,
    p.tb_dim_dt_ocorrencia_sinistro AS dt_sinistro,
    p.tb_dim_dt_abertura_sinistro AS data_portal,
    v.tb_dim_placa AS placa_veiculo,
    v.tb_dim_chassi AS chassi_veiculo,
    v.tb_dim_marca AS marca_veiculo,
    v.tb_dim_modelo AS modelo_veiculo,
    v.tb_dim_sub_modelo AS sub_modelo_veiculo,
    v.tb_dim_ano_fabricacao AS ano_fabricacao,
    v.tb_dim_is_alienado AS veiculo_alienado,
    v.tb_dim_valor_fipe AS valor_fipe,
    f.tb_fact_data_hora_agendamento AS data_agendada
FROM tb_fact_fila_envio f
JOIN tb_dim_processo p ON f.tb_fact_id_processo_cod = p.tb_dim_id_processo_cod
LEFT JOIN tb_dic_tipo_expediente de ON p.tb_dim_id_tipo_expediente_cod = de.tb_dic_id_tipo_expediente_cod
LEFT JOIN tb_dom_status_portal sm ON p.tb_dim_id_status_portal_cod = sm.tb_dom_id_status_portal_cod 
LEFT JOIN tb_dom_status_operadora se ON sm.tb_dom_id_status_operadora_cod = se.tb_dom_id_status_operadora_cod
LEFT JOIN (
    SELECT tb_fact_id_processo_cod, MAX(tb_fact_id_usuario_cod) AS id_usuario 
    FROM tb_fact_historico_usuario_processo 
    GROUP BY tb_fact_id_processo_cod
) hist ON p.tb_dim_id_processo_cod = hist.tb_fact_id_processo_cod
LEFT JOIN tb_dim_usuario_robo u ON hist.id_usuario = u.tb_dim_id_usuario_cod
LEFT JOIN tb_dim_envolvido env_ana_seguradora ON p.tb_dim_id_processo_cod = env_ana_seguradora.tb_dim_id_processo_cod AND env_ana_seguradora.tb_dim_id_tipo_envolvido_cod = 4
OUTER APPLY (SELECT TOP 1 tb_dim_valor_contato FROM tb_dim_contato WHERE tb_dim_id_envolvido_cod = env_ana_seguradora.tb_dim_id_envolvido_cod AND tb_dim_id_tipo_contato_cod = 3 ORDER BY tb_dim_is_principal DESC) AS con_ana_email
LEFT JOIN tb_dim_envolvido env ON p.tb_dim_id_processo_cod = env.tb_dim_id_processo_cod AND env.tb_dim_id_tipo_envolvido_cod IN (1, 2)
OUTER APPLY (SELECT TOP 1 tb_dim_valor_contato FROM tb_dim_contato WHERE tb_dim_id_envolvido_cod = env.tb_dim_id_envolvido_cod AND tb_dim_id_tipo_contato_cod = 3 ORDER BY tb_dim_is_principal DESC) AS con_email
OUTER APPLY (SELECT TOP 1 tb_dim_ddd_cod, tb_dim_valor_contato FROM tb_dim_contato WHERE tb_dim_id_envolvido_cod = env.tb_dim_id_envolvido_cod AND tb_dim_id_tipo_contato_cod = 2 ORDER BY tb_dim_is_principal DESC) AS con_tel
LEFT JOIN tb_dim_envolvido env_corr ON p.tb_dim_id_processo_cod = env_corr.tb_dim_id_processo_cod AND env_corr.tb_dim_id_tipo_envolvido_cod = 3
OUTER APPLY (SELECT TOP 1 tb_dim_valor_contato FROM tb_dim_contato WHERE tb_dim_id_envolvido_cod = env_corr.tb_dim_id_envolvido_cod AND tb_dim_id_tipo_contato_cod = 3 ORDER BY tb_dim_is_principal DESC) AS con_corr_email
OUTER APPLY (SELECT TOP 1 tb_dim_ddd_cod, tb_dim_valor_contato FROM tb_dim_contato WHERE tb_dim_id_envolvido_cod = env_corr.tb_dim_id_envolvido_cod AND tb_dim_id_tipo_contato_cod = 2 ORDER BY tb_dim_is_principal DESC) AS con_corr_tel
LEFT JOIN tb_dim_veiculo v ON p.tb_dim_id_processo_cod = v.tb_dim_id_processo_cod
WHERE f.tb_fact_id_status_fila_cod IN (1, 3) AND f.tb_fact_ativo = 1;
GO

-- =========================================================================
-- 2. CORRIGINDO A VIEW DE HISTÓRICO GERAL (Mantendo o padrão)
-- =========================================================================
CREATE OR ALTER VIEW vw_historico_geral_processos AS
SELECT 
    p.tb_dim_id_processo_cod AS id_processo,
    CASE WHEN de.tb_dic_sigla_expediente = 'TRC' THEN p.tb_dim_no_sinistro + 'T' ELSE p.tb_dim_no_sinistro END AS sinistro_tratado,
    p.tb_dim_no_sinistro AS numero_sinistro_original,
    p.tb_dim_nm_cia AS cia,
    p.tb_dim_uf_processo AS uf_processo, 
    de.tb_dic_desc_expediente AS tipo_expediente,
    p.tb_dim_fase_processo AS fase_processo_site,
    p.tb_dim_fl_alerta AS alerta_processo,
    se.tb_dom_desc_status_operadora AS status_oficial_operadora,
    sm.tb_dom_desc_status_portal AS status_portal_original,
    sf.tb_dic_codigo_status AS status_robo,
    fe.tb_fact_mensagem_erro AS mensagem_robo_api,
    p.tb_dim_dt_abertura_sinistro AS data_abertura_sinistro,
    p.tb_dim_dt_ocorrencia_sinistro AS data_ocorrencia_sinistro,
    sla.tb_fact_data_captura_robo AS data_capturado_site,
    sla.tb_fact_data_envio_plataforma AS data_cadastrado_plataforma,
    hist.data_saida AS data_saida_fila_portal,
    ult_alt.ultima_alteracao_site AS data_ultima_mudanca_site,
    u.tb_dim_nome_usuario AS analista_operadora,
    env_ana_seguradora.tb_dim_nome AS analista_seguradora,
    con_ana_email.tb_dim_valor_contato AS email_analista_seguradora,
    te.tb_dom_desc_tipo_envolvido AS papel_envolvido,
    LTRIM(RTRIM(REPLACE(REPLACE(REPLACE(env.tb_dim_nome, '  ', ' ' + CHAR(7)), CHAR(7) + ' ', ''), CHAR(7), ''))) AS nome_segurado_terceiro,
    CASE WHEN LEN(REPLACE(env.tb_dim_cpf_cnpj, '.0', '')) <= 11 
         THEN RIGHT('00000000000' + REPLACE(env.tb_dim_cpf_cnpj, '.0', ''), 11)
         ELSE RIGHT('00000000000000' + REPLACE(env.tb_dim_cpf_cnpj, '.0', ''), 14)
    END AS documento_segurado_terceiro,
    con_email.tb_dim_valor_contato AS email_segurado_terceiro,
    CAST(con_tel.tb_dim_ddd_cod AS VARCHAR) + CAST(con_tel.tb_dim_valor_contato AS VARCHAR) AS telefone_segurado_terceiro,
    env_corr.tb_dim_nome AS nome_corretor,
    con_corr_email.tb_dim_valor_contato AS email_corretor,
    CAST(con_corr_tel.tb_dim_ddd_cod AS VARCHAR) + CAST(con_corr_tel.tb_dim_valor_contato AS VARCHAR) AS telefone_corretor,
    v.tb_dim_placa AS placa_veiculo,
    v.tb_dim_chassi AS chassi_veiculo,
    v.tb_dim_marca AS marca_veiculo,
    v.tb_dim_modelo AS modelo_veiculo,
    v.tb_dim_sub_modelo AS sub_modelo_veiculo,
    v.tb_dim_ano_fabricacao AS ano_fabricacao,
    v.tb_dim_is_alienado AS veiculo_alienado,
    v.tb_dim_valor_fipe AS valor_fipe
FROM tb_dim_processo p
LEFT JOIN tb_dic_tipo_expediente de ON p.tb_dim_id_tipo_expediente_cod = de.tb_dic_id_tipo_expediente_cod
LEFT JOIN tb_dom_status_portal sm ON p.tb_dim_id_status_portal_cod = sm.tb_dom_id_status_portal_cod 
LEFT JOIN tb_dom_status_operadora se ON sm.tb_dom_id_status_operadora_cod = se.tb_dom_id_status_operadora_cod
LEFT JOIN tb_fact_fila_envio fe ON p.tb_dim_id_processo_cod = fe.tb_fact_id_processo_cod
LEFT JOIN tb_dic_status_fila sf ON fe.tb_fact_id_status_fila_cod = sf.tb_dic_status_fila_cod
LEFT JOIN tb_fact_sla_processo sla ON p.tb_dim_id_processo_cod = sla.tb_fact_id_processo_cod
LEFT JOIN tb_dim_veiculo v ON p.tb_dim_id_processo_cod = v.tb_dim_id_processo_cod
LEFT JOIN (
    SELECT 
        tb_fact_id_processo_cod, 
        MAX(tb_fact_id_usuario_cod) AS id_usuario,
        MAX(tb_fact_data_saida) AS data_saida
    FROM tb_fact_historico_usuario_processo 
    GROUP BY tb_fact_id_processo_cod
) hist ON p.tb_dim_id_processo_cod = hist.tb_fact_id_processo_cod
LEFT JOIN tb_dim_usuario_robo u ON hist.id_usuario = u.tb_dim_id_usuario_cod
OUTER APPLY (
    SELECT MAX(dt) AS ultima_alteracao_site
    FROM (
        SELECT tb_dim_data_cadastro AS dt FROM tb_dim_processo WHERE tb_dim_id_processo_cod = p.tb_dim_id_processo_cod
        UNION ALL
        SELECT MAX(tb_fact_data_cadastro) FROM tb_fact_workflow_portal WHERE tb_fact_id_processo_cod = p.tb_dim_id_processo_cod
        UNION ALL
        SELECT MAX(tb_fact_data_cadastro) FROM tb_fact_workflow_step WHERE tb_fact_id_processo_cod = p.tb_dim_id_processo_cod
    ) AS datas
) AS ult_alt
LEFT JOIN tb_dim_envolvido env_ana_seguradora ON p.tb_dim_id_processo_cod = env_ana_seguradora.tb_dim_id_processo_cod AND env_ana_seguradora.tb_dim_id_tipo_envolvido_cod = 4
OUTER APPLY (SELECT TOP 1 tb_dim_valor_contato FROM tb_dim_contato WHERE tb_dim_id_envolvido_cod = env_ana_seguradora.tb_dim_id_envolvido_cod AND tb_dim_id_tipo_contato_cod = 3 ORDER BY tb_dim_is_principal DESC) AS con_ana_email
LEFT JOIN tb_dim_envolvido env ON p.tb_dim_id_processo_cod = env.tb_dim_id_processo_cod AND env.tb_dim_id_tipo_envolvido_cod IN (1, 2)
LEFT JOIN tb_dom_tipo_envolvido te ON env.tb_dim_id_tipo_envolvido_cod = te.tb_dom_id_tipo_envolvido_cod
OUTER APPLY (SELECT TOP 1 tb_dim_valor_contato FROM tb_dim_contato WHERE tb_dim_id_envolvido_cod = env.tb_dim_id_envolvido_cod AND tb_dim_id_tipo_contato_cod = 3 ORDER BY tb_dim_is_principal DESC) AS con_email
OUTER APPLY (SELECT TOP 1 tb_dim_ddd_cod, tb_dim_valor_contato FROM tb_dim_contato WHERE tb_dim_id_envolvido_cod = env.tb_dim_id_envolvido_cod AND tb_dim_id_tipo_contato_cod = 2 ORDER BY tb_dim_is_principal DESC) AS con_tel
LEFT JOIN tb_dim_envolvido env_corr ON p.tb_dim_id_processo_cod = env_corr.tb_dim_id_processo_cod AND env_corr.tb_dim_id_tipo_envolvido_cod = 3
OUTER APPLY (SELECT TOP 1 tb_dim_valor_contato FROM tb_dim_contato WHERE tb_dim_id_envolvido_cod = env_corr.tb_dim_id_envolvido_cod AND tb_dim_id_tipo_contato_cod = 3 ORDER BY tb_dim_is_principal DESC) AS con_corr_email
OUTER APPLY (SELECT TOP 1 tb_dim_ddd_cod, tb_dim_valor_contato FROM tb_dim_contato WHERE tb_dim_id_envolvido_cod = env_corr.tb_dim_id_envolvido_cod AND tb_dim_id_tipo_contato_cod = 2 ORDER BY tb_dim_is_principal DESC) AS con_corr_tel;
GO
