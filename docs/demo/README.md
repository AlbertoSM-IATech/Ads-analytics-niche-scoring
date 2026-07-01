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

## Matriz de casos esperados

Los 16 keywords del CSV cubren **9 de los 10 `action_type` del motor**.
Cifras calculadas con: regalía = 3.50, ACoS PE = 35 %, fase Dominio (mult 1.2),
CPC referencia = 0.40. Todos los match types se aplican tal cual salen del CSV.

| # | Keyword (Targeting) | Campaña | Match | Clicks | Pedidos | ACoS | Beneficio KDP | Relevancia manual | Acción esperada | Dónde se ve |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `premium dash diet recipe book` | Sana | exact | 20 | 12 | 1.7 % | +40.0 $ | **Alta** | `SCALE` | `/keywords` badge · `/acciones` prioridad Baja |
| 2 | `dash diet meal plan` | Sana | phrase | 15 | 5 | 6.0 % | +14.5 $ | (sin revisar) | `HOLD` | `/keywords` badge · `/acciones` prioridad Baja |
| 3 | `low sodium dash diet` | Sana | phrase | 12 | 0 | — | -2.4 $ | (sin revisar) | `OBSERVE` | `/keywords` badge · `/acciones` prioridad Baja |
| 4 | `dash diet for beginners` | Sana | broad | 25 | 8 | 6.3 % | +23.0 $ | **Alta** | `HOLD` ⚠ ver nota | `/keywords` badge · `/acciones` prioridad Baja |
| 5 | `mindfulness para principiantes` | Problema | broad | 40 | 2 | 75.1 % | -8.0 $ | (sin revisar) | `LOWER_BID` | `/keywords` badge · `/acciones` prioridad Alta |
| 6 | `mindfulness pdf gratis` | Problema | phrase | 12 | 0 | — | -4.8 $ | (sin revisar) | `NEGATIVE_PHRASE_CANDIDATE` | `/keywords` badge · `/acciones` prioridad Media |
| 7 | `mindfulness reading techniques` | Problema | exact | 15 | 0 | — | -6.0 $ | **Baja** | `NEGATIVE_EXACT_CANDIDATE` | `/keywords` badge · `/acciones` prioridad Alta |
| 8 | `mindfulness journal book` | Problema | broad | 25 | 2 | 50.1 % | -3.0 $ | (sin revisar) | `LOWER_BID` | `/keywords` badge · `/acciones` prioridad Media |
| 9 | `mindfulness exercises daily` | Problema | exact | 10 | 1 | 50.1 % | -1.5 $ | (sin revisar) | `LOWER_BID` | `/keywords` badge · `/acciones` prioridad Baja |
| 10 | `dash diet quick start guide` | Exploración | exact | 1 | 0 | — | — | (sin revisar) | `WAIT_FOR_DATA` | `/keywords` badge · `/acciones` prioridad Baja |
| 11 | `dash diet recipes easy` | Exploración | phrase | 2 | 0 | — | — | (sin revisar) | `WAIT_FOR_DATA` | idem |
| 12 | `dash diet plan weekly` | Exploración | broad | 2 | 0 | — | — | (sin revisar) | `WAIT_FOR_DATA` | idem |
| 13 | `dash diet for hypertension` | Exploración | exact | 1 | 0 | — | — | (sin revisar) | `WAIT_FOR_DATA` | idem |
| 14 | `dash diet asin lookalike` | Exploración | exact | 20 | 0 | — | -8.0 $ | **Baja** | `PAUSE_TARGET` | `/keywords` badge · `/acciones` prioridad Alta |
| 15 | `dash diet cookbook hardcover` | Exploración | phrase | 6 | 0 | — | -1.8 $ | (sin revisar) | `WAIT_FOR_DATA` | idem |
| 16 | `dash diet sample chapter` | Exploración | exact | 4 | 0 | — | -1.2 $ | (sin revisar) | `WAIT_FOR_DATA` | idem |

**Campaña agregada `[DEMO] Campaña Problema`** dispara además:

| Campaña | Filas | Spend agregado | Beneficio agregado | ACoS agregado | Acción esperada |
|---|---|---|---|---|---|
| `[DEMO] Campaña Problema` | 5 | 40.80 $ | -23.3 $ | 81.7 % (> PE × 1.20) | `REVIEW_CAMPAIGN` |

### Cobertura por `action_type` (17 recomendaciones totales)

| action_type | Cantidad | Nota |
|---|---|---|
| `WAIT_FOR_DATA` | 6 | Camp. Exploración |
| `OBSERVE` | 1 | `low sodium dash diet` |
| `LOWER_BID` | 3 | 3 keywords de Camp. Problema con beneficio < 0 |
| `HOLD` | 2 | `dash diet meal plan`, `dash diet for beginners` |
| `SCALE` | 1 | `premium dash diet recipe book` con relevancia Alta |
| `MOVE_TO_EXACT` | 0 | **No demostrable** — ver nota abajo |
| `NEGATIVE_EXACT_CANDIDATE` | 1 | `mindfulness reading techniques` con relevancia Baja |
| `NEGATIVE_PHRASE_CANDIDATE` | 1 | `mindfulness pdf gratis` |
| `REVIEW_CAMPAIGN` | 1 | Camp. Problema agregada |
| `PAUSE_TARGET` | 1 | `dash diet asin lookalike` con relevancia Baja |

> ⚠ **Limitación conocida — `MOVE_TO_EXACT` no aparece en este demo.**
>
> El motor solo emite `MOVE_TO_EXACT` cuando la fila tiene
> `Customer Search Term` presente (regla G10 requiere que sea un search-term
> harvest para poder promocionarlo a exacta). Y `PAUSE_TARGET` requiere lo
> contrario: `customer_search_term == None`.
>
> El backend indexa el término mediante
> `key = "customer_search_term" if any(rows) else "targeting"` — global al
> dataset. Por tanto un solo CSV no puede demostrar ambas acciones a la vez.
>
> Este demo prioriza `PAUSE_TARGET` (más ilustrativo del control económico
> del motor). Para probar `MOVE_TO_EXACT` con datos reales, importa un
> Sponsored Products **Search Term Report** que tenga la columna
> `Customer Search Term` poblada.

> ⚠ **Nota sobre `dash diet for beginners`**: cumple todas las condiciones de
> `MOVE_TO_EXACT` salvo que le falta `customer_search_term`, por lo que el
> motor lo clasifica como `HOLD` (rentable, mantener). Es esperado.

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
