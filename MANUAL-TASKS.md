# AutoSpec.AI Production - Manual Tasks Guide

## Overview

After running the automated production setup scripts, these 5 manual tasks must be completed to enable full production functionality. Each task includes detailed step-by-step instructions with screenshots guidance.

**Estimated Total Time: 30 minutes + approval wait times**

---

## 1. 🤖 Amazon Bedrock Model Access (CRITICAL)

**Time Required: 2 minutes**  
**Approval Time: Usually immediate**  
**Required For: AI document processing functionality**

### Steps:

1. **Navigate to Amazon Bedrock Console**
   - Go to [AWS Console](https://console.aws.amazon.com/)
   - In the search bar, type "Bedrock" and select "Amazon Bedrock"
   - Ensure you're in the **us-east-1** region (top right corner)

2. **Access Model Access Page**
   - In the left sidebar, click "**Model access**"
   - You'll see a list of available models

3. **Request Claude 3.5 Sonnet v2 Access**
   - Look for "**Anthropic**" in the model providers list
   - Find "**Claude 3.5 Sonnet v2**" (model ID: `anthropic.claude-3-5-sonnet-20241022-v2:0`)
   - Click "**Request model access**" or "**Manage model access**"

4. **Submit Access Request**
   - Check the box next to "**Claude 3.5 Sonnet v2**"
   - Review and accept the terms of use
   - Click "**Submit**"

5. **Verify Access Granted**
   - Wait 30-60 seconds
   - Refresh the page
   - Status should show "**Access granted**" in green
   - If still pending, wait a few more minutes and refresh

### ✅ Success Criteria:
- Claude 3.5 Sonnet v2 model shows "Access granted" status
- You can see the model in the "Available models" section

### ❌ Troubleshooting:
- If access is denied: Contact AWS Support with your use case
- If region issues: Ensure you're in us-east-1
- If model not visible: Check you have proper IAM permissions

---

## 2A. 🌐 Quick Domain Setup (REQUIRED FIRST)

**Time Required: 10 minutes**  
**Cost: $12-15/year**  
**Required For: SES production access**

### Fastest Path - AWS Route 53:

1. **Go to Route 53**
   - AWS Console → Search "Route 53" → Click service
   - Click "**Register domain**" (big blue button)

2. **Find Available Domain**
   - Search suggestions: `autospec-ai.com`, `[yourname]-ai.com`, `[yourname]-docs.com`
   - Select `.com` domains (most reliable)
   - Click "Add to cart" on available domain

3. **Complete Purchase**
   - Contact info: Use `ai.autospec@gmail.com`
   - Enable "Privacy protection" (recommended)
   - Auto-renew: Enable
   - Complete purchase
   - **⚠️ Note your exact domain name for next steps**

4. **Wait for Registration**
   - Check email for confirmation
   - Wait 5-10 minutes for "Active" status in Route 53
   - Refresh the "Registered domains" page

### ✅ Success Criteria:
- Domain shows "Active" in Route 53 console
- Registration confirmation email received

---

## 2B. 📧 Amazon SES Production Access (CRITICAL)

**Time Required: 10 minutes to submit (after domain setup)**  
**Approval Time: 24-48 hours**  
**Required For: Email functionality and notifications**

### Prerequisites: Domain Setup (REQUIRED for SES Production Access)

**⚠️ IMPORTANT: AWS now requires a verified domain for SES production access**

**Quick Domain Setup Options:**

**Option A: AWS Route 53 (Fastest - 5 minutes)**
- Purchase domain directly in AWS
- Automatic DNS setup and verification
- Integrated with SES
- Cost: $12-15/year

**Option B: Use Existing Domain**
- If you own a domain, add it to Route 53
- Point DNS to AWS
- Verify ownership

### Steps:

1. **Navigate to Amazon SES Console**
   - Go to [AWS Console](https://console.aws.amazon.com/)
   - Search for "SES" and select "Amazon Simple Email Service"
   - Ensure you're in the **us-east-1** region

2. **Check Current Status**
   - In the left sidebar, click "**Account dashboard**"
   - Look for "**Sending quota**" - if it shows "200 emails per 24-hour period", you're in sandbox mode
   - Note: You need production access to send to any email address

3. **Set Up Domain First (REQUIRED)**
   
   **Quick Route 53 Domain Purchase:**
   - Go to AWS Console → Route 53
   - Click "Register domain"
   - Search for available domain (try: autospec-ai.com, your-name-ai.com)
   - Select domain and add to cart
   - Use `ai.autospec@gmail.com` as contact email
   - Complete purchase ($12-15)
   - **Wait 5-10 minutes for registration**
   
   **Then Add Domain to SES:**
   - Go to SES Console → "Verified identities"
   - Click "Create identity" → "Domain"
   - Enter your new domain (e.g., autospec-ai.com)
   - SES will provide DNS records
   - **For Route 53 domains: Click "Publish to Route 53" button**
   - Wait for "Verified" status (usually 5-15 minutes)

4. **Request Production Access**
   - Click "**Request production access**" button (usually prominent on dashboard)
   - If not visible, go to "Account dashboard" → "Sending statistics" → "Request production access"

5. **Fill Out the Request Form**
   
   **Mail Type**: Select "**Transactional**"
   
   **Website URL**: `https://yourdomain.com` (use your newly registered domain)
   
   **Use Case Description** (copy this template):
   ```
   AutoSpec.AI is a document processing and requirements analysis platform that uses AI to convert documents into structured system requirements. 
   
   We need SES production access for:
   - Transactional emails: Document processing confirmations, system notifications
   - User notifications: Processing status updates, error alerts
   - System alerts: Monitoring and operational notifications
   
   Email Volume: Expected 100-500 emails per day
   Recipients: Business users and system administrators who have opted in
   Bounce/Complaint Handling: Automated via SNS topics and DynamoDB tracking
   
   This is a legitimate business application with proper email handling practices.
   Domain verified and ready for production email sending.
   ```
   
   **Additional Details**:
   ```
   - All emails are transactional (no marketing)
   - Users explicitly request document processing
   - Automated bounce and complaint handling implemented
   - Email sending triggered only by user actions or system events
   - Proper unsubscribe mechanisms in place
   - Domain ownership verified through DNS records
   ```
   
   **Expected Sending Volume**: 
   - Daily: 500
   - Monthly: 15,000
   
   **Compliance Contact**: `ai.autospec@gmail.com`

6. **Submit Request**
   - Review all information carefully
   - Click "**Submit request**"
   - You'll receive a confirmation email

7. **Monitor Request Status**
   - Check the SES console dashboard for status updates
   - You'll receive email notifications about approval status
   - Approval typically takes 24-48 hours

8. **After Approval: Add Domain (Optional)**
   - Once SES production access is approved
   - Purchase domain via Route 53 or external registrar
   - Add domain to SES "Verified identities"
   - Update application configuration to use domain emails

### ✅ Success Criteria:
- Request submitted successfully
- Confirmation email received
- Status shows "Under review" in SES console

### ❌ Troubleshooting:
- If rejected: Respond to AWS with more detailed use case
- If delayed: Check spam folder for AWS communications
- If unclear: Contact AWS Support for clarification

---

## 3. 🔗 GitHub Repository Secrets (For CI/CD)

**Time Required: 5 minutes**  
**Required For: Automated deployments via GitHub Actions**

### Steps:

1. **Navigate to Your GitHub Repository**
   - Go to your AutoSpec.AI repository on GitHub
   - Click on the "**Settings**" tab (far right in the repository menu)

2. **Access Secrets and Variables**
   - In the left sidebar, expand "**Secrets and variables**"
   - Click "**Actions**"

3. **Create Environment Secrets**
   
   You need to create environments and secrets for each deployment stage:

   **a. Create Development Environment:**
   - Click "**New environment**"
   - Name: `development`
   - Click "**Configure environment**"
   - Add environment secrets:
     - `AWS_ACCESS_KEY_ID`: Your AWS access key
     - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
   
   **b. Create Staging Environment:**
   - Click "**New environment**"
   - Name: `staging`
   - Add the same AWS credentials
   
   **c. Create Production Environment:**
   - Click "**New environment**"
   - Name: `production`
   - Add the same AWS credentials
   - **Optional**: Add protection rules (require reviews for production deployments)

4. **Add Repository Secrets** (if using same AWS account for all environments)
   - Click "**New repository secret**"
   - Name: `AWS_ACCESS_KEY_ID`
   - Value: Your AWS access key ID
   - Click "**Add secret**"
   
   - Click "**New repository secret**"
   - Name: `AWS_SECRET_ACCESS_KEY`
   - Value: Your AWS secret access key
   - Click "**Add secret**"

### 📋 Required Secrets Summary:
```
Repository Secrets:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY

Environment Secrets (for each: development, staging, production):
- AWS_ACCESS_KEY_ID  
- AWS_SECRET_ACCESS_KEY
```

### ✅ Success Criteria:
- All three environments created (development, staging, production)
- AWS credentials added to each environment
- Secrets show as "Updated X minutes ago"

### ❌ Troubleshooting:
- If AWS credentials don't work: Verify IAM permissions
- If environments not saving: Check repository admin permissions
- If unclear: See [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

---

## 4. 📧 Email Confirmations (SNS Subscriptions)

**Time Required: 2 minutes**  
**Required For: Alert notifications and monitoring**

### Steps:

1. **Check Email Inbox**
   - Go to `ai.autospec@gmail.com`
   - Look for emails from "AWS Notifications" or "no-reply@sns.amazonaws.com"
   - You should have received 3-4 confirmation emails

2. **Confirm Each SNS Subscription**
   
   Expected emails:
   - "AWS Notification - Subscription Confirmation" for **critical alerts**
   - "AWS Notification - Subscription Confirmation" for **warning alerts**
   - "AWS Notification - Subscription Confirmation" for **business metrics**
   - "AWS Budget Notification" for **budget alerts**

3. **Click Confirmation Links**
   - Open each email
   - Click "**Confirm subscription**" link
   - This will open a browser page confirming the subscription
   - You should see "Subscription confirmed!" message

4. **Verify Subscriptions**
   - Go to AWS Console → Simple Notification Service (SNS)
   - Click "**Subscriptions**" in the left sidebar
   - Verify you see subscriptions with status "**Confirmed**"

### ✅ Success Criteria:
- All subscription emails confirmed
- SNS console shows "Confirmed" status for all subscriptions
- You receive a test notification (may take a few minutes)

### ❌ Troubleshooting:
- If no emails received: Check spam/junk folder
- If confirmation links don't work: Try copying URL to new browser tab
- If still issues: Go to SNS console and resubscribe manually

---

## 5. 🌐 Additional Domain Configuration (OPTIONAL)

**Time Required: 5 minutes**  
**Required For: Additional email addresses and subdomains**  
**Status: Can be done after basic setup**

### Add Subdomains (Optional)

- Set up `app.yourdomain.com` for web interface
- Set up `api.yourdomain.com` for API endpoint
- Configure in Route 53 hosted zone

### Additional Email Addresses (Optional)

1. **Add Additional Email Addresses**
   - Go to SES Console → "Verified identities"
   - Click "Create identity" → "Email address"
   - Add addresses like: `support@yourdomain.com`, `noreply@yourdomain.com`
   - SES will send verification emails to these addresses

2. **Configure Email Forwarding (Optional)**
   - Set up email forwarding from domain emails to your Gmail
   - Use Route 53 MX records or third-party email service

### Update Application Configuration

1. **Update Config Files**
   - Edit `config/environments/prod.json`
   - Change email addresses to use your domain
   - Update branding URLs to use your domain

2. **Redeploy Application**
   - Run deployment script with updated configuration
   - Test email functionality with new domain emails

### ✅ Success Criteria:
- Domain shows "Active" status in Route 53 (if using AWS)
- Domain verification email confirmed
- SES shows domain as "Verified" (if added)
- DNS queries return results for your domain

### ❌ Troubleshooting:
- If domain verification email not received: Check spam folder
- If DNS not working: Wait 24-48 hours for propagation
- If domain not showing in Route 53: Contact AWS Support
- **Remember: Domain is optional - your app works without it!**

---

## 🎯 After Completing All Manual Tasks

### Verification Checklist:
- [x] Bedrock Claude 3.5 Sonnet v2 access granted
- [x] Domain purchased and verified (autospec-ai.com)
- [x] SES production access request submitted (awaiting approval)
- [x] GitHub secrets configured for all environments
- [x] All SNS subscription emails confirmed
- [x] Production configuration updated with actual domain values

### Deployment Options:

**Option A: Deploy Now (Recommended)**
- Your system will work fully even while SES is in sandbox mode
- Emails will only send to verified addresses (ai.autospec@gmail.com)
- All other functionality works normally
- SES will automatically switch to production mode when approved

**Option B: Wait for SES Approval**
- Wait 24-48 hours for AWS SES production approval
- Then deploy with full email functionality

### Production Deployment Commands:
```bash
source ./scripts/load-config.sh prod
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION
./scripts/deploy.sh prod
```

2. Validate deployment:
   ```bash
   ./scripts/validate-deployment.sh prod
   ```

3. Monitor your deployment:
   - CloudWatch Dashboard: `autospec-ai-prod-operational`
   - Application URL: `https://app.auto-spec.ai`
   - API Health: `https://api.auto-spec.ai/health`

## 📞 Support

If you encounter issues with any manual tasks:

1. **AWS-related issues**: Check AWS Service Health Dashboard
2. **GitHub issues**: Verify repository permissions and admin access
3. **Email issues**: Check spam folders and email client settings
4. **Domain issues**: Contact domain registrar support

**Contact Information:**
- Primary Email: `ai.autospec@gmail.com`
- AWS Account: Configured in your local credentials

---

**Last Updated:** December 26, 2024  
**Version:** 1.0  
**Status:** Ready for Production