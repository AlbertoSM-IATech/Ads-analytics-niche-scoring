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
