"""
src/db_sql.py
=============
Banco de dados SQLite para dados ESTRUTURADOS e RELACIONAIS do pipeline RAG.

Responsabilidade por base:
  - producao_estruturada → tabela `artigos`  (título, autores, ano, DOI, citações, financiamento)
  - metricas_agregada    → tabela `metricas` (ranking, citações institucionais, indicadores)
  - pareceres_conversacional → tabela `pareceres` (protocolo, decisão, área, data)
  - editais_normativo    → tabela `editais`  (nome, órgão, ano, tipo, arquivo)

Estas tabelas suportam consultas SQL diretas (filtros por ano, ranking,
financiador, decisão, etc.) complementando a busca semântica do ChromaDB.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "academic_rag.db"
RAW_DIR = BASE_DIR / "data" / "raw" / "v1"


# ---------------------------------------------------------------------------
# Conexão e criação do schema
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão SQLite com row_factory para dict-like access."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Cria todas as tabelas do schema relacional (idempotente)."""
    conn.executescript("""
    -- -----------------------------------------------------------------------
    -- 1. Artigos da produção científica estruturada
    -- -----------------------------------------------------------------------
    CREATE TABLE IF NOT EXISTS artigos (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        work_id       TEXT    UNIQUE,
        titulo        TEXT    NOT NULL,
        ano           INTEGER,
        doi           TEXT,
        revista       TEXT,
        qualis        TEXT,
        citacoes      INTEGER DEFAULT 0,
        tipo_acesso   TEXT,
        financiamento TEXT,           -- JSON array ou string CSV
        agradecimentos TEXT,
        autores       TEXT,           -- JSON array
        instituicoes  TEXT,           -- JSON array
        resumo        TEXT,
        origem        TEXT DEFAULT 'openalex',  -- openalex | sintetico
        base_id       TEXT DEFAULT 'producao_estruturada'
    );

    CREATE INDEX IF NOT EXISTS idx_artigos_ano      ON artigos(ano);
    CREATE INDEX IF NOT EXISTS idx_artigos_citacoes ON artigos(citacoes DESC);
    CREATE INDEX IF NOT EXISTS idx_artigos_doi      ON artigos(doi);

    -- -----------------------------------------------------------------------
    -- 2. Métricas e indicadores bibliométricos agregados
    -- -----------------------------------------------------------------------
    CREATE TABLE IF NOT EXISTS metricas (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo            TEXT NOT NULL,  -- 'top_artigo' | 'resumo_institucional' | 'topico' | 'etica_ia'
        periodo         TEXT,
        instituicao     TEXT,
        rank            INTEGER,
        titulo          TEXT,
        citacoes        INTEGER DEFAULT 0,
        doi             TEXT,
        revista         TEXT,
        financiamento   TEXT,
        autores         TEXT,
        mencao_cep      INTEGER DEFAULT 0,   -- 0=Não, 1=Sim
        protocolo_cep   TEXT,
        dados_extras    TEXT,                -- JSON com campos adicionais
        base_id         TEXT DEFAULT 'metricas_agregada'
    );

    CREATE INDEX IF NOT EXISTS idx_metricas_tipo     ON metricas(tipo);
    CREATE INDEX IF NOT EXISTS idx_metricas_rank     ON metricas(rank);
    CREATE INDEX IF NOT EXISTS idx_metricas_citacoes ON metricas(citacoes DESC);

    -- -----------------------------------------------------------------------
    -- 3. Pareceres de revisão por pares e fomento
    -- -----------------------------------------------------------------------
    CREATE TABLE IF NOT EXISTS pareceres (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        protocolo_id   TEXT UNIQUE,
        titulo_projeto TEXT,
        area           TEXT,
        data_parecer   TEXT,
        rodada         TEXT,
        decisao        TEXT,
        status_anonimato TEXT DEFAULT 'duplo_cego',
        parecer_texto  TEXT,
        origem_arquivo TEXT,
        base_id        TEXT DEFAULT 'pareceres_conversacional'
    );

    CREATE INDEX IF NOT EXISTS idx_pareceres_decisao    ON pareceres(decisao);
    CREATE INDEX IF NOT EXISTS idx_pareceres_protocolo  ON pareceres(protocolo_id);

    -- -----------------------------------------------------------------------
    -- 4. Editais e documentos normativos
    -- -----------------------------------------------------------------------
    CREATE TABLE IF NOT EXISTS editais (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        nome        TEXT NOT NULL,
        orgao       TEXT,
        ano         INTEGER,
        tipo        TEXT,  -- 'edital_fomento' | 'resolucao' | 'normativa'
        numero      TEXT,
        arquivo     TEXT,
        resumo      TEXT,
        base_id     TEXT DEFAULT 'editais_normativo'
    );

    CREATE INDEX IF NOT EXISTS idx_editais_orgao ON editais(orgao);
    CREATE INDEX IF NOT EXISTS idx_editais_ano   ON editais(ano);

    -- -----------------------------------------------------------------------
    -- 5. Beneficiários de fomento (cross-source: edital × produção)
    -- -----------------------------------------------------------------------
    CREATE TABLE IF NOT EXISTS beneficiarios_fomento (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        pesquisador         TEXT NOT NULL,
        instituicao         TEXT,
        edital              TEXT,
        categoria           TEXT,
        valor_concedido     REAL,
        projeto_financiado  TEXT,
        cumprimento_meta    TEXT,
        publicacoes_json    TEXT,  -- JSON com lista de publicações declaradas
        base_id             TEXT DEFAULT 'producao_estruturada'
    );

    CREATE INDEX IF NOT EXISTS idx_beneficiarios_edital ON beneficiarios_fomento(edital);
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Populadores (carregam dados dos arquivos JSON/TXT para o SQLite)
# ---------------------------------------------------------------------------

def _populate_artigos(conn: sqlite3.Connection) -> int:
    """Lê os arquivos OpenAlex da producao_estruturada e popula a tabela artigos."""
    base_dir = RAW_DIR / "producao_estruturada"
    count = 0
    if not base_dir.exists():
        return count

    for file_path in base_dir.glob("*.json"):
        # Ignora arquivo de beneficiários (tratado separado)
        if "beneficiarios" in file_path.name:
            continue
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[SQL] Erro ao ler {file_path.name}: {e}")
            continue

        if isinstance(data, dict) and "results" in data:
            records = data["results"]
        elif isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = [data]
        else:
            records = []

        for item in records:
            if not isinstance(item, dict):
                continue
            work_id = str(item.get("id", "")).split("/")[-1] or None
            title = item.get("title") or "Sem título"
            pub_year = item.get("publication_year")
            cited_by = item.get("cited_by_count", 0)
            doi = item.get("doi", "")
            origem = "sintetico" if "sintetico" in file_path.name else "openalex"

            authors_list = []
            institutions_list = []
            for authorship in item.get("authorships", []):
                if isinstance(authorship, dict):
                    aname = authorship.get("author", {}).get("display_name")
                    if aname:
                        authors_list.append(aname)
                    for inst in authorship.get("institutions", []):
                        if isinstance(inst, dict):
                            iname = inst.get("display_name")
                            if iname and iname not in institutions_list:
                                institutions_list.append(iname)

            grants = []
            for grant in item.get("grants", []):
                if isinstance(grant, dict):
                    fn = grant.get("funder_display_name")
                    if fn and fn not in grants:
                        grants.append(fn)

            if not grants:
                for funder in item.get("funders", []):
                    if isinstance(funder, dict):
                        fn = funder.get("display_name")
                        if fn and fn not in grants:
                            grants.append(fn)

            abstract_idx = item.get("abstract_inverted_index")
            abstract_text = ""
            if abstract_idx and isinstance(abstract_idx, dict):
                word_pos = []
                for word, positions in abstract_idx.items():
                    if isinstance(positions, list):
                        for pos in positions:
                            word_pos.append((pos, word))
                word_pos.sort()
                abstract_text = " ".join(w for _, w in word_pos)[:1000]

            try:
                conn.execute("""
                    INSERT OR IGNORE INTO artigos
                    (work_id, titulo, ano, doi, citacoes, financiamento, autores, instituicoes, resumo, origem)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (
                    work_id, title, pub_year, doi, cited_by,
                    json.dumps(grants, ensure_ascii=False),
                    json.dumps(authors_list[:10], ensure_ascii=False),
                    json.dumps(institutions_list[:5], ensure_ascii=False),
                    abstract_text, origem
                ))
                count += 1
            except Exception as e:
                print(f"[SQL] Erro ao inserir artigo {work_id}: {e}")

    conn.commit()
    return count


