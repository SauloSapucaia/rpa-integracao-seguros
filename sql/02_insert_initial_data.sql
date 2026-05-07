-- 1. TIPOS DE EXPEDIENTE
INSERT INTO tb_dic_tipo_expediente (tb_dic_id_tipo_expediente_cod, tb_dic_sigla_expediente, tb_dic_desc_expediente) VALUES (1, 'DPA', 'Segurado DPA');
INSERT INTO tb_dic_tipo_expediente (tb_dic_id_tipo_expediente_cod, tb_dic_sigla_expediente, tb_dic_desc_expediente) VALUES (2, 'TRC', 'Terceiro TRC');
INSERT INTO tb_dic_tipo_expediente (tb_dic_id_tipo_expediente_cod, tb_dic_sigla_expediente, tb_dic_desc_expediente) VALUES (0, 'N/D', 'Não Identificado/Outros');

-- 2. STATUS DA FILA DO ROBÔ
INSERT INTO tb_dic_status_fila (tb_dic_status_fila_cod, tb_dic_codigo_status, tb_dic_desc_status, tb_dic_requer_atencao) VALUES (1, 'PENDENTE', 'Aguardando processamento', 0);
INSERT INTO tb_dic_status_fila (tb_dic_status_fila_cod, tb_dic_codigo_status, tb_dic_desc_status, tb_dic_requer_atencao) VALUES (2, 'ENVIADO', 'Sucesso - Retorno 201', 0);
INSERT INTO tb_dic_status_fila (tb_dic_status_fila_cod, tb_dic_codigo_status, tb_dic_desc_status, tb_dic_requer_atencao) VALUES (3, 'ERRO', 'Falha na comunicação', 1);
INSERT INTO tb_dic_status_fila (tb_dic_status_fila_cod, tb_dic_codigo_status, tb_dic_desc_status, tb_dic_requer_atencao) VALUES (4, 'CONFLITO', 'Erro 409 - Duplicidade', 1);

-- 3. TIPOS DE ENVOLVIDOS
INSERT INTO tb_dom_tipo_envolvido (tb_dom_id_tipo_envolvido_cod, tb_dom_desc_tipo_envolvido) VALUES (1, 'Segurado');
INSERT INTO tb_dom_tipo_envolvido (tb_dom_id_tipo_envolvido_cod, tb_dom_desc_tipo_envolvido) VALUES (2, 'Terceiro');
INSERT INTO tb_dom_tipo_envolvido (tb_dom_id_tipo_envolvido_cod, tb_dom_desc_tipo_envolvido) VALUES (3, 'Corretor');
INSERT INTO tb_dom_tipo_envolvido (tb_dom_id_tipo_envolvido_cod, tb_dom_desc_tipo_envolvido) VALUES (4, 'Analista Seguradora');

-- 4. TIPOS DE CONTATO
INSERT INTO tb_dom_tipo_contato (tb_dom_id_tipo_contato_cod, tb_dom_desc_tipo_contato) VALUES (1, 'Telefone Fixo');
INSERT INTO tb_dom_tipo_contato (tb_dom_id_tipo_contato_cod, tb_dom_desc_tipo_contato) VALUES (2, 'Telefone Celular');
INSERT INTO tb_dom_tipo_contato (tb_dom_id_tipo_contato_cod, tb_dom_desc_tipo_contato) VALUES (3, 'E-mail');

-- 5. CONFIGURAÇÕES DINÂMICAS DO ROBÔ E API PLATAFORMA DE GESTÃO
-- Credenciais da API da Plataforma de Gestão
INSERT INTO tb_config_api_plataforma_gestao (tb_config_base_url, tb_config_client_id, tb_config_client_secret, tb_config_timeout)
VALUES (
    'URL_API_PLATAFORMA_GESTAO_COLE_AQUI',
    'USUARIO_CLIENT_ID_AQUI',
    'SENHA_CLIENT_SECRET_AQUI',
    30
);
GO

-- Parâmetros Gerais (Com separação de Texto e Número)
INSERT INTO tb_config_parametros_robo (tb_config_chave_parametro, tb_config_tipo_dado, tb_config_descricao, tb_config_valor_texto, tb_config_valor_numero)
VALUES ('WEBHOOK_POWER_AUTOMATE', 'String', 'Gatilho de e-mail', 'COLE_SUA_URL_AQUI', NULL);

