/**
 * Centralized HTTP API Client for Edvora Study Companion.
 * Uses standard native fetch, attaches auth tokens, handles errors consistently.
 */

function resolveApiBaseUrl() {
  const envUrl = typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL;
  if (envUrl && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  // If no explicit VITE_API_BASE_URL was configured at build time,
  // warn if running on a non-loopback host where localhost:8000 would target the client device.
  if (typeof window !== 'undefined' && window.location && window.location.hostname) {
    const host = window.location.hostname;
    if (host !== 'localhost' && host !== '127.0.0.1' && host !== '0.0.0.0') {
      console.warn(
        `[Edvora API Client] VITE_API_BASE_URL was not set at build time and defaulted to 'http://localhost:8000'. ` +
        `API requests from client origin '${window.location.origin}' will fail unless backend is reachable on client loopback. ` +
        `Set VITE_API_BASE_URL to your backend host.`
      );
    }
  }
  return 'http://localhost:8000';
}

export const API_BASE_URL = resolveApiBaseUrl();
const TOKEN_KEY = 'edvora_auth_token';
const USER_KEY = 'edvora_user';

export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || null;
  } catch {
    return null;
  }
}

export function setStoredToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch (err) {
    console.error('Failed to set stored auth token:', err);
  }
}

export function normalizeUser(rawUser) {
  if (!rawUser) return null;
  const name =
    rawUser.full_name ||
    rawUser.name ||
    rawUser.username ||
    (rawUser.email ? rawUser.email.split('@')[0] : 'Student');
  const initials =
    rawUser.initials ||
    (name
      .split(' ')
      .filter(Boolean)
      .map((n) => n[0])
      .join('')
      .slice(0, 2)
      .toUpperCase() || 'ST');
  return {
    ...rawUser,
    name,
    initials,
  };
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? normalizeUser(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user) {
  try {
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(normalizeUser(user)));
    } else {
      localStorage.removeItem(USER_KEY);
    }
  } catch (err) {
    console.error('Failed to set stored user profile:', err);
  }
}

export function clearAuthSession() {
  setStoredToken(null);
  setStoredUser(null);
}

/**
 * Universal fetch wrapper for Edvora backend.
 */
export async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const headers = new Headers(options.headers || {});

  // Inject Authorization Bearer token if present
  const token = getStoredToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Handle JSON serialization if body is an object and not FormData
  let body = options.body;
  if (body && !(body instanceof FormData) && typeof body === 'object') {
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    body = JSON.stringify(body);
  }

  const fetchOptions = {
    ...options,
    headers,
    body,
  };

  let response;
  try {
    response = await fetch(url, fetchOptions);
  } catch (networkErr) {
    throw new ApiError(
      `Network connection failed: ${networkErr.message || 'Server unavailable'}. Ensure the Edvora backend is running at ${API_BASE_URL}.`,
      0,
      null
    );
  }

  // Attempt to parse JSON response body
  let data = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    try {
      data = await response.text();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    if (data && typeof data === 'object') {
      if (typeof data.detail === 'string') {
        errorDetail = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorDetail = data.detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
      } else if (data.message) {
        errorDetail = data.message;
      }
    } else if (typeof data === 'string' && data.trim()) {
      errorDetail = data.trim();
    }

    if (response.status === 401) {
      clearAuthSession();
    }

    throw new ApiError(errorDetail, response.status, data);
  }

  return data;
}

export default {
  apiFetch,
  getStoredToken,
  setStoredToken,
  getStoredUser,
  setStoredUser,
  clearAuthSession,
  ApiError,
};

