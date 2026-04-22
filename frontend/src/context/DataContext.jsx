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
  const [datasets, setDatasets] = useState([]);       // ALL datasets (any mp)
  const [active, setActive] = useState(null);          // full dataset
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("marketplace", marketplace);
  }, [marketplace]);

  const loadActive = useCallback(async (id) => {
    setLoading(true);
    try {
      const r = await getDataset(id);
      setActive(r.data);
      localStorage.setItem("active_dataset", id);
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    const r = await listDatasets();
    const all = r.data || [];
    setDatasets(all);
    // Filter for the current marketplace
    const forMp = all.filter((d) => d.marketplace === marketplace);
    const stored = localStorage.getItem("active_dataset");
    if (stored && forMp.find((d) => d.id === stored)) {
      await loadActive(stored);
    } else if (forMp[0]) {
      await loadActive(forMp[0].id);
    } else {
      setActive(null);
      localStorage.removeItem("active_dataset");
    }
  }, [marketplace, loadActive]);

  useEffect(() => { refresh(); }, [refresh]);

  // Datasets filtered by current marketplace
  const datasetsForMp = datasets.filter((d) => d.marketplace === marketplace);

  return (
    <DataCtx.Provider
      value={{
        marketplace, setMarketplace,
        theme, setTheme,
        datasets,           // all
        datasetsForMp,      // only current marketplace
        refresh,
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
