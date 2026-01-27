
**The Problem**

Cloud misconfigurations are a leading cause of data breaches.
One public S3 bucket. One open database port. One misconfigured security group. That's all it takes for attackers to access sensitive data.
The challenge: manually checking security settings across hundreds of cloud resources doesn't scale, and by the time you notice a misconfiguration, it may already be too late.

**The Solution**

CloudPlate is a production-ready restaurant review API that demonstrates how to build secure cloud applications with automated breach prevention.
It combines:

 * Real application - Flask REST API with sentiment analysis
 * Cloud deployment - Dockerized on AWS EC2
 * Automated security - AWS Config detects violations in real-time
 * Instant alerts - SNS emails security team immediately

**What It Does**

For Users:

Add restaurants and post reviews
AI automatically analyzes sentiment (positive/negative/neutral)
Real-time leaderboard ranked by customer happiness
Redis-powered caching for lightning-fast responses

For Security Teams:

CloudTrail logs every AWS action (audit trail)
AWS Config checks compliance rules automatically
CloudWatch monitors API health and errors
SNS sends email alerts when violations are detected


**Architecture**


**Application Layer (AWS EC2)**


Docker Compose Stack:

Flask API (Port 5000) - Handles REST requests
PostgreSQL Database - Stores restaurants & reviews
Redis Cache - Powers real-time leaderboard

**Security Monitoring Layer**


AWS Services:

CloudTrail - Audit logs for all AWS actions
AWS Config - Automated compliance rules
CloudWatch - Application logs & alarms
SNS - Email alerts for violations

Data Flow:
User Request → Flask API → PostgreSQL/Redis → CloudWatch Logs → Config Rules → SNS Alerts

**Tech Stack**

**Backend**:

-Flask 2.3 (Python web framework)
-PostgreSQL 15 (database)
-Redis 7 (caching layer)
-VADER Sentiment Analysis (NLP)
-SQLAlchemy (ORM)

**Infrastructure**:

-Docker & Docker Compose
-AWS EC2 (compute)
-AWS CloudWatch (monitoring & logs)
-AWS CloudTrail (audit logs)
-AWS Config (compliance rules)
-AWS SNS (email alerts)
-AWS IAM (access control)

**How It Works**

**1. The Application Layer**
Users interact with a Flask REST API that:

Stores restaurant and review data in PostgreSQL
Analyzes review sentiment using VADER NLP
Caches leaderboard rankings in Redis for fast queries
Returns JSON responses for all operations

**2. The Security Layer**
While the app runs, AWS services monitor everything:
CloudTrail: Records every AWS API call (who did what, when)
AWS Config: Continuously checks compliance rules (e.g., "Are any S3 buckets public?")
CloudWatch: Monitors API errors and creates alarms
SNS: Sends email alerts when violations are detected

**What's Next**
1.Immediate Improvements

 Add JWT authentication
 Implement rate limiting
 Add HTTPS/SSL certificate
 Set up CI/CD pipeline

2.Scalability

 Auto Scaling Group + Load Balancer
 Migrate to RDS (managed PostgreSQL)
 Migrate to ElastiCache (managed Redis)
 Multi-region deployment

3.Advanced Features

 Custom ML model for domain-specific sentiment
 Fraud detection for fake reviews
 GraphQL API
 Admin dashboard