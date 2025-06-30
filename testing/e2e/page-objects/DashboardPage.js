/**
 * Dashboard Page Object Model
 * Page object for dashboard functionality and navigation
 */

class DashboardPage {
  constructor(page) {
    this.page = page;
    
    // Selectors
    this.mainContent = page.locator('[data-testid="dashboard-main"]');
    this.welcomeMessage = page.locator('[data-testid="welcome-message"]');
    this.documentsCard = page.locator('[data-testid="documents-card"]');
    this.analyticsCard = page.locator('[data-testid="analytics-card"]');
    this.workflowsCard = page.locator('[data-testid="workflows-card"]');
    this.recentDocuments = page.locator('[data-testid="recent-documents"]');
    this.pendingTasks = page.locator('[data-testid="pending-tasks"]');
    this.activityFeed = page.locator('[data-testid="activity-feed"]');
    this.navigationMenu = page.locator('[data-testid="navigation-menu"]');
    this.userProfile = page.locator('[data-testid="user-profile"]');
    this.notificationBell = page.locator('[data-testid="notification-bell"]');
  }

  async navigateTo() {
    await this.page.goto('/dashboard');
    await this.mainContent.waitFor({ state: 'visible' });
  }

  async navigateToDocuments() {
    await this.documentsCard.click();
    await this.page.waitForURL('/documents');
  }

  async navigateToAnalytics() {
    await this.analyticsCard.click();
    await this.page.waitForURL('/analytics');
  }

  async navigateToWorkflows() {
    await this.workflowsCard.click();
    await this.page.waitForURL('/workflows');
  }

  async getRecentDocuments() {
    const documents = await this.recentDocuments.locator('.document-item').all();
    const documentData = [];
    
    for (const doc of documents) {
      const title = await doc.locator('.document-title').textContent();
      const status = await doc.locator('.document-status').textContent();
      const lastModified = await doc.locator('.document-date').textContent();
      
      documentData.push({ title, status, lastModified });
    }
    
    return documentData;
  }

  async getPendingTasks() {
    const tasks = await this.pendingTasks.locator('.task-item').all();
    const taskData = [];
    
    for (const task of tasks) {
      const title = await task.locator('.task-title').textContent();
      const type = await task.locator('.task-type').textContent();
      const dueDate = await task.locator('.task-due-date').textContent();
      
      taskData.push({ title, type, dueDate });
    }
    
    return taskData;
  }

  async getActivityFeedItems() {
    const activities = await this.activityFeed.locator('.activity-item').all();
    const activityData = [];
    
    for (const activity of activities) {
      const message = await activity.locator('.activity-message').textContent();
      const timestamp = await activity.locator('.activity-timestamp').textContent();
      const user = await activity.locator('.activity-user').textContent();
      
      activityData.push({ message, timestamp, user });
    }
    
    return activityData;
  }

  async openNotifications() {
    await this.notificationBell.click();
    await this.page.locator('[data-testid="notifications-dropdown"]').waitFor({ state: 'visible' });
  }

  async getNotificationCount() {
    const badge = this.notificationBell.locator('.notification-badge');
    if (await badge.isVisible()) {
      return parseInt(await badge.textContent() || '0');
    }
    return 0;
  }

  async openUserProfile() {
    await this.userProfile.click();
    await this.page.locator('[data-testid="user-profile-dropdown"]').waitFor({ state: 'visible' });
  }

  async logout() {
    await this.openUserProfile();
    await this.page.locator('[data-testid="logout-button"]').click();
    await this.page.waitForURL('/login');
  }

  async searchGlobal(query) {
    const searchInput = this.page.locator('[data-testid="global-search"]');
    await searchInput.fill(query);
    await searchInput.press('Enter');
    await this.page.waitForURL('/search*');
  }

  async waitForDashboardLoad() {
    await this.mainContent.waitFor({ state: 'visible' });
    await this.recentDocuments.waitFor({ state: 'visible' });
    await this.pendingTasks.waitFor({ state: 'visible' });
  }
}

module.exports = { DashboardPage };