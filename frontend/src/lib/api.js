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
export const getSearchTerms = (id) => api.get(`/datasets/${id}/search-terms`);
export const getTimeseries = (id) => api.get(`/datasets/${id}/timeseries`);
export const getAiRecs = (id) => api.post(`/datasets/${id}/ai-recommendations`);
export const getKeywordsUnified = (id) => api.get(`/datasets/${id}/keywords-unified`);
export const updateBook = (id, payload) => api.put(`/datasets/${id}/book`, payload);

// Keywords overrides (inline edit / manual add)
export const upsertKeyword = (id, payload) => api.put(`/datasets/${id}/keyword`, payload);
export const deleteKeywordOverride = (id, term) =>
  api.delete(`/datasets/${id}/keyword/${encodeURIComponent(term)}`);

// Campaign wizard
export const createCampaign = (id, payload) => api.post(`/datasets/${id}/campaign`, payload);

// Snapshots & detail
export const snapshotAll = (id) => api.post(`/datasets/${id}/snapshot-all`);
export const getSnapshots = (id, term) =>
  api.get(`/datasets/${id}/snapshots/${encodeURIComponent(term)}`);
export const getKeywordDetail = (id, term) =>
  api.get(`/datasets/${id}/keyword-detail`, { params: { term } });

// Campaign plans
export const listPlans = (id) => api.get(`/datasets/${id}/plans`);
export const createPlan = (id, payload) => api.post(`/datasets/${id}/plans`, payload);
export const updatePlan = (id, planId, payload) =>
  api.put(`/datasets/${id}/plans/${planId}`, payload);
export const deletePlan = (id, planId) =>
  api.delete(`/datasets/${id}/plans/${planId}`);
export const getPlanSummary = (id, planId) =>
  api.get(`/datasets/${id}/plans/${planId}/summary`);

export const exportNegativesUrl = (id, minClicks = 6) =>
  `${API}/datasets/${id}/export/negatives?min_clicks=${minClicks}`;

// Autopilot + niche import + compare
export const getAutopilot = (id, phase = "dominio") =>
  api.get(`/datasets/${id}/autopilot`, { params: { phase } });
export const exportAutopilotUrl = (id) => `${API}/datasets/${id}/export/autopilot`;
export const importNiche = (id, file) => {
  const fd = new FormData();
  fd.append("file", file);
  return api.post(`/datasets/${id}/import-niche`, fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
export const compareDatasets = (id, otherId) =>
  api.get(`/datasets/${id}/compare/${otherId}`);
