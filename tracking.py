"""
tracking.py — Sistema de Rastreamento Completo StarCheck (CORBANs)
================================================================
Registra todo uso da plataforma no Supabase.

PRINCÍPIO: todas as funções são não-bloqueantes.
Se o tracking falhar, a plataforma continua funcionando normalmente.
Erros são logados no console e nunca propagados para o usuário.

COBERTURA:
  ✅ Logins e logouts
  ✅ Upload de holerites (Supabase Storage)
  ✅ Análises individuais (evento + resultado resumido)
  ✅ Análises em lote (sessão agregada + itens individuais)
  ✅ Geração de estratégia Stella
  ✅ Chat com Stella (individual e lote)
  ✅ Exports (Excel / CSV / PDF)
"""

import streamlit as st
from datetime import datetime, timezone
import json
import time
from typing import Optional, Dict, Any

# ============================================================================
# HELPERS INTERNOS
# ============================================================================

def _get_sb():
    """Retorna o cliente Supabase cacheado (mesmo objeto do auth.py)."""
    from auth import get_supabase_client
    return get_supabase_client()


def _uid() -> Optional[str]:
    """Retorna o user_id UUID do usuário logado, ou None."""
    try:
        return st.session_state.usuario.get("id")
    except Exception:
        return None


def _user_meta() -> Dict:
    """Retorna metadados básicos do usuário logado para inserção."""
    try:
        u = st.session_state.usuario
        return {
            "user_id": u.get("id"),
            "email":   u.get("email", ""),
            "nome":    u.get("nome", ""),
            "setor":   u.get("setor", ""),
        }
    except Exception:
        return {}


