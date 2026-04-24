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
