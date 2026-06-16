"""
   CLASSIFICADOR DE EVENTOS DE CRÉDITO & CONTABILIZAÇÃO DE FATOS RELEVANTES
   Mercado Brasileiro de Securitização (CRA / CRI) - VERSÃO 2.0
   Compatível com Python 3.11

   METODOLOGIA:
   - Normalização de texto com dicionário de sinônimos (inclui acentos e plurais).
   - Regras baseadas em palavras obrigatórias e exclusoras.
   - Cobertura aprimorada para rating, assembleias, aditamentos e índices financeiros.

   HISTÓRICO DE VERSÕES:
   - v2.0: Sinônimos expandidos, nova regra para "observação negativa",
           plural "fluxo de pagamentos", regras para assembleias com recompra/waiver.
   - v1.0: Versão inicial com correções de acentos e exclusões refinadas.
"""

import logging
import sys
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import pandas as pd

#  Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


#  CONSTANTES & CONFIGURAÇÕES
BASE_DIR   = Path(__file__).resolve().parent
INPUT_DIR  = BASE_DIR
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EVENTOS_FILE = INPUT_DIR / "EventosCredito.csv"
FATOS_FILE   = INPUT_DIR / "Fatos_Relevantes.csv"

COL_EVENTO_NOME  = "Eventos"
COL_EVENTO_CLASS = "Positivo/Neutro/Negativo"
COL_CETIP    = "CETIP"
COL_CATEG    = "Categoria"
COL_TIPO     = "Tipo"
COL_RESUMO   = "Resumo"
COL_DATA_REF = "DataReferencia"
COL_EVENTO_ID   = "Evento_Identificado"
COL_CLASSIF_OUT = "Classificacao"
COL_PESO_OUT    = "Peso"


#  DICIONÁRIO DE SINÔNIMOS (expandido)
SYNONYM_MAP: Dict[str, str] = {
    # Inadimplência
    "inadimplência": "inadimpl",
    "inadimplente": "inadimpl",
    "inadimplemento": "inadimpl",
    "default": "inadimpl",
    "insolvência": "inadimpl",
    # Recuperação judicial
    "recuperação judicial": "recuperacao judicial",
    "recuperação extrajudicial": "recuperacao extrajudicial",
    "bankruptcy": "recuperacao judicial",
    "falência": "recuperacao judicial",
    # Rating (com acentos removidos)
    "relatório": "relatorio",
    "relatórios": "relatorio",
    "agência": "agencia",
    "agências": "agencia",
    "rating": "rating",
    "classificação de risco": "rating",
    "rebaixamento": "downgrade",
    "rebaixou": "downgrade",
    "elevação": "upgrade",
    "elevou": "upgrade",
    "melhora": "upgrade",
    "perspectiva negativa": "perspectiva negativa",
    "perspectiva positiva": "perspectiva positiva",
    "observação": "observacao",
    "observação negativa": "observacao negativa",
    "creditwatch": "creditwatch",
    # Waiver
    "waiver": "waiver",
    "dispensa": "waiver",
    "anuência": "waiver",
    # Covenants e índices
    "covenant": "covenant",
    "índice financeiro": "covenant",
    "índice de alavancagem": "alavancagem",
    "alavancagem": "alavancagem",
    "cobertura": "cobertura",
    "garantia": "garantia",
    "garantias": "garantia",
    "colateral": "garantia",
    # Garantias adicionais
    "garantia adicional": "garantia adicional",
    "garantias adicionais": "garantia adicional",
    "reforço de garantia": "garantia adicional",
    "reforço de garantias": "garantia adicional",
    # Vencimento antecipado
    "vencimento antecipado": "vencimento antecipado",
    "aceleração da dívida": "vencimento antecipado",
    "cross default": "vencimento antecipado",
    # Resgate e recompra
    "resgate": "resgate",
    "recompra": "recompra",
    "amortização": "amortizacao",
    "obrigatório": "obrigatorio",
    "obrigatória": "obrigatorio",
    "facultativo": "facultativo",
    "prêmio": "premio",
    # Fluxo de pagamento (inclui plural)
    "fluxo de pagamento": "fluxo pagamento",
    "fluxo de pagamentos": "fluxo pagamento",
    "cronograma": "cronograma",
    "repactuação": "repactuacao",
    # Assembleia
    "assembleia": "assembleia",
    "agt": "assembleia",
    "ago": "assembleia",
    "age": "assembleia",
    # Demonstrações financeiras
    "demonstrações financeiras": "demonstracoes",
    "dfs": "demonstracoes",
    "patrimônio separado": "patrimonio separado",
    # Fundo de reserva
    "fundo de reserva": "fundo reserva",
    "fundo de liquidez": "fundo liquidez",
    "recomposição": "recomposicao",
    # Outros
    "prorrogação": "prorrogacao",
    "carência": "carencia",
    "pagamento": "pagamento",
    "juros": "juros",
    "amortização": "amortizacao",
    "cura": "cura",
    "regularização": "regularizacao",
}


