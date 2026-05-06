# 🤖 Pipeline RPA: Integração End-to-End entre Portais de Seguros e Sistema de Gestão

> **Nota de Confidencialidade:** Este projeto foi desenvolvido em ambiente corporativo real. Os nomes das empresas envolvidas foram omitidos por contrato de confidencialidade. Toda a lógica de negócio, arquitetura de dados e código estão preservados em sua forma original.

---

## 📋 Visão Geral do Problema

O fluxo operacional exigia o monitoramento humano constante de um portal web de terceiros (Seguradora Parceira) para identificar a entrada de novos sinistros. Essa verificação manual e sistemática ao longo do dia consumia muitas horas da equipe e gerava atrasos na atualização da base de dados interna e no registro na Plataforma de Gestão de Sinistros.

**A solução foi a construção de um ecossistema de automação completo e autossuficiente.**

---

## 🏗️ Arquitetura da Solução

```
Portal da Seguradora (API REST) 
        │
        ▼
[ portal_seguradora_api.py ]   ← Extração com Rate Limiting, Retry e Paginação
        │
        ▼
[ main.py - Orquestrador ]     ← Controle de Fluxo, Modos e Logs
        │
        ├──► [ database.py ]   ← Persistência no Microsoft Fabric (SQL Server)
        │         │
        │         ▼
        │    [ Azure Fabric ]  ← Data Warehouse com Modelagem Dimensional
        │
        └──► [ sinistro_api.py ] ← Envio para Plataforma de Gestão + Notificações
                  │
                  ▼
         [ Power Automate ]    ← Disparador de Alertas por E-mail
```

### Stack Tecnológico

| Componente              | Tecnologia                                              |
|-------------------------|---------------------------------------------------------|
| Linguagem               | Python 3.x                                              |
| Banco de Dados em Nuvem | Microsoft Fabric (SQL Server / T-SQL)                   |
| Autenticação de Banco   | Azure Identity (Entra ID / InteractiveBrowserCredential)|
| Autenticação de API     | JWT Bearer Token                                        |
| Alertas                 | Microsoft Power Automate (Webhook)                      |
| Parametrização          | Padrão EAV no banco — zero hardcode de credenciais      |

---

## ⚙️ Funcionalidades Implementadas

### 🔄 Modos de Execução Inteligente
O robô detecta automaticamente o horário de execução e escolhe o modo:

- **Modo Captura (padrão):** Busca processos *inéditos* no portal com filtro de IDs existentes.
- **Modo Enriquecimento (horários específicos):** Recarrega dados pesados (veículo, envolvidos, workflow) em processos existentes — estratégia de *backfill* agendado.
- **Modo Auditoria (sexta-feira às 18h):** Varredura semanal silenciosa que consulta o status real de processos antigos e realiza baixa automática dos encerrados.

### 🛡️ Resiliência e Governança
- **Rate Limiting e Retry Exponencial:** Controle de intervalo com backoff para não sobrecarregar APIs externas.
- **Conciliação de Saídas:** Detecta processos que sumiram da fila e registra a data de saída do analista.
- **Sincronização de Status:** Atualiza fase/status a cada ciclo, mantendo a base sempre consistente.
- **Log Estruturado:** Toda execução gera registro no banco com UUID único, timestamps, contagens e status.

### 📬 Notificações Automáticas
Integração com Power Automate que dispara e-mails HTML ricos com dados do processo (segurado, veículo, corretor, analistas) tanto para confirmações de sucesso quanto para alertas de falha.

---

## 📂 Estrutura de Arquivos

```
.
├── main.py                      # Orquestrador principal do robô
├── portal_seguradora_api.py     # Extração do portal (Rate limit, Retry, Paginação)
├── sinistro_api.py              # Envio para a Plataforma de Gestão + notificações
├── database.py                  # Todas as operações no banco Microsoft Fabric
├── auditoria.py                 # Modo auditoria semanal de baixa automática
├── funcoes_auxiliares.py        # Utilitários (agendamento, formatação, timezone)
├── config.py                    # Carregamento seguro de variáveis via .env
├── http_request.json            # Schema JSON do payload para o Power Automate
├── estrutura_e-mail.html        # Template HTML do e-mail de notificação
├── requirements.txt             # Dependências Python
├── .env.example                 # Template de configuração (sem dados reais)
└── sql/
    ├── 00_drop_tables.sql       # (Opcional) Limpeza de ambiente
    ├── 01_create_tables.sql     # Modelagem completa: RAW, DIM, FATO, VIEWS
    └── 02_insert_initial_data.sql # Dados iniciais e parâmetros de configuração
```

---

## 🗄️ Modelagem de Dados (Microsoft Fabric)

A modelagem segue os princípios de um **Data Warehouse dimensional**:

- **Camada RAW:** Snapshot JSON bruto de cada processo capturado, com histórico *append-only* para auditoria completa.
- **Camada DIM:** Processo, Veículo, Envolvido (Segurado, Corretor, Analista), Contato, Usuário interno.
- **Camada FATO:** Fila de envio (controle de status e retry), SLA, Workflow de eventos, Histórico de responsáveis, Logs de API e Notificação.
- **Camada SEMÂNTICA:** View analítica consolidada (`vw_processos_completo`) que une todas as tabelas e expõe colunas prontas para Power BI.

---

## 🚀 Como Configurar

### Passo 1: Banco de Dados (Microsoft Fabric)

Execute os scripts SQL na seguinte ordem:
```sql
-- 1. (Opcional) Limpa ambiente anterior
00_drop_tables.sql

-- 2. Cria toda a modelagem
01_create_tables.sql

-- 3. Insere dicionários e parâmetros
-- Preencha as URLs e credenciais reais antes de executar
02_insert_initial_data.sql
```

### Passo 2: Ambiente Python

```bash
git clone <este-repositório>
cd rpa-integracao-seguros

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Passo 3: Configuração do `.env`

```bash
cp .env.example .env
# Edite o .env com suas credenciais reais
```

### Passo 4: Execução

```bash
python main.py
```

---

## 🔒 Segurança e LGPD

Este repositório **não contém**:
- Credenciais, senhas ou tokens de nenhuma API
- URLs reais de ambientes de produção
- E-mails ou dados pessoais de colaboradores ou clientes
- Dados reais de sinistros ou segurados

Todas as configurações sensíveis são gerenciadas via variáveis de ambiente (`.env`) e/ou pela tabela de parâmetros no banco (padrão EAV) — garantindo zero hardcode de segredos no código-fonte.
