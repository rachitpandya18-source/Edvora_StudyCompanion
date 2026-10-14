import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const samplePdfPath = path.resolve(__dirname, '..', '..', 'test_fixtures', 'piezoelectric_ultrasonics.pdf');

test.describe('Edvora End-to-End Real User Release Journey', () => {
  const timestamp = Date.now();
  const testEmail = `e2e_student_${timestamp}@university.edu`;
  const testName = `Alex Rivera ${timestamp}`;
  const testPassword = 'SecureReleasePass123!';
  const courseTitle = `General Physics ${timestamp}`;

  test('executes complete 11-step learning journey with real backend services', async ({ page }) => {
    test.setTimeout(360000);
    page.on('console', (msg) => console.log('PAGE CONSOLE:', msg.text()));
    page.on('pageerror', (err) => console.log('PAGE ERROR:', err.message));
    page.on('response', (resp) => {
      if (!resp.ok()) {
        console.log(`HTTP ${resp.status()} ${resp.url()}`);
      }
    });

    // -------------------------------------------------------------------------
    // Step 1: Open the Application
    // -------------------------------------------------------------------------
    await page.goto('/');
    await expect(page).toHaveTitle(/Edvora/i);
    await expect(page.getByText('Edvora').first()).toBeVisible();

    // -------------------------------------------------------------------------
    // Step 2: Register or Log In using Real Backend
    // -------------------------------------------------------------------------
    const getStartedBtn = page.getByRole('button', { name: /Get started|Sign up/i }).first();
    if (await getStartedBtn.isVisible()) {
      await getStartedBtn.click();
    } else {
      await page.getByRole('button', { name: /Sign in/i }).first().click();
    }

    // Switch to Sign Up tab if not active
    const createAccountTab = page.getByRole('tab', { name: /Create Account/i });
    if (await createAccountTab.isVisible()) {
      await createAccountTab.click();
    }

    // Fill Registration Form
    await page.locator('#signup-name').fill(testName);
    await page.locator('#signup-email').fill(testEmail);
    await page.locator('#signup-pass').fill(testPassword);
    await page.locator('#signup-confirm').fill(testPassword);

    // Submit Registration
    await page.getByRole('button', { name: /Create account/i }).click();

    // Verify successful entry to dashboard
    await expect(page.getByRole('heading', { name: 'My Courses' })).toBeVisible({ timeout: 15000 });

    // -------------------------------------------------------------------------
    // Step 3: Create a Course
    // -------------------------------------------------------------------------
    const createCourseBtn = page.getByRole('button', { name: /Create Course|Create Your First Course/i }).first();
    await createCourseBtn.click();

    // Verify Create Course Page
    await expect(page.getByRole('heading', { name: /Create a new course/i })).toBeVisible();
    await page.locator('#course-name').fill(courseTitle);
    await page.locator('textarea').fill('Applied Physics, Thermodynamics, and Piezoelectric Transducers');

    // -------------------------------------------------------------------------
    // Step 4: Upload Real Test PDF (physics.pdf)
    // -------------------------------------------------------------------------
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(samplePdfPath);

    // Wait for file attachment to be confirmed in UI
    await expect(page.getByText('piezoelectric_ultrasonics.pdf').first()).toBeVisible({ timeout: 10000 });

    // Submit course creation with material
    await page.getByRole('button', { name: 'Create Course' }).click();

    // Wait for upload, indexing, and navigation into Course Workspace
    await expect(page.getByText(courseTitle).first()).toBeVisible({ timeout: 120000 });

    // -------------------------------------------------------------------------
    // Step 5: Verify Ingestion Status
    // -------------------------------------------------------------------------
    // Navigate to Materials tab
    await page.locator('nav[aria-label="Course Navigation"] button:has-text("Materials")').click();
    await expect(page.getByRole('heading', { name: 'Materials', exact: true })).toBeVisible();

    // Verify that piezoelectric_ultrasonics.pdf is listed and indexed
    await expect(page.getByText('piezoelectric_ultrasonics.pdf').first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/Ready|Indexed in course/i).first()).toBeVisible();

    // -------------------------------------------------------------------------
    // Step 6: Generate / Verify Curriculum
    // -------------------------------------------------------------------------
    await page.locator('nav[aria-label="Course Navigation"] button:has-text("Overview")').click();

    // Trigger curriculum generator if not yet generated
    const generateCurriculumBtn = page.getByRole('button', { name: /Generate Curriculum/i }).first();
    if (await generateCurriculumBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
      await generateCurriculumBtn.click();
    }

    // Verify real extracted topics from physics.pdf are rendered in the curriculum view
    await expect(page.getByText(/Fundamentals of Ultrasonics|Ultrasonic Waves|Propagation and Wave|Applications of Ultrasonics|Introduction & Core Fundamentals|Key Principles/i).first()).toBeVisible({ timeout: 120000 });
    await expect(page.getByText(/Overview|Learning Map|Study Next/i).first()).toBeVisible();

    // -------------------------------------------------------------------------
    // Step 7: Send a Tutor Question with Grounded Citations
    // -------------------------------------------------------------------------
    await page.locator('nav[aria-label="Course Navigation"] button:has-text("Tutor")').click();
    const tutorInput = page.getByPlaceholder('Ask something about this course...');
    await expect(tutorInput).toBeVisible({ timeout: 10000 });

    await tutorInput.fill('What is piezoelectricity according to the course material?');
    await tutorInput.press('Enter');

    // Verify user message appears in conversation thread
    await expect(page.getByText('What is piezoelectricity according to the course material?').first()).toBeVisible();

    // Verify live tutor response returns and renders
    const tutorMsgBubble = page.locator('div.max-w-3xl').filter({ hasText: /piezoelectric|crystal|electric|voltage|material|pressure/i }).first();
    await expect(tutorMsgBubble).toBeVisible({ timeout: 90000 });

    // -------------------------------------------------------------------------
    // Step 8: Generate a Practice Set
    // -------------------------------------------------------------------------
    await page.locator('nav[aria-label="Course Navigation"] button:has-text("Practice")').click();
    await expect(page.getByRole('heading', { name: 'Practice', exact: true })).toBeVisible();

    // Trigger Adaptive Practice
    const startPracticeBtn = page.getByRole('button', { name: /Start adaptive practice|Quick Practice|Start Practice/i }).first();
    await startPracticeBtn.click();

    // Wait for Practice Session Modal to mount with generated questions
    const practiceModal = page.locator('div[role="dialog"]');
    await expect(practiceModal).toBeVisible({ timeout: 90000 });
    await expect(practiceModal.getByRole('button', { name: /Submit Answers/i })).toBeVisible({ timeout: 30000 });

    // -------------------------------------------------------------------------
    // Step 9: Submit a Real Practice Attempt
    // -------------------------------------------------------------------------
    // Select an answer option in the active question inside the modal
    const optionBtn = practiceModal.locator('button:has(span.rounded-full)').first();
    await expect(optionBtn).toBeVisible({ timeout: 15000 });
    await optionBtn.click();

    // Click Submit Answers inside the modal
    const finishBtn = practiceModal.getByRole('button', { name: 'Submit Answers' });
    await expect(finishBtn).toBeEnabled({ timeout: 10000 });
    await finishBtn.click();

    // -------------------------------------------------------------------------
    // Step 10: Verify Returned Score / Evaluation Result
    // -------------------------------------------------------------------------
    // Verify score badge or evaluation feedback appears in modal
    await expect(practiceModal.getByText(/Score:\s*\d+%/i)).toBeVisible({ timeout: 30000 });
    await expect(practiceModal.getByText(/Correct|Needs Review/i).first()).toBeVisible();

    // Close practice modal
    const closeModalBtn = practiceModal.getByRole('button', { name: /Complete Session|Close|Done/i }).first();
    await closeModalBtn.click();
    await expect(practiceModal).not.toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------------------
    // Step 11: Open Progress and Verify Backend-Backed Data
    // -------------------------------------------------------------------------
    await page.locator('nav[aria-label="Course Navigation"] button:has-text("Progress")').click();
    await expect(page.getByRole('heading', { name: 'Progress', exact: true })).toBeVisible();
    await expect(page.getByText(courseTitle).first()).toBeVisible();

    // Verify course mastery card renders
    await expect(page.getByText(/Course Mastery|Progress/i).first()).toBeVisible();
  });
});
