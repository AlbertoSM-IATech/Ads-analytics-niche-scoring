import { Info } from "lucide-react";
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "./ui/tooltip";

export const TOOLTIPS = {
  ctr: "CTR (Click-Through Rate) = clicks / impresiones × 100. Indica la relevancia del anuncio.",
  cpc: "CPC (Coste por clic) = gasto / clicks. Tu coste medio por cada clic.",
  acos: "ACoS = gasto / ventas × 100. Porcentaje de tus ventas publicitarias que se destina a publicidad.",
  roas: "ROAS = ventas / gasto. Cuántos dólares genera cada dólar invertido en ads.",
  cvr: "Tasa de conversión = pedidos / clicks × 100. Cuántos clicks acaban en venta.",
  pe: "ACoS de Equilibrio: tu límite máximo de gasto en Ads por venta. Si lo superas pierdes dinero. Sirve para fijar pujas y filtrar keywords no rentables.",
  acos_siguiente:
    "Simula qué ACoS tendrías si el próximo click acaba en compra. Si vuelve a estar por debajo del PE, la keyword es recuperable y conviene esperar. Si no, baja la puja o pausa.",
  beneficio_ahora: "Beneficio actual = ventas − gasto. Cuánto te queda después de pagar publicidad (sin considerar costes del producto).",
  beneficio_siguiente: "Beneficio si la siguiente venta se produce = (pedidos+1) × precio − (gasto + CPC).",
  badge_bajo_pe: "La keyword está por debajo de tu ACoS de Equilibrio: genera beneficio. Considera escalar la puja.",
  badge_recuperable: "ACoS actual por encima del PE pero el siguiente click con venta volvería al equilibrio. Vale la pena esperar 1-2 ciclos.",
  badge_en_perdida: "ACoS por encima del PE y el siguiente click no lo recupera. Baja la puja o pausa la keyword.",
  badge_sin_datos: "Faltan datos para calcular ACoS (necesitas precio del libro y regalías por venta).",
  lanzamiento: "Fase de Lanzamiento: ACoS objetivo ≈ 1.7 × PE. Prioridad: visibilidad e historial.",
  dominio: "Fase de Dominio: ACoS objetivo ≈ 1.2 × PE. Prioridad: posición en keywords principales.",
  beneficio_fase: "Fase de Beneficio: ACoS objetivo ≈ 0.5 × PE. Prioridad: rentabilidad máxima.",
  suggest_negative:
    "Sugerencia de keyword negativa: recibió ≥6 clicks pero 0 ventas. Agrégala como negativa exacta para evitar gasto irrelevante.",

  // ---- KDP Economy (/book) ----
  marketplace: "Marketplace de Amazon donde se vende el libro. Determina divisa, IVA, tasas de impresión y CPC medio del nicho. Cámbialo si vendes en varios países.",
  formato: "Formato del libro: eBook (Kindle) o impresión bajo demanda (paperback/hardcover). Cambia el cálculo de regalías y costes.",
  tipo_impresion: "Tipo de impresión: blanco y negro, color estándar o color premium. Afecta al coste de impresión por copia.",
  pages: "Número de páginas del libro. Determina el coste de impresión y el peso del cálculo de regalía neta.",
  pvp: "Precio de venta al público (PVP) del libro en este marketplace, con IVA incluido donde aplique.",
  regalia_neta: "Lo que realmente cobras por cada venta, tras restar comisión Amazon, coste de impresión, delivery e IVA. Es la base para saber cuánto puedes gastar en Ads sin perder dinero.",
  acos_eq: "Tu límite máximo de gasto en Ads por venta. Si lo superas, esa venta pierde dinero. Úsalo como techo al fijar pujas y al evaluar keywords.",
  cpc_referencia: "CPC medio estimado del nicho. Se usa cuando aún no tienes CPC real propio. Ayuda a estimar consumo PE en keywords nuevas; ajústalo cuando tengas más datos.",
  clicks_pe: "Cuántos clicks puede permitirse el libro sin venta antes de quedar en pérdida. Si una keyword supera estos clicks sin pedidos, está consumiendo margen futuro: revisa puja o pausa.",
  score_economico: "Puntuación global de viabilidad económica del libro (margen × precio × competencia). Verde = configuración rentable; rojo = ajusta precio o costes antes de invertir en Ads.",
  pvp_minimo: "Precio mínimo que asegura tu margen objetivo con los costes actuales. Por debajo no compensa publicar; por encima, mejor margen pero menos competitividad.",

  // ---- Keywords table & engine badges ----
  cpc_real: "Coste medio real de cada clic en esta keyword (gasto / clicks). Si no hay clicks suficientes se usa el CPC de referencia. Cuanto más alto, antes consumes margen.",
  consumo_pe: "Cuánto margen económico puro ha consumido este término. Si supera 100% ya ha gastado más de lo que el libro puede soportar en equilibrio: baja puja o evalúa pausar.",
  consumo_fase: "Igual que Consumo PE pero ajustado a la fase actual (Lanzamiento, Dominio, Beneficio). Es la métrica que el motor usa para sus recomendaciones diarias.",
  beneficio_kdp: "Beneficio estimado = pedidos × regalía neta − gasto en Ads. Más fiable que ventas − gasto porque considera la regalía real. Negativo = la keyword pierde dinero.",
  relevance: "Etiqueta manual de si la keyword encaja con tu libro. Alta = mantener aunque cueste; Baja = más probable de pausar/negativizar. Afecta a la severidad de las recomendaciones.",
  engine_badge: "Recomendación calculada por el motor (Bajar puja, Mantener, Pausar...). Read-only: nunca aplica cambios solo. Clic para abrir todas las acciones de ese tipo en /acciones.",
  legacy_negative_badge: "Regla antigua: ≥6 clicks y 0 ventas. Solo se muestra cuando no hay economía configurada. El motor moderno es más preciso porque considera margen, fase y recuperabilidad.",
  acos_siguiente_con_venta:
    "Qué ACoS tendrías si el próximo click cierra venta. Por debajo del PE = recuperable, mantén o sube; por encima = no recuperable, baja puja o pausa.",

  // ---- Engine recommendation panel ----
  contexto_kdp: "Datos económicos del libro aplicados al término: regalía neta, ACoS PE, multiplicador de fase. Sirve para entender por qué el motor recomienda lo que recomienda.",
  recomendacion_motor: "Acción sugerida por el motor para esta keyword. Read-only: tú decides si aplicarla. Cada recomendación va con confianza, riesgo y razón explícita.",
  rec_priority: "Cuán urgente es atender esta recomendación. Alta = pérdida activa o gasto fuera de control; trátala primero. Baja = vigilancia.",
  rec_confidence: "Cuán seguro está el motor de la sugerencia. Alta = datos suficientes y CPC real; Baja = pocos clicks o CPC estimado, conviene esperar más datos.",
  rec_risk: "Probabilidad de aplicar la acción y arrepentirse. Alto = puede pausar una keyword que podría recuperarse; revísala antes de actuar.",

  // ---- /acciones page ----
  acciones_total: "Total de recomendaciones generadas por el motor para este dataset.",
  acciones_high: "Recomendaciones de prioridad alta: tratar primero, suelen implicar pérdida activa.",
  acciones_medium: "Recomendaciones de prioridad media: revisar tras las altas.",
  acciones_low: "Recomendaciones de prioridad baja: vigilancia o esperar datos.",
  action_type: "Tipo de acción que sugiere el motor: bajar puja, escalar, mantener, pausar... Clic en un chip para filtrar la tabla por ese tipo.",
  only_with_orders: "Mostrar solo términos que tengan al menos un pedido registrado.",
  only_negative_profit: "Mostrar solo términos cuyo beneficio KDP estimado sea negativo.",
  export_actions: "Descarga las acciones visibles según los filtros actuales en CSV informativo. Útil para trabajar en Excel; no es un archivo listo para subir a Amazon Ads.",

  // ---- Import ----
  import_window: "Para obtener recomendaciones fiables, usa una ventana con suficientes clicks y gasto. Con pocos datos, el motor recomendará esperar.",
  import_file_type: "Archivos esperados: CSV o XLSX exportados desde Amazon Ads (Search Terms Report), Helium10 o Publisher Rocket.",
};

export function InfoTooltip({ content, className = "" }) {
  const text = typeof content === "string" ? TOOLTIPS[content] || content : content;
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={`inline-flex items-center justify-center size-3.5 text-muted-foreground/70 hover:text-coral cursor-help ${className}`}
            data-testid="info-tooltip"
          >
            <Info className="size-3.5" />
          </span>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          className="max-w-xs text-xs leading-relaxed bg-foreground text-background border-none"
        >
          {text}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