def _populate_beneficiarios(conn: sqlite3.Connection) -> int:
    """Popula beneficiários FAPERJ com publicações cruzadas."""
    fpath = RAW_DIR / "producao_estruturada" / "faperj_2022_beneficiarios_publicacoes.json"
    if not fpath.exists():
        return 0
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return 0

    count = 0
    edital = data.get("edital", "FAPERJ 05/2022")
    for pesq in data.get("beneficiarios_com_publicacoes", []):
        if not isinstance(pesq, dict):
            continue
        conn.execute("""
            INSERT OR IGNORE INTO beneficiarios_fomento
            (pesquisador, instituicao, edital, categoria, valor_concedido,
             projeto_financiado, cumprimento_meta, publicacoes_json)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            pesq.get("pesquisador", ""),
            pesq.get("instituicao", ""),
            edital,
            pesq.get("categoria_edital", ""),
            pesq.get("valor_concedido", 0),
            pesq.get("projeto_financiado", ""),
            pesq.get("cumprimento_meta_publicacoes", ""),
            json.dumps(pesq.get("publicacoes_com_financiamento_declarado", []), ensure_ascii=False)
        ))
        count += 1
    conn.commit()
    return count


def _populate_metricas(conn: sqlite3.Connection) -> int:
    """Popula métricas de citação institucional e artigos de ética em IA."""
    base_dir = RAW_DIR / "metricas_agregada"
    count = 0
    if not base_dir.exists():
        return count

    for file_path in base_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        # Citações institucionais (top artigos)
        if isinstance(data, dict) and "top_artigos_citacoes_2023" in data:
            periodo = data.get("periodo_referencia", "2023")
            inst = data.get("instituicao", "")

            # Resumo institucional como uma única linha
            resumo = data.get("resumo_indicadores_institucionais_2023", {})
            conn.execute("""
                INSERT INTO metricas (tipo, periodo, instituicao, dados_extras)
                VALUES ('resumo_institucional',?,?,?)
            """, (periodo, inst, json.dumps(resumo, ensure_ascii=False)))

            for art in data.get("top_artigos_citacoes_2023", []):
                conn.execute("""
                    INSERT INTO metricas
                    (tipo, periodo, instituicao, rank, titulo, citacoes, doi, revista, financiamento, autores)
                    VALUES ('top_artigo',?,?,?,?,?,?,?,?,?)
                """, (
                    periodo, art.get("instituicao_principal", inst),
                    art.get("rank"), art.get("titulo", ""),
                    art.get("citacoes_openalex", 0),
                    art.get("doi", ""), art.get("revista", ""),
                    art.get("financiamento_declarado", ""),
                    json.dumps(art.get("autores", []), ensure_ascii=False)
                ))
                count += 1

        # Artigos de ética em IA com menção CEP
        elif isinstance(data, dict) and "artigos" in data and "total_encontrado" in data:
            periodo = data.get("periodo", "2023")
            stats = data.get("estatisticas_gerais_2023", {})
            conn.execute("""
                INSERT INTO metricas (tipo, periodo, dados_extras)
                VALUES ('estatistica_etica_ia',?,?)
            """, (periodo, json.dumps(stats, ensure_ascii=False)))

            for art in data.get("artigos", []):
                conn.execute("""
                    INSERT INTO metricas
                    (tipo, periodo, titulo, citacoes, doi, revista, financiamento,
                     autores, mencao_cep, protocolo_cep)
                    VALUES ('etica_ia',?,?,?,?,?,?,?,?,?)
                """, (
                    periodo, art.get("titulo", ""),
                    art.get("citacoes", 0), art.get("doi", ""),
                    art.get("revista", ""),
                    json.dumps(art.get("financiamento", []), ensure_ascii=False),
                    json.dumps(art.get("autores", []), ensure_ascii=False),
                    1 if art.get("mencao_aprovacao_cep_no_resumo") else 0,
                    art.get("protocolo_cep", "")
                ))
                count += 1

        # Tópicos genéricos OpenAlex
        elif isinstance(data, dict) and "results" in data:
            for topic in data.get("results", []):
                if not isinstance(topic, dict):
                    continue
                conn.execute("""
                    INSERT INTO metricas (tipo, titulo, citacoes, dados_extras)
                    VALUES ('topico',?,?,?)
                """, (
                    topic.get("display_name", ""),
                    topic.get("cited_by_count", 0),
                    json.dumps({
                        "works_count": topic.get("works_count", 0),
                        "subfield": topic.get("subfield", {}).get("display_name", "") if isinstance(topic.get("subfield"), dict) else "",
                        "field": topic.get("field", {}).get("display_name", "") if isinstance(topic.get("field"), dict) else "",
                    }, ensure_ascii=False)
                ))
                count += 1

    conn.commit()
    return count


def _populate_pareceres(conn: sqlite3.Connection) -> int:
    """Popula pareceres da base conversacional."""
    base_dir = RAW_DIR / "pareceres_conversacional"
    count = 0
    if not base_dir.exists():
        return count

    for file_path in base_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                pareceres = json.load(f)
        except Exception:
            continue

        if not isinstance(pareceres, list):
            pareceres = [pareceres]

        for p in pareceres:
            if not isinstance(p, dict):
                continue
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO pareceres
                    (protocolo_id, titulo_projeto, area, data_parecer, rodada,
                     decisao, status_anonimato, parecer_texto, origem_arquivo)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    p.get("protocolo_id", ""),
                    p.get("titulo_projeto", ""),
                    p.get("area", ""),
                    p.get("data_parecer", ""),
                    p.get("rodada", ""),
                    p.get("decisao", ""),
                    p.get("status_anonimato", "duplo_cego"),
                    p.get("parecer_texto", ""),
                    file_path.name
                ))
                count += 1
            except Exception as e:
                print(f"[SQL] Erro ao inserir parecer: {e}")

    conn.commit()
    return count


def _populate_editais(conn: sqlite3.Connection) -> int:
    """Popula editais/normativos com metadados básicos dos arquivos."""
    base_dir = RAW_DIR / "editais_normativo"
    count = 0
    if not base_dir.exists():
        return count

    metadados = {
        "faperj_edital_05_2022": {
            "nome": "Edital FAPERJ nº 05/2022 – Biotecnologia e Saúde",
            "orgao": "FAPERJ",
            "ano": 2022,
            "tipo": "edital_fomento",
            "numero": "05/2022",
            "resumo": "Chamada pública para projetos de pesquisa em Biotecnologia e Saúde no Estado do Rio de Janeiro."
        },
        "resolucao_cns_510_2016": {
            "nome": "Resolução CNS nº 510/2016",
            "orgao": "CNS/CONEP",
            "ano": 2016,
            "tipo": "resolucao",
            "numero": "510/2016",
            "resumo": "Dispõe sobre normas aplicáveis a pesquisas em Ciências Humanas e Sociais, incluindo regras de dispensa de CEP."
        },
    }

    for file_path in base_dir.glob("*.*"):
        stem = file_path.stem
        meta = metadados.get(stem, {
            "nome": file_path.name,
            "orgao": "FAPERJ" if "faperj" in stem.lower() else "CNS/CONEP" if "cns" in stem.lower() else "Desconhecido",
            "ano": None,
            "tipo": "normativa",
            "numero": "",
            "resumo": ""
        })

        try:
            conn.execute("""
                INSERT OR IGNORE INTO editais (nome, orgao, ano, tipo, numero, arquivo, resumo)
                VALUES (?,?,?,?,?,?,?)
            """, (
                meta["nome"], meta["orgao"], meta.get("ano"), meta["tipo"],
                meta.get("numero", ""), file_path.name, meta.get("resumo", "")
            ))
            count += 1
        except Exception as e:
            print(f"[SQL] Erro ao inserir edital: {e}")

    conn.commit()
    return count


# ---------------------------------------------------------------------------
# API pública: construção e consultas
# ---------------------------------------------------------------------------

def build_sql_db(force: bool = False) -> None:
    """
    Constrói (ou reconstrói) o banco SQLite a partir dos arquivos raw.
    Se force=True, apaga e recria tudo. Caso contrário, é idempotente.
    """
    if force and DB_PATH.exists():
        DB_PATH.unlink()
        print("[SQL] Banco anterior removido para rebuild completo.")

    conn = get_connection()
    create_schema(conn)

    # Verifica se já tem dados
    existing = conn.execute("SELECT COUNT(*) FROM artigos").fetchone()[0]
    if existing > 0 and not force:
        print(f"[SQL] Banco já populado ({existing} artigos). Use force=True para recriar.")
        conn.close()
        return

    print("[SQL] Populando banco de dados SQLite...")
    n_art = _populate_artigos(conn)
    n_ben = _populate_beneficiarios(conn)
    n_met = _populate_metricas(conn)
    n_par = _populate_pareceres(conn)
    n_edi = _populate_editais(conn)

    print(f"[SQL] OK - Banco construido:")
    print(f"       artigos={n_art} | beneficiários={n_ben} | métricas={n_met} | pareceres={n_par} | editais={n_edi}")
    conn.close()


# ---------------------------------------------------------------------------
# Funções de consulta SQL usadas pelo pipeline RAG
# ---------------------------------------------------------------------------

def query_top_artigos_citacoes(ano: Optional[int] = None, limit: int = 5) -> List[Dict]:
    """Retorna os artigos mais citados, opcionalmente filtrando por ano."""
    conn = get_connection()
    sql = "SELECT rank, titulo, autores, instituicao, revista, citacoes, financiamento, doi FROM metricas WHERE tipo='top_artigo'"
    params: list = []
    if ano:
        sql += " AND periodo=?"
        params.append(str(ano))
    sql += " ORDER BY citacoes DESC, rank ASC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def query_artigos_financiamento(financiador: str, ano: Optional[int] = None) -> List[Dict]:
    """Retorna artigos com financiamento declarado por um dado financiador."""
    conn = get_connection()
    sql = "SELECT titulo, autores, ano, doi, citacoes, financiamento FROM artigos WHERE financiamento LIKE ?"
    params: list = [f"%{financiador}%"]
    if ano:
        sql += " AND ano=?"
        params.append(ano)
    sql += " ORDER BY citacoes DESC LIMIT 20"
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def query_artigos_etica_cep(ano: Optional[int] = None) -> List[Dict]:
    """Retorna artigos de ética em IA com menção de aprovação CEP no resumo."""
    conn = get_connection()
    sql = "SELECT titulo, autores, revista, citacoes, doi, protocolo_cep FROM metricas WHERE tipo='etica_ia' AND mencao_cep=1"
    params: list = []
    if ano:
        sql += " AND periodo=?"
        params.append(str(ano))
    sql += " ORDER BY citacoes DESC"
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def query_beneficiarios_fomento(edital: Optional[str] = None) -> List[Dict]:
    """Retorna beneficiários de editais com suas publicações declaradas."""
    conn = get_connection()
    sql = "SELECT pesquisador, instituicao, edital, categoria, valor_concedido, projeto_financiado, cumprimento_meta, publicacoes_json FROM beneficiarios_fomento"
    params: list = []
    if edital:
        sql += " WHERE edital LIKE ?"
        params.append(f"%{edital}%")
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def query_pareceres(decisao: Optional[str] = None, protocolo: Optional[str] = None) -> List[Dict]:
    """Retorna pareceres filtrados por decisão ou protocolo."""
    conn = get_connection()
    conditions = []
    params: list = []
    if decisao:
        conditions.append("decisao LIKE ?")
        params.append(f"%{decisao}%")
    if protocolo:
        conditions.append("protocolo_id LIKE ?")
        params.append(f"%{protocolo}%")

    sql = "SELECT protocolo_id, titulo_projeto, area, data_parecer, decisao, status_anonimato, parecer_texto FROM pareceres"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def query_editais(orgao: Optional[str] = None, ano: Optional[int] = None) -> List[Dict]:
    """Retorna editais/normativos filtrados."""
    conn = get_connection()
    conditions = []
    params: list = []
    if orgao:
        conditions.append("orgao LIKE ?")
        params.append(f"%{orgao}%")
    if ano:
        conditions.append("ano=?")
        params.append(ano)
    sql = "SELECT nome, orgao, ano, tipo, numero, arquivo, resumo FROM editais"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def query_resumo_institucional(periodo: Optional[str] = None) -> Optional[Dict]:
    """Retorna o resumo de indicadores institucionais."""
    conn = get_connection()
    sql = "SELECT dados_extras, periodo, instituicao FROM metricas WHERE tipo='resumo_institucional'"
    params: list = []
    if periodo:
        sql += " AND periodo=?"
        params.append(str(periodo))
    sql += " LIMIT 1"
    row = conn.execute(sql, params).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["dados_extras"] = json.loads(result["dados_extras"] or "{}")
        return result
    return None


def format_sql_context(results: List[Dict], source_label: str) -> str:
    """Converte resultados SQL em texto de contexto para o LLM."""
    if not results:
        return ""
    lines = [f"[Fonte SQL – {source_label}]"]
    for r in results:
        item_lines = []
        for k, v in r.items():
            if v is None or v == "" or v == "[]" or v == "{}":
                continue
            # Desserializa JSON embutido
            if isinstance(v, str) and v.startswith("["):
                try:
                    v = ", ".join(json.loads(v))
                except Exception:
                    pass
            item_lines.append(f"  {k}: {v}")
        if item_lines:
            lines.append("\n".join(item_lines))
            lines.append("---")
    return "\n".join(lines)


if __name__ == "__main__":
    build_sql_db(force=True)
    print("\n[Teste] Top artigos 2023:")
    for r in query_top_artigos_citacoes(ano=2023, limit=3):
        print(f"  #{r['rank']} {r['titulo']} — {r['citacoes']} citações")
    print("\n[Teste] Artigos ética IA com CEP:")
    for r in query_artigos_etica_cep():
        print(f"  {r['titulo']} — protocolo: {r['protocolo_cep']}")
    print("\n[Teste] Beneficiários FAPERJ 2022:")
    for r in query_beneficiarios_fomento("05/2022"):
        print(f"  {r['pesquisador']} ({r['instituicao']}) — {r['cumprimento_meta']}")
