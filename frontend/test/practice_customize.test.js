import test from 'node:test';
import assert from 'node:assert/strict';

// Test 1: practiceApi.generatePractice sends custom practice payload correctly
test('practiceApi.generatePractice sends custom configuration payload with topics, count, type, and difficulty', async () => {
  let capturedUrl = null;
  let capturedOptions = null;

  globalThis.fetch = async (url, options) => {
    capturedUrl = url;
    capturedOptions = options;
    return {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        assessment_id: 'ass-custom-1',
        attempt_id: 'att-custom-1',
        questions: [
          {
            id: 'q-1',
            prompt: 'Explain the difference between TCP and UDP.',
            question_type: 'short_answer',
            concept_title: 'Transport Layer Protocols',
          },
        ],
      }),
    };
  };

  const { generatePractice } = await import('../src/api/practiceApi.js');

  const customPayload = {
    mode: 'adaptive',
    topic_id: 'topic-uuid-456',
    question_count: 5,
    question_types: ['short_answer'],
    difficulty: 'hard',
  };

  const result = await generatePractice('course-789', customPayload);

  assert.equal(capturedUrl, 'http://localhost:8000/courses/course-789/practice/generate');
  assert.equal(capturedOptions.method, 'POST');
  const parsedBody = JSON.parse(capturedOptions.body);

  assert.equal(parsedBody.mode, 'adaptive');
  assert.equal(parsedBody.topic_id, 'topic-uuid-456');
  assert.equal(parsedBody.question_count, 5);
  assert.deepEqual(parsedBody.question_types, ['short_answer']);
  assert.equal(parsedBody.difficulty, 'hard');

  assert.equal(result.assessment_id, 'ass-custom-1');
  assert.equal(result.questions.length, 1);
});

// Test 2: practiceApi.getPracticeOptions returns topics for active course
test('practiceApi.getPracticeOptions returns topic options and planner focus for active course', async () => {
  let capturedUrl = null;

  globalThis.fetch = async (url) => {
    capturedUrl = url;
    return {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        course_id: 'course-789',
        topics: [
          { id: 'top-1', title: 'Thermodynamics', concept_count: 3 },
          { id: 'top-2', title: 'Kinetics', concept_count: 2 },
        ],
        question_types: [{ value: 'mcq', label: 'Multiple Choice' }],
        difficulties: [{ value: 'medium', label: 'Medium' }],
        recommended_concept_name: 'Gibbs Free Energy',
      }),
    };
  };

  const { getPracticeOptions } = await import('../src/api/practiceApi.js');
  const result = await getPracticeOptions('course-789');

  assert.equal(capturedUrl, 'http://localhost:8000/courses/course-789/practice/options');
  assert.equal(result.course_id, 'course-789');
  assert.equal(result.topics.length, 2);
  assert.equal(result.topics[0].title, 'Thermodynamics');
  assert.equal(result.topics[1].title, 'Kinetics');
});
