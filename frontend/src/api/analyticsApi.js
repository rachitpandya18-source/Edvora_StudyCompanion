import { apiFetch } from './client.js';

export async function getOverview(courseId, { trendDays = 30 } = {}) {
  return await apiFetch(`/courses/${courseId}/analytics/overview?trend_days=${trendDays}`, {
    method: 'GET',
  });
}

export async function getTopicAnalytics(courseId, topicId) {
  return await apiFetch(`/courses/${courseId}/topics/${topicId}/analytics`, {
    method: 'GET',
  });
}

export async function getTrends(courseId, { days = 30 } = {}) {
  return await apiFetch(`/courses/${courseId}/analytics/trends?days=${days}`, {
    method: 'GET',
  });
}

export default {
  getOverview,
  getTopicAnalytics,
  getTrends,
};

