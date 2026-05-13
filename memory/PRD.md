# Amazon Ads Analytics - PRD

## Problem Statement (original, Spanish)
"me gustaria crear una app totalmente funcional con esta maqueta, el usuario deberia poder importar los datos de amazon ads atraves de un csv o similar. asegurate bien de que sea totalmente compatible con los informes que genera amazon ads para que la aplicacion encaje perfectamente y tenga una compatibilidad excelente"

## User Personas
- KDP / Amazon sellers who run Sponsored Products / Brands / Display campaigns
- Agencies analysing client accounts per marketplace (US/ES/UK/DE/FR/IT/MX/JP/AU/CA)
- Users who export reports directly from Amazon Ads UI in ES/EN/IT

## Core Requirements (static)
- Import Amazon Ads CSV/XLSX (Search Term, Campaign, Placement) with auto-detection
- Multi-language headers (ES/EN/IT)
- KPI dashboard: Impressions, Clicks, CTR, CPC, Spend, Sales, Orders, ACoS, ROAS, CVR
- Charts: spend vs sales, ACoS per campaign
- Campaigns and Search Terms tables with filter/sort and negative-keyword suggestions
- AI recommendations with Claude Sonnet 4.5
- MongoDB persistence + dataset history
- Marketplace selector + dark/light theme

## What's been implemented (2026-04-22)
- Backend: /api/imports/upload (multipart), /api/datasets (+ /{id}, /campaigns, /search-terms, /timeseries, /ai-recommendations, DELETE); CSV/XLSX parser with ES/EN/IT header aliases, UE decimal handling, auto-detection of report type and ad type.
- Frontend: Sidebar + Header (marketplace selector, theme toggle), Dashboard (KPIs, Recharts), Importar (drag-and-drop), Campañas (filter+sort), Search Terms (neg-keyword flag), IA panel, Historial.
- Claude Sonnet 4.5 via Emergent LLM key (emergentintegrations).
- Swiss/high-contrast design per /app/design_guidelines.json, Chivo + IBM Plex Sans/Mono, zero purple-on-white.

## Testing status
- 17/17 backend tests passing (pytest). Frontend flow verified end-to-end.
- No blocking bugs. Minor optional improvements noted (targeting report detection, file-size guard, rows-collection split for very large datasets).

## Backlog (P1/P2)
- P1: `targeting` report_type branch (SP Targeting exports)
- P1: Upload size limit + extension validation in UI
- P2: Export negatives as Amazon Bulk Sheet (CSV)
- P2: Date range filter on dashboard (requires start_date across rows)
- P2: Multi-dataset comparison view
- P2: Move `rows` out of dataset doc into separate collection for very large imports
- P2: Optional user auth (JWT / Google) for multi-user mode

## Next tasks
- Gather feedback from user on first import with real Amazon Ads exports
- Add P1 items on request

## Update 2026-04-22 (iter 2)
- **Rebranding Publify**: coral `#FB923C` primary, Inter + Poppins, sidebar siempre oscuro, rounded-md, logo Publify en sidebar.
- **Lógica del archivo original añadida**:
  - `BookInfo` + `BookEconomy` (precio_libro, regalias_por_venta) + **ACoS de Equilibrio** (`(regalias/precio)*100`).
  - **ACoS del siguiente click** (`(spend+cpc)/(sales+precio)*100`) + **Beneficio ahora** + **Beneficio siguiente click**.
  - Badges semánticos: `bajo-pe` / `recuperable` / `en-perdida` / `sin-datos`.
  - Vista **Keywords unificadas** con ACoS actual, ACoS +1 click, Beneficio, CVR y badge por término.
  - Guías de fase **Lanzamiento / Dominio / Beneficio** (1.7x / 1.2x / 0.5x del PE).
- **Endpoints nuevos**: `PUT /api/datasets/{id}/book`, `GET /api/datasets/{id}/keywords-unified`. Existentes enriquecidos con `acos_siguiente` y `badge`.
- **Bug fijado**: `_id` de Mongo se filtraba en respuesta de `/imports/upload` → 500. Corregido.
- **Tests**: 24/24 backend OK. Frontend verificado.