#  TABELA MESTRE DE EVENTOS
EVENT_MASTER: Dict[str, Tuple[str, str]] = {
    "Waiver de Não Pagamento de Juros/Amortização": (
        "Negativo",
        "Sinaliza inadimplência efetiva; credor concede tolerância formal. "
        "Equivalente a uma grace-period extension pós-default segundo S&P/Moody's.",
    ),
    "Carência de Pagamento de Juros/Amortização": (
        "Negativo",
        "Concessão de prazo para pagamento indica que o devedor não tem fluxo "
        "de caixa suficiente para honrar obrigações na data original.",
    ),
    "Aditamento com repactuação do fluxo de pagamento": (
        "Negativo",
        "Modificação do cronograma de amortização/juros é tratada como "
        "Distressed Exchange pelas agências quando decorre de incapacidade de pagamento.",
    ),
    "Waiver de Descumprimento de Índices Financeiros": (
        "Negativo",
        "Covenant breach – o devedor violou índices financeiros contratados "
        "(leverage, cobertura de juros etc.). Pré-requisito frequente de rebaixamento.",
    ),
    "Recomposição de Fundo de reserva/Liquidez": (
        "Positivo",
        "Restabelecimento do colchão de liquidez reforça a estrutura da "
        "operação e sinaliza comprometimento do devedor com suas obrigações.",
    ),
    "Descumprimento de Índice de Cobertura": (
        "Negativo",
        "Quebra direta de covenant de cobertura de dívida. Pode acionar "
        "vencimento antecipado se não mitigado por waiver.",
    ),
    "Aprovado declaração de vencimento antecipado": (
        "Negativo",
        "Credores declararam aceleração da dívida – evento de default técnico "
        "severo. Pressiona fortemente o rating.",
    ),
    "Waiver para não declarar vencimento antecipado": (
        "Negativo",
        "Implica que o gatilho de vencimento antecipado foi acionado (evento "
        "negativo subjacente). A abstenção alivia mas não elimina o risco.",
    ),
    "Descumprimento de razão de garantia": (
        "Negativo",
        "LTV ou razão de garantia abaixo do mínimo contratual. Sinaliza "
        "deterioração do colateral relativa ao saldo devedor.",
    ),
    "Pedido de Recuperação Judicial/Extrajudicial": (
        "Negativo",
        "Evento de crédito extremo – equivalente a bankruptcy filing. "
        "Implica default ou iminência de default segundo todas as agências.",
    ),
    "Resgate/Recompra Antecipado Facultativo": (
        "Positivo",
        "Exercício voluntário de call option indica disponibilidade de caixa "
        "e reduz endividamento – ação pró-crédito.",
    ),
    "Resgate/Recompra Antecipado Obrigatório": (
        "Negativo",
        "Recompra compulsória geralmente acionada por eventos adversos "
        "(liquidez excessiva por sinistro, inadimplência do lastro etc.).",
    ),
    "Waiver de entrega de demonstração financeira": (
        "Negativo",
        "Não entrega de demonstrações financeiras viola covenant de "
        "transparência. Pode indicar problemas operacionais ou de governança.",
    ),
    "Prorrogação de vencimento": (
        "Negativo",
        "Extensão de prazo tipicamente decorre de incapacidade de refinanciar "
        "ou pagar o principal; tratada como Distressed Exchange pela Fitch.",
    ),
    "Rebaixamento de Rating de Agência de Risco": (
        "Negativo",
        "Ação formal de downgrade – indicador-chave de deterioração de "
        "crédito. Aumenta custo de capital e pode acionar covenants de rating.",
    ),
    "Melhora de Rating de Agência de Risco": (
        "Positivo",
        "Upgrade formal – reconhecimento de melhora na capacidade de pagamento "
        "e/ou perspectivas mais favoráveis.",
    ),
    "Manutenção de Rating de Agência de Risco": (
        "Neutro",
        "Afirmação de rating sem mudança – não altera a percepção de risco. "
        "Pode sinalizar estabilidade em cenário de revisão.",
    ),
    "Prestação de Garantias Adicionais": (
        "Neutro",
        "Reforço de colateral pode ser pré-acordado ou acionado por triggers. "
        "Protege o credor, mas sinaliza deterioração do LTV original. "
        "Classificado como Neutro por decisão do analista (poderia ser Negativo).",
    ),
    "Aprovação das demonstrações financeiras do patrimônio separado": (
        "Neutro",
        "Evento administrativo/rotineiro. Aprovação das DFs do patrimônio "
        "separado em AGE/AGO sem impacto material no fluxo de pagamentos.",
    ),
}

