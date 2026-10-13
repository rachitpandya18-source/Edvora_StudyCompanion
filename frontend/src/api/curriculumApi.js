import { apiFetch } from './client.js';

export async function getCurriculum(courseId) {
  return await apiFetch(`/courses/${courseId}/curriculum`, {
    method: 'GET',
  });
}

export async function getCurriculumStatus(courseId) {
  return await apiFetch(`/courses/${courseId}/curriculum/status`, {
    method: 'GET',
  });
}

export async function generateCurriculum(courseId, { mode = 'replace', max_topics = 5, concepts_per_topic = 4 } = {}) {
  return await apiFetch(`/courses/${courseId}/curriculum/generate`, {
    method: 'POST',
    body: {
      mode,
      max_topics,
      concepts_per_topic,
    },
  });
}

export async function getStudyPlan(courseId) {
  return await apiFetch(`/courses/${courseId}/study-plan`, {
    method: 'GET',
  });
}

export async function getStudyNext(courseId) {
  return await apiFetch(`/courses/${courseId}/study-next`, {
    method: 'GET',
  });
}

export default {
  getCurriculum,
  getCurriculumStatus,
  generateCurriculum,
  getStudyPlan,
  getStudyNext,
};

