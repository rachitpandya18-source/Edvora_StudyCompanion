import { apiFetch, setStoredToken, setStoredUser, clearAuthSession } from './client.js';

export async function register({ email, username, password, full_name }) {
  const result = await apiFetch('/auth/register', {
    method: 'POST',
    body: { email, username, password, full_name },
  });
  if (result.access_token) {
    setStoredToken(result.access_token);
  }
  if (result.user) {
    setStoredUser(result.user);
  }
  return result;
}

export async function login({ username_or_email, password }) {
  const result = await apiFetch('/auth/login', {
    method: 'POST',
    body: { username_or_email, password },
  });
  if (result.access_token) {
    setStoredToken(result.access_token);
  }
  if (result.user) {
    setStoredUser(result.user);
  }
  return result;
}

export async function getMe() {
  return await apiFetch('/auth/me', {
    method: 'GET',
  });
}

export function logout() {
  clearAuthSession();
}

export default {
  register,
  login,
  getMe,
  logout,
};

