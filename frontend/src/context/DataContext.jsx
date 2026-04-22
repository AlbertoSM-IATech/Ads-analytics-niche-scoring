import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { listDatasets, getDataset } from "../lib/api";

const DataCtx = createContext(null);

export const DataProvider = ({ children }) => {
  const [marketplace, setMarketplace] = useState(
    () => localStorage.getItem("marketplace") || "us"
  );
  const [theme, setTheme] = useState(
    () => localStorage.getItem("theme") || "dark"
  );
  const [datasets, setDatasets] = useState([]);
  const [active, setActive] = useState(null); // full dataset
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("marketplace", marketplace);
  }, [marketplace]);

  const refresh = useCallback(async () => {
    const r = await listDatasets();
    setDatasets(r.data || []);
    const stored = localStorage.getItem("active_dataset");
    if (stored && r.data.find((d) => d.id === stored)) {
      await loadActive(stored);
    } else if (r.data?.[0]) {
      await loadActive(r.data[0].id);
    } else {
      setActive(null);
    }
  }, []);

  const loadActive = async (id) => {
    setLoading(true);
    try {
      const r = await getDataset(id);
      setActive(r.data);
      localStorage.setItem("active_dataset", id);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <DataCtx.Provider
      value={{
        marketplace, setMarketplace,
        theme, setTheme,
        datasets, refresh,
        active, loadActive, setActive,
        loading,
      }}
    >
      {children}
    </DataCtx.Provider>
  );
};

export const useData = () => {
  const ctx = useContext(DataCtx);
  if (!ctx) throw new Error("useData must be inside DataProvider");
  return ctx;
};
