import { useEffect, useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, BarChart, Bar, Cell,
} from "recharts";
import { getTimeseries, getCampaigns } from "../lib/api";
import { fmtNum } from "../lib/format";

const baseAxis = {
  tick: { fill: "hsl(var(--muted-foreground))", fontSize: 11, fontFamily: "IBM Plex Mono" },
  axisLine: { stroke: "hsl(var(--border))" },
  tickLine: false,
};

const tooltipStyle = {
  background: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: 2,
  fontSize: 12,
  fontFamily: "IBM Plex Mono",
};

export default function ChartsPanel({ datasetId }) {
  const [series, setSeries] = useState([]);
  const [mode, setMode] = useState("date");
  const [camps, setCamps] = useState([]);

  useEffect(() => {
    if (!datasetId) return;
    (async () => {
      try {
        const [ts, cs] = await Promise.all([
          getTimeseries(datasetId),
          getCampaigns(datasetId),
        ]);
        setSeries(ts.data.points || []);
        setMode(ts.data.mode || "date");
        setCamps((cs.data || []).slice(0, 10));
      } catch (e) { /* noop */ }
    })();
  }, [datasetId]);

  return (
    <div className="grid md:grid-cols-2 gap-3" data-testid="charts-panel">
      <div className="border border-border p-4 rounded-sm bg-card">
        <div className="flex items-baseline justify-between mb-3">
          <h3 className="text-sm font-semibold">Gasto vs Ventas</h3>
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
            {mode === "date" ? "por fecha" : "por campaña"}
          </span>
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={series}>
            <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="0" vertical={false} />
            <XAxis dataKey="date" {...baseAxis} />
            <YAxis {...baseAxis} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="linear" dataKey="spend" stroke="hsl(var(--chart-2))" strokeWidth={2} dot={false} name="Gasto" />
            <Line type="linear" dataKey="sales" stroke="hsl(var(--chart-1))" strokeWidth={2} dot={false} name="Ventas" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="border border-border p-4 rounded-sm bg-card">
        <h3 className="text-sm font-semibold mb-3">ACoS por Campaña (Top 10)</h3>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={camps} layout="vertical" margin={{ left: 10 }}>
            <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="0" horizontal={false} />
            <XAxis type="number" {...baseAxis} />
            <YAxis
              dataKey="campaign"
              type="category"
              width={140}
              {...baseAxis}
              tick={{ ...baseAxis.tick, fontSize: 10 }}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(v) => [`${fmtNum(v)}%`, "ACoS"]}
            />
            <Bar dataKey="acos" name="ACoS" radius={0}>
              {camps.map((c, i) => (
                <Cell
                  key={i}
                  fill={
                    c.acos > 50
                      ? "hsl(var(--destructive))"
                      : c.acos > 25
                      ? "hsl(var(--chart-2))"
                      : "hsl(var(--chart-3))"
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
