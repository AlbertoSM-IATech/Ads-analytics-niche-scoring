import {
  PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip,
} from "recharts";

const COLORS = {
  "bajo-pe": "#16A34A",      // green
  "recuperable": "#F59E0B",  // amber
  "en-perdida": "#EF4444",   // red
  "sin-datos": "#737373",    // neutral
};
const LABELS = {
  "bajo-pe": "Bajo PE",
  "recuperable": "Recuperable",
  "en-perdida": "En pérdida",
  "sin-datos": "Sin datos",
};

export default function DistributionChart({ summary }) {
  if (!summary) return null;
  const total = Object.values(summary).reduce((a, b) => a + b, 0);
  if (total === 0) return null;
  const data = Object.entries(summary)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ name: LABELS[k] || k, key: k, value: v }));

  return (
    <div className="border border-border rounded-lg p-5 bg-card" data-testid="distribution-chart">
      <h3 className="text-sm font-semibold mb-3">Distribución de keywords por estado</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            label={({ name, value }) => `${name}: ${value}`}
            labelLine={false}
          >
            {data.map((entry) => (
              <Cell key={entry.key} fill={COLORS[entry.key]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 11 }} />
          <Legend wrapperStyle={{ fontSize: 11 }} iconType="circle" />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
