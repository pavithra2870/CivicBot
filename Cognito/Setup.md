# AWS Cognito Authentication Setup

This document provides instructions for setting up the User Pool and Client required to secure the **CivicBotAdminAPI** and the Administrator Dashboard.

## 1. User Pool Configuration

**Purpose:** Manages the database of administrator accounts.

### General Settings

* **Pool Name:** `CivicBot_Admin_Pool`
* **Sign-in Experience:** - **User Pool Sign-in:** Email (Usernames are not required).
* **Password Policy:** Custom (Recommend: Min 8 chars, 1 uppercase, 1 number).
* **MFA:** Optional (Keep "No MFA" for development, "Required" for production).

### 📝 User Attributes

* **Required Attributes:** `email`, `given_name` (First Name), `family_name` (Last Name).
* **Custom Attributes:** (Optional) `department` (e.g., Roadways, Sanitation).

## 2. App Client Settings

**Purpose:** Allows your Admin Dashboard (Frontend) to communicate with Cognito.

### App Client Configuration

* **App Client Name:** `CivicBot_Web_Client`
* **Refresh Token Expiration:** 30 days.
* **Authentication Flows:** - `ALLOW_USER_PASSWORD_AUTH`
* `ALLOW_REFRESH_TOKEN_AUTH`
* `ALLOW_USER_SRP_AUTH` (Secure Remote Password).

### 🌐 Hosted UI & OAuth 2.0

* **Allowed Callback URLs:** `http://localhost:3000` (for dev) and your production URL.
* **Allowed OAuth Flows:** `Implicit Grant` or `Authorization Code Grant`.
* **Allowed OAuth Scopes:** `email`, `openid`, `profile`.

## 3. Integrating Cognito with API Gateway

To secure the `CivicBotAdminAPI`, follow these steps to link Cognito as an **Authorizer**.

### 🛠️ Step-by-Step Integration

1. **Navigate to API Gateway:** Open API `ur-api`.
2. **Create Authorizer:**
* Click **Authorizers** > **Create New Authorizer**.
* **Name:** `CognitoAuthorizer`.
* **Type:** Cognito.
* **Cognito User Pool:** Select `CivicBot_Admin_Pool`.
* **Token Source:** `Authorization`.

3. **Apply to Methods:**
* Go to **Resources** > `/issues`.
* Select the `GET` or `PUT` method.
* Click **Method Request**.
* Edit **Authorization** and select `CognitoAuthorizer`.

4. **Deploy API:** Redeploy the `prod` stage for changes to take effect.

## Testing the Auth Flow

1. **Create User:** Manually create an admin user in the Cognito Console under the **Users** tab.
2. **Get ID Token:** Use the AWS CLI or your frontend login to obtain an `IdToken`.
3. **Invoke API:** Add the token to your header when calling the API:
```bash
curl -X GET https://t5qeu9sdn9.execute-api.us-east-1.amazonaws.com/prod/issues \
-H "Authorization: <YOUR_ID_TOKEN>"
```
