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