PESO_MAP: Dict[str, int] = {
    "Positivo": +1,
    "Neutro":    0,
    "Negativo": -1,
}


#  REGRAS DE MAPEAMENTO 
#  Exclusões comuns para aditamentos que NÃO alteram fluxo
EXCLUSAO_SEM_ALTERACAO = [
    "sem alteracoes", "correcao", "erro material",
    "sem modificacoes", "sem impacto", "retificacao"
]

MAPPING_RULES: List[Tuple[List[str], List[str], str]] = [

    #  RECUPERAÇÃO JUDICIAL 
    (["recuperacao judicial"], [], "Pedido de Recuperação Judicial/Extrajudicial"),
    (["recuperacao extrajudicial"], [], "Pedido de Recuperação Judicial/Extrajudicial"),

    #  RATING – REBAIXAMENTO 
    (["downgrade", "rating"], [], "Rebaixamento de Rating de Agência de Risco"),
    (["rebaixamento", "rating"], [], "Rebaixamento de Rating de Agência de Risco"),
    (["observacao negativa", "rating"], [], "Rebaixamento de Rating de Agência de Risco"),
    (["creditwatch negative"], [], "Rebaixamento de Rating de Agência de Risco"),
    (["perspectiva negativa", "rating"], [], "Rebaixamento de Rating de Agência de Risco"),

    #  RATING – MELHORA 
    (["upgrade", "rating"], [], "Melhora de Rating de Agência de Risco"),
    (["perspectiva positiva", "rating"], [], "Melhora de Rating de Agência de Risco"),

    #  RATING – MANUTENÇÃO 
    (["relatorio de agencia de rating", "mantem"], [], "Manutenção de Rating de Agência de Risco"),
    (["relatorio de agencia de rating", "manteve"], [], "Manutenção de Rating de Agência de Risco"),
    (["relatorio de agencia de rating", "afirma"], [], "Manutenção de Rating de Agência de Risco"),
    (["relatorio de agencia de rating", "reafirma"], [], "Manutenção de Rating de Agência de Risco"),
    # Fallback: qualquer relatório de rating sem downgrade/upgrade
    (["relatorio de agencia de rating"],
     ["downgrade", "rebaixamento", "upgrade", "observacao negativa",
      "perspectiva negativa", "perspectiva positiva"],
     "Manutenção de Rating de Agência de Risco"),

    #  VENCIMENTO ANTECIPADO – DECLARADO 
    (["vencimento antecipado automatico"], [], "Aprovado declaração de vencimento antecipado"),
    (["declarando vencimento antecipado"], [], "Aprovado declaração de vencimento antecipado"),
    (["vencimento antecipado", "aprovada"], [], "Aprovado declaração de vencimento antecipado"),
    (["cross default", "vencimento antecipado"], [], "Aprovado declaração de vencimento antecipado"),

    #  VENCIMENTO ANTECIPADO – WAIVER PARA NÃO DECLARAR 
    (["nao declarar vencimento antecipado"], [], "Waiver para não declarar vencimento antecipado"),
    (["suspensao", "deliberacao", "vencimento antecipado"], [], "Waiver para não declarar vencimento antecipado"),
    (["nao declaracao", "vencimento antecipado"], [], "Waiver para não declarar vencimento antecipado"),
    (["assembleia", "vencimento antecipado"],
     ["automatico", "declarando", "aprovada"], "Waiver para não declarar vencimento antecipado"),

    #  INADIMPLÊNCIA / NÃO PAGAMENTO 
    (["inadimpl"], [], "Waiver de Não Pagamento de Juros/Amortização"),
    (["nao repassou", "patrimonio separado"], [], "Waiver de Não Pagamento de Juros/Amortização"),
    (["irregularidade", "gestao de recursos"], [], "Waiver de Não Pagamento de Juros/Amortização"),
    (["impossibilitando o pagamento"], [], "Waiver de Não Pagamento de Juros/Amortização"),
    (["nao pagou", "parcela"], [], "Waiver de Não Pagamento de Juros/Amortização"),
    (["nao pagamento", "parcela"], [], "Waiver de Não Pagamento de Juros/Amortização"),
    (["nao havera pagamento"], [], "Waiver de Não Pagamento de Juros/Amortização"),
    (["insuficiencia de recursos", "pagamento"], [], "Waiver de Não Pagamento de Juros/Amortização"),

    #  RESGATE OBRIGATÓRIO 
    (["resgate antecipado obrigatorio"], [], "Resgate/Recompra Antecipado Obrigatório"),
    (["recompra obrigatoria"], [], "Resgate/Recompra Antecipado Obrigatório"),

    #  RESGATE FACULTATIVO 
    (["resgate antecipado facultativo"], [], "Resgate/Recompra Antecipado Facultativo"),
    (["recompra facultativa"], [], "Resgate/Recompra Antecipado Facultativo"),
    (["amortizacao antecipada facultativa"], [], "Resgate/Recompra Antecipado Facultativo"),
    (["pagamento antecipado facultativo"], [], "Resgate/Recompra Antecipado Facultativo"),

    #  CARÊNCIA 
    (["carencia", "pagamento"], [], "Carência de Pagamento de Juros/Amortização"),
    (["carencia de", "meses"], [], "Carência de Pagamento de Juros/Amortização"),

    #  PRORROGAÇÃO 
    (["prorrogacao", "vencimento"], [], "Prorrogação de vencimento"),
    (["nova data de vencimento"],
     ["carencia"], "Prorrogação de vencimento"),

    #  ADITAMENTO COM REPACTUAÇÃO (exclusões refinadas) 
    (["aditamento", "repactuacao"], EXCLUSAO_SEM_ALTERACAO,
     "Aditamento com repactuação do fluxo de pagamento"),
    (["aditamento", "cronograma", "pagamento"], EXCLUSAO_SEM_ALTERACAO,
     "Aditamento com repactuação do fluxo de pagamento"),
    # Novo: captura plural "fluxo de pagamentos"
    (["aditamento", "fluxo pagamento"], EXCLUSAO_SEM_ALTERACAO,
     "Aditamento com repactuação do fluxo de pagamento"),
    (["aditamento", "cronograma de amortizacao"], EXCLUSAO_SEM_ALTERACAO,
     "Aditamento com repactuação do fluxo de pagamento"),

    #  RECOMPOSIÇÃO DE FUNDO 
    (["recomposicao", "fundo reserva"], [], "Recomposição de Fundo de reserva/Liquidez"),
    (["recomposicao", "fundo liquidez"], [], "Recomposição de Fundo de reserva/Liquidez"),
    (["constituicao", "fundo reserva"], [], "Recomposição de Fundo de reserva/Liquidez"),

    #  DESCUMPRIMENTO DE GARANTIA 
    (["razao de garantia"], [], "Descumprimento de razão de garantia"),
    (["descumprimento", "garantia"], [], "Descumprimento de razão de garantia"),
    (["garantias nao constituidas"], [], "Descumprimento de razão de garantia"),
    (["nao constituicao", "garantia"], [], "Descumprimento de razão de garantia"),
    (["pendencia", "garantia"], [], "Descumprimento de razão de garantia"),

    #  DESCUMPRIMENTO DE ÍNDICE DE COBERTURA 
    (["descumprimento", "indice"], [], "Descumprimento de Índice de Cobertura"),
    (["descumprimento", "cobertura"], [], "Descumprimento de Índice de Cobertura"),
    (["desenquadramento", "fundo"], [], "Descumprimento de Índice de Cobertura"),

    #  WAIVER DE ÍNDICES FINANCEIROS 
    (["waiver", "indice"], [], "Waiver de Descumprimento de Índices Financeiros"),
    (["waiver", "covenant"], [], "Waiver de Descumprimento de Índices Financeiros"),
    (["covenant", "descumprimento"], [], "Waiver de Descumprimento de Índices Financeiros"),

    #  WAIVER DE ENTREGA DE DEMONSTRAÇÕES 
    (["waiver", "demonstracoes"], [], "Waiver de entrega de demonstração financeira"),
    (["nao entrega", "demonstracoes"], [], "Waiver de entrega de demonstração financeira"),

    #  PRESTAÇÃO DE GARANTIAS ADICIONAIS 
    (["garantia adicional"], [], "Prestação de Garantias Adicionais"),
    (["cessao fiduciaria", "recebiveis", "inclusao"], [], "Prestação de Garantias Adicionais"),
    (["reforço de garantia"], [], "Prestação de Garantias Adicionais"),

    #  ASSEMBLEIAS – NOVAS REGRAS 
    # Recompra facultativa decidida em assembleia
    (["assembleia", "recompra facultativa"], [], "Resgate/Recompra Antecipado Facultativo"),
    # Waiver de prêmio de resgate (neutro, pois não impacta fluxo)
    (["assembleia", "waiver de premio"], [], "Aprovação das demonstrações financeiras do patrimônio separado"),

    #  APROVAÇÃO DAS DEMONSTRAÇÕES DO PATRIMÔNIO SEPARADO 
    (["aprovacao", "demonstracoes", "patrimonio separado"], [],
     "Aprovação das demonstrações financeiras do patrimônio separado"),
    (["aprovacao automatica", "demonstracoes"], [],
     "Aprovação das demonstrações financeiras do patrimônio separado"),
    (["aprovadas as demonstracoes financeiras"], [],
     "Aprovação das demonstrações financeiras do patrimônio separado"),
    (["assembleia", "demonstracoes"],
     ["vencimento antecipado", "inadimpl", "recuperacao"],
     "Aprovação das demonstrações financeiras do patrimônio separado"),
    (["adimplente com suficiencia de lastro", "sem pendencias"], [],
     "Aprovação das demonstrações financeiras do patrimônio separado"),
    (["emissao adimplente"],
     ["pendencia", "nao constituidas"],
     "Aprovação das demonstrações financeiras do patrimônio separado"),
]


