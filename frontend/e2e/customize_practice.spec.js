import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const samplePdfPath = path.resolve(__dirname, '..', '..', 'test_fixtures', 'piezoelectric_ultrasonics.pdf');

test.describe('Customize Practice Modal E2E Flow', () => {
  const timestamp = Date.now();
  const testEmail = `cust_student_${timestamp}@university.edu`;
  const testName = `Student ${timestamp}`;
  const testPassword = 'SecureReleasePass123!';
  const courseTitle = `Customize Course ${timestamp}`;

  test('verifies "Customize your practice" button opens modal, closes on cancel, and generates custom session', async ({ page }) => {
    test.setTimeout(360000);

    // 1. Open app and register
    await page.goto('/');
    const getStartedBtn = page.getByRole('button', { name: /Get started|Sign up/i }).first();
    if (await getStartedBtn.isVisible()) {
      await getStartedBtn.click();
    } else {
      await page.getByRole('button', { name: /Sign in/i }).first().click();
    }

    const createAccountTab = page.getByRole('tab', { name: /Create Account/i });
    if (await createAccountTab.isVisible()) {
      await createAccountTab.click();
    }

    await page.locator('#signup-name').fill(testName);
    await page.locator('#signup-email').fill(testEmail);
    await page.locator('#signup-pass').fill(testPassword);
    await page.locator('#signup-confirm').fill(testPassword);
    await page.getByRole('button', { name: /Create account/i }).click();

    await expect(page.getByRole('heading', { name: 'My Courses' })).toBeVisible({ timeout: 15000 });

    // 2. Create Course with PDF Material
    const createCourseBtn = page.getByRole('button', { name: /Create Course|Create Your First Course/i }).first();
    await createCourseBtn.click();

    await expect(page.getByRole('heading', { name: /Create a new course/i })).toBeVisible();
    await page.locator('#course-name').fill(courseTitle);
    await page.locator('textarea').fill('Acoustics and ultrasonic wave transducers.');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(samplePdfPath);
    await expect(page.getByText('piezoelectric_ultrasonics.pdf').first()).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: 'Create Course' }).click();
    await expect(page.getByText(courseTitle).first()).toBeVisible({ timeout: 120000 });

    // 3. Navigate directly to Practice Page
    await page.locator('nav[aria-label="Course Navigation"] button:has-text("Practice")').click();
    await expect(page.getByRole('heading', { name: 'Practice', exact: true })).toBeVisible();

    // 4. Verify "Want something specific?" CTA section
    await expect(page.getByText('Want something specific?')).toBeVisible();
    const customizeBtn = page.getByRole('button', { name: /Customize your practice/i });
    await expect(customizeBtn).toBeVisible();

    // 5. Click "Customize your practice" and verify modal opens
    await customizeBtn.click();
    const modal = page.locator('div[role="dialog"][aria-labelledby="customize-practice-title"]');
    await expect(modal).toBeVisible({ timeout: 5000 });
    await expect(modal.getByRole('heading', { name: 'Customize Practice' })).toBeVisible();

    // 6. Verify topics are populated in modal (includes "All Course Topics")
    await expect(modal.getByText('All Course Topics')).toBeVisible();

    // 7. Test Cancel / Close dismisses modal without starting session
    const cancelBtn = modal.getByRole('button', { name: 'Cancel' });
    await cancelBtn.click();
    await expect(modal).not.toBeVisible({ timeout: 5000 });

    // 8. Re-open modal
    await customizeBtn.click();
    await expect(modal).toBeVisible({ timeout: 5000 });

    // 9. Select Configuration: Question Type = MCQ, Count = 5
    const mcqBtn = modal.getByRole('button', { name: /Multiple Choice/i });
    await mcqBtn.click();
    const count5Btn = modal.getByRole('button', { name: '5', exact: true });
    await count5Btn.click();

    // 10. Intercept backend request to verify payload
    let capturedPayload = null;
    page.on('request', (req) => {
      if (req.url().includes('/practice/generate') && req.method() === 'POST') {
        try {
          capturedPayload = req.postDataJSON();
        } catch {
          // ignore
        }
      }
    });

    // 11. Submit custom practice
    const startBtn = modal.getByRole('button', { name: /Start custom practice/i });
    await startBtn.click();

    // Verify button goes to loading state or session modal opens
    await expect(
      page.locator('div[role="dialog"]').filter({ hasText: /Custom Practice|Question|Adaptive Practice/i }).first()
    ).toBeVisible({ timeout: 90000 });

    // Assert that the intercepted backend payload had the customized settings
    expect(capturedPayload).not.toBeNull();
    expect(capturedPayload.question_count).toBe(5);
    expect(capturedPayload.mode).toBe('adaptive');
    expect(capturedPayload.question_types).toEqual(['mcq']);
  });
});