## Update 2026-04-22 (iter 3)
- **Tooltips** (`InfoTooltip`) con 17 definiciones (CTR, CPC, ACoS, ACoS+1, PE, Beneficio, ROAS, CVR, badges y fases) en KpiGrid, Keywords Unified, Side Panel y Wizards.
- **Edición inline** en la tabla Keywords: doble click → input → Enter persiste → recalcula todas las métricas.
- **Panel lateral por keyword** (`Sheet`): resumen completo, chart de snapshots (Recharts, ACoS vs ACoS+1), botón Snapshot manual, edición rápida y eliminación de override manual. Auto-snapshot una vez al día (localStorage).
- **Dashboard blocks**: Bajo PE / Recuperable / En pérdida / Sin datos → click navega a `/keywords` con filtro precargado.
- **Wizards**:
  - `AddKeywordWizard` (3 pasos): keyword+campaña → métricas → preview con todos los cálculos.
  - `AddCampaignWizard`: campaña + N keywords en una sola operación con autocálculo de gasto/ventas.
- **Endpoints nuevos**: `PUT /datasets/{id}/keyword`, `DELETE /datasets/{id}/keyword/{term}`, `POST /datasets/{id}/campaign`, `POST /datasets/{id}/snapshot-all`, `GET /datasets/{id}/snapshots/{term}`, `GET /datasets/{id}/keyword-detail`, y `summary` en keywords-unified.
- **Testing**: 37/37 backend OK (24 legacy + 13 iter 3). Frontend flows verificados.

## Update 2026-04-22 (iter 4)
- **Side panel con 2 pestañas** (Estudio de KW / Gestión de Ads) como el archivo original.
- **Inline edit**: clicks/impresiones/pedidos con step=1 (enteros), CPC/gasto/ventas con step=0.01.
- **Auto-calc gasto** (clicks × CPC) con toggle en el side panel + al editar clicks/CPC en la tabla.
- **Auto-calc ventas** (pedidos × precio del libro) con toggle.
- **ACoS del siguiente click** ahora con 2 variantes: `con venta` (optimista) y `sin venta` (peor caso) — fórmulas revisadas y correctas.
- **Marketplaces independientes**: datasets filtrados por marketplace activo, badge del marketplace en wizards y side panel, filtro en historial.
- **Niche Study (Market Score 0-100)**: nueva ruta `/niche` con stats cards + tabla ordenada por score + breakdown (Volumen 25, Competidores 25, Precio 15, Regalías 10, Demanda 12, Competencia 12). Editable por keyword desde el tab Estudio de KW del side panel con 6 checkboxes de demanda y 3 de competencia.
- **Testing**: 49/49 backend OK (12 nuevos: Market Score unit, acos sin venta, niche fields persistence, auto_spend).

## Update 2026-04-22 (iter 5)
- **Simulación explícita +1 click con venta**: side panel muestra una tarjeta "Simulación" con las 5 cifras antes/después (clicks, pedidos, gasto, ventas, ACoS) cuando precio_libro > 0, dejando claro que la simulación sube clicks +1 y pedidos +1 (no sólo ventas).
- **Quick actions** del mockup original: botones `+1 Click`, `+0.01 CPC`, `+1 Pedido (con click)` para modificar manualmente los valores editables.
- **Campaign Plans CRUD** en `/plans`: crear/editar/borrar planes agrupando keywords con fase (Lanzamiento/Dominio/Beneficio), ACoS objetivo, presupuesto diario y notas. Tarjetas con resumen agregado y `phase_target_acos` = PE × {1.7 / 1.2 / 0.5}.
- **Export de keywords negativas** en formato Amazon Bulk Sheet (`GET /datasets/{id}/export/negatives`) para subir directamente a Seller Central. Botón en /keywords.
- **Testing**: 65/65 backend (16 nuevos) + frontend de simulación, plans y export validado.

## Update 2026-04-22 (iter 6)
- **Autopilot por fase**: selector Lanzamiento / Dominio / Beneficio con multiplicadores 1.7× / 1.2× / 0.5× sobre el ACoS de Equilibrio. Reglas adaptadas por fase:
  - Lanzamiento: pausa sólo con ≥12 clicks sin venta, escala +20% con tracción.
  - Dominio: pausa con ≥8 clicks sin venta, escala +15% con ROAS ≥4.
  - Beneficio: pausa con ≥5 clicks sin venta, escala +10% con ROAS ≥5.
