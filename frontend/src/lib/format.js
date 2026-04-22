export const MARKETPLACES = [
  { id: "us", name: "Estados Unidos", flag: "🇺🇸", currency: "USD", symbol: "$" },
  { id: "ca", name: "Canadá", flag: "🇨🇦", currency: "CAD", symbol: "CA$" },
  { id: "uk", name: "Reino Unido", flag: "🇬🇧", currency: "GBP", symbol: "£" },
  { id: "es", name: "España", flag: "🇪🇸", currency: "EUR", symbol: "€" },
  { id: "de", name: "Alemania", flag: "🇩🇪", currency: "EUR", symbol: "€" },
  { id: "fr", name: "Francia", flag: "🇫🇷", currency: "EUR", symbol: "€" },
  { id: "it", name: "Italia", flag: "🇮🇹", currency: "EUR", symbol: "€" },
  { id: "mx", name: "México", flag: "🇲🇽", currency: "MXN", symbol: "MX$" },
  { id: "jp", name: "Japón", flag: "🇯🇵", currency: "JPY", symbol: "¥" },
  { id: "au", name: "Australia", flag: "🇦🇺", currency: "AUD", symbol: "A$" },
];

export const getMarketplace = (id) =>
  MARKETPLACES.find((m) => m.id === id) || MARKETPLACES[0];

export const fmtInt = (n) =>
  new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0 }).format(n || 0);
export const fmtNum = (n, d = 2) =>
  new Intl.NumberFormat("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d }).format(n || 0);
export const fmtPct = (n) => `${fmtNum(n, 2)}%`;
export const fmtMoney = (n, symbol = "$") => `${symbol}${fmtNum(n, 2)}`;

export const REPORT_LABELS = {
  search_term: "Search Term",
  campaign: "Campaign",
  placement: "Placement",
  unknown: "Desconocido",
};
