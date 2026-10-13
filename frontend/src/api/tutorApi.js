import { apiFetch } from './client.js';

export async function listThreads(courseId) {
  return await apiFetch(`/courses/${courseId}/tutor/threads`, {
    method: 'GET',
  });
}

export async function getThread(courseId, threadId) {
  return await apiFetch(`/courses/${courseId}/tutor/threads/${threadId}`, {
    method: 'GET',
  });
}

export async function createThread(courseId, { title = 'New Study Session' } = {}) {
  return await apiFetch(`/courses/${courseId}/tutor/threads`, {
    method: 'POST',
    body: { title },
  });
}

export async function deleteThread(courseId, threadId) {
  return await apiFetch(`/courses/${courseId}/tutor/threads/${threadId}`, {
    method: 'DELETE',
  });
}

export async function postMessage(courseId, threadId, { question, top_k = 3, source_id = null }) {
  return await apiFetch(`/courses/${courseId}/tutor/threads/${threadId}/messages`, {
    method: 'POST',
    body: {
      question,
      top_k,
      source_id,
    },
  });
}

export async function askDirect(courseId, { question, top_k = 3, source_id = null }) {
  return await apiFetch(`/courses/${courseId}/tutor/ask`, {
    method: 'POST',
    body: {
      question,
      top_k,
      source_id,
    },
  });
}

export default {
  listThreads,
  getThread,
  createThread,
  deleteThread,
  postMessage,
  askDirect,
};