- **Helium10 / Publisher Rocket import** (`POST /datasets/{id}/import-niche`): carga CSV/XLSX y auto-rellena volumen y competidores por término (match insensible a mayúsculas/minúsculas).
- **Distribución por estado** (PieChart) añadida al Dashboard.
- **Comparación de datasets** (`GET /compare/{other_id}`): KPI delta + 30 top movers por |Δspend|+|Δsales|. Ruta `/compare`.
- **Export Bulk Sheet autopilot** (`/export/autopilot?phase=...`) con filas Pause/Increase bid listas para Seller Central.
- **Edición inline ampliada**: `campaign` y `match_type` ahora editables en la tabla; persistencia vía PUT `/keyword`.
- **Bug crítico corregido**: upsert_keyword reemplazaba todo el sub-documento `overrides.{term}`; ahora usa `$set` con claves con punto para MERGE partial de cada campo. 78/78 backend tests OK.

## Update 2026-04-22 (iter 7) — Simplificación + V2
- **Sidebar colapsable** (persiste en localStorage); arquitectura reducida a **Dashboard, Libro, Importar, Campañas, Keywords**. Eliminadas: Planes, Historial, Comparar, Autopilot standalone, Niche (Autopilot ahora vive dentro del panel de keyword).
- **Fase global del libro** (Lanzamiento / Dominio / Beneficio) + botón "Restaurar estándar" en `/book`. Se muestra como badge en el Header.
- **KeywordDetailSheet redimensionable** con drag handle en el borde izquierdo (persistido). Incluye:
  - **Panel Autopilot por keyword** usando la fase del libro por defecto (con override).
  - **Multi-campaña**: reemplazado input de texto por selector de campañas existentes + chips removibles.
- **Criterios por Mercado (V2)**: modal accesible desde el Header (ícono ⚙︎) con defaults exactos del repo original (ES/US/UK/DE/FR/IT/MX/CA/JP/AU). Algoritmo V2 continuo portado a `market_score_v2.py`.
- **Backup JSON**: export desde `/backup` y restore vía `/restore` (icono en el Header).
- **IA recalibrada**: prompt del sistema incluye ahora fase global + criterios de mercado activo.
- **Testing**: **98/98 backend OK** + frontend todos los data-testid verificados. Bug fix: `keywords-unified` ahora devuelve `campaigns: []` por fila.

## Update 2026-05-01 (iter 8) — Pesos editables + Multi-campaña inline + Negativas
- **Pesos del Market Score editables** (`/book`): los 6 bloques (volumen 26, competidores 34, precio 8, regalías 8, demanda 12, competencia 12) ahora son configurables. Score normalizado a 0-100 según la suma de pesos. Botones "default: X" y "Restaurar estándar". Endpoints: `GET|PUT|DELETE /api/datasets/{id}/score-weights`.
- **Multi-campaña inline** en la tabla Keywords: nueva columna "Campañas" con popover de checkboxes + input "Nueva campaña…". Persistida como `campaigns: []` en `upsert_keyword`.
- **Columna Negativas** en la tabla Keywords: badge rojo "Sugerida" (clicks≥6 + orders=0), icono 🚫 junto al término, fila tintada en rojo muy suave. Filtro toggle "Solo negativas" con contador.
- **Summary extendido** en `/keywords-unified`: nueva clave `negativas` (ortogonal a las 4 categorías de badge). Test iter3 actualizado para reflejar que `negativas` no se suma a las badges.
- Tests: 98/98 backend regresión OK + 61 nuevos (unit + compat fixture).

## Update 2026-05-01 (iter 9) — Fase 1 Profit Navigator: Configuración económica KDP
- **Nuevo módulo `/app/backend/kdp_economy.py`** (puro, sin DB):
  - `MARKETPLACE_CONFIG` para 9 marketplaces (ES/COM/DE/FR/IT/UK/CA/AU/JP) con currency, symbol, iva_default_pct, royalty_threshold, region.
  - Tablas de impresión completas (EU/COM/UK/CA/AU/JP) + recargo hardcover por región.
  - Funciones: `calc_precio_sin_iva` (IVA solo en ES), `calc_delivery_cost` (eBook 70%), `calc_coste_impresion`, `calc_regalia_neta` (eBook/PRINT con threshold dinámico), `calc_acos_pe`, `calc_cpc_max_rentable`, `calc_clicks_pe_base`, `calc_tasa_conv_breakeven`, `beneficio_kdp`, `calc_pvp_minimo`, `diagnose` (risk + viability), `compute_full_diagnosis`.
  - Normalización `us`→`COM` para marketplaces legacy lowercase.
  - Scoring 50/40/10 corregido: ≥14→50, 13→35, 12→25, 11→15, 10→10 (no cero), <10→0.
