import { apiFetch } from './client.js';

export async function listCourses(skip = 0, limit = 100) {
  return await apiFetch(`/courses?skip=${skip}&limit=${limit}`, {
    method: 'GET',
  });
}

export async function getCourse(courseId) {
  return await apiFetch(`/courses/${courseId}`, {
    method: 'GET',
  });
}

export async function createCourse({ title, description }) {
  return await apiFetch('/courses', {
    method: 'POST',
    body: { title, description },
  });
}

export async function updateCourse(courseId, { title, description }) {
  return await apiFetch(`/courses/${courseId}`, {
    method: 'PUT',
    body: { title, description },
  });
}

export async function deleteCourse(courseId) {
  return await apiFetch(`/courses/${courseId}`, {
    method: 'DELETE',
  });
}

export async function uploadMaterial(courseId, file) {
  const formData = new FormData();
  formData.append('file', file);
  return await apiFetch(`/courses/${courseId}/materials/upload`, {
    method: 'POST',
    body: formData,
  });
}

export async function listSources(courseId) {
  return await apiFetch(`/courses/${courseId}/sources`, {
    method: 'GET',
  });
}

export async function listContentUnits(courseId, skip = 0, limit = 100) {
  return await apiFetch(`/courses/${courseId}/content-units?skip=${skip}&limit=${limit}`, {
    method: 'GET',
  });
}

export function getMaterialDownloadUrl(courseId, sourceId) {
  return `/courses/${courseId}/materials/${sourceId}/download`;
}

export async function downloadMaterial(courseId, sourceId) {
  return await apiFetch(`/courses/${courseId}/materials/${sourceId}/download`, {
    method: 'GET',
  });
}

export default {
  listCourses,
  getCourse,
  createCourse,
  updateCourse,
  deleteCourse,
  uploadMaterial,
  listSources,
  listContentUnits,
  getMaterialDownloadUrl,
  downloadMaterial,
};

