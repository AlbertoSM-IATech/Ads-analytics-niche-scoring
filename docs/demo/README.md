# Profit Navigator — Dataset Demo / Sintético

Este dataset es **100% sintético**. No representa datos reales de ninguna cuenta
de Amazon Ads ni de ningún libro real. Su único propósito es permitir explorar
todas las funcionalidades de la plataforma con un caso de uso de ejemplo.

> ⚠️ Las recomendaciones del motor sobre este dataset son ilustrativas. No
> tomes decisiones de pujas reales basadas en ellas.

---

## Cómo importarlo

1. Ve a **`/import`**.
2. Arrastra `profit_navigator_demo_dataset.csv`.
3. Cuando termine la carga, ponle como título exactamente:
   ```
   [DEMO] Profit Navigator Showcase
   ```
   (así lo distingues de tus datasets reales).
4. Activa el dataset desde el selector superior para que `/keywords`,
   `/acciones` y `/book` apunten a él.

## Configuración económica recomendada (`/book`)

Para que las recomendaciones del motor reproduzcan los casos de demo,
configura el bloque **"Configuración económica KDP"** con estos valores:

| Campo | Valor |
|---|---|
| Marketplace | **Estados Unidos (US)** |
| Formato | **eBook** |
| Tipo de interior | (no aplica para eBook) |
| Páginas | `120` (opcional) |
| PVP | `9.99` |
| % Regalía | `35` |
| CPC de referencia | `0.40` |
| Fase del libro | **Dominio** (`mult = 1.2`) |
| Margen objetivo % | `30` |

Con esta configuración:
- **Regalía neta ≈ 3.50 USD**
- **ACoS de equilibrio ≈ 35%**
- **Clicks PE ≈ 8.75** (regalía / CPC referencia)

### Configuración manual adicional en `/keywords`

Algunas recomendaciones requieren que **etiquetes la relevancia manualmente**
después de importar (campo `Relevancia` en la tabla o side panel):

| Targeting | Relevancia recomendada |
|---|---|
| `premium dash diet recipe book` | **Alta** → activa `SCALE` |
| `dash diet for beginners` | **Alta** → activa `MOVE_TO_EXACT` |
| `mindfulness reading techniques` | **Baja** → activa `NEGATIVE_EXACT_CANDIDATE` |
| `dash diet asin lookalike` | **Baja** → activa `PAUSE_TARGET` |

El resto puedes dejarlas como `Sin revisar`.

---

## Qué se espera ver en `/keywords`

16 keywords distribuidas en 3 campañas demo:

| Campaña | Filas | Caso |
|---|---|---|
| `[DEMO] Campaña Sana` | 4 | Casos rentables (SCALE, HOLD, OBSERVE, MOVE_TO_EXACT) |
| `[DEMO] Campaña Problema` | 5 | Casos en pérdida (LOWER_BID×2, NEG_EXACT, NEG_PHRASE, +1 filler) |
| `[DEMO] Campaña Exploración` | 7 | Tráfico nuevo + PAUSE_TARGET + OBSERVE |

En la tabla simplificada deberías ver:
- Badges del motor variados (Bajar puja, Mantener, Esperar datos, Negativa exacta, Negativa frase, Pausar target, Mover a exacta, Escalar...).
- Beneficio KDP positivo en `[DEMO] Campaña Sana`, negativo en `[DEMO] Campaña Problema`.
- Consumo PE bajo en la sana, > 100% en varias de problema.
- Mezcla de match types: `exact`, `phrase`, `broad`.

## Qué se espera ver en `/acciones`

Resumen aproximado (con economía y relevancias configuradas como arriba):

| Prioridad | ~ #Recs |
|---|---|
| Alta | 3-4 (LOWER_BID con pérdida, NEG_EXACT, PAUSE_TARGET) |
| Media | 2-3 (NEG_PHRASE, REVIEW_CAMPAIGN) |
| Baja | ~9 (WAIT_FOR_DATA, OBSERVE, HOLD, SCALE, MOVE_TO_EXACT) |

Por `action_type`:
- `WAIT_FOR_DATA` × 4 (tráfico recién lanzado)
- `OBSERVE` × 1-2
- `LOWER_BID` × 2 (ventas con pérdida)
- `HOLD` × 1 (rentable, sin alarma)
- `SCALE` × 1 (con `relevance=high` en `premium dash diet recipe book`)
- `MOVE_TO_EXACT` × 1 (con `relevance=high` en `dash diet for beginners`)
- `NEGATIVE_EXACT_CANDIDATE` × 1 (con `relevance=low` en `mindfulness reading techniques`)
- `NEGATIVE_PHRASE_CANDIDATE` × 1 (patrón "pdf gratis" en targeting)
- `REVIEW_CAMPAIGN` × 1 (sobre `[DEMO] Campaña Problema`: B1 — beneficio agregado negativo y ACoS agregado > PE × 1.20)
- `PAUSE_TARGET` × 1 (con `relevance=low` en `dash diet asin lookalike`)

Si algún caso no se dispara, revisa:
- Que la economía KDP esté guardada (banner azul "KDP oficial" en `/book`).
- Que la fase sea **Dominio** (las recomendaciones cambian con la fase).
- Que las relevancias manuales estén aplicadas como indica la tabla anterior.

Pequeñas variaciones (±1 fila) en cada `action_type` son normales si los
umbrales del motor cambian en futuras iteraciones — los tests del backend
siguen siendo la fuente de verdad.

---

## Cómo borrar el dataset demo

Cuando ya no lo necesites:

1. Selecciona `[DEMO] Profit Navigator Showcase` en el selector superior.
2. Abre el panel de gestión del dataset (icono de papelera o menú `⋯`).
3. Confirma la eliminación.

O directamente vía API:

```bash
curl -X DELETE "$REACT_APP_BACKEND_URL/api/datasets/<dataset_id>"
```

(El `dataset_id` se obtiene desde `GET /api/datasets` o desde el URL al navegar.)

---

## Notas técnicas

- El CSV usa el esquema **Search Term Report** de Amazon Sponsored Products
  con headers en inglés (compatibles con Amazon Ads ES/EN/IT por auto-detección).
- Solo se incluye la columna `Targeting` (sin `Customer Search Term`).
  Esto es intencional: permite que el motor evalúe `PAUSE_TARGET` en filas
  donde corresponda (la regla requiere `customer_search_term == None`).
- No depende de ningún script, seed, ni botón dev-only.
- No se mezcla con datos reales: cada dataset es independiente en MongoDB.