- **`BookEconomy` extendido** con 10 campos opcionales KDP (`format_type EBOOK|PRINT`, `book_format PAPERBACK|HARDCOVER`, `interior_type BN|COLOR_PREMIUM|COLOR_STANDARD`, `book_size`, `pages`, `iva_type`, `royalty_rate_ebook 70|35`, `tamano_mb`, `cpc_referencia`, `margen_objetivo_pct`). Compatibilidad legacy total garantizada.
- **Nuevo endpoint `GET /api/datasets/{id}/economy-diagnosis`** (read-only). Devuelve `{mode: "legacy"|"kdp", marketplace, marketplace_config, inputs, outputs, diagnosis, notes}`. En modo legacy sólo calcula ACoS PE / CPC máx básicos.
- **Nuevo sub-panel `BookEconomyKDP.jsx`** en `/book` con selector de marketplace KDP, formato (ebook/impreso), sub-tipo (tapa blanda/dura), interior, tamaño, páginas, IVA (sólo ES), CPC referencia, margen objetivo. Outputs en vivo: regalía neta, ACoS PE (=BACOS=break-even ACoS), CPC máx, clicks PE base, precio sin IVA, coste impresión, PVP mínimo + score económico + diagnóstico risk/viability.
- **NO tocados en Fase 1** (garantizado por tests de regresión con fixtures pre-phase1): `keywords-unified`, `autopilot`, multiplicadores de fase, cálculo de beneficio visible en la tabla ADS, importador, recomendaciones.
- **Testing**: **159/159 backend OK** (98 previos + 61 nuevos):
  - 57 unit tests de fórmulas y scoring en `test_kdp_economy.py`.
  - 4 tests de compatibilidad en `test_phase1_compat.py` comparando byte-a-byte contra fixtures JSON del estado pre-fase1.

## Próximas fases (planificadas, NO implementadas aún)
- **Fase 2**: conectar economía KDP con reportes Ads (`cpc_real = spend/clicks`, clicks_pe por término, consumo_fase, beneficio_kdp en tabla).
- **Fase 3**: motor de recomendaciones con output `Recommendation` (§17 del puente): WAIT_FOR_DATA, OBSERVE, LOWER_BID, HOLD, SCALE, MOVE_TO_EXACT, NEGATIVE_EXACT_CANDIDATE, NEGATIVE_PHRASE_CANDIDATE, REVIEW_CAMPAIGN, PAUSE_TARGET. Basado en consumo_pe/fase + recuperabilidad + relevancia manual (high/medium/low/unreviewed).
- **Fase 4**: UI priorizada `/acciones` + exportaciones por tipo de acción.

