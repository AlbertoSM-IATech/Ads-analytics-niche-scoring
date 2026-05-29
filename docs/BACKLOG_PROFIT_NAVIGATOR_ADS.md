# Backlog — Profit Navigator / Ads Analytics

Última actualización: 2026-05-29

Lista breve y priorizada de mejoras pendientes. Cualquier ítem requiere
decisión explícita antes de implementarse.

---

## P1 — Limpieza y mantenimiento crítico

- **Dataset de test aislado**: crear un dataset estable en MongoDB de pruebas
  para que los tests `test_phase2_compat`, `test_phase4d*` no dependan del
  dataset live mutable. Permitirá restaurar comparaciones byte-a-byte.
- **Refactor `server.py` por rutas**: actualmente >1300 líneas. Mover endpoints
  a `/app/backend/routes/` agrupando por dominio (datasets, recommendations,
  exports, economy, autopilot). Sin cambios funcionales.
- **Revisión de código muerto**: eliminar `frontend/src/components/SearchTermsTable.jsx`
  y `getSearchTerms` en `lib/api.js`. Una vez fuera, decidir si el endpoint
  `/search-terms` se mantiene o se retira.

## P2 — Mejoras de producto

- **Patrones negativos configurables por dataset**: hoy `NEGATIVE_PHRASE_CANDIDATE`
  usa una lista hardcoded en `recommendations.py`. Mover a `book_economy` para
  que el usuario pueda añadir patrones propios (por idioma, por nicho).
- **AI-enhanced reason opcional**: toggle por dataset que enriquezca el campo
  `reason` con Claude. Reglas deterministas siguen siendo la fuente; la IA solo
  reformula el texto en lenguaje natural.
- **Auth / multi-tenant**: añadir autenticación (JWT o Emergent Google Auth) y
  scope de datasets por usuario. Hoy cualquiera con la URL accede a todo.
- **Mejoras de onboarding**: tour guiado opcional la primera vez que el usuario
  abre `/book`, `/import` y `/acciones`. Sin imponerlo.

## P3 — Funcionalidades avanzadas

- **Amazon SP Bulk Sheet real**: nuevo endpoint y export específico, con
  Campaign/Ad Group IDs reales y formato apto para subir a Amazon Ads. Separado
  del CSV informativo actual.
- **Date range filter**: filtrar la vista por rango temporal. Requiere
  `start_date`/`end_date` por row a nivel importador.
- **Comparación multi-dataset**: visualizar dos o más datasets juntos
  (período A vs período B) con KPIs delta.
- **Export XLSX avanzado**: hoja por tipo de acción, formato con colores y
  fórmulas Excel para que el usuario edite en local.
- **Trace de keywords culpables en REVIEW_CAMPAIGN**: dentro del drawer de
  `/acciones`, listar las 3-5 keywords con mayor `priority_score` de la
  campaña afectada.
- **TTL / archive en MongoDB**: política de retención para datasets antiguos.

---

## Decisiones firmes ya tomadas

Estas decisiones están en `PROFIT_NAVIGATOR_ADS_CIERRE_FUNCIONAL.md` y no
forman parte del backlog hasta que el producto las revoque:

- No sustituir `autopilot.py` legacy.
- No sustituir `suggest_negative` legacy (convive con motor).
- No automatizar acciones directamente sobre Amazon Ads.
- No llamar al CSV de `/acciones` "Bulk Sheet".
- Reglas del motor no se tocan sin tests previos.