def _now() -> str:
    """Retorna timestamp UTC no formato ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def _safe_float(v) -> float:
    try:
        return float(v or 0)
    except Exception:
        return 0.0


# ============================================================================
# 1. SESSÕES — LOGIN / LOGOUT
# ============================================================================

def track_login(user_data: dict):
    """
    Registra evento de login.
    Chamado em auth.py → fazer_login(), após autenticação bem-sucedida.

    Parâmetros:
        user_data: dict com id, email, nome, setor retornado por fazer_login()
    """
    try:
        _get_sb().table("track_sessoes").insert({
            "user_id":    user_data.get("id"),
            "email":      user_data.get("email", ""),
            "nome":       user_data.get("nome", ""),
            "setor":      user_data.get("setor", ""),
            "evento":     "login",
            "created_at": _now(),
        }).execute()
    except Exception as e:
        print(f"[tracking] track_login: {e}")


def track_logout():
    """
    Registra evento de logout.
    Chamado em auth.py → fazer_logout(), antes de limpar a sessão.
    """
    try:
        meta = _user_meta()
        if not meta.get("user_id"):
            return
        _get_sb().table("track_sessoes").insert({
            **meta,
            "evento":     "logout",
            "created_at": _now(),
        }).execute()
    except Exception as e:
        print(f"[tracking] track_logout: {e}")


# ============================================================================
# 2. STORAGE — UPLOAD DE HOLERITES
# ============================================================================

def upload_holerite(
    file_bytes: bytes,
    filename: str,
    user_id: str,
    prefeitura: str = "",
    nome_servidor: str = "",
) -> Optional[str]:
    """
    Faz upload do holerite para o Supabase Storage (bucket 'holerites').
    Organização: {user_id}/{YYYY-MM}/{timestamp}_{filename}

    Retorna o storage_path em caso de sucesso, ou None em caso de erro.
    Chamado em main.py antes de track_analise_individual() e _track_lote_itens().
    """
    try:
        now = datetime.now(timezone.utc)
        ts  = int(time.time())
        # Sanitiza o filename — remove espaços e barras
        safe = filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
        path = f"{user_id}/{now.strftime('%Y-%m')}/{ts}_{safe}"

        ext_map = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp",
            "bmp":  "image/bmp",
            "tiff": "image/tiff", "tif": "image/tiff",
        }
        ext  = filename.lower().rsplit(".", 1)[-1]
        ctype = ext_map.get(ext, "application/octet-stream")

        _get_sb().storage.from_("holerites").upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": ctype, "upsert": "false"},
        )
        return path
    except Exception as e:
        print(f"[tracking] upload_holerite '{filename}': {e}")
        return None


def track_holerite_salvo(
    user_id: str,
    arquivo_original: str,
    storage_path: Optional[str],
    tamanho_bytes: int,
    tipo_mime: str,
    prefeitura: str = "",
    nome_servidor: str = "",
    analise_id: Optional[str] = None,
):
    """
    Registra os metadados do holerite salvo na tabela track_holerites.
    Chamado logo após upload_holerite().
    """
    try:
        _get_sb().table("track_holerites").insert({
            "user_id":          user_id,
            "analise_id":       analise_id,
            "arquivo_original": arquivo_original,
            "storage_path":     storage_path,
            "storage_bucket":   "holerites",
            "tamanho_bytes":    tamanho_bytes,
            "tipo_mime":        tipo_mime,
            "prefeitura":       prefeitura,
            "nome_servidor":    nome_servidor,
            "created_at":       _now(),
        }).execute()
    except Exception as e:
        print(f"[tracking] track_holerite_salvo: {e}")


# ============================================================================
# 3. ANÁLISE INDIVIDUAL
# ============================================================================

def track_analise_individual(
    dados: dict,
    margem: dict,
    arquivo_nome: str,
    arquivo_bytes: int,
    storage_path: Optional[str] = None,
    duracao_ms: int = 0,
) -> Optional[str]:
    """
    Registra uma análise individual de holerite com resultado resumido.
    Retorna o UUID do registro criado — salve em st.session_state["analise_id_atual"]
    para linkar a estratégia Stella e o chat.

    Chamado em main.py → bloco "Análise Individual", após analisar_arquivo() e
    calcular_margem_ia() com sucesso.
    """
    uid = _uid()
    if not uid:
        return None
    try:
        marg_ok = margem.get("disponivel", False)
        emp = margem.get("emprestimo", {})         if marg_ok else {}
        cc  = margem.get("cartao_consignado", {})  if marg_ok else {}
        cb  = margem.get("cartao_beneficio", {})   if marg_ok else {}

        cartoes      = dados.get("cartoes", [])      or []
        emprestimos  = dados.get("emprestimos", [])  or []
        concorrentes = [c for c in cartoes if c.get("tipo") == "concorrente"]
        nossos       = [c for c in cartoes if c.get("tipo") == "nosso"]
        nao_comp     = [c for c in cartoes if c.get("tipo") == "nao_comprado"]

        # Oportunidade — mesma lógica do processar_lote
        emp_disp = _safe_float(emp.get("disponivel", 0))
        if concorrentes and emp_disp > 50:
            oportunidade = "🔥 Compra Dívida + Empréstimo"
        elif concorrentes:
            oportunidade = "💳 Compra de Dívida"
        elif emp_disp > 200:
            oportunidade = "💵 Empréstimo Disponível"
        elif emp_disp > 0:
            oportunidade = "💵 Margem Disponível"
        elif not marg_ok:
            oportunidade = "❓ Prefeitura Não Mapeada"
        else:
            oportunidade = "⛔ Margem Lotada"

        row = {
            "user_id":                uid,
            "arquivo_nome":           arquivo_nome,
            "arquivo_bytes":          arquivo_bytes,
            "storage_path":           storage_path,
            "prefeitura":             dados.get("prefeitura", ""),
            "prefeitura_key":         margem.get("prefeitura_key", ""),
            "nome_servidor":          dados.get("nome", ""),
            "matricula":              dados.get("matricula", ""),
            "regime":                 dados.get("regime", ""),
            "liquido":                _safe_float(dados.get("liquido")),
            "vencimentos_total":      _safe_float(dados.get("vencimentos_total")),
            "salario_base":           _safe_float(dados.get("salario_base")),
            "base_calculo":           _safe_float(margem.get("base_calculo")),
            "margem_emp_total":       _safe_float(emp.get("margem_total")),
            "margem_emp_disponivel":  emp_disp,
            "margem_emp_comprometido":_safe_float(emp.get("comprometido")),
            "margem_cc_total":        _safe_float(cc.get("margem_total")),
            "margem_cc_disponivel":   _safe_float(cc.get("disponivel")),
            "margem_cb_total":        _safe_float(cb.get("margem_total")),
            "margem_cb_disponivel":   _safe_float(cb.get("disponivel")),
            "oportunidade":           oportunidade,
            "qt_concorrentes":        len(concorrentes),
            "qt_nossos":              len(nossos),
            "qt_nao_comp":            len(nao_comp),
            "total_concorrentes":     _safe_float(sum(abs(c.get("valor", 0)) for c in concorrentes)),
            "total_emprestimos":      _safe_float(sum(abs(e.get("valor", 0)) for e in emprestimos)),
            "total_cartoes":          _safe_float(sum(abs(c.get("valor", 0)) for c in cartoes)),
            "margem_disponivel_ok":   marg_ok,
            "duracao_ms":             duracao_ms,
            "created_at":             _now(),
        }

        resp = _get_sb().table("track_analises_individuais").insert(row).execute()
        if resp.data:
            return resp.data[0].get("id")
    except Exception as e:
        print(f"[tracking] track_analise_individual: {e}")
    return None


# ============================================================================
# 4. ANÁLISE EM LOTE
# ============================================================================

def track_lote_sessao(resultados: list, duracao_ms: int = 0) -> Optional[str]:
    """
    Registra a sessão de lote (nível agregado) e todos os itens individuais.
    Retorna o UUID da sessão criada.

    Chamado em main.py → bloco "Análise em Lote", após processar_lote() retornar.
    """
    uid = _uid()
    if not uid or not resultados:
        return None
    try:
        from collections import Counter
        opps  = dict(Counter(r.get("oportunidade", "") for r in resultados))
        prefs = list(set(r.get("prefeitura", "") for r in resultados if r.get("prefeitura")))

        row = {
            "user_id":                uid,
            "total_arquivos":         len(resultados),
            "prefeituras":            prefs,
            "oportunidades_dist":     opps,
            "total_margem_emp_disp":  _safe_float(
                sum(r.get("emp_disp", 0) for r in resultados if r.get("emp_disp", 0) > 0)
            ),
            "total_concorrentes":     _safe_float(
                sum(r.get("total_concorrentes", 0) for r in resultados)
            ),
            "qt_com_concorrente":     len([r for r in resultados if r.get("qt_concorrentes", 0) > 0]),
            "qt_com_nossos":          len([r for r in resultados if r.get("qt_nossos", 0) > 0]),
            "qt_sem_consig":          len([
                r for r in resultados
                if r.get("total_cartoes", 0) == 0 and r.get("total_emprestimos", 0) == 0
            ]),
            "duracao_ms":             duracao_ms,
            "created_at":             _now(),
        }

        resp = _get_sb().table("track_lote_sessoes").insert(row).execute()
        if resp.data:
            sessao_id = resp.data[0].get("id")
            _track_lote_itens(sessao_id, uid, resultados)
            return sessao_id
    except Exception as e:
        print(f"[tracking] track_lote_sessao: {e}")
    return None


def _track_lote_itens(sessao_id: str, user_id: str, resultados: list):
    """Batch-insere os itens individuais de uma sessão de lote (chunks de 100)."""
    try:
        rows = []
        for r in resultados:
            rows.append({
                "sessao_id":           sessao_id,
                "user_id":             user_id,
                "arquivo_nome":        r.get("arquivo", ""),
                "storage_path":        r.get("_storage_path"),
                "prefeitura":          r.get("prefeitura", ""),
                "nome_servidor":       r.get("nome", ""),
                "regime":              r.get("regime", ""),
                "liquido":             _safe_float(r.get("liquido")),
                "salario_base":        _safe_float(r.get("salario_base")),
                "base_calculo":        _safe_float(r.get("base_calculo")),
                "margem_emp_disp":     _safe_float(r.get("emp_disp")),
                "margem_cc_disp":      _safe_float(r.get("cc_disp")),
                "margem_cb_disp":      _safe_float(r.get("cb_disp")),
                "oportunidade":        r.get("oportunidade", ""),
                "prioridade":          r.get("prioridade", 9),
                "qt_concorrentes":     r.get("qt_concorrentes", 0),
                "qt_nossos":           r.get("qt_nossos", 0),
                "total_concorrentes":  _safe_float(r.get("total_concorrentes")),
                "total_emprestimos":   _safe_float(r.get("total_emprestimos")),
                "total_cartoes":       _safe_float(r.get("total_cartoes")),
                "created_at":          _now(),
            })

        sb = _get_sb()
        for i in range(0, len(rows), 100):
            sb.table("track_lote_itens").insert(rows[i:i + 100]).execute()
    except Exception as e:
        print(f"[tracking] _track_lote_itens: {e}")


# ============================================================================
# 5. ESTRATÉGIA STELLA
# ============================================================================

def track_stella_estrategia(
    dados: dict,
    estrategia: dict,
    analise_id: Optional[str] = None,
    modo: str = "individual",
):
    """
    Registra a geração de estratégia pela Stella.

    Chamado em main.py → render_resultado(), no botão "Gerar Estratégia com Stella",
    após stella_estrategia() retornar com sucesso.
    """
    uid = _uid()
    if not uid or not estrategia:
        return
    try:
        prods = estrategia.get("produtos_recomendados", [])
        _get_sb().table("track_stella_estrategias").insert({
            "user_id":               uid,
            "analise_id":            analise_id,
            "modo":                  modo,
            "prefeitura":            dados.get("prefeitura", ""),
            "nome_servidor":         dados.get("nome", ""),
            "oportunidade_principal":estrategia.get("oportunidade_principal", "")[:500],
            "combo_recomendado":     (estrategia.get("combo_recomendado") or "")[:500],
            "produtos_recomendados": json.dumps(prods, ensure_ascii=False),
            "qt_produtos":           len(prods),
            "created_at":            _now(),
        }).execute()
    except Exception as e:
        print(f"[tracking] track_stella_estrategia: {e}")


# ============================================================================
# 6. CHAT COM STELLA
# ============================================================================

def track_stella_chat(
    pergunta: str,
    resposta: str,
    modo: str = "individual",
    analise_id: Optional[str] = None,
    prefeitura: str = "",
):
    """
    Registra uma mensagem do chat com a Stella (individual ou lote).

    Chamado em main.py → render_chat_stella(), logo após a resposta da IA.
    modo: "individual" | "lote"
    """
    uid = _uid()
    if not uid:
        return
    try:
        _get_sb().table("track_stella_chats").insert({
            "user_id":     uid,
            "analise_id":  analise_id,
            "modo":        modo,
            "pergunta":    (pergunta or "")[:1000],
            "resposta":    (resposta or "")[:4000],
            "prefeitura":  prefeitura,
            "tokens_aprox": len((pergunta or "").split()) + len((resposta or "").split()),
            }).execute()
    except Exception as e:
        print(f"[tracking] track_stella_chat: {e}")


# ============================================================================
# 7. EXPORTS
# ============================================================================

def track_export(
    tipo: str,
    contexto: str,
    prefeitura: str = "",
    total_registros: int = 0,
):
    """
    Registra um evento de exportação.

    Parâmetros:
        tipo:            "excel" | "csv" | "pdf"
        contexto:        "individual" | "lote"
        prefeitura:      nome da prefeitura (individual) ou vazio (lote)
        total_registros: número de servidores exportados
    """
    uid = _uid()
    if not uid:
        return
    try:
        _get_sb().table("track_exports").insert({
            "user_id":         uid,
            "tipo":            tipo,
            "contexto":        contexto,
            "prefeitura":      prefeitura,
            "total_registros": total_registros,
            "created_at":      _now(),
        }).execute()
    except Exception as e:
        print(f"[tracking] track_export: {e}")


# ============================================================================
# 8. VALIDADOR DE DOCUMENTOS
# ============================================================================

def upload_documento_validador(
    file_bytes: bytes,
    filename: str,
    user_id: str,
) -> Optional[str]:
    """
    Faz upload do documento processado para o Supabase Storage (bucket 'holerites').
    Usa o mesmo bucket dos holerites para evitar problemas de permissão.
    Organização: validador/{user_id}/{YYYY-MM}/{timestamp}_{filename}
    
    Retorna o storage_path em caso de sucesso, ou None em caso de erro.
    """
    try:
        now = datetime.now(timezone.utc)
        ts  = int(time.time())
        safe = filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
        path = f"validador/{user_id}/{now.strftime('%Y-%m')}/{ts}_{safe}"
        
        _get_sb().storage.from_("holerites").upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": "application/pdf", "upsert": "false"},
        )
        return path
    except Exception as e:
        # Silencia erro de bucket - tracking é secundário
        error_msg = str(e).lower()
        if "bucket" in error_msg and "not found" in error_msg:
            print(f"[tracking] Bucket não configurado - upload ignorado")
        else:
            print(f"[tracking] upload_documento_validador '{filename}': {e}")
        return None


def track_validador_sessao(
    arquivos_processados: list,
    duracao_ms: int = 0,
) -> Optional[str]:
    """
    Registra uma sessão de processamento do validador de documentos.
    Retorna o UUID da sessão criada.
    
    Chamado em validador_arquivos.py após processar todos os arquivos.
    """
    uid = _uid()
    if not uid or not arquivos_processados:
        return None
    try:
        sucessos = sum(1 for a in arquivos_processados if a.get("sucesso"))
        
        row = {
            "user_id":           uid,
            "total_arquivos":    len(arquivos_processados),
            "sucessos":          sucessos,
            "erros":             len(arquivos_processados) - sucessos,
            "duracao_ms":        duracao_ms,
            "created_at":        _now(),
        }
        
        resp = _get_sb().table("track_validador_sessoes").insert(row).execute()
        if resp.data:
            sessao_id = resp.data[0].get("id")
            _track_validador_itens(sessao_id, uid, arquivos_processados)
            return sessao_id
    except Exception as e:
        error_msg = str(e).lower()
        if "row-level security" in error_msg or "42501" in error_msg:
            print(f"[tracking] Permissão negada na tabela track_validador_sessoes - sessão não registrada")
        else:
            print(f"[tracking] track_validador_sessao: {e}")
    return None


def _track_validador_itens(
    sessao_id: str,
    user_id: str,
    arquivos_processados: list,
):
    """Batch-insere os itens individuais do validador (chunks de 100)."""
    try:
        rows = []
        for a in arquivos_processados:
            rows.append({
                "sessao_id":       sessao_id,
                "user_id":         user_id,
                "arquivo_original": a.get("original", ""),
                "novo_nome":       a.get("novo_nome", ""),
                "categoria":       a.get("categoria", ""),
                "referencia":      a.get("referencia", ""),
                "sucesso":         a.get("sucesso", False),
                "erro":            a.get("erro", "") if not a.get("sucesso") else None,
                "storage_path":    a.get("storage_path"),
                "tamanho_bytes":   len(a.get("pdf_bytes", b"")) if a.get("pdf_bytes") else 0,
                "created_at":      _now(),
            })
        
        sb = _get_sb()
        for i in range(0, len(rows), 100):
            sb.table("track_validador_itens").insert(rows[i:i + 100]).execute()
    except Exception as e:
        error_msg = str(e).lower()
        if "row-level security" in error_msg or "42501" in error_msg:
            print(f"[tracking] Permissão negada na tabela track_validador_itens - itens não registrados")
        else:
            print(f"[tracking] _track_validador_itens: {e}")
