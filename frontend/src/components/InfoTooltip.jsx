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
  pe: "ACoS de Equilibrio (Punto de Equilibrio) = regalías / precio × 100. Por encima de este valor, pierdes dinero por cada venta publicitaria.",
  acos_siguiente:
    "ACoS del siguiente click = (gasto + CPC) / (ventas + precio) × 100. Simula qué ACoS tendrías si el siguiente click termina en compra. Útil para decidir si seguir invirtiendo en una keyword.",
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
  marketplace: "Marketplace de Amazon donde se vende el libro. Determina divisa, IVA aplicable, tasas de impresión y CPC medio del nicho.",
  formato: "Formato del libro: eBook (Kindle) o impresión bajo demanda (paperback/hardcover). Cambia el cálculo de regalías y costes.",
  tipo_impresion: "Tipo de impresión: blanco y negro, color estándar o color premium. Afecta al coste de impresión por copia.",
  pages: "Número de páginas del libro. Determina el coste de impresión y el peso del cálculo de regalía neta.",
  pvp: "Precio de venta al público (PVP) del libro en este marketplace, con IVA incluido donde aplique.",
  regalia_neta: "Regalía neta por venta: lo que cobras tras restar comisión Amazon, coste de impresión, delivery e IVA si aplica.",
  acos_eq: "ACoS de equilibrio: porcentaje máximo de ventas que puedes gastar en Ads antes de perder dinero con este libro.",
  cpc_referencia: "CPC de referencia del nicho: estimación de cuánto cuesta de media un clic en este marketplace. Se usa cuando aún no tienes CPC real.",
  clicks_pe: "Clicks PE: número aproximado de clicks que el libro puede soportar antes de necesitar una venta para no perder dinero.",
  score_economico: "Score económico: puntuación global del libro según margen, precio y competencia. Verde = económicamente viable.",
  pvp_minimo: "PVP mínimo recomendado para que el libro sea económicamente rentable con este coste de impresión y regalías.",

  // ---- Keywords table & engine badges ----
  cpc_real: "CPC real: gasto / clicks reales de Amazon Ads. Si no hay datos suficientes, se usa el CPC de referencia.",
  consumo_pe: "Consumo PE: porcentaje del margen económico puro que ya ha consumido este término. ≥100% = ya superó el punto de equilibrio.",
  consumo_fase: "Consumo fase: igual que consumo PE pero ajustado por la fase del libro (lanzamiento, dominio, beneficio).",
  beneficio_kdp: "Beneficio KDP: pedidos × regalía neta − gasto publicitario. Estimación más realista que ventas − gasto.",
  relevance: "Relevancia: marcador manual (alta/media/baja) que indica si el término encaja con el libro. Influye en recomendaciones del motor.",
  engine_badge: "Recomendación del motor determinista basada en consumo PE, recuperabilidad, beneficio KDP y relevancia. Read-only.",
  legacy_negative_badge: "Regla legacy: basada solo en clicks y pedidos. El motor de recomendaciones tiene prioridad cuando hay economía configurada.",
  acos_siguiente_con_venta:
    "ACoS si la siguiente venta se produce = (gasto + CPC) / (ventas + PVP) × 100. Indica si la keyword puede recuperarse con una venta más.",

  // ---- Engine recommendation panel ----
  contexto_kdp: "Datos económicos del libro aplicados al término: regalía, ACoS PE, multiplicador de fase, etc.",
  recomendacion_motor: "Recomendación calculada por el motor determinista. No aplica cambios automáticamente — es una sugerencia revisable.",
  rec_priority: "Prioridad: combina urgencia, gasto y desviación frente al equilibrio. Alta exige atención cuanto antes.",
  rec_confidence: "Confianza: cuán seguro está el motor de la recomendación. Baja confianza suele ir asociada a CPC estimado o pocos datos.",
  rec_risk: "Riesgo: probabilidad de aplicar la acción y arrepentirse. Alto riesgo requiere revisión humana antes de actuar.",

  // ---- /acciones page ----
  acciones_total: "Total de recomendaciones generadas por el motor para este dataset.",
  acciones_high: "Recomendaciones de prioridad alta: tratar primero, suelen implicar pérdida activa.",
  acciones_medium: "Recomendaciones de prioridad media: revisar tras las altas.",
  acciones_low: "Recomendaciones de prioridad baja: vigilancia o esperar datos.",
  action_type: "Tipo de acción recomendada: bajar puja, mantener, escalar, pausar, etc.",
  only_with_orders: "Mostrar solo términos que tengan al menos un pedido registrado.",
  only_negative_profit: "Mostrar solo términos cuyo beneficio KDP estimado sea negativo.",
  export_actions: "Exportar vista actual: descarga las acciones visibles con los filtros aplicados en CSV. No es un archivo bulk listo para subir a Amazon Ads.",

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
