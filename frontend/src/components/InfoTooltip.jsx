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
