/**
 * Document Editor Page Object Model
 * Page object for document editing and collaboration features
 */

class DocumentEditorPage {
  constructor(page) {
    this.page = page;
    
    // Selectors
    this.documentEditor = page.locator('[data-testid="document-editor"]');
    this.documentContent = page.locator('[data-testid="document-content"]');
    this.editorContent = page.locator('.monaco-editor .view-lines');
    this.analysisPanel = page.locator('[data-testid="analysis-panel"]');
    this.requirementsList = page.locator('[data-testid="requirements-list"]');
    this.commentsPanel = page.locator('[data-testid="comments-panel"]');
    this.commentIndicator = page.locator('[data-testid="comment-indicator"]');
    this.resolvedCommentsSection = page.locator('[data-testid="resolved-comments"]');
    this.versionHistory = page.locator('[data-testid="version-history"]');
    this.diffViewer = page.locator('[data-testid="diff-viewer"]');
    this.workflowStatus = page.locator('[data-testid="workflow-status"]');
    this.saveButton = page.locator('[data-testid="save-button"]');
    this.editButton = page.locator('[data-testid="edit-button"]');
    this.mobileToolbar = page.locator('[data-testid="mobile-toolbar"]');
    this.commentsDrawer = page.locator('[data-testid="comments-drawer"]');
    this.presenceIndicators = page.locator('[data-testid="presence-indicators"]');
  }

  async startEditing() {
    await this.editButton.click();
    await this.editorContent.waitFor({ state: 'visible' });
  }

  async typeInEditor(text) {
    await this.editorContent.click();
    await this.page.keyboard.type(text);
  }

  async saveDocument(commitMessage = 'Document updated') {
    await this.saveButton.click();
    
    // If commit message dialog appears
    const commitDialog = this.page.locator('[data-testid="commit-dialog"]');
    if (await commitDialog.isVisible()) {
      await this.page.locator('[data-testid="commit-message"]').fill(commitMessage);
      await this.page.locator('[data-testid="commit-save"]').click();
    }
    
    // Wait for save to complete
    await this.page.locator('[data-testid="save-success"]').waitFor({ state: 'visible' });
  }

  async selectText(text) {
    // Find and select specific text in the editor
    await this.page.keyboard.press('Control+F');
    await this.page.locator('[data-testid="search-box"]').fill(text);
    await this.page.keyboard.press('Enter');
    await this.page.keyboard.press('Escape'); // Close search
  }

  async addComment(commentText) {
    // Assume text is already selected
    await this.page.locator('[data-testid="add-comment-button"]').click();
    await this.page.locator('[data-testid="comment-input"]').fill(commentText);
    await this.page.locator('[data-testid="submit-comment"]').click();
    
    // Wait for comment to appear
    await this.commentsPanel.locator(`text="${commentText}"`).waitFor({ state: 'visible' });
  }

  async replyToComment(originalComment, replyText) {
    const commentElement = this.commentsPanel.locator(`text="${originalComment}"`).locator('..');
    await commentElement.locator('[data-testid="reply-button"]').click();
    await commentElement.locator('[data-testid="reply-input"]').fill(replyText);
    await commentElement.locator('[data-testid="submit-reply"]').click();
  }

  async resolveComment(commentText) {
    const commentElement = this.commentsPanel.locator(`text="${commentText}"`).locator('..');
    await commentElement.locator('[data-testid="resolve-button"]').click();
  }

  async openVersionHistory() {
    await this.page.locator('[data-testid="version-history-button"]').click();
    await this.versionHistory.waitFor({ state: 'visible' });
  }

  async getVersionList() {
    const versions = await this.versionHistory.locator('[data-testid="version-item"]').all();
    const versionData = [];
    
    for (const version of versions) {
      const versionNumber = await version.getAttribute('data-version');
      const timestamp = await version.locator('.version-timestamp').textContent();
      const author = await version.locator('.version-author').textContent();
      const message = await version.locator('.version-message').textContent();
      
      versionData.push({ versionNumber, timestamp, author, message });
    }
    
    return versionData;
  }

  async compareVersions(version1, version2) {
    await this.versionHistory.locator(`[data-version="${version1}"] [data-testid="select-version"]`).click();
    await this.versionHistory.locator(`[data-version="${version2}"] [data-testid="select-version"]`).click();
    await this.page.locator('[data-testid="compare-versions"]').click();
    await this.diffViewer.waitFor({ state: 'visible' });
  }

  async restoreVersion(versionNumber) {
    await this.versionHistory.locator(`[data-version="${versionNumber}"] [data-testid="restore-button"]`).click();
    await this.page.locator('[data-testid="confirm-restore"]').click();
    await this.page.locator('[data-testid="restore-success"]').waitFor({ state: 'visible' });
  }

  async startApprovalWorkflow() {
    await this.page.locator('[data-testid="workflow-menu"]').click();
    await this.page.locator('[data-testid="start-approval"]').click();
    await this.page.locator('[data-testid="approval-workflow-dialog"]').waitFor({ state: 'visible' });
  }

  async addApprover(email) {
    await this.page.locator('[data-testid="approver-email"]').fill(email);
    await this.page.locator('[data-testid="add-approver"]').click();
  }

  async setApprovalDeadline(date) {
    await this.page.locator('[data-testid="approval-deadline"]').fill(date);
  }

  async addWorkflowDescription(description) {
    await this.page.locator('[data-testid="workflow-description"]').fill(description);
  }

  async submitWorkflow() {
    await this.page.locator('[data-testid="submit-workflow"]').click();
    await this.page.locator('[data-testid="workflow-success"]').waitFor({ state: 'visible' });
  }

  async presenceIndicator(userEmail) {
    return this.presenceIndicators.locator(`[data-user="${userEmail}"]`);
  }

  async openMobileComments() {
    await this.page.locator('[data-testid="mobile-comments-button"]').click();
    await this.commentsDrawer.waitFor({ state: 'visible' });
  }

  async getDocumentStatistics() {
    const stats = {};
    
    // Get word count
    const wordCountElement = this.page.locator('[data-testid="word-count"]');
    if (await wordCountElement.isVisible()) {
      stats.wordCount = await wordCountElement.textContent();
    }
    
    // Get requirements count
    const requirementsCount = await this.requirementsList.locator('.requirement-item').count();
    stats.requirementsCount = requirementsCount;
    
    // Get comments count
    const commentsCount = await this.commentsPanel.locator('.comment-item').count();
    stats.commentsCount = commentsCount;
    
    return stats;
  }

  async exportDocument(format = 'pdf') {
    await this.page.locator('[data-testid="export-menu"]').click();
    await this.page.locator(`[data-testid="export-${format}"]`).click();
    
    // Wait for download to be initiated
    const downloadPromise = this.page.waitForEvent('download');
    await this.page.locator('[data-testid="confirm-export"]').click();
    
    return await downloadPromise;
  }

  async toggleAnalysisPanel() {
    await this.page.locator('[data-testid="toggle-analysis"]').click();
  }

  async getAnalysisResults() {
    const requirements = await this.requirementsList.locator('.requirement-item').all();
    const analysisData = [];
    
    for (const req of requirements) {
      const id = await req.locator('.requirement-id').textContent();
      const title = await req.locator('.requirement-title').textContent();
      const type = await req.locator('.requirement-type').textContent();
      const priority = await req.locator('.requirement-priority').textContent();
      
      analysisData.push({ id, title, type, priority });
    }
    
    return analysisData;
  }
}

module.exports = { DocumentEditorPage };