INSERT INTO tb_config_parametros_robo (tb_config_chave_parametro, tb_config_tipo_dado, tb_config_descricao, tb_config_valor_texto, tb_config_valor_numero)
VALUES ('ID_SOLICITANTE', 'Int', 'ID padrao do solicitante', NULL, 80);

INSERT INTO tb_config_parametros_robo (tb_config_chave_parametro, tb_config_tipo_dado, tb_config_descricao, tb_config_valor_texto, tb_config_valor_numero)
VALUES ('ID_SERVICO', 'Int', 'Código do Serviço', NULL, 2);

INSERT INTO tb_config_parametros_robo (tb_config_chave_parametro, tb_config_tipo_dado, tb_config_descricao, tb_config_valor_texto, tb_config_valor_numero)
VALUES ('ID_NATUREZA', 'Int', 'Código da Natureza do Sinistro', NULL, 3);
GO

-- 6. DICIONÁRIO DE DDDs E UFs
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (11, 'SP', 'São Paulo', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (12, 'SP', 'São Paulo', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (13, 'SP', 'São Paulo', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (14, 'SP', 'São Paulo', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (15, 'SP', 'São Paulo', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (16, 'SP', 'São Paulo', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (17, 'SP', 'São Paulo', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (18, 'SP', 'São Paulo', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (19, 'SP', 'São Paulo', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (21, 'RJ', 'Rio de Janeiro', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (22, 'RJ', 'Rio de Janeiro', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (24, 'RJ', 'Rio de Janeiro', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (27, 'ES', 'Espírito Santo', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (28, 'ES', 'Espírito Santo', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (31, 'MG', 'Minas Gerais', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (32, 'MG', 'Minas Gerais', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (33, 'MG', 'Minas Gerais', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (34, 'MG', 'Minas Gerais', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (35, 'MG', 'Minas Gerais', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (37, 'MG', 'Minas Gerais', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (38, 'MG', 'Minas Gerais', 'Sudeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (41, 'PR', 'Paraná', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (42, 'PR', 'Paraná', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (43, 'PR', 'Paraná', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (44, 'PR', 'Paraná', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (45, 'PR', 'Paraná', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (46, 'PR', 'Paraná', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (47, 'SC', 'Santa Catarina', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (48, 'SC', 'Santa Catarina', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (49, 'SC', 'Santa Catarina', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (51, 'RS', 'Rio Grande do Sul', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (53, 'RS', 'Rio Grande do Sul', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (54, 'RS', 'Rio Grande do Sul', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (55, 'RS', 'Rio Grande do Sul', 'Sul');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (61, 'DF', 'Distrito Federal', 'Centro-Oeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (62, 'GO', 'Goiás', 'Centro-Oeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (63, 'TO', 'Tocantins', 'Norte');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (64, 'GO', 'Goiás', 'Centro-Oeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (65, 'MT', 'Mato Grosso', 'Centro-Oeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (66, 'MT', 'Mato Grosso', 'Centro-Oeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (67, 'MS', 'Mato Grosso do Sul', 'Centro-Oeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (68, 'AC', 'Acre', 'Norte');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (69, 'RO', 'Rondônia', 'Norte');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (71, 'BA', 'Bahia', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (73, 'BA', 'Bahia', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (74, 'BA', 'Bahia', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (75, 'BA', 'Bahia', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (77, 'BA', 'Bahia', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (79, 'SE', 'Sergipe', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (81, 'PE', 'Pernambuco', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (82, 'AL', 'Alagoas', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (83, 'PB', 'Paraíba', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (84, 'RN', 'Rio Grande do Norte', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (85, 'CE', 'Ceará', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (86, 'PI', 'Piauí', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (87, 'PE', 'Pernambuco', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (88, 'CE', 'Ceará', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (89, 'PI', 'Piauí', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (91, 'PA', 'Pará', 'Norte');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (92, 'AM', 'Amazonas', 'Norte');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (93, 'PA', 'Pará', 'Norte');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (94, 'PA', 'Pará', 'Norte');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (95, 'RR', 'Roraima', 'Norte');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (96, 'AP', 'Amapá', 'Norte');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (97, 'AM', 'Amazonas', 'Norte');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (98, 'MA', 'Maranhão', 'Nordeste');
INSERT INTO tb_dic_ddd_uf (tb_dic_ddd_cod, tb_dic_uf, tb_dic_nome_estado, tb_dic_regiao) VALUES (99, 'MA', 'Maranhão', 'Nordeste');