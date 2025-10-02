import axios, { AxiosRequestConfig, AxiosError } from 'axios';

export const api = axios.create({
  baseURL: process.env.EXPO_PUBLIC_BACKEND_URL,
  withCredentials: false,
  headers: {
    accept: 'application/json',
  },
});

export const apiFetchData = async <T = any>(config: AxiosRequestConfig): Promise<T> => {
  try {
    const res = await api.request<T>(config);
    return res.data;
  } catch (e) {
    throw e;
  }
};

export const withPublicAPIToken = async <T = any>(config: AxiosRequestConfig): Promise<T | undefined> => {
  try {
    const res = await apiFetchData<T>(config);
    return res;
  } catch (e) {
    const error = e as AxiosError;
    if (error.name !== 'CanceledError' && error.name !== 'AbortError') {
      throw e;
    }
    return undefined;
  }
};
