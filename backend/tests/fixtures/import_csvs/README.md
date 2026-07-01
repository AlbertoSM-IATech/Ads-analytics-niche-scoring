# Fixtures IMPORT-2 · Amazon Ads CSVs

**Todos los archivos de este directorio son SINTÉTICOS.**

No se distribuyen datos reales de ninguna cuenta de Amazon Ads. Los valores
están inspirados en la estructura real de los reportes exportados por la
interfaz web de Amazon Ads (Sponsored Products) y adaptados a los idiomas
declarados en cada fichero para ejercitar el parser.

## Ficheros

| Fichero | Idioma | Reporte | Objetivo |
|---|---|---|---|
| `search_term_es.csv` | ES | Search Term SP | Cabeceras españolas realistas, match types en español, ACOS en `%` |
| `campaign_en.csv` | EN | Campaign SP | Cabeceras inglesas canónicas, sin `customer_search_term` |
| `acos_percent.csv` | EN | Search Term SP | ACOS explícito con `%` (`39.66%`) |
| `acos_fractional.csv` | EN | Search Term SP | ACOS fraccional sin `%` (`0.3966`) — debe autopromocionarse a % |
| `match_types_es.csv` | ES | Search Term SP | `Exacta`, `Frase`, `Amplia`, `Automática` |
| `parenthesised_currency.csv` | ES | Search Term SP | `Coste total (EUR)`, `Puja (EUR)`, `Ventas (EUR)` — evita colisión `coste` |
| `unknown_headers.csv` | ??? | — | Cabeceras deliberadamente no reconocibles (debe caer en `unknown`, warning) |

Los tests que consumen estos fixtures viven en
`tests/test_import_stabilization.py`. No modifiques estos ficheros sin
actualizar los tests.
