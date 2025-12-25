# CivicBot – Serverless WhatsApp Assistant for Civic Issue Management
CivicBot is a fully serverless conversational assistant built on AWS that allows citizens to report civic issues directly through WhatsApp. It leverages AI to classify priority, generate executive summaries for administrators, and enables real-time status notifications without requiring any server infrastructure.
This project demonstrates how modern cloud services, conversational AI, and event-driven architecture can be combined to build scalable digital governance platforms.

# Overview

CivicBot is designed to reduce friction in civic issue reporting and increase transparency between citizens and municipal teams.

Citizens interact via WhatsApp. Messages are routed through Twilio to an AWS API Gateway webhook, then processed by Amazon Lex V2 and AWS Lambda. All data is stored in DynamoDB and media in S3. Amazon Bedrock Titan models provide priority classification and executive summaries for administrators.

Admins and field staff manage issues using secure REST APIs protected by Amazon Cognito.

# Goals

- Simplify issue reporting using natural-language chat

- Provide citizens with tracking IDs and proactive notifications

- Enable data-driven governance using AI-generated summaries

- Use 100 percent serverless architecture for elasticity and low operational overhead

# Features
# 1. Citizen Flows

- Report Issue: Users submit descriptions, GPS or text location, and images via WhatsApp.

- Track Issue Status: Retrieve current status using tracking ID.

- Retrieve Issue ID: Search for forgotten tracking IDs using keywords and location.

- Rate Service: Citizens provide 1–5 star feedback after resolution.

# 2. Admin / Employee Flows

- Issue Listing & Filtering: Filter by New, Processing, Completed using REST APIs.

- Status Updates: Update issue state and expected completion date.

- AI Summaries: Generate executive dashboards using Bedrock Titan.

# 3. Automation

- AI Priority Classification: Assigns HIGH, MEDIUM, LOW severity automatically.

- Real-time Notifications: DynamoDB Streams trigger WhatsApp updates.

- Media Handling: Images are securely stored in S3 with optional analysis workflows.

# System Architecture
- High-level message flow:
  <img width="940" height="749" alt="image" src="https://github.com/user-attachments/assets/bce1f892-119c-4fb3-b2f3-417452b29e62" />

- Data Flow (Report Issue):
  <img width="940" height="504" alt="image" src="https://github.com/user-attachments/assets/d3a2b6e7-1129-44e4-b993-1b16489b472e" />

# AWS Services
| Service        | Purpose                       |
| -------------- | ----------------------------- |
| Amazon Lex V2  | NLP intent recognition        |
| AWS Lambda     | Stateless orchestration       |
| API Gateway    | Webhook + Admin REST APIs     |
| DynamoDB       | Issue and session data        |
| S3             | Media storage                 |
| Amazon Bedrock | AI classification + summaries |
| Cognito        | Admin authentication          |
| Twilio API     | WhatsApp integration          |
| CloudWatch     | Logs & metrics                |

# Tech Stack
| Layer             | Technology                          |
| ----------------- | ----------------------------------- |
| Runtime           | AWS Lambda (Python)                 |
| Conversational AI | Amazon Lex V2                       |
| AI Model          | Amazon Bedrock – Titan Text Express |
| Storage           | DynamoDB, S3                        |
| Messaging         | Twilio WhatsApp API                 |
| Auth              | Amazon Cognito                      |
| API Layer         | Amazon API Gateway                  |
| Observability     | CloudWatch                          |

# Data Models
- CivicIssues Table
{
  "IssueID": "a3b72c1e",
  "Category": "Garbage Overflow",
  "Description": "Garbage pile near 4th cross",
  "LocationText": "4th Cross, Ward 12",
  "GPS": { "lat": 13.06, "long": 77.59 },
  "Priority": "HIGH",
  "Status": "New",
  "CreatedTimestamp": 1732000000,
  "StatusLastModified": 1732000100,
  "ExpectedCompletionDate": "2025-12-02",
  "Attachments": ["s3://civicbot-media-reports/..."],
  "Rating": 5
}
GSI: Status-Timestamp-index
Partition key: Status
Sort key: CreatedTimestamp

- UserSessions Table
{
  "UserID": "wa:987654321",
  "LastIssueID": "a3b72c1e",
  "History": [],
  "LastSeen": 1732000200
}

# API Endpoints
| Method | Path               |
| ------ | ------------------ |
| GET    | /issues            |
| GET    | /issues?status=New |
| PUT    | /issues/{issueId}  |
| GET    | /stats             |
| POST   | /webhook           |

# Security & Compliance
- IAM roles use least privilege policies

- Twilio credentials stored in AWS Secrets Manager

- S3 bucket blocks all public access

- Cognito secures Admin APIs

# Observability
- Centralized logs in CloudWatch

- Structured JSON logging

- Alarms on error rate and latency

- Retry handling on DynamoDB Streams failures

- CORS and throttling configured in API Gateway
