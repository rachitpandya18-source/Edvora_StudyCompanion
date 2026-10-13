import test from 'node:test';
import assert from 'node:assert/strict';

// Test A: practiceApi.submitAttempt payload structure
test('practiceApi.submitAttempt formats answers array payload correctly', async () => {
  let capturedUrl = null;
  let capturedOptions = null;

  globalThis.fetch = async (url, options) => {
    capturedUrl = url;
    capturedOptions = options;
    return {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        id: 'attempt-1',
        assessment_id: 'ass-1',
        score: 1.0,
        status: 'submitted',
        answers: [],
      }),
    };
  };

  const { submitAttempt } = await import('../src/api/practiceApi.js');
  const dummyAnswers = [
    { question_id: 'q-1', student_answer: 'Option B' },
    { question_id: 'q-2', student_answer: 'True' },
  ];

  const result = await submitAttempt('course-123', 'ass-1', 'att-1', dummyAnswers);

  assert.equal(capturedUrl, 'http://localhost:8000/courses/course-123/assessments/ass-1/attempts/att-1/submit');
  assert.equal(capturedOptions.method, 'POST');
  const parsedBody = JSON.parse(capturedOptions.body);
  assert.deepEqual(parsedBody, { answers: dummyAnswers });
  assert.equal(result.status, 'submitted');
});

// Test B: coursesApi.listCourses calls endpoint with query params
test('coursesApi.listCourses calls endpoint with query params', async () => {
  let capturedUrl = null;

  globalThis.fetch = async (url) => {
    capturedUrl = url;
    return {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        items: [
          { id: 'c-1', title: 'Data Structures' },
        ],
        total: 1,
      }),
    };
  };

  const { listCourses } = await import('../src/api/coursesApi.js');
  const result = await listCourses(0, 10);

  assert.equal(capturedUrl, 'http://localhost:8000/courses?skip=0&limit=10');
  assert.equal(result.total, 1);
  assert.equal(result.items[0].id, 'c-1');
});

// Test C: client apiFetch attaches Bearer token when present in storage
test('client apiFetch injects Authorization Bearer header from stored token', async () => {
  let capturedHeaders = null;

  globalThis.fetch = async (url, options) => {
    capturedHeaders = options.headers;
    return {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ ok: true }),
    };
  };

  const { apiFetch, setStoredToken, clearAuthSession } = await import('../src/api/client.js');
  // Mock localStorage for node environment
  globalThis.localStorage = {
    _data: {},
    getItem(k) { return this._data[k] || null; },
    setItem(k, v) { this._data[k] = String(v); },
    removeItem(k) { delete this._data[k]; },
  };

  setStoredToken('test-jwt-token-xyz');
  await apiFetch('/test-protected');

  assert.equal(capturedHeaders.get('Authorization'), 'Bearer test-jwt-token-xyz');
  clearAuthSession();
});

// Test D: client apiFetch handles empty responses
test('client apiFetch handles empty response gracefully', async () => {
  globalThis.fetch = async () => {
    return {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ items: [] }),
    };
  };

  const { apiFetch } = await import('../src/api/client.js');
  const result = await apiFetch('/courses');
  assert.deepEqual(result, { items: [] });
});

// Test E: curriculumApi.generateCurriculum sends concepts_per_topic matching backend schema
test('curriculumApi.generateCurriculum formats concepts_per_topic payload correctly', async () => {
  let capturedUrl = null;
  let capturedOptions = null;

  globalThis.fetch = async (url, options) => {
    capturedUrl = url;
    capturedOptions = options;
    return {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        course_id: 'c-100',
        topics: [],
        concepts: [],
        edges: [],
      }),
    };
  };

  const { generateCurriculum } = await import('../src/api/curriculumApi.js');
  const result = await generateCurriculum('c-100', {
    mode: 'replace',
    max_topics: 4,
    concepts_per_topic: 3,
  });

  assert.equal(capturedUrl, 'http://localhost:8000/courses/c-100/curriculum/generate');
  assert.equal(capturedOptions.method, 'POST');
  const parsedBody = JSON.parse(capturedOptions.body);
  assert.equal(parsedBody.mode, 'replace');
  assert.equal(parsedBody.max_topics, 4);
  assert.equal(parsedBody.concepts_per_topic, 3);
  assert.equal(parsedBody.max_concepts_per_topic, undefined);
  assert.equal(result.course_id, 'c-100');
});
