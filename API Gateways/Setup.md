
# AWS API Gateway Setup Guide

This document details the configuration for the two REST APIs used in the CivicBot ecosystem: the **Twilio Webhook** (Inbound) and the **Admin API** (Outbound/Management).

## 1. API: `CivicBot_Twilio_Webhook`

**ID:** `47brb5stj5`

**Type:** REST (Regional)

**Purpose:** Acts as the entry point for all incoming WhatsApp messages from Twilio.

### Resources & Methods

* **Resource:** `/whatsapp`
* **Method:** `POST`
* **Integration Type:** Lambda Proxy Integration
* **Target Lambda:** `WhatsApp_Connector`

### Configuration Steps

1. **Create Resource:** Create a new resource named `whatsapp`.
2. **Create Method:** Under `/whatsapp`, create a `POST` method.
3. **Lambda Integration:** * Check **"Use Lambda Proxy integration"**.
* Select your `WhatsApp_Connector` function.

4. **Deploy API:**
* Create a new Stage (e.g., `prod`).
* **Webhook URL:** `https://47brb5stj5.execute-api.[region].amazonaws.com/prod/whatsapp`

5. **Twilio Linkage:** * Copy the Webhook URL.
* Paste it into your **Twilio Console** under the Sandbox/Phone Number settings for "A MESSAGE COMES IN."

<img width="175" height="130" alt="image" src="https://github.com/user-attachments/assets/f92faf6f-3af1-4d07-b047-f296576f0fad" />


## 2. API: `CivicBotAdminAPI`

**ID:** `t5qeu9sdn9`

**Type:** REST (Regional)

**Purpose:** Powers the Administrator Dashboard to retrieve and update civic reports.

### Resources & Methods

* **Resource:** `/issues`
* **Method:** `GET` (Retrieves all issues or filters via query params)
* **Target Lambda:** `CivicBot_Admin_Handler`
* **Resource:** `/issues/{issueId}`
* **Method:** `PUT` (Updates status/dates)
* **Target Lambda:** `CivicBot_Admin_Handler`

### Configuration Steps

1. **Enable CORS:** * Select the `/issues` resource.
* Click **Actions > Enable CORS**.
* *This is critical if your Admin Dashboard is hosted on a different domain (e.g., Vercel or localhost).*

2. **Path Parameters:**
* For the `PUT` method, ensure the resource path is `/issues/{issueId}`.
* This allows the Lambda to access the ID via `event['pathParameters']['issueId']`.

3. **Deploy API:**
* Create/Update the `prod` stage.
* **Base URL:** `https://t5qeu9sdn9.execute-api.[region].amazonaws.com/prod/`

<img width="235" height="400" alt="image" src="https://github.com/user-attachments/assets/0d8b6de1-4044-4634-a70f-6be0f820d351" />

## Security & Protocol Settings

| Setting | Value | Note |
| --- | --- | --- |
| **Protocol** | REST | Standard HTTP-based communication. |
| **Endpoint Type** | Regional | Reduced latency for users in the same AWS region. |
| **Min. TLS Version** | `TLS_1_2` | *Recommendation:* Update your `TLS_1_0` to `1_2` in the console for better security compliance. |
