# OAuth Provider Setup Guide: Google & Microsoft

This guide provides step-by-step instructions for registering **AI Stream Radio** with Google Cloud Console and Microsoft Entra ID (Azure) to acquire your **Client ID** and **Client Secret** for single sign-on (SSO).

---

## 1. Application Callback URIs

When setting up your OAuth credentials with Google or Microsoft, you must specify the authorized redirect/callback URIs.

- **Local Development Callback URIs:**
  - Google: `http://127.0.0.1:8000/auth/callback/google`
  - Microsoft: `http://127.0.0.1:8000/auth/callback/microsoft`

*(Note: If you run your application on a custom domain, replace `http://127.0.0.1:8000` with `https://yourdomain.com`).*

---

## 2. Google OAuth 2.0 Registration Instructions

### Step 1: Create a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Log in with your Google account.
3. Click the project dropdown near the top logo and click **New Project**.
4. Name your project (e.g., `AI Stream Radio`) and click **Create**.

### Step 2: Configure the OAuth Consent Screen
1. In the left navigation menu, go to **APIs & Services** > **OAuth consent screen**.
2. Select **External** (unless you have a Google Workspace organization for internal users) and click **Create**.
3. Fill out the required App information:
   - **App name**: `AI Stream Radio`
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
4. Click **Save and Continue**.
5. Under **Scopes**, click **Add or Remove Scopes**, select:
   - `userinfo.email`
   - `userinfo.profile`
   - `openid`
6. Click **Update** and then **Save and Continue**.
7. Under **Test users**, add your own Google email address so you can test logging in while the app is in Development mode. Click **Save and Continue**.

### Step 3: Create Credentials (Client ID & Client Secret)
1. Go to **APIs & Services** > **Credentials**.
2. Click **+ Create Credentials** at the top and select **OAuth client ID**.
3. Set **Application type** to **Web application**.
4. Set **Name** to `AI Stream Radio Web Client`.
5. Under **Authorized redirect URIs**, click **+ Add URI** and enter:
   ```text
   http://127.0.0.1:8000/auth/callback/google
   ```
   *(Also add `http://localhost:8000/auth/callback/google` if applicable)*.
6. Click **Create**.
7. A dialog will display your **Client ID** and **Client Secret**. Copy both values.

---

## 3. Microsoft Entra ID (Azure Portal) Registration Instructions

### Step 1: Register a New Application
1. Go to the [Microsoft Azure Portal](https://portal.azure.com/) or [Microsoft Entra Admin Center](https://entra.microsoft.com/).
2. Navigate to **Microsoft Entra ID** (formerly Azure Active Directory) > **App registrations**.
3. Click **+ New registration**.
4. Fill in the fields:
   - **Name**: `AI Stream Radio`
   - **Supported account types**: Select **Accounts in any organizational directory (Any Microsoft Entra ID directory - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)**.
   - **Redirect URI**: Select **Web** and enter:
     ```text
     http://127.0.0.1:8000/auth/callback/microsoft
     ```
5. Click **Register**.

### Step 2: Obtain Application (Client) ID
1. Once created, you will be taken to the application **Overview** page.
2. Copy the **Application (client) ID**. This is your `MICROSOFT_CLIENT_ID`.

### Step 3: Create a Client Secret
1. In the left navigation menu of your app registration, click **Certificates & secrets**.
2. Select the **Client secrets** tab and click **+ New client secret**.
3. Add a description (e.g., `Local Dev Secret`) and select an expiration period (e.g., 180 days).
4. Click **Add**.
5. **IMPORTANT:** Copy the **Value** column (not the Secret ID) immediately. This is your `MICROSOFT_CLIENT_SECRET`. *(You will not be able to view it again after leaving the page).*

---

## 4. Configuring Credentials in your Environment (`.env`)

Add your acquired credentials to the `.env` file in the root of your project:

```env
# Database Settings
DATABASE_URL=sqlite:///./data/radiostation.db

# Authentication Security Settings
AUTH_SECRET_KEY=your_super_secret_jwt_key_at_least_32_chars_long

# Google OAuth Keys
GOOGLE_CLIENT_ID=your_google_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_google_client_secret_here

# Microsoft OAuth Keys
MICROSOFT_CLIENT_ID=your_microsoft_client_id_guid_here
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret_value_here
```

---

## 5. Verifying OAuth Integration

1. Start your application server:
   ```bash
   uv run uvicorn app.main:app --reload
   ```
2. Navigate to `http://127.0.0.1:8000` in your web browser.
3. The auth login panel will now dynamically detect the configured OAuth keys and present the **Sign in with Google** and **Sign in with Microsoft** buttons!