## Update 2026-05-02 (iter 11) — Fase 2A Profit Navigator: Métricas económicas por término
- **Helpers nuevos en `kdp_economy.py`**: `resolve_regalia_neta(book_economy, marketplace)` resuelve cascade `kdp → legacy → none` con `regalia_source`. `compute_row_econ(...)` calcula los 9 campos económicos por fila con seguridad ante divisiones por cero.
- **`/keywords-unified` extendido** (sin romper compatibilidad — claves antiguas intactas, ya no byte-idéntico): cada fila ahora incluye `cpc_real`, `cpc_source` (real|reference|none), `regalia_neta_kdp`, `regalia_source` (kdp|legacy|none), `acos_pe_kdp`, `clicks_pe`, `clicks_fase`, `phase_mult_used`, `consumo_pe`, `consumo_fase`, `beneficio_kdp`, `acos_siguiente_con_venta`. Top-level: `regalia_source`, `regalia_neta_dataset`, `phase`. Además `customer_search_term` y `targeting` quedan como claves separadas en cada fila (nunca se sobrescriben).
- **`/keyword-detail` extendido** con los mismos 9 campos económicos en `metrics{...}` + `regalia_source`. Para que el detalle lateral tenga el contexto sin requerir otra llamada.
- **CPC fallback jerarquía**: real (clicks>0 y spend>0) → reference (si hay `cpc_referencia`) → none. Etiquetado claramente en UI.
- **Multiplicadores de fase intactos**: usa `mult_lanzamiento=1.7`, `mult_dominio=1.2`, `mult_beneficio=0.5` del dataset. **Defaults NO cambiados** (test canario `test_clicks_fase_uses_dataset_multiplier_not_new_defaults` previene migración accidental).
- **`KeywordsUnified.jsx`**: 3 columnas nuevas (Clicks PE, Consumo fase, Beneficio KDP). Color de Consumo fase: <50% verde, 50-80% amber, 80-100% naranja, >100% rojo. Badge "est." junto a Clicks PE cuando `cpc_source==="reference"`. Beneficio KDP sustituye al bruto cuando hay economía configurada; en `regalia_source==="none"` cae al bruto pero etiquetado.
- **`KeywordDetailSheet.jsx`**: bloque "Contexto económico KDP" en tab "Gestión de Ads" con 9 métricas + badges de fuente (Regalía: KDP/legacy/no config., CPC: real/estimado/n/d) + disclaimer "Beneficio bruto (Sales − Spend, NO es beneficio real KDP)" debajo.
- **Endpoints sin tocar (verificado por fixtures byte-equivalent)**: `/autopilot`, `/imports/upload`. NO se ha tocado: motor de recomendaciones, multiplicadores, importador, lógica de Market Score.
- **Testing**: **187/187 backend OK** (89 fase 1 + 98 anteriores + 28 nuevos en Fase 2: 23 unit `test_phase2_metrics.py` + 5 compat `test_phase2_compat.py`). Iter 11 testing agent: 100% UI/integration validated, sin bugs, sin acciones pendientes.

## Update 2026-05-13 (iter 12) — Fase 2B Profit Navigator: Relevancia manual
- **Campo `relevance` por keyword/search term**: persiste vía el mecanismo de overrides existente (NO colección nueva). Valores permitidos: `unreviewed | high | medium | low`. Default: `"unreviewed"`. Validación en `upsert_keyword`: valor inválido → 400.
- **Backend**:
  - `KeywordOverrideIn` extendido con `relevance: Optional[str]`.
  - `_merge_rows_with_overrides` propaga `relevance` desde el override a cada fila merged.
  - `/keywords-unified` y `/keyword-detail` exponen `relevance` (default `"unreviewed"` cuando no hay override).
  - Omitir el campo en un PUT NO modifica el valor existente (gracias a `exclude_none=True` y `setdoc` por dotted keys).
- **Frontend**:
  - **Tabla `/keywords`**: dot 8×8px junto al término con color por relevancia (gris/verde/amber/rojo suave) y tooltip. Sin columna nueva, sin saturación.
  - **Detalle lateral**: bloque "Relevancia: [selector]" justo debajo del SheetHeader, con dot visual sincronizado, 4 opciones y `InfoTooltip` aclarando que en Fase 2B sólo se persiste y muestra.
  - Lib helper `/app/frontend/src/lib/relevance.js` (RELEVANCE_OPTIONS + RELEVANCE_DOT + getRelevanceDot()).
- **Garantías cumplidas** (verificadas por tests):
  - `/autopilot` byte-equivalente con cualquier valor de relevance (test prueba los 4 valores en bucle).
  - `/imports/upload` byte-equivalente al fixture pre-fase-2.
  - Las 12 métricas económicas Fase 2A (cpc_real, regalia_neta_kdp, clicks_pe, clicks_fase, etc.) **IDÉNTICAS** al cambiar relevance entre los 4 valores.
  - `relevance` NO se usa en `autopilot.py`, `suggest_negative`, ni en `compute_row_econ` (sólo lectura/escritura).
- **Testing**: **199/199 backend OK** (187 anteriores + 12 nuevos en `test_phase2b_relevance.py`). Validación visual del frontend OK: 16/16 dots en tabla, selector funcional en detalle, transiciones unreviewed→high→medium→low→unreviewed sin errores.
- **NO se ha tocado**: `autopilot.py`, `amazon_ads.py`, `kdp_economy.py`, `compute_row_econ`, `suggest_negative`, motor de recomendaciones, multiplicadores.

