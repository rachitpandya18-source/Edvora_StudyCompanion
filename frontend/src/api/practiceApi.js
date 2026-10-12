import { apiFetch } from './client.js';

export async function getPracticeOptions(courseId) {
  return await apiFetch(`/courses/${courseId}/practice/options`, {
    method: 'GET',
  });
}

export async function generatePractice(courseId, payload = {}) {
  return await apiFetch(`/courses/${courseId}/practice/generate`, {
    method: 'POST',
    body: payload,
  });
}

export async function getAssessment(courseId, assessmentId) {
  return await apiFetch(`/courses/${courseId}/assessments/${assessmentId}`, {
    method: 'GET',
  });
}

export async function submitAttempt(courseId, assessmentId, attemptId, answers = []) {
  return await apiFetch(`/courses/${courseId}/assessments/${assessmentId}/attempts/${attemptId}/submit`, {
    method: 'POST',
    body: { answers },
  });
}

export async function listAssessments(courseId) {
  return await apiFetch(`/courses/${courseId}/assessments`, {
    method: 'GET',
  });
}

export default {
  getPracticeOptions,
  generatePractice,
  getAssessment,
  submitAttempt,
  listAssessments,
};

