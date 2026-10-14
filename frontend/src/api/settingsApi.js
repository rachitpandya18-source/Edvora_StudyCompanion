import { apiFetch } from './client.js';

export async function getSettings() {
  return await apiFetch('/settings', {
    method: 'GET',
  });
}

export async function updateGeminiKey(apiKey) {
  return await apiFetch('/settings/gemini-key', {
    method: 'POST',
    body: { api_key: apiKey },
  });
}

export async function testGeminiConnection() {
  return await apiFetch('/settings/test-gemini', {
    method: 'POST',
  });
}

export default {
  getSettings,
  updateGeminiKey,
  testGeminiConnection,
};