## Update 2026-05-14 (iter 13) — Fase 3A Profit Navigator: Motor de recomendaciones paralelo
- **Nuevo módulo `/app/backend/recommendations.py`** (puro, sin DB, **NO importa `autopilot.py`** — zero coupling):
  - Schema Pydantic `Recommendation` + `RecommendationMetrics` (§17 del puente).
  - 10 `action_type`s: WAIT_FOR_DATA, OBSERVE, LOWER_BID, HOLD, SCALE, MOVE_TO_EXACT, NEGATIVE_EXACT_CANDIDATE, NEGATIVE_PHRASE_CANDIDATE, REVIEW_CAMPAIGN, PAUSE_TARGET. Los dos últimos están **reservados pero no se emiten en 3A** (test lo verifica).
  - 12 reglas de decisión (G1..G12) evaluadas secuencialmente.
  - `IRRELEVANT_PATTERNS`: lista cerrada bilingüe (13 patrones multi-palabra ES+EN; "free"/"gratis" solos NO disparan).
  - `normalize_match_type()` mapea automatic→auto, broad match→broad, etc.
  - `priority_score(0..100)` transparente: consumo_pe×18 + spend/20×15 + 12 si no recuperable + 10 si 0 orders sobre PE + 8/4/2/0 por relevance + 8 si beneficio negativo. Mapeo a buckets: ≥70 high, ≥40 medium, <40 low.
  - `is_recoverable_with_next_sale`: `acos_siguiente_con_venta ≤ acos_pe_kdp × 1.10` (buffer del 10%).
- **Nuevo endpoint `GET /api/datasets/{id}/recommendations`** (1 endpoint añadido, ningún otro tocado):
  - Estrictamente **READ-ONLY**: 0 escrituras a DB (test sha256-hash del documento antes/después de 5 llamadas).
  - Reutiliza `get_keywords_unified` internamente (no duplica lógica de enriquecimiento).
  - Devuelve `{count, phase, regalia_source, generated_at, by_action, recommendations[]}` ordenadas por `priority_score desc`.
  - IDs deterministas (`hashlib.sha256(dataset_id+term+action_type)[:16]`) → llamar al endpoint N veces produce los mismos IDs.
- **Ajustes obligatorios cumplidos**:
  - G2 (NEGATIVE_PHRASE_CANDIDATE) requiere `orders==0 AND clicks≥3 AND consumo_fase≥0.5` además del patrón.
  - G7 calcula `cpc_max_rentable = regalia_neta_kdp/10` y degrada a regla basada en relevance/consumo si no está disponible.
  - REVIEW_CAMPAIGN y PAUSE_TARGET reservados en el schema, sin reglas activas en 3A.
  - `suggest_negative` original sigue conviviendo — sin sustitución.
- **NO tocados** (garantizado por tests): `autopilot.py` byte-equivalente al fixture `autopilot_dominio_pre_phase3.json` tras 5 llamadas a `/recommendations`; `/imports/upload` byte-equivalente al fixture `import_response_pre_phase2.json`; UI completa.
- **Testing**: **232/232 backend OK** (199 anteriores + 33 nuevos en `test_recommendations.py`). Cubre cada regla G1..G12, parametrize de G7 por relevance, guards de G2 (single-word "free" no dispara, orders>0 no dispara, clicks<3 cae a WAIT_FOR_DATA), bounds de priority_score, determinismo de IDs, read-only del endpoint, regresión de autopilot + importador.

## Próximas fases (planificadas, NO implementadas aún)
- **Fase 3B**: pequeña UI no intrusiva — mostrar el `action_type` principal por término como badge en la tabla (sin tabla nueva), + tooltip con el `recommended_action`. Posible AI-enhanced `reason` con Claude. Patrones irrelevantes configurables por dataset.
- **Fase 4**: ruta `/acciones` con tabla priorizada, filtros por `action_type`/`priority`, y exportaciones bulk (CSV por tipo de acción). Reglas REVIEW_CAMPAIGN (agregaciones a nivel campaña) y PAUSE_TARGET (agregaciones a nivel ad_group). Decisión post-validación: ¿se sustituye `suggest_negative` por este motor?
