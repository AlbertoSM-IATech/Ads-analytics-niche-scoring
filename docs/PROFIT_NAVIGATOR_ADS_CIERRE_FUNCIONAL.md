# Profit Navigator / Ads Analytics — Cierre funcional

Estado: **Cerrado funcionalmente** · Última actualización: 2026-05-29

Este documento fija el estado del módulo. Cualquier cambio fuera de lo descrito
aquí requiere decisión explícita.

---

## 1. Estado final del módulo

- **Backend**: estable. `git diff backend/` sin cambios pendientes tras la
  validación final.
- **Frontend**: estable. Lint sin issues en `components/` y `lib/`.
- **Tests**: suite limpia (248 passed, 7 skipped, 0 failed).
- **Fuente de verdad**:
  - **Con economía resuelta** (`regalia_source != "none"`): el motor determinista
    en `backend/recommendations.py` es la única fuente para `suggest_negative`,
    `/export/negatives` y el panel `/acciones`.
  - **Sin economía**: fallback legacy `clicks ≥ 6 AND orders == 0` se mantiene
    activo para no romper compatibilidad.

## 2. Funcionalidades completadas

- Import Amazon Ads CSV/XLSX (ES/EN/IT), Helium10, Publisher Rocket.
- Configuración económica KDP (Profit Navigator): 9 marketplaces, eBook/PRINT,
  scoring 50/40/10, multiplicadores por fase (lanzamiento/dominio/beneficio).
- Métricas económicas por término (Fase 2A): `cpc_real`, `acos_pe_kdp`,
  `clicks_pe`, `clicks_fase`, `consumo_pe`, `consumo_fase`, `beneficio_kdp`,
  `acos_siguiente_con_venta`.
- Relevancia manual (Fase 2B): `unreviewed | low | medium | high`.
- Motor determinista `/recommendations` (Fases 3A/3A.1/4C):
  reglas G1..G12 per-row + G2.5 PAUSE_TARGET + agregación REVIEW_CAMPAIGN.
- `/keywords`: tabla con edición inline, badge de motor (Fase 3B) clicable como
  deep-link, panel lateral con bloque "Recomendación del motor".
- `/acciones`: ruta read-only con resumen, filtros (priority/action_type/
  confidence/risk/relevance/onlyWithOrders/onlyNegativeProfit), drawer
  detallado, deep-link bidireccional desde `/keywords`.
- Export CSV "Exportar vista actual" (Fase 4B): respeta filtros + deep-links,
  30 columnas, separador `;`, BOM UTF-8, filename
  `publify_acciones_filtradas_YYYY-MM-DD.csv` (informativo, **no Amazon Bulk**).
- REVIEW_CAMPAIGN activo: agregación por campaña con guards conservadores
  (min 3 rows, <70% WAIT_FOR_DATA, spend ≥ max(5, regalía×5), B1 o B2).
- PAUSE_TARGET activo: severo, solo bidded targets, doble umbral según
  relevancia (low: 8/2.0/×1.5; unreviewed: 12/2.5/×2.0).
- Alineación `suggest_negative` (Fase 4D): deriva del motor cuando hay economía.
- Alineación `/export/negatives` (Fase 4D.1): exporta el set
  `NEGATIVE_EXACT_CANDIDATE ∪ NEGATIVE_PHRASE_CANDIDATE` del motor; match_type
  refleja exacta vs frase.

## 3. Endpoints principales

| Endpoint | Método | Notas |
|---|---|---|
| `/api/imports/upload` | POST | Importer Amazon Ads/Helium10/Publisher Rocket. |
| `/api/datasets/{id}/keywords-unified` | GET | Tabla principal. `suggest_negative` deriva del motor si hay economía. |
| `/api/datasets/{id}/recommendations` | GET | Motor determinista, **read-only**. |
| `/api/datasets/{id}/economy-diagnosis` | GET | KDP Economy: regalía, ACoS PE, fases. |
| `/api/datasets/{id}/export/negatives` | GET | CSV Amazon SP Bulk Sheet de negativas. Alineado con motor. |
| `/api/datasets/{id}/autopilot` | GET | Legacy AI/rule-based, intacto. |
| `/api/datasets/{id}/keyword` | PUT | Overrides por término (relevance, manual fields). |
| `/api/datasets/{id}/campaigns-list` | GET | Lista de campañas para asignaciones múltiples. |

Endpoint legacy interno con código muerto en UI:
`/api/datasets/{id}/search-terms` (`SearchTermsTable.jsx` huérfano).

## 4. Reglas importantes de negocio