#  FUNÇÕES AUXILIARES (mantidas, com pequena otimização)
def normalize_text(text: object, use_synonyms: bool = True) -> str:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    s = str(text).strip().lower()
    s = re.sub(r"\s+", " ", s)
    if use_synonyms:
        # Substitui palavras inteiras (usando boundaries)
        for term, syn in sorted(SYNONYM_MAP.items(), key=lambda x: -len(x[0])):
            s = re.sub(rf"\b{re.escape(term)}\b", syn, s)
    return s


def load_and_validate_csv(path: Path, required_cols: List[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    logger.info(f"Carregando '{path.name}' …")
    df = pd.read_csv(path, dtype=str, encoding="utf-8")
    df.columns = df.columns.str.strip()
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes em '{path.name}': {missing}")
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()
        df[col] = df[col].replace("", pd.NA)
    n_before = len(df)
    df = df.drop_duplicates()
    n_removed = n_before - len(df)
    if n_removed:
        logger.warning(f"  → {n_removed} linha(s) duplicada(s) removida(s)")
    logger.info(f"  → {len(df)} linhas carregadas")
    return df


def build_eventos_table(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    classificacoes, pesos, justificativas = [], [], []
    for _, row in df.iterrows():
        evento = str(row[COL_EVENTO_NOME]).strip() if pd.notna(row[COL_EVENTO_NOME]) else ""
        if pd.notna(row.get(COL_EVENTO_CLASS)) and str(row[COL_EVENTO_CLASS]).strip() in PESO_MAP:
            cl = str(row[COL_EVENTO_CLASS]).strip()
            just = "Classificação fornecida no arquivo de entrada."
        elif evento in EVENT_MASTER:
            cl, just = EVENT_MASTER[evento]
        else:
            cl, just = "Neutro", "Evento não reconhecido; classificado como Neutro por padrão."
            logger.warning(f"  Evento não mapeado: '{evento}'")
        classificacoes.append(cl)
        pesos.append(PESO_MAP.get(cl, 0))
        justificativas.append(just)
    df["Classificacao"] = classificacoes
    df["Peso"] = pesos
    df["Justificativa"] = justificativas
    return df[[COL_EVENTO_NOME, "Classificacao", "Peso", "Justificativa"]]


def match_event(resumo: object, categoria: object, tipo: object) -> Optional[str]:
    text = (
        normalize_text(resumo, use_synonyms=True) + " " +
        normalize_text(categoria, use_synonyms=True) + " " +
        normalize_text(tipo, use_synonyms=True)
    )
    for required_kws, exclusion_kws, event_name in MAPPING_RULES:
        all_present = all(kw in text for kw in required_kws)
        none_present = not any(kw in text for kw in exclusion_kws)
        if all_present and none_present:
            return event_name
    return None


def classify_fatos(df_fatos: pd.DataFrame, eventos_map: Dict[str, Tuple[str, int]]) -> pd.DataFrame:
    df = df_fatos.copy()
    ev_ids, cls_out, wgt_out = [], [], []
    nao_id = 0
    for _, row in df.iterrows():
        evento = match_event(
            row.get(COL_RESUMO),
            row.get(COL_CATEG),
            row.get(COL_TIPO)
        )
        if evento and evento in eventos_map:
            cl, peso = eventos_map[evento]
        else:
            evento = "Não Identificado"
            cl, peso = "Neutro", 0
            nao_id += 1
        ev_ids.append(evento)
        cls_out.append(cl)
        wgt_out.append(peso)
    df[COL_EVENTO_ID] = ev_ids
    df[COL_CLASSIF_OUT] = cls_out
    df[COL_PESO_OUT] = wgt_out
    logger.info(f"  → Fatos classificados: {len(df)-nao_id} identificados / {nao_id} não identificados")
    return df


def compute_metrics(df: pd.DataFrame) -> dict:
    total = len(df)
    pos = int((df[COL_CLASSIF_OUT] == "Positivo").sum())
    neu = int((df[COL_CLASSIF_OUT] == "Neutro").sum())
    neg = int((df[COL_CLASSIF_OUT] == "Negativo").sum())
    n_id = int((df[COL_EVENTO_ID] == "Não Identificado").sum())
    soma = int(df[COL_PESO_OUT].sum())
    df_id = df[df[COL_EVENTO_ID] != "Não Identificado"]
    ranking = (df_id.groupby([COL_EVENTO_ID, COL_CLASSIF_OUT]).size()
               .reset_index(name="Ocorrencias")
               .sort_values("Ocorrencias", ascending=False)
               .reset_index(drop=True))
    ranking.index += 1
    top_neg = (df_id[df_id[COL_CLASSIF_OUT] == "Negativo"]
               .groupby(COL_EVENTO_ID).size().nlargest(10)
               .reset_index(name="Ocorrencias").reset_index(drop=True))
    top_neg.index += 1
    top_pos = (df_id[df_id[COL_CLASSIF_OUT] == "Positivo"]
               .groupby(COL_EVENTO_ID).size().nlargest(10)
               .reset_index(name="Ocorrencias").reset_index(drop=True))
    top_pos.index += 1
    return {
        "total": total, "positivos": pos, "neutros": neu, "negativos": neg,
        "nao_id": n_id, "pct_pos": round(pos/total*100,2) if total else 0,
        "pct_neu": round(neu/total*100,2) if total else 0,
        "pct_neg": round(neg/total*100,2) if total else 0,
        "soma_pesos": soma, "ranking": ranking, "top_neg": top_neg, "top_pos": top_pos,
    }


def generate_consolidated_table(df: pd.DataFrame) -> pd.DataFrame:
    df_id = df[df[COL_EVENTO_ID] != "Não Identificado"]
    consolidated = (df_id.groupby([COL_EVENTO_ID, COL_CLASSIF_OUT, COL_PESO_OUT])
                    .agg(Ocorrencias=(COL_PESO_OUT, "count"), Soma_Pesos=(COL_PESO_OUT, "sum"))
                    .reset_index()
                    .rename(columns={COL_EVENTO_ID:"Evento", COL_CLASSIF_OUT:"Classificacao", COL_PESO_OUT:"Peso_Unitario"})
                    .sort_values(["Classificacao", "Ocorrencias"], ascending=[True, False])
                    .reset_index(drop=True))
    return consolidated


def print_section(title: str, width: int = 78):
    print(f"\n{'─'*width}\n  {title}\n{'─'*width}")


def print_metrics(metrics: dict):
    print_section("RESUMO GERAL")
    print(f"  Total de fatos relevantes  : {metrics['total']:>6}")
    print(f"  ├─ Positivos               : {metrics['positivos']:>6}  ({metrics['pct_pos']:>6.2f}%)")
    print(f"  ├─ Neutros                 : {metrics['neutros']:>6}  ({metrics['pct_neu']:>6.2f}%)")
    print(f"  ├─ Negativos               : {metrics['negativos']:>6}  ({metrics['pct_neg']:>6.2f}%)")
    print(f"  └─ Não Identificados       : {metrics['nao_id']:>6}")
    print(f"\n  Soma de Pesos (score total): {metrics['soma_pesos']:>+6}")
    print_section("RANKING GERAL")
    print(f"  {'Rank':<5} {'Evento':<55} {'Classif.':<12} {'Ocorr.':>7}")
    for rank, row in metrics["ranking"].iterrows():
        print(f"  {rank:<5} {row[COL_EVENTO_ID][:54]:<55} {row[COL_CLASSIF_OUT]:<12} {row['Ocorrencias']:>7}")
    print_section("TOP 10 NEGATIVOS")
    for rank, row in metrics["top_neg"].iterrows():
        print(f"  {rank:<5} {row[COL_EVENTO_ID][:61]:<62} {row['Ocorrencias']:>7}")
    print_section("TOP 10 POSITIVOS")
    for rank, row in metrics["top_pos"].iterrows():
        print(f"  {rank:<5} {row[COL_EVENTO_ID][:61]:<62} {row['Ocorrencias']:>7}")


def save_outputs(df_eventos, df_fatos_class, df_consolidated, metrics):
    out_eventos = OUTPUT_DIR / "EventosCredito_Classificados.csv"
    df_eventos.to_csv(out_eventos, index=False, encoding="utf-8-sig")
    cols_export = [c for c in [COL_CETIP, COL_CATEG, COL_TIPO, "Especie", COL_DATA_REF, "Status",
                               COL_EVENTO_ID, COL_CLASSIF_OUT, COL_PESO_OUT, COL_RESUMO] if c in df_fatos_class.columns]
    out_fatos = OUTPUT_DIR / "FatosRelevantes_Classificados.csv"
    df_fatos_class[cols_export].to_csv(out_fatos, index=False, encoding="utf-8-sig")
    out_consol = OUTPUT_DIR / "Consolidado.csv"
    df_consolidated.to_csv(out_consol, index=False, encoding="utf-8-sig")
    ranking_frames = {"Ranking_Geral": metrics["ranking"], "Top10_Negativos": metrics["top_neg"], "Top10_Positivos": metrics["top_pos"]}
    out_rank = OUTPUT_DIR / "TopEventos.csv"
    with open(out_rank, "w", encoding="utf-8-sig") as fh:
        for label, df_r in ranking_frames.items():
            fh.write(f"# {label}\n")
            df_r.to_csv(fh, index=True, index_label="Rank")
            fh.write("\n")
    kpis = {"Total_Fatos": metrics["total"], "Positivos": metrics["positivos"], "Neutros": metrics["neutros"],
            "Negativos": metrics["negativos"], "Nao_Identificados": metrics["nao_id"],
            "Perc_Positivos": metrics["pct_pos"], "Perc_Neutros": metrics["pct_neu"],
            "Perc_Negativos": metrics["pct_neg"], "Soma_Pesos_Total": metrics["soma_pesos"]}
    out_kpi = OUTPUT_DIR / "Metricas.csv"
    pd.DataFrame(kpis.items(), columns=["KPI", "Valor"]).to_csv(out_kpi, index=False, encoding="utf-8-sig")
    logger.info(f"Arquivos salvos em {OUTPUT_DIR}")


def run_pipeline():
    logger.info("═"*60 + "\n  PIPELINE DE EVENTOS DE CRÉDITO – V2.0 (REFINADO)\n" + "═"*60)
    df_eventos_raw = load_and_validate_csv(EVENTOS_FILE, [COL_EVENTO_NOME])
    df_fatos_raw = load_and_validate_csv(FATOS_FILE, [COL_CATEG, COL_RESUMO])
    df_eventos = build_eventos_table(df_eventos_raw)
    eventos_map = {row[COL_EVENTO_NOME]: (row["Classificacao"], int(row["Peso"])) for _, row in df_eventos.iterrows()}
    df_fatos = classify_fatos(df_fatos_raw, eventos_map)
    metrics = compute_metrics(df_fatos)
    df_consolidated = generate_consolidated_table(df_fatos)
    print_metrics(metrics)
    print_section("TABELA CONSOLIDADA")
    print(df_consolidated.to_string(index=False))
    save_outputs(df_eventos, df_fatos, df_consolidated, metrics)
    logger.info("═"*60 + "\n  PIPELINE CONCLUÍDO COM SUCESSO\n" + "═"*60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logger.exception(f"Erro: {e}")
        sys.exit(1)
