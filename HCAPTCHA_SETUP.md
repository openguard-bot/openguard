# hCaptcha Verification Setup Guide

This guide explains how to set up the hCaptcha verification system for your Discord bot.

## Prerequisites

1. **hCaptcha Account**: Sign up at [hCaptcha.com](https://hcaptcha.com)
2. **Web Hosting**: A place to host the verification web page (optional but recommended)

## Step 1: Get hCaptcha Keys

1. Go to [hCaptcha Dashboard](https://dashboard.hcaptcha.com/)
2. Create a new site
3. Get your **Site Key** and **Secret Key**

## Step 2: Configure Environment Variables

Add these to your `.env` file:

```env
HCAPTCHA_SITE_KEY=your_site_key_here
HCAPTCHA_SECRET_KEY=your_secret_key_here
```

## Step 3: Set Up Web Verification (Optional)

### Option A: Host the Web Page

1. Take the `web_verification_template.html` file
2. Replace `YOUR_HCAPTCHA_SITE_KEY` with your actual site key
3. Host it on your web server
4. Update the verification URL in the bot code to point to your hosted page

### Option B: Use Manual Token Entry

Users can complete hCaptcha on any website and manually enter the response token using the "Enter hCaptcha Response" button.

## Step 4: Bot Commands

### Enable Captcha
```
/captcha enable
```

### Configure Verification Role
```
/captcha config roleset @VerifiedRole
```

### Configure Failure Settings
```
/captcha config failverify 3 kick
```
- `3` = maximum attempts
- `kick` = punishment (kick, ban, or timeout)

### Send Verification Embed
```
/captcha embed send #verification-channel
```

### Manual Verification (Admin Only)
```
/captcha verify @user hcaptcha_response_token
```

## How It Works

### For Users:
1. Click "Start Verification" button
2. Choose verification method:
   - **Complete Verification**: Opens web page with hCaptcha
   - **Enter Response**: Manually enter hCaptcha response token
3. Complete hCaptcha challenge
4. Get verification role automatically

### For Administrators:
- All errors are reported with detailed information
- Can manually verify users with response tokens
- Full configuration control over attempts and punishments

## Verification Methods

### Method 1: Web Interface
1. User clicks "Complete Verification"
2. Opens web page with embedded hCaptcha
3. User solves captcha
4. Returns to Discord with automatic role assignment

### Method 2: Manual Token Entry
1. User completes hCaptcha on any website
2. Copies the response token
3. Uses "Enter hCaptcha Response" button in Discord
4. Pastes token and gets verified

### Method 3: Admin Verification
1. Admin gets hCaptcha response token from user
2. Uses `/captcha verify @user token` command
3. User gets verified immediately

## Error Reporting

The system includes comprehensive error reporting:
- hCaptcha API failures
- Network connectivity issues
- Database operation errors
- Configuration problems

All errors are sent to the configured error notification channel/user with full technical details.

## Security Features

- Verification tokens expire after 10 minutes
- Response tokens are validated against hCaptcha servers
- Failed attempts are tracked and limited
- Configurable punishments for repeated failures

## Troubleshooting

### "hCaptcha secret key not configured"
- Make sure `HCAPTCHA_SECRET_KEY` is set in your environment variables

### "hCaptcha verification failed"
- Check that your secret key is correct
- Ensure the response token is valid and not expired
- Check error logs for specific hCaptcha error codes

### "Failed to assign role"
- Check bot permissions
- Ensure the verification role exists
- Verify bot role hierarchy

## Advanced Configuration

### Custom Web Interface
You can create your own verification web page by:
1. Including the hCaptcha JavaScript library
2. Using your site key
3. Implementing the verification flow
4. Sending response tokens to your bot

### Database Integration
The system stores:
- User verification attempts
- Configuration settings
- Verification status

### Rate Limiting
- Built-in attempt limiting
- Configurable maximum attempts
- Automatic punishment application

## Support

If you encounter issues:
1. Check the error notification channel for detailed error reports
2. Verify your hCaptcha keys are correct
3. Ensure proper bot permissions
4. Check the console logs for additional information
