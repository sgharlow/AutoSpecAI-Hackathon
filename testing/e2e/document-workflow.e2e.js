/**
 * End-to-End Document Workflow Tests
 * Complete user journey testing for document processing and collaboration
 */

const { test, expect } = require('@playwright/test');
const { LoginPage } = require('./page-objects/LoginPage');
const { DashboardPage } = require('./page-objects/DashboardPage');
const { DocumentsPage } = require('./page-objects/DocumentsPage');
const { DocumentEditorPage } = require('./page-objects/DocumentEditorPage');
const { createTestUser, generateTestDocument } = require('./helpers/test-data');

test.describe('Document Workflow E2E Tests', () => {
  let user;
  let loginPage;
  let dashboardPage;
  let documentsPage;
  let editorPage;

  test.beforeEach(async ({ page }) => {
    // Create test user
    user = await createTestUser();
    
    // Initialize page objects
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    documentsPage = new DocumentsPage(page);
    editorPage = new DocumentEditorPage(page);
    
    // Navigate to application
    await page.goto('/');
  });

  test.describe('Document Upload and Processing', () => {
    test('complete document upload and processing workflow', async ({ page }) => {
      // Step 1: Login
      await loginPage.login(user.email, user.password);
      await expect(page).toHaveURL('/dashboard');
      
      // Step 2: Navigate to documents
      await dashboardPage.navigateToDocuments();
      await expect(page).toHaveURL('/documents');
      
      // Step 3: Upload document
      const testFile = generateTestDocument('requirements.pdf', 'pdf');
      await documentsPage.uploadDocument(testFile);
      
      // Step 4: Verify upload success
      await expect(documentsPage.successMessage).toBeVisible();
      await expect(documentsPage.getDocumentByName('requirements.pdf')).toBeVisible();
      
      // Step 5: Wait for processing to complete
      await documentsPage.waitForProcessingComplete('requirements.pdf');
      
      // Step 6: Verify document appears in list
      const documentCard = documentsPage.getDocumentByName('requirements.pdf');
      await expect(documentCard).toBeVisible();
      await expect(documentCard.locator('[data-testid="status-chip"]')).toHaveText('completed');
      
      // Step 7: Open document
      await documentCard.click();
      await expect(page).toHaveURL(/\/documents\/[^\/]+$/);
      
      // Step 8: Verify AI analysis results
      await expect(editorPage.analysisPanel).toBeVisible();
      await expect(editorPage.requirementsList).toContainText('REQ-');
      
      // Step 9: Verify document content is displayed
      await expect(editorPage.documentEditor).toBeVisible();
      await expect(editorPage.documentContent).not.toBeEmpty();
    });

    test('handles upload errors gracefully', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      // Try to upload unsupported file type
      const invalidFile = generateTestDocument('invalid.exe', 'application/octet-stream');
      await documentsPage.uploadDocument(invalidFile);
      
      // Verify error message
      await expect(documentsPage.errorMessage).toBeVisible();
      await expect(documentsPage.errorMessage).toContainText('file type');
    });

    test('handles file size validation', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      // Try to upload oversized file (mock large file)
      const largeFile = generateTestDocument('large.pdf', 'pdf', 60 * 1024 * 1024); // 60MB
      await documentsPage.uploadDocument(largeFile);
      
      // Verify error message
      await expect(documentsPage.errorMessage).toBeVisible();
      await expect(documentsPage.errorMessage).toContainText('file size');
    });

    test('supports drag and drop upload', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      // Create test file for drag and drop
      const testFile = generateTestDocument('dragdrop.pdf', 'pdf');
      
      // Simulate drag and drop
      await documentsPage.dragAndDropFile(testFile);
      
      // Verify upload initiated
      await expect(documentsPage.uploadProgress).toBeVisible();
      await expect(documentsPage.getDocumentByName('dragdrop.pdf')).toBeVisible();
    });
  });

  test.describe('Document Management', () => {
    test('document list operations', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      // Upload multiple documents
      const files = [
        generateTestDocument('doc1.pdf', 'pdf'),
        generateTestDocument('doc2.docx', 'docx'),
        generateTestDocument('doc3.txt', 'txt'),
      ];
      
      for (const file of files) {
        await documentsPage.uploadDocument(file);
        await documentsPage.waitForUploadComplete();
      }
      
      // Test search functionality
      await documentsPage.searchDocuments('doc1');
      await expect(documentsPage.getDocumentByName('doc1.pdf')).toBeVisible();
      await expect(documentsPage.getDocumentByName('doc2.docx')).not.toBeVisible();
      
      // Clear search
      await documentsPage.clearSearch();
      await expect(documentsPage.getDocumentByName('doc2.docx')).toBeVisible();
      
      // Test filtering by status
      await documentsPage.filterByStatus('completed');
      const visibleDocs = await documentsPage.getVisibleDocuments();
      for (const doc of visibleDocs) {
        await expect(doc.locator('[data-testid="status-chip"]')).toHaveText('completed');
      }
      
      // Test sorting
      await documentsPage.sortBy('title', 'asc');
      const sortedTitles = await documentsPage.getDocumentTitles();
      expect(sortedTitles).toEqual([...sortedTitles].sort());
    });

    test('document deletion', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      // Upload and wait for completion
      const testFile = generateTestDocument('delete-test.pdf', 'pdf');
      await documentsPage.uploadDocument(testFile);
      await documentsPage.waitForProcessingComplete('delete-test.pdf');
      
      // Delete document
      await documentsPage.deleteDocument('delete-test.pdf');
      
      // Confirm deletion
      await documentsPage.confirmDeletion();
      
      // Verify document is removed
      await expect(documentsPage.getDocumentByName('delete-test.pdf')).not.toBeVisible();
    });

    test('document sharing', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      // Upload document
      const testFile = generateTestDocument('share-test.pdf', 'pdf');
      await documentsPage.uploadDocument(testFile);
      await documentsPage.waitForProcessingComplete('share-test.pdf');
      
      // Open sharing dialog
      await documentsPage.shareDocument('share-test.pdf');
      
      // Add collaborator
      await documentsPage.addCollaborator('collaborator@example.com', 'edit');
      
      // Verify sharing confirmation
      await expect(documentsPage.shareSuccessMessage).toBeVisible();
    });
  });

  test.describe('Real-time Collaboration', () => {
    test('collaborative editing workflow', async ({ browser }) => {
      // Create two browser contexts for two users
      const context1 = await browser.newContext();
      const context2 = await browser.newContext();
      
      const page1 = await context1.newPage();
      const page2 = await context2.newPage();
      
      const user2 = await createTestUser('user2@example.com');
      
      // User 1 login and setup
      const loginPage1 = new LoginPage(page1);
      const documentsPage1 = new DocumentsPage(page1);
      const editorPage1 = new DocumentEditorPage(page1);
      
      await page1.goto('/');
      await loginPage1.login(user.email, user.password);
      await documentsPage1.navigateTo();
      
      // Upload and share document
      const testFile = generateTestDocument('collab-test.pdf', 'pdf');
      await documentsPage1.uploadDocument(testFile);
      await documentsPage1.waitForProcessingComplete('collab-test.pdf');
      await documentsPage1.shareDocument('collab-test.pdf');
      await documentsPage1.addCollaborator(user2.email, 'edit');
      
      // Open document in editor
      await documentsPage1.openDocument('collab-test.pdf');
      await editorPage1.startEditing();
      
      // User 2 login and join collaboration
      const loginPage2 = new LoginPage(page2);
      const documentsPage2 = new DocumentsPage(page2);
      const editorPage2 = new DocumentEditorPage(page2);
      
      await page2.goto('/');
      await loginPage2.login(user2.email, user2.password);
      await documentsPage2.navigateTo();
      await documentsPage2.openDocument('collab-test.pdf');
      
      // Verify presence indicators
      await expect(editorPage1.presenceIndicator(user2.email)).toBeVisible();
      await expect(editorPage2.presenceIndicator(user.email)).toBeVisible();
      
      // User 1 makes changes
      await editorPage1.typeInEditor('This is a collaborative edit from User 1');
      
      // Verify User 2 sees the changes
      await expect(editorPage2.editorContent).toContainText('This is a collaborative edit from User 1');
      
      // User 2 adds a comment
      await editorPage2.selectText('collaborative edit');
      await editorPage2.addComment('Great addition!');
      
      // Verify User 1 sees the comment
      await expect(editorPage1.commentIndicator).toBeVisible();
      await expect(editorPage1.commentsPanel).toContainText('Great addition!');
      
      await context1.close();
      await context2.close();
    });

    test('comment system workflow', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      // Upload and open document
      const testFile = generateTestDocument('comment-test.pdf', 'pdf');
      await documentsPage.uploadDocument(testFile);
      await documentsPage.waitForProcessingComplete('comment-test.pdf');
      await documentsPage.openDocument('comment-test.pdf');
      
      // Add comment
      await editorPage.selectText('requirements');
      await editorPage.addComment('This section needs more detail');
      
      // Verify comment appears
      await expect(editorPage.commentsPanel).toContainText('This section needs more detail');
      
      // Reply to comment
      await editorPage.replyToComment('This section needs more detail', 'I agree, will add more details');
      
      // Verify reply appears
      await expect(editorPage.commentsPanel).toContainText('I agree, will add more details');
      
      // Resolve comment
      await editorPage.resolveComment('This section needs more detail');
      
      // Verify comment is marked as resolved
      await expect(editorPage.resolvedCommentsSection).toContainText('This section needs more detail');
    });

    test('version control workflow', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      // Upload and open document
      const testFile = generateTestDocument('version-test.pdf', 'pdf');
      await documentsPage.uploadDocument(testFile);
      await documentsPage.waitForProcessingComplete('version-test.pdf');
      await documentsPage.openDocument('version-test.pdf');
      
      // Make initial edit
      await editorPage.startEditing();
      await editorPage.typeInEditor('Version 1 content');
      await editorPage.saveDocument('Added initial content');
      
      // Make second edit
      await editorPage.typeInEditor('\nVersion 2 addition');
      await editorPage.saveDocument('Added version 2 content');
      
      // View version history
      await editorPage.openVersionHistory();
      
      // Verify versions are listed
      const versions = await editorPage.getVersionList();
      expect(versions.length).toBeGreaterThanOrEqual(2);
      
      // Compare versions
      await editorPage.compareVersions(1, 2);
      await expect(editorPage.diffViewer).toBeVisible();
      await expect(editorPage.diffViewer).toContainText('Version 2 addition');
      
      // Restore previous version
      await editorPage.restoreVersion(1);
      await expect(editorPage.editorContent).not.toContainText('Version 2 addition');
    });
  });

  test.describe('Workflow Management', () => {
    test('approval workflow process', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      // Upload document
      const testFile = generateTestDocument('approval-test.pdf', 'pdf');
      await documentsPage.uploadDocument(testFile);
      await documentsPage.waitForProcessingComplete('approval-test.pdf');
      await documentsPage.openDocument('approval-test.pdf');
      
      // Start approval workflow
      await editorPage.startApprovalWorkflow();
      await editorPage.addApprover('approver@example.com');
      await editorPage.setApprovalDeadline('2024-02-01');
      await editorPage.addWorkflowDescription('Please review and approve this document');
      await editorPage.submitWorkflow();
      
      // Verify workflow started
      await expect(editorPage.workflowStatus).toContainText('Pending Approval');
      
      // Check workflow in dashboard
      await dashboardPage.navigateTo();
      await expect(dashboardPage.pendingTasks).toContainText('approval-test.pdf');
    });

    test('workflow task management', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      await page.goto('/workflows');
      
      // View pending tasks
      const workflowsPage = page.locator('[data-testid="workflows-page"]');
      await expect(workflowsPage).toBeVisible();
      
      // Filter tasks by status
      await page.click('[data-testid="filter-pending"]');
      const pendingTasks = page.locator('[data-testid="task-card"][data-status="pending"]');
      await expect(pendingTasks.first()).toBeVisible();
      
      // View task details
      await pendingTasks.first().click();
      await expect(page.locator('[data-testid="task-details"]')).toBeVisible();
    });
  });

  test.describe('Mobile Responsiveness', () => {
    test('mobile document upload', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      // Test mobile upload interface
      await documentsPage.openMobileUpload();
      const testFile = generateTestDocument('mobile-test.pdf', 'pdf');
      await documentsPage.uploadDocument(testFile);
      
      await expect(documentsPage.getDocumentByName('mobile-test.pdf')).toBeVisible();
    });

    test('mobile document viewing', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      const testFile = generateTestDocument('mobile-view.pdf', 'pdf');
      await documentsPage.uploadDocument(testFile);
      await documentsPage.waitForProcessingComplete('mobile-view.pdf');
      await documentsPage.openDocument('mobile-view.pdf');
      
      // Verify mobile editor interface
      await expect(editorPage.mobileToolbar).toBeVisible();
      await expect(editorPage.documentEditor).toBeVisible();
      
      // Test mobile comments
      await editorPage.openMobileComments();
      await expect(editorPage.commentsDrawer).toBeVisible();
    });
  });

  test.describe('Performance and Accessibility', () => {
    test('page load performance', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      
      // Measure dashboard load time
      const dashboardStart = Date.now();
      await dashboardPage.navigateTo();
      await expect(dashboardPage.mainContent).toBeVisible();
      const dashboardLoadTime = Date.now() - dashboardStart;
      
      expect(dashboardLoadTime).toBeLessThan(3000); // 3 second max
      
      // Measure documents page load time
      const documentsStart = Date.now();
      await documentsPage.navigateTo();
      await expect(documentsPage.documentsList).toBeVisible();
      const documentsLoadTime = Date.now() - documentsStart;
      
      expect(documentsLoadTime).toBeLessThan(2000); // 2 second max
    });

    test('accessibility compliance', async ({ page }) => {
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateTo();
      
      // Check keyboard navigation
      await page.keyboard.press('Tab');
      await expect(page.locator(':focus')).toBeVisible();
      
      // Check ARIA labels
      const buttons = page.locator('button');
      const buttonCount = await buttons.count();
      
      for (let i = 0; i < Math.min(buttonCount, 10); i++) {
        const button = buttons.nth(i);
        const ariaLabel = await button.getAttribute('aria-label');
        const text = await button.textContent();
        
        // Each button should have either aria-label or text content
        expect(ariaLabel || text).toBeTruthy();
      }
      
      // Check color contrast (simplified check)
      const colorElements = page.locator('[style*="color"]');
      await expect(colorElements.first()).toBeVisible();
    });

    test('offline functionality', async ({ page, context }) => {
      await loginPage.login(user.email, user.password);
      await dashboardPage.navigateToDocuments();
      
      // Upload document while online
      const testFile = generateTestDocument('offline-test.pdf', 'pdf');
      await documentsPage.uploadDocument(testFile);
      await documentsPage.waitForProcessingComplete('offline-test.pdf');
      await documentsPage.openDocument('offline-test.pdf');
      
      // Go offline
      await context.setOffline(true);
      
      // Verify offline indicator
      await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();
      
      // Verify cached content is still accessible
      await expect(editorPage.documentEditor).toBeVisible();
      
      // Try to make edit (should queue for later sync)
      await editorPage.startEditing();
      await editorPage.typeInEditor('Offline edit');
      
      // Verify offline edit indicator
      await expect(page.locator('[data-testid="offline-changes"]')).toBeVisible();
      
      // Go back online
      await context.setOffline(false);
      
      // Verify sync occurs
      await expect(page.locator('[data-testid="sync-complete"]')).toBeVisible();
    });
  });
});