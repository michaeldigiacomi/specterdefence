# SpecterDefence Full Solution Documentation

> **A comprehensive guide to the SpecterDefence Microsoft 365 security posture, threat monitoring, and response platform.**

---

## 1. Executive Summary

SpecterDefence is a scalable, API-driven security application explicitly designed to protect Microsoft 365 environments. It continuously ingests configurations, audit logs, and security policies from Office 365 tenants via the Microsoft Graph API and O365 Management Activity API. By performing near real-time correlation—including Cyber Threat Intelligence (CTI)—it proactively prevents identity compromise, policy drift, and sensitive data exposure.

It caters specifically to **organizations managing multiple M365 tenants**, such as Managed Service Providers (MSPs), enterprises with isolated business unit tenants, and Security Operations Centers (SOC).

---

## 2. Platform Capabilities

### 2.1 Identity Posture & Login Monitoring
- **MFA Compliance Checking:** Discovers and categorizes authentication methods. Identifies weak MFA (SMS/Voice) vs moderate (Authenticator App) vs strong (FIDO2, Windows Hello) methods.
- **Login Anomaly Detection:** Detects "Impossible Travel," brute-force attempts, and anomalous logins from new countries or known malicious IP addresses.
- **Approved Countries:** Configurable per-tenant allows restricting logins to specific geographic regions.

### 2.2 Insider Threat & Resource Security
- **SharePoint Sharing Analytics:** Tracks anonymous and external sharing links in SharePoint and OneDrive.
- **Data Loss Prevention (DLP):** Monitoring of DLP policy matches and sensitive data exposure events.
- **Endpoint Protection:** The Windows Endpoint Agent tracks device health and suspicious process executions. See [ENDPOINT-AGENT.md](./ENDPOINT-AGENT.md) for details.

### 2.3 Configuration Drift Monitoring
- **Conditional Access (CA) Tracker:** Analyzes changes in CA policies and alerts on misconfigurations.
- **Mailbox Rules Monitoring:** Detects suspicious forwarding or hidden redirect rules in Exchange Online.

### 2.3 Application Risk Assessment
- **OAuth App Monitoring:** Audits all Azure AD Enterprise Applications and App Registrations. Identifies high-risk API permissions (`Mail.ReadWrite`, `User.Read.All`) paired with unverified publishers, providing a prioritized list for remediation.

---

## 3. System Architecture

SpecterDefence utilizes a microservices architecture optimally deployed on Kubernetes.

### 3.1 The Backend (Core API)
- **Framework:** Written in Python 3.11+ using the **FastAPI** framework, ensuring high concurrency and performance.
- **Data Layer:** Uses **PostgreSQL** (via `SQLAlchemy` ORM) for long-term storage of tenant configuration, user assets, and alert history. Uses **Redis** for stateful caching and rate-limiting.
- **Graph Client (MSAL):** Manages OAuth 2.0 app-only authentication (Client Credentials flow) to pull data securely, observing pagination and M365 API rate limits.

### 3.2 The Frontend
- **Framework:** Built using **React + Vite + TypeScript**.
- **State Management:** **Zustand** ensures responsive data flow.
- A single-pane dashboard displays global M365 posture, aggregated tenant alerts, and specific analytics regarding recent incidents.

### 3.3 The Collector Engine
- The Collector runs as a continuous Kubernetes `CronJob` (or scheduled daemon process). 
- It actively polls the Microsoft ecosystems and utilizes an intricate batching mechanism to ensure large tenants (100,000+ objects) are completely scanned efficiently.
- Anomaly detectors function as pipelines, comparing previous state versus current state without heavy manual SIEM queries.

### 3.4 Storage & Security
- **Credential Storage:** Stores tenant `client_secrets` by encrypting them at rest with military-grade encryption using **Fernet (AES-128-CBC with HMAC-SHA256)** and PBKDF2 key derivation.
- **Secret Management Integration:** Natively supports HashiCorp Vault, AWS Secrets Manager, and Kubernetes External Secrets Operator.

---

## 4. Alerting & Notification Engine

Actionable alerts, not noise, are fundamental to SpecterDefence.

- **Intelligent Rules Syntax:** Customers customize threat rules based on Severity mapping (LOW, MEDIUM, HIGH, CRITICAL).
- **Advanced Deduplication:** Before dispatching an alert, SpecterDefence generates an event-unique SHA-256 hash (combining event type, email, IP address, user locations, and tenant ID). If a duplicate hash exists within the admin-defined `cooldown_minute` window, the alert is suppressed, eliminating alert storms.
- **Instant Webhooks:** WebSockets push live alerts directly to the dashboard, and integrations with Discord/Slack webhooks format and route the alarm immediately to responders.

---

## 5. Deployment Overview

SpecterDefence provides a Kubernetes Helm Chart out-of-the-box.

### 5.1 Deployment Steps
1. Configure necessary Kubernetes namespaces and secrets.
2. Provide the AES `ENCRYPTION_KEY` and Application `SECRET_KEY`. 
3. Apply the backend API pods, frontend pods, and collector cron jobs via `helm upgrade --install`.
4. SpecterDefence is deployed securely behind an Nginx or Traefik Ingress controller with strict Let's Encrypt TLS enabled, rate limiting, and defensive HTTP headers (CSP, HSTS).

*Refer to the full repository [ARCHITECTURE.md](./ARCHITECTURE.md) and [SECURE-DEPLOYMENT.md](./SECURE-DEPLOYMENT.md) for extended compliance and infrastructure guidance.*
