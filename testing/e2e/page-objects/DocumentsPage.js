/**
 * Documents Page Object Model
 * Page object for document management functionality
 */

class DocumentsPage {
  constructor(page) {
    this.page = page;
    
    // Selectors
    this.documentsList = page.locator('[data-testid="documents-list"]');
    this.uploadButton = page.locator('[data-testid="upload-button"]');
    this.fileInput = page.locator('[data-testid="file-input"]');
    this.dragDropZone = page.locator('[data-testid="drag-drop-zone"]');
    this.searchInput = page.locator('[data-testid="search-input"]');
    this.filterDropdown = page.locator('[data-testid="filter-dropdown"]');
    this.sortDropdown = page.locator('[data-testid="sort-dropdown"]');
    this.successMessage = page.locator('[data-testid="success-message"]');
    this.errorMessage = page.locator('[data-testid="error-message"]');
    this.uploadProgress = page.locator('[data-testid="upload-progress"]');
    this.loadingSpinner = page.locator('[data-testid="loading-spinner"]');
  }

  async navigateTo() {
    await this.page.goto('/documents');
    await this.documentsList.waitFor({ state: 'visible' });
  }

  async uploadDocument(file) {
    // Create a file input if using programmatic upload
    if (typeof file === 'object' && file.name) {
      // Set files on the input
      await this.fileInput.setInputFiles({
        name: file.name,
        mimeType: file.type || 'application/pdf',
        buffer: file.buffer || Buffer.from('mock file content')
      });
    } else {
      // Click upload button and select file
      await this.uploadButton.click();
      await this.fileInput.setInputFiles(file);
    }
    
    // Wait for upload to start
    await this.uploadProgress.waitFor({ state: 'visible' });
  }

  async dragAndDropFile(file) {
    // Simulate drag and drop
    await this.dragDropZone.hover();
    
    // Create DataTransfer object and add file
    const dataTransfer = await this.page.evaluateHandle((file) => {
      const dt = new DataTransfer();
      const fileObj = new File([file.buffer || 'mock content'], file.name, {
        type: file.type || 'application/pdf'
      });
      dt.items.add(fileObj);
      return dt;
    }, file);
    
    // Dispatch drop event
    await this.dragDropZone.dispatchEvent('drop', { dataTransfer });
  }

  async getDocumentByName(name) {
    return this.documentsList.locator(`[data-testid="document-card"][data-title="${name}"]`);
  }

  async waitForProcessingComplete(documentName) {
    const documentCard = this.getDocumentByName(documentName);
    const statusChip = documentCard.locator('[data-testid="status-chip"]');
    
    // Wait for status to change from 'processing' to 'completed'
    await this.page.waitForFunction(
      ({ statusElement }) => {
        return statusElement.textContent !== 'processing';
      },
      { statusElement: statusChip },
      { timeout: 60000 }
    );
  }

  async waitForUploadComplete() {
    await this.uploadProgress.waitFor({ state: 'hidden' });
    await this.successMessage.waitFor({ state: 'visible' });
  }

  async searchDocuments(query) {
    await this.searchInput.fill(query);
    await this.searchInput.press('Enter');
    await this.loadingSpinner.waitFor({ state: 'hidden' });
  }

  async clearSearch() {
    await this.searchInput.clear();
    await this.searchInput.press('Enter');
    await this.loadingSpinner.waitFor({ state: 'hidden' });
  }

  async filterByStatus(status) {
    await this.filterDropdown.click();
    await this.page.locator(`[data-testid="filter-${status}"]`).click();
    await this.loadingSpinner.waitFor({ state: 'hidden' });
  }

  async sortBy(field, direction = 'asc') {
    await this.sortDropdown.click();
    await this.page.locator(`[data-testid="sort-${field}-${direction}"]`).click();
    await this.loadingSpinner.waitFor({ state: 'hidden' });
  }

  async getVisibleDocuments() {
    return await this.documentsList.locator('[data-testid="document-card"]:visible').all();
  }

  async getDocumentTitles() {
    const documents = await this.getVisibleDocuments();
    const titles = [];
    
    for (const doc of documents) {
      const title = await doc.getAttribute('data-title');
      titles.push(title);
    }
    
    return titles;
  }

  async deleteDocument(documentName) {
    const documentCard = this.getDocumentByName(documentName);
    await documentCard.locator('[data-testid="document-menu"]').click();
    await this.page.locator('[data-testid="delete-option"]').click();
  }

  async confirmDeletion() {
    await this.page.locator('[data-testid="confirm-delete"]').click();
    await this.successMessage.waitFor({ state: 'visible' });
  }

  async shareDocument(documentName) {
    const documentCard = this.getDocumentByName(documentName);
    await documentCard.locator('[data-testid="share-button"]').click();
    await this.page.locator('[data-testid="sharing-dialog"]').waitFor({ state: 'visible' });
  }

  async addCollaborator(email, permission = 'edit') {
    await this.page.locator('[data-testid="collaborator-email"]').fill(email);
    await this.page.locator('[data-testid="permission-select"]').selectOption(permission);
    await this.page.locator('[data-testid="add-collaborator"]').click();
    
    this.shareSuccessMessage = this.page.locator('[data-testid="share-success"]');
    await this.shareSuccessMessage.waitFor({ state: 'visible' });
  }

  async openDocument(documentName) {
    const documentCard = this.getDocumentByName(documentName);
    await documentCard.click();
    await this.page.waitForURL(/\/documents\/[^\/]+$/);
  }

  async openMobileUpload() {
    // For mobile viewport
    await this.page.locator('[data-testid="mobile-upload-fab"]').click();
    await this.page.locator('[data-testid="mobile-upload-sheet"]').waitFor({ state: 'visible' });
  }

  async getDocumentCount() {
    const documents = await this.getVisibleDocuments();
    return documents.length;
  }

  async selectMultipleDocuments(documentNames) {
    for (const name of documentNames) {
      const checkbox = this.getDocumentByName(name).locator('[data-testid="document-checkbox"]');
      await checkbox.check();
    }
  }

  async bulkDelete(documentNames) {
    await this.selectMultipleDocuments(documentNames);
    await this.page.locator('[data-testid="bulk-actions"]').click();
    await this.page.locator('[data-testid="bulk-delete"]').click();
    await this.confirmDeletion();
  }
}

module.exports = { DocumentsPage };