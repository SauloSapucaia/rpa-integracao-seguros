
import pandas as pd
import pytz
from datetime import datetime, timedelta
from datetime import time as dt_time

# Configuração de Fuso Horário para evitar erro UTC no Microsoft Fabric
FUSO_BR = pytz.timezone('America/Sao_Paulo')

def obter_agora_br():
    """Retorna o datetime atual no fuso horário de Brasília."""
    return datetime.now(FUSO_BR).replace(tzinfo=None)

def consertar_uf_linha(linha, mapa_ddd_banco):
    """
    Cruza o DDD da linha com o dicionário vindo da tb_dic_ddd_uf.
    Substitui o antigo mapa fixo do código.
    """
    uf_atual = str(linha.get("dsUF", "SP")).strip().upper()
    ddd_val = linha.get("ddd")
    
    # Tratamento de Nulos
    if uf_atual in ["NAN", "NONE", "<NA>", "NAT", ""]:
        uf_atual = "SP"

    if pd.isna(ddd_val) or str(ddd_val).strip() in ["", "nan", "None"]:
        return uf_atual
        
    try:
        # Converte DDD para inteiro para bater com a chave do dicionário do banco
        ddd_int = int(str(ddd_val).replace(".0", "").strip())
        if ddd_int in mapa_ddd_banco:
            return mapa_ddd_banco[ddd_int]
    except (ValueError, TypeError):
        pass 
        
    return uf_atual

def tratar_valor_fipe(valor):
    """Converte valores monetários/texto para float puro para o banco."""
    try:
        if pd.isna(valor): return None
        if isinstance(valor, (int, float)): return float(valor)
        
        txt = str(valor).strip().upper()
        if txt in ["", "NAN", "NONE", "<NA>"]: return None
        
        # Limpeza de formatação brasileira (R$ 1.200,50 -> 1200.50)
        if "," in txt:
            txt = txt.replace(".", "").replace(",", ".")
            
        return float(txt)
    except Exception:
        return None

def calcular_data_agendamento(dt_real, ultimo_horario_usado):
    """
    Implementação rigorosa da FILA INDIANA (SLA):
    1. Apenas dias úteis.
    2. Horário: 08:15 às 18:00.
    3. Incremento de 5 min entre processos.
    4. Pós-18h vai para o dia seguinte às 08:15.
    5. Trava de segurança: Nunca menor que a data real do Portal.
    """
    # Se a data real vier nula, usamos o agora (Brasil)
    if pd.isna(dt_real) or not isinstance(dt_real, datetime):
        dt_base = obter_agora_br()
    else:
        dt_base = dt_real

    # --- REGRA 1: Fim de Semana ---
    # 5 = Sábado, 6 = Domingo
    if dt_base.weekday() == 5:
        dt_base = (dt_base + timedelta(days=2)).replace(hour=8, minute=15, second=0, microsecond=0)
    elif dt_base.weekday() == 6:
        dt_base = (dt_base + timedelta(days=1)).replace(hour=8, minute=15, second=0, microsecond=0)

    # --- REGRA 2: Horário Comercial ---
    if dt_base.time() < dt_time(8, 15):
        dt_base = dt_base.replace(hour=8, minute=15, second=0, microsecond=0)
    elif dt_base.time() >= dt_time(18, 0):
        # Regra 4: Pós-18h joga para o próximo dia útil
        dt_base += timedelta(days=1)
        # Re-valida se o próximo dia não caiu no sábado
        if dt_base.weekday() == 5: dt_base += timedelta(days=2)
        dt_base = dt_base.replace(hour=8, minute=15, second=0, microsecond=0)

    # --- REGRA 3: Fila Indiana (+5 minutos) ---
    if ultimo_horario_usado and dt_base <= ultimo_horario_usado:
        dt_soma = ultimo_horario_usado + timedelta(minutes=5)
        
        # Trava: Não deixa o incremento de 5min estourar as 18h do dia atual
        if dt_soma.time() >= dt_time(18, 0) and dt_soma.date() == dt_base.date():
            dt_final = dt_base # Mantém o horário limite ou real
        else:
            dt_final = dt_soma
    else:
        dt_final = dt_base

    # --- REGRA 5: Trava de Segurança Absoluta ---
    # Nunca agendar para um horário anterior ao recebimento oficial
    if dt_final < dt_real:
        dt_final = dt_real

    return dt_final