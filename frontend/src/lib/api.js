import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;
export const api = axios.create({ baseURL: API });

export const uploadCsv = (file, marketplace, name) => {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("marketplace", marketplace);
  if (name) fd.append("dataset_name", name);
  return api.post("/imports/upload", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const listDatasets = (marketplace) =>
  api.get("/datasets", { params: marketplace ? { marketplace } : {} });
export const getDataset = (id) => api.get(`/datasets/${id}`);
export const deleteDataset = (id) => api.delete(`/datasets/${id}`);
export const getCampaigns = (id) => api.get(`/datasets/${id}/campaigns`);
export const getCampaignsList = (id) => api.get(`/datasets/${id}/campaigns-list`);
export const getSearchTerms = (id) => api.get(`/datasets/${id}/search-terms`);
export const getTimeseries = (id) => api.get(`/datasets/${id}/timeseries`);
export const getAiRecs = (id) => api.post(`/datasets/${id}/ai-recommendations`);
export const getKeywordsUnified = (id) => api.get(`/datasets/${id}/keywords-unified`);
export const updateBook = (id, payload) => api.put(`/datasets/${id}/book`, payload);
export const setPhase = (id, phase) => api.put(`/datasets/${id}/phase`, { phase });

export const upsertKeyword = (id, payload) => api.put(`/datasets/${id}/keyword`, payload);
export const deleteKeywordOverride = (id, term) =>
  api.delete(`/datasets/${id}/keyword/${encodeURIComponent(term)}`);

export const createCampaign = (id, payload) => api.post(`/datasets/${id}/campaign`, payload);

export const snapshotAll = (id) => api.post(`/datasets/${id}/snapshot-all`);
export const getSnapshots = (id, term) =>
  api.get(`/datasets/${id}/snapshots/${encodeURIComponent(term)}`);
export const getKeywordDetail = (id, term) =>
  api.get(`/datasets/${id}/keyword-detail`, { params: { term } });

export const getMarketCriteria = (id, mp) =>
  api.get(`/datasets/${id}/market-criteria/${mp}`);
export const putMarketCriteria = (id, mp, payload) =>
  api.put(`/datasets/${id}/market-criteria/${mp}`, payload);
export const resetMarketCriteria = (id, mp) =>
  api.delete(`/datasets/${id}/market-criteria/${mp}`);

export const backupUrl = (id) => `${API}/datasets/${id}/backup`;
export const restoreBackup = (id, file) => {
  const fd = new FormData();
  fd.append("file", file);
  return api.post(`/datasets/${id}/restore`, fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getAutopilot = (id, phase = "dominio") =>
  api.get(`/datasets/${id}/autopilot`, { params: { phase } });
export const exportAutopilotUrl = (id) => `${API}/datasets/${id}/export/autopilot`;
export const exportNegativesUrl = (id, minClicks = 6) =>
  `${API}/datasets/${id}/export/negatives?min_clicks=${minClicks}`;
export const importNiche = (id, file) => {
  const fd = new FormData();
  fd.append("file", file);
  return api.post(`/datasets/${id}/import-niche`, fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