- **`suggest_negative` con economía**: `true` solo si el motor devuelve
  `NEGATIVE_EXACT_CANDIDATE` o `NEGATIVE_PHRASE_CANDIDATE`.
- **`suggest_negative` sin economía**: fallback legacy
  (`clicks ≥ 6 AND orders == 0`).
- **`LOWER_BID`** se usa para términos con ventas pero pérdida (`beneficio_kdp
  < 0`) y consumo PE alto; **nunca se sugiere como negativa** (regla G9.5/G9.6
  de Fase 3A.1).
- **`PAUSE_TARGET`** solo per-row con señales muy fuertes:
  - bidded target (`row.targeting` set Y `customer_search_term` None);
  - `relevance ∈ {low, unreviewed}` (jamás high/medium);
  - `cpc_source == "real"` (jamás reference);
  - umbrales doblados para `unreviewed`.
- **`REVIEW_CAMPAIGN`** solo por agregación con guards conservadores; score
  acotado a 90; nunca es una acción individual.
- **No aplicar acciones automáticamente** en Amazon Ads. El motor es read-only.
  Ninguna recomendación dispara cambios externos sin intervención humana.

## 5. Estado de tests

- Última suite (29-may-2026): **248 passed, 7 skipped, 0 failed**.
- Skips conocidos:
  - 6 skips en `test_phase4d*` por dataset live sin economía o sin PAUSE_TARGET
    activo; comportamiento esperado del fallback (no rompe nada).
  - 1 skip en `test_phase2_compat::test_keywords_unified_adds_phase2_fields`
    cuando no hay rows.
- Tests excluidos de la suite por requerir variable de entorno:
  `tests/test_iter4.py`, `tests/test_iter5.py` (necesitan
  `REACT_APP_BACKEND_URL` en backend). Documentado, no bloquea.
- **Fixture `keywords_unified_pre_phase1.json`**: campos derivados de la `phase`
  del dataset y de `book_economy.cpc_referencia` están relajados a nivel byte;
  presencia, tipo y coherencia de fórmulas siguen verificándose
  (`clicks_fase ≈ clicks_pe × phase_mult_used`,
  `consumo_pe ≈ clicks / clicks_pe`, `consumo_fase ≈ clicks / clicks_fase`).

## 6. Riesgos conocidos

- **Código muerto**: `frontend/src/components/SearchTermsTable.jsx` +
  `getSearchTerms` en `lib/api.js`. No referenciados en rutas activas;
  candidatos a eliminar antes de tocar `/search-terms` backend.
- **`server.py` >1300 líneas**: deuda técnica, no bloquea ejecución.
- **Sin autenticación**: cualquier usuario con la URL ve todos los datasets.
- **MongoDB sin TTL ni archive**: histórico crece sin límite.
- **Fixture mutable**: mitigado con relax de campos derivados; aún depende del
  dataset live `d17b595d-…`.

## 7. Backlog priorizado

| Prioridad | Item |
|---|---|
| **P1** | Dataset de test aislado + refresh limpio de fixtures. |
| **P1** | Refactor `server.py` → `/app/backend/routes/` por dominio. |
| **P2** | Patrones de `NEGATIVE_PHRASE_CANDIDATE` configurables por dataset. |
| **P2** | AI-enhanced `reason` con Claude (toggle opcional por usuario). |
| **P2** | Auth (JWT o Emergent Google Auth) + multi-tenant. |
| **P2** | Eliminar código muerto `/search-terms` UI + endpoint. |
| **P3** | Export Amazon SP Bulk Sheet real (separado del CSV informativo). |
| **P3** | Date range filter + multi-dataset comparison view. |
| **P3** | Trace de las 3-5 keywords culpables dentro del drawer de REVIEW_CAMPAIGN. |
| **P3** | TTL / archive en MongoDB para datasets antiguos. |

## 8. Decisiones explícitas

- **No tocar más lógica del motor sin tests previos** que cubran el cambio.
- **No sustituir el fallback legacy** (clicks≥6 AND orders=0) sin decisión
  explícita del producto. Convive con el motor por compatibilidad.
- **No llamar al CSV actual de `/acciones` "Amazon Bulk Sheet"**. El filename y
  copy deben dejar claro que es una exportación informativa, no apta para
  subida directa a Amazon Ads.
- **No activar automatizaciones directas** sobre Amazon Ads desde el motor:
  todas las recomendaciones requieren revisión humana.
- **`autopilot.py` y `suggest_negative` legacy quedan intactos** hasta nueva
  decisión. Coexisten con el motor pero sin competir visualmente en la UI
  (badge legacy demoteado en `/keywords`).
- **No tocar `/search-terms`** hasta limpiar antes el código muerto en
  frontend.
