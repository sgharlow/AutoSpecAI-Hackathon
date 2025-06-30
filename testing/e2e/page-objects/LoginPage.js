/**
 * Login Page Object Model
 * Page object for authentication and login functionality
 */

class LoginPage {
  constructor(page) {
    this.page = page;
    
    // Selectors
    this.emailInput = page.locator('[data-testid="email-input"]');
    this.passwordInput = page.locator('[data-testid="password-input"]');
    this.loginButton = page.locator('[data-testid="login-button"]');
    this.errorMessage = page.locator('[data-testid="error-message"]');
    this.loadingIndicator = page.locator('[data-testid="loading-indicator"]');
    this.forgotPasswordLink = page.locator('[data-testid="forgot-password-link"]');
    this.signupLink = page.locator('[data-testid="signup-link"]');
  }

  async login(email, password) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
    
    // Wait for navigation or error
    await Promise.race([
      this.page.waitForURL('/dashboard'),
      this.errorMessage.waitFor({ state: 'visible' })
    ]);
  }

  async loginWithRememberMe(email, password) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.page.locator('[data-testid="remember-me-checkbox"]').check();
    await this.loginButton.click();
  }

  async getErrorMessage() {
    await this.errorMessage.waitFor({ state: 'visible' });
    return await this.errorMessage.textContent();
  }

  async isLoginButtonDisabled() {
    return await this.loginButton.isDisabled();
  }

  async clickForgotPassword() {
    await this.forgotPasswordLink.click();
  }

  async clickSignUp() {
    await this.signupLink.click();
  }

  async waitForLoadingToComplete() {
    await this.loadingIndicator.waitFor({ state: 'hidden' });
  }
}

module.exports = { LoginPage };