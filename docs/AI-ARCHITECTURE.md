# SpecterDefence AI Architecture Design

## Table of Contents
1. [System Overview](#1-system-overview)
2. [AI Layer Components](#2-ai-layer-components)
3. [Database Schema](#3-database-schema)
4. [API Specifications](#4-api-specifications)
5. [Kimi Integration](#5-kimi-integration)
6. [Learning Loop](#6-learning-loop)

---

## 1. System Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SpecterDefence AI Platform                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        API Gateway (FastAPI)                         │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │    │
│  │  │   /ai/query  │  │/ai/analyze-* │  │ /ai/feedback │  │/insights │ │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────┬─────┘ │    │
│  └─────────┼─────────────────┼─────────────────┼───────────────┼───────┘    │
│            │                 │                 │               │            │
│  ┌─────────▼─────────────────▼─────────────────▼───────────────▼───────┐    │
│  │                      AI Orchestration Layer                          │    │
│  │         (Task routing, caching, rate limiting, monitoring)           │    │
│  └─────────────────────────┬──────────────────────────────────────────┘    │
│                            │                                               │
│  ┌─────────────────────────┼───────────────────────────────────────────┐   │
│  │                         ▼                   AI Service Layer          │   │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐         │   │
│  │  │ Alert Enrichment│ │ Adaptive Thresh │ │  NLP Query Eng  │         │   │
│  │  │    Service      │ │     Engine      │ │                 │         │   │
│  │  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘         │   │
│  │  ┌────────┴───────────────────┴───────────────────┴────────┐         │   │
│  │  │              Behavioral Analysis Service                │         │   │
│  │  │     (User baselines, anomaly detection, UEBA)          │         │   │
│  │  └─────────────────────────┬───────────────────────────────┘         │   │
│  │  ┌─────────────────────────┴─────────────────────────────────┐       │   │
│  │  │              Auto-Response Engine                          │       │   │
│  │  │     (Policy engine, automated actions, playbooks)          │       │   │
│  │  └───────────────────────────────────────────────────────────┘       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                            │                                                │
│  ┌─────────────────────────┼───────────────────────────────────────────┐   │
│  │                         ▼                    Kimi API Integration     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │                    Kimi API Client                           │     │   │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────┐ │     │   │
│  │  │  │  Prompt    │  │   Rate     │  │   Cache    │  │ Retry  │ │     │   │
│  │  │  │ Templates  │  │  Limiter   │  │   Layer    │  │ Logic  │ │     │   │
│  │  │  └────────────┘  └────────────┘  └────────────┘  └────────┘ │     │   │
│  │  └─────────────────────────┬───────────────────────────────────┘     │   │
│  │                            │                                          │   │
│  │  ┌─────────────────────────▼─────────────────────────────────────┐   │   │
│  │  │                    Kimi API (Moonshot AI)                      │   │   │
│  │  │              https://api.moonshot.cn/v1/chat/completions       │   │   │
│  │  └────────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                            │                                                │
│  ┌─────────────────────────▼───────────────────────────────────────────┐   │
│  │                         Data Layer                                   │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │ ai_analysis│  │ai_decisions│  │ user_behav │  │ai_models   │     │   │
│  │  │            │  │            │  │_baselines  │  │            │     │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘     │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                     │   │
│  │  │alert_feedbk│  │  tenants   │  │   alerts   │                     │   │
│  │  │            │  │            │  │            │                     │   │
│  │  └────────────┘  └────────────┘  └────────────┘                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Interaction Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Alert Processing Flow                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐          │
│   │  Alert   │────▶│  Alert   │────▶│   AI     │────▶│ Enriched │          │
│   │ Triggered│     │ Stored   │     │Analysis  │     │  Alert   │          │
│   └──────────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘          │
│                         │                │                │                │
│                         ▼                ▼                ▼                │
│                    ┌──────────┐     ┌──────────┐     ┌──────────┐          │
│                    │  Alert   │     │  Kimi    │     │  Analyst │          │
│                    │  Table   │     │  API     │     │  Review  │          │
│                    └──────────┘     └──────────┘     └────┬─────┘          │
│                                                          │                 │
│                               ┌──────────────────────────┘                 │
│                               ▼                                            │
│                          ┌──────────┐     ┌──────────┐                     │
│                          │ Feedback │────▶│ Learning │                     │
│                          │ Captured │     │  Loop    │                     │
│                          └──────────┘     └──────────┘                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Data Flow for AI-Enhanced Alerts

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI-Enhanced Alert Data Flow                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Stage 1: Alert Ingestion                                              │   │
│  │  • Microsoft Graph API streams audit logs                            │   │
│  │  • Detection rules evaluate patterns                                 │   │
│  │  • Alert created with raw event data                                 │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Stage 2: Context Enrichment                                           │   │
│  │  • Fetch user history and baseline behavior                          │   │
│  │  • Query related alerts (same user, IP, time window)                 │   │
│  │  • Gather tenant security posture context                            │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Stage 3: AI Analysis                                                  │   │
│  │  • Send enriched context to Kimi API                                 │   │
│  │  • Generate risk assessment and severity recommendation              │   │
│  │  • Produce natural language summary and remediation steps            │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Stage 4: Decision & Storage                                           │   │
│  │  • Store AI analysis in ai_analysis table                            │   │
│  │  • Log decision in ai_decisions for audit trail                      │   │
│  │  • Update alert with AI-enhanced fields                              │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Stage 5: Action & Feedback                                            │   │
│  │  • Auto-response engine evaluates policy triggers                    │   │
│  │  • Alert presented to analyst with AI context                        │   │
│  │  • Analyst feedback captured for learning loop                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. AI Layer Components

### 2.1 Alert Enrichment Service

**Purpose:** Automatically analyzes security alerts using AI to provide context, risk assessment, and actionable recommendations.

#### Architecture

```python
class AlertEnrichmentService:
    """
    Enriches security alerts with AI-generated analysis.
    """
    
    async def enrich_alert(self, alert_id: str) -> AIAnalysis:
        # 1. Gather context
        alert = await self.get_alert(alert_id)
        user_history = await self.get_user_history(alert.user_id)
        related_alerts = await self.get_related_alerts(alert)
        tenant_context = await self.get_tenant_security_posture(alert.tenant_id)
        
        # 2. Build prompt
        prompt = self.build_analysis_prompt(
            alert=alert,
            user_history=user_history,
            related_alerts=related_alerts,
            tenant_context=tenant_context
        )
        
        # 3. Call Kimi API
        analysis = await self.kimi_client.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=2048
        )
        
        # 4. Parse and store
        return await self.store_analysis(alert_id, analysis)
```

#### Key Features

| Feature | Description | Implementation |
|---------|-------------|----------------|
| Risk Scoring | Multi-factor risk assessment (1-100) | Kimi analyzes 10+ risk factors |
| Severity Recommendation | Suggests LOW/MEDIUM/HIGH/CRITICAL | Based on risk score + context |
| Attack Chain Detection | Links related alerts into campaigns | Graph analysis of alert relationships |
| Remediation Guidance | Step-by-step response actions | Context-aware recommendations |
| False Positive Flag | Indicates potential false positive | Confidence score + reasoning |

#### Enrichment Data Model

```python
class AIAnalysis(BaseModel):
    id: UUID
    alert_id: UUID
    
    # Analysis Results
    summary: str  # Natural language summary
    risk_score: int  # 0-100
    recommended_severity: AlertSeverity
    false_positive_probability: float  # 0.0-1.0
    
    # Risk Factors
    risk_factors: List[RiskFactor]
    
    # Recommendations
    remediation_steps: List[RemediationStep]
    suggested_actions: List[AutoAction]
    
    # Metadata
    model_version: str
    created_at: datetime
    processing_time_ms: int

class RiskFactor(BaseModel):
    name: str
    severity: str  # info, low, medium, high, critical
    description: str
    confidence: float

class RemediationStep(BaseModel):
    order: int
    action: str
    automation_available: bool
    estimated_time: str
```

### 2.2 Adaptive Threshold Engine

**Purpose:** Learns from analyst feedback to automatically tune alert thresholds and reduce false positives.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Adaptive Threshold Engine                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Learning Pipeline                                                     │   │
│  │                                                                       │   │
│  │  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌──────────┐  │   │
│  │  │   Alert    │───▶│  Analyst   │───▶│  Feedback  │───▶│  Model   │  │   │
│  │  │   Fires    │    │  Reviews   │    │  Stored    │    │  Update  │  │   │
│  │  └────────────┘    └────────────┘    └────────────┘    └──────────┘  │   │
│  │        │                                                  │          │   │
│  │        │              ┌─────────────────────────────────────┘          │   │
│  │        │              ▼                                                │   │
│  │        │    ┌──────────────────┐    ┌──────────────────┐              │   │
│  │        └───▶│  Pattern Detect  │───▶│ Threshold Adjust │              │   │
│  │             │  (User/Rule/Time)│    │  (Auto/Manual)   │              │   │
│  │             └──────────────────┘    └──────────────────┘              │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Threshold Types                                                       │   │
│  │                                                                       │   │
│  │  • Global:      Organization-wide baseline                            │   │
│  │  • Per-User:    Individual user behavior patterns                     │   │
│  │  • Per-Rule:    Detection rule sensitivity                            │   │
│  │  • Per-Tenant:  Tenant-specific adjustments                           │   │
│  │  • Temporal:    Time-based variations (business hours vs off-hours)    │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Learning Algorithm

```python
class AdaptiveThresholdEngine:
    """
    Learns from analyst feedback to optimize alert thresholds.
    """
    
    async def process_feedback(self, feedback: AlertFeedback):
        """Process analyst feedback to update thresholds."""
        
        # Update feedback statistics
        await self.update_feedback_stats(feedback)
        
        # Check if threshold adjustment needed
        if await self.should_adjust_threshold(feedback.alert_id):
            # Calculate new threshold
            adjustment = await self.calculate_adjustment(feedback)
            
            # Apply adjustment
            await self.apply_threshold_adjustment(
                rule_id=feedback.rule_id,
                user_id=feedback.user_id,
                tenant_id=feedback.tenant_id,
                adjustment=adjustment
            )
    
    async def calculate_adjustment(self, feedback: AlertFeedback) -> Adjustment:
        """Calculate threshold adjustment based on feedback patterns."""
        
        # Get recent feedback for this context
        recent_feedback = await self.get_recent_feedback(
            rule_id=feedback.rule_id,
            user_id=feedback.user_id,
            days=30
        )
        
        # Calculate false positive rate
        total = len(recent_feedback)
        false_positives = sum(1 for f in recent_feedback if f.is_false_positive)
        fp_rate = false_positives / total if total > 0 else 0
        
        # Determine adjustment direction
        if fp_rate > 0.7:  # High FP rate - raise threshold
            return Adjustment(direction="increase", magnitude=0.15)
        elif fp_rate < 0.1:  # Low FP rate - may be missing alerts
            return Adjustment(direction="decrease", magnitude=0.05)
        else:
            return Adjustment(direction="maintain", magnitude=0)
```

#### Threshold Configuration

```python
class AdaptiveThreshold(BaseModel):
    id: UUID
    rule_id: Optional[UUID]  # Null for global thresholds
    user_id: Optional[str]   # Null for non-user-specific
    tenant_id: UUID
    
    # Threshold Values
    base_threshold: float  # Original rule threshold
    current_threshold: float  # Adjusted threshold
    adjustment_history: List[ThresholdAdjustment]
    
    # Learning State
    total_alerts: int
    false_positives: int
    true_positives: int
    fp_rate_7d: float
    fp_rate_30d: float
    
    # Auto-adjustment settings
    auto_adjust_enabled: bool
    min_samples_before_adjust: int  # Min alerts before auto-adjust
    max_adjustment_percent: float  # Cap on total adjustment
    
    created_at: datetime
    updated_at: datetime
```

### 2.3 NLP Query Engine

**Purpose:** Converts natural language security questions into database queries.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NLP Query Engine                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Query Processing Pipeline                                             │   │
│  │                                                                       │   │
│  │   User Query: "Show me admins without MFA enabled"                   │   │
│  │                    │                                                  │   │
│  │                    ▼                                                  │   │
│  │   ┌────────────────────────────┐                                     │   │
│  │   │  Intent Classification     │  →  IDENTIFY_USERS_WITHOUT_MFA     │   │
│  │   └────────────────────────────┘                                     │   │
│  │                    │                                                  │   │
│  │                    ▼                                                  │   │
│  │   ┌────────────────────────────┐                                     │   │
│  │   │  Entity Extraction         │  →  {role: "admin", has_mfa: false}│   │
│  │   └────────────────────────────┘                                     │   │
│  │                    │                                                  │   │
│  │                    ▼                                                  │   │
│  │   ┌────────────────────────────┐                                     │   │
│  │   │  SQL Generation (Kimi)     │  →  SELECT u.* FROM users u...     │   │
│  │   └────────────────────────────┘                                     │   │
│  │                    │                                                  │   │
│  │                    ▼                                                  │   │
│  │   ┌────────────────────────────┐                                     │   │
│  │   │  Query Validation          │  →  Check for injection, limits    │   │
│  │   └────────────────────────────┘                                     │   │
│  │                    │                                                  │   │
│  │                    ▼                                                  │   │
│  │   ┌────────────────────────────┐                                     │   │
│  │   │  Results Formatting        │  →  Natural language response      │   │
│  │   └────────────────────────────┘                                     │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Query Types Supported

| Category | Example Queries | SQL Complexity |
|----------|-----------------|----------------|
| User Lookup | "Who logged in from Russia?" | Simple WHERE clauses |
| Aggregation | "Failed logins by hour this week" | GROUP BY, time functions |
| Comparison | "Compare login failures this week vs last" | Window functions, CTEs |
| Correlation | "Users who accessed file X and then emailed it" | JOINs, subqueries |
| Anomaly | "Show unusual admin activity" | Statistical functions |
| Compliance | "Which users haven't completed security training?" | Multi-table joins |

#### Implementation

```python
class NLPQueryEngine:
    """
    Converts natural language to SQL queries.
    """
    
    # Database schema for context
    SCHEMA_CONTEXT = """
    Database Schema:
    
    Table: users
    - id (UUID): User ID
    - email (TEXT): User email
    - tenant_id (UUID): Organization tenant
    - role (TEXT): admin, user, guest
    - created_at (TIMESTAMP)
    - last_login_at (TIMESTAMP)
    - mfa_enabled (BOOLEAN)
    
    Table: login_events
    - id (UUID)
    - user_id (UUID) → users.id
    - timestamp (TIMESTAMP)
    - ip_address (INET)
    - location (TEXT): City, Country
    - success (BOOLEAN)
    - auth_method (TEXT): password, mfa, sso
    
    Table: alerts
    - id (UUID)
    - user_id (UUID) → users.id
    - rule_id (UUID)
    - severity (TEXT): low, medium, high, critical
    - status (TEXT): open, acknowledged, resolved, dismissed
    - created_at (TIMESTAMP)
    - ai_risk_score (INTEGER): 0-100
    """
    
    async def process_query(self, query: str, tenant_id: UUID) -> QueryResult:
        """Process a natural language query."""
        
        # Build prompt with schema and examples
        prompt = f"""{self.SCHEMA_CONTEXT}

Convert this natural language question to a SQL query:
Question: {query}

Requirements:
- Use only the tables defined above
- Add tenant_id = '{tenant_id}' filter for all queries
- Use proper SQL syntax (PostgreSQL)
- Limit results to 1000 rows by default
- Add appropriate ORDER BY for consistent results

Respond in this JSON format:
{{
    "sql": "SELECT ...",
    "description": "What this query does",
    "parameters": {{}},
    "estimated_rows": number
}}
"""
        
        # Call Kimi API
        response = await self.kimi_client.generate(
            prompt=prompt,
            temperature=0.1,  # Low creativity for SQL
            response_format={"type": "json_object"}
        )
        
        # Parse and validate
        query_spec = json.loads(response)
        validated_sql = self.validate_sql(query_spec["sql"])
        
        # Execute with safety limits
        results = await self.execute_safe_query(validated_sql)
        
        # Generate natural language summary
        summary = await self.summarize_results(query, results)
        
        return QueryResult(
            original_query=query,
            sql=validated_sql,
            results=results,
            summary=summary
        )
    
    def validate_sql(self, sql: str) -> str:
        """Validate SQL for safety before execution."""
        
        # Block dangerous operations
        forbidden_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 'ALTER']
        sql_upper = sql.upper()
        
        for keyword in forbidden_keywords:
            if keyword in sql_upper:
                raise UnsafeQueryError(f"Forbidden operation: {keyword}")
        
        # Ensure LIMIT is present
        if 'LIMIT' not in sql_upper:
            sql += " LIMIT 1000"
        
        return sql
```

### 2.4 Behavioral Analysis Service

**Purpose:** Establishes baselines for user behavior and detects anomalies using statistical and ML-based methods.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Behavioral Analysis Service                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Baseline Creation                                                     │   │
│  │                                                                       │   │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌───────────┐ │   │
│  │  │ Collect 30d │──▶│  Extract    │──▶│  Calculate  │──▶│  Store    │ │   │
│  │  │  History    │   │  Features   │   │  Statistics │   │  Baseline │ │   │
│  │  └─────────────┘   └─────────────┘   └─────────────┘   └───────────┘ │   │
│  │                                                                       │   │
│  │  Features Tracked:                                                    │   │
│  │  • Login times (hour of day, day of week)                            │   │
│  │  • Locations (countries, cities, IP ranges)                          │   │
│  │  • Applications accessed                                             │   │
│  │  • Data access patterns (files, volume)                              │   │
│  │  • Admin actions frequency                                           │   │
│  │  • Peer group comparisons                                            │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Anomaly Detection                                                     │   │
│  │                                                                       │   │
│  │  Current Activity ──▶ Feature Extraction ──▶ Compare to Baseline      │   │
│  │                                                      │                │   │
│  │                                                      ▼                │   │
│  │                                            ┌─────────────────┐        │   │
│  │                                            │  Z-Score / IQR  │        │   │
│  │                                            │  Deviation Calc │        │   │
│  │                                            └────────┬────────┘        │   │
│  │                                                     │                 │   │
│  │                              ┌──────────────────────┼────────┐        │   │
│  │                              ▼                      ▼        ▼        │   │
│  │                         [Normal]              [Suspicious] [Anomaly]  │   │
│  │                         (0-2σ)                (2-3σ)       (>3σ)      │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### User Behavior Profile

```python
class UserBehaviorBaseline(BaseModel):
    """Baseline behavioral profile for a user."""
    
    id: UUID
    user_id: str
    tenant_id: UUID
    
    # Time-based patterns
    login_time_distribution: TimeDistribution  # Hour of day
    work_days: List[int]  # 0=Monday, 6=Sunday
    typical_session_duration: DurationStats
    
    # Location patterns
    common_locations: List[LocationPattern]
    ip_ranges: List[IPRangePattern]
    country_whitelist: List[str]  # Countries user normally accesses from
    
    # Application patterns
    app_usage_frequency: Dict[str, FrequencyStats]  # app_name -> stats
    admin_action_frequency: Dict[str, FrequencyStats]
    
    # Data access patterns
    typical_download_volume: VolumeStats  # MB per day
    typical_share_count: FrequencyStats
    sensitive_file_access: FrequencyStats
    
    # Peer comparison
    department: Optional[str]
    role: str
    peer_group_baseline: Optional[PeerGroupStats]
    
    # Model metadata
    baseline_period_days: int
    sample_size: int
    confidence_score: float  # 0-1, higher = more reliable
    last_updated: datetime
    
    # Versioning
    version: int
    previous_version_id: Optional[UUID]

class TimeDistribution(BaseModel):
    """Statistical distribution of activity times."""
    hourly_histogram: List[int]  # 24 values, count per hour
    mean_hour: float  # 0-24
    std_deviation: float
    is_business_hours_heavy: bool

class FrequencyStats(BaseModel):
    """Statistical frequency metrics."""
    daily_mean: float
    daily_std: float
    weekly_pattern: List[float]  # 7 values
    seasonal_adjustment: Optional[Dict[str, float]]
```

#### Anomaly Detection Algorithm

```python
class BehavioralAnalysisService:
    """
    Detects behavioral anomalies based on user baselines.
    """
    
    async def analyze_activity(
        self,
        user_id: str,
        activity: UserActivity
    ) -> AnomalyReport:
        """Analyze user activity for anomalies."""
        
        # Get user's baseline
        baseline = await self.get_user_baseline(user_id)
        
        if not baseline or baseline.confidence_score < 0.5:
            # Insufficient data for reliable detection
            return AnomalyReport(
                user_id=user_id,
                anomaly_score=0,
                anomalies=[],
                reliability="low"
            )
        
        anomalies = []
        total_score = 0
        
        # Check time-based anomaly
        time_anomaly = self.check_time_anomaly(
            activity.timestamp, baseline.login_time_distribution
        )
        if time_anomaly.score > 2.0:
            anomalies.append(time_anomaly)
            total_score += time_anomaly.score
        
        # Check location anomaly
        location_anomaly = self.check_location_anomaly(
            activity.location, baseline.common_locations
        )
        if location_anomaly.score > 2.0:
            anomalies.append(location_anomaly)
            total_score += location_anomaly.score
        
        # Check application access anomaly
        app_anomaly = self.check_app_anomaly(
            activity.application, baseline.app_usage_frequency
        )
        if app_anomaly.score > 2.0:
            anomalies.append(app_anomaly)
            total_score += app_anomaly.score
        
        # Check volume anomaly
        volume_anomaly = self.check_volume_anomaly(
            activity.data_volume, baseline.typical_download_volume
        )
        if volume_anomaly.score > 2.0:
            anomalies.append(volume_anomaly)
            total_score += volume_anomaly.score
        
        # Calculate combined anomaly score
        combined_score = min(total_score / len(anomalies) if anomalies else 0, 10)
        
        return AnomalyReport(
            user_id=user_id,
            anomaly_score=combined_score,
            anomalies=anomalies,
            reliability="high" if baseline.confidence_score > 0.8 else "medium"
        )
    
    def check_location_anomaly(
        self,
        current_location: Location,
        baseline_locations: List[LocationPattern]
    ) -> Anomaly:
        """Check if current location is anomalous."""
        
        # Check if in known locations
        for loc in baseline_locations:
            if self.is_same_location(current_location, loc):
                return Anomaly(
                    type="location",
                    score=0,
                    description="Location in normal pattern"
                )
        
        # Check for impossible travel
        last_location = self.get_last_known_location(current_location.user_id)
        if last_location:
            travel_time = current_location.timestamp - last_location.timestamp
            distance = self.calculate_distance(last_location, current_location)
            
            if distance > 500 and travel_time < timedelta(hours=4):
                return Anomaly(
                    type="impossible_travel",
                    score=10,
                    description=f"Impossible travel: {distance}km in {travel_time}"
                )
        
        # New country check
        known_countries = {loc.country for loc in baseline_locations}
        if current_location.country not in known_countries:
            return Anomaly(
                type="new_country",
                score=5,
                description=f"First access from {current_location.country}"
            )
        
        return Anomaly(type="location", score=0, description="")
```

### 2.5 Auto-Response Engine

**Purpose:** Executes automated response actions based on policy rules with confidence thresholds.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Auto-Response Engine                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Policy-Based Decision Tree                                            │   │
│  │                                                                       │   │
│  │  Alert + AI Analysis                                                  │   │
│  │       │                                                               │   │
│  │       ▼                                                               │   │
│  │  ┌─────────────────┐                                                  │   │
│  │  │ Evaluate Policies│                                                 │   │
│  │  └────────┬────────┘                                                  │   │
│  │           │                                                           │   │
│  │     ┌─────┴─────┬─────────────┬──────────────┐                        │   │
│  │     ▼           ▼             ▼              ▼                        │   │
│  │  ┌──────┐   ┌──────┐    ┌──────────┐   ┌──────────┐                  │   │
│  │  │Confidence│   │Severity│    │  Risk    │   │ Business │                  │   │
│  │  │  ≥ 95%  │   │CRITICAL│    │  Score   │   │  Impact  │                  │   │
│  │  └────┬───┘   └───┬───┘    └────┬─────┘   └────┬─────┘                  │   │
│  │       │           │             │              │                        │   │
│  │       └───────────┴──────┬──────┴──────────────┘                        │   │
│  │                          ▼                                             │   │
│  │              ┌───────────────────────┐                                 │   │
│  │              │   Decision Engine     │                                 │   │
│  │              └───────────┬───────────┘                                 │   │
│  │                          │                                             │   │
│  │        ┌─────────────────┼─────────────────┐                          │   │
│  │        ▼                 ▼                 ▼                          │   │
│  │   ┌──────────┐     ┌──────────┐     ┌──────────┐                      │   │
│  │   │  AUTO    │     │  SUGGEST │     │  NOTIFY  │                      │   │
│  │   │ EXECUTE  │     │  ACTION  │     │  ONLY    │                      │   │
│  │   └────┬─────┘     └────┬─────┘     └────┬─────┘                      │   │
│  │        │                │                │                             │   │
│  │        ▼                ▼                ▼                             │   │
│  │   Immediate      Recommend to      Queue for analyst                  │   │
│  │   action         analyst           review                             │   │
│  │   (logged)       (requires         (no auto-action)                   │   │
│  │                  approval)                                             │   │
│  │                                                                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Available Actions                                                     │   │
│  │                                                                       │   │
│  │  User Actions:          Session Actions:         Tenant Actions:      │   │
│  │  • Disable user         • Revoke all sessions    • Increase logging   │   │
│  │  • Reset password       • Revoke specific app    • Enable MFA req     │   │
│  │  • Require MFA reset    • Block IP               • Alert admins       │   │
│  │  • Add to watchlist                                                  │   │
│  │                                                                       │   │
│  │  Notification Actions:                                                │   │
│  │  • Email admin          • Slack alert         • Webhook               │   │
│  │  • SMS on-call          • Create ticket       • PagerDuty             │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Policy Configuration

```python
class AutoResponsePolicy(BaseModel):
    """Policy for automated response actions."""
    
    id: UUID
    name: str
    tenant_id: UUID
    enabled: bool
    priority: int  # Higher = evaluated first
    
    # Matching conditions
    conditions: PolicyConditions
    
    # Response configuration
    action_type: AutoActionType
    action_config: Dict[str, Any]
    
    # Execution settings
    execution_mode: ExecutionMode  # auto, suggest, disabled
    require_approval_above_severity: Optional[AlertSeverity]
    
    # Safety limits
    daily_action_limit: int  # Max auto-actions per day
    cooldown_hours: float  # Hours before re-triggering for same user
    
    created_at: datetime
    updated_at: datetime

class PolicyConditions(BaseModel):
    """Conditions for triggering a policy."""
    
    # Alert characteristics
    min_severity: Optional[AlertSeverity]
    alert_types: Optional[List[str]]
    
    # AI analysis criteria
    min_ai_confidence: float  # 0-1
    min_risk_score: int  # 0-100
    
    # User criteria
    user_roles: Optional[List[str]]
    exclude_users: Optional[List[str]]
    
    # Behavioral criteria
    behavioral_anomaly_score: Optional[float]
    
    # Time-based
    active_hours_only: bool  # Only auto-respond during business hours
    
    # Composite conditions (AND/OR logic)
    require_all: bool = True  # True = AND, False = OR

class ExecutionMode(str, Enum):
    """How the action should be executed."""
    AUTO = "auto"        # Execute immediately
    SUGGEST = "suggest"  # Recommend to analyst
    DISABLED = "disabled"  # Policy disabled
```

#### Action Execution

```python
class AutoResponseEngine:
    """
    Executes automated response actions based on policies.
    """
    
    async def evaluate_and_execute(
        self,
        alert: Alert,
        ai_analysis: AIAnalysis
    ) -> ActionResult:
        """Evaluate policies and execute appropriate actions."""
        
        # Get applicable policies
        policies = await self.get_applicable_policies(
            tenant_id=alert.tenant_id,
            alert=alert,
            ai_analysis=ai_analysis
        )
        
        for policy in sorted(policies, key=lambda p: p.priority, reverse=True):
            # Check if conditions met
            if not self.check_conditions(policy.conditions, alert, ai_analysis):
                continue
            
            # Check rate limits
            if not await self.check_rate_limits(policy, alert):
                logger.warning(f"Rate limit exceeded for policy {policy.id}")
                continue
            
            # Execute based on mode
            if policy.execution_mode == ExecutionMode.AUTO:
                result = await self.execute_action(policy, alert, ai_analysis)
                await self.log_decision(policy, alert, result, auto_executed=True)
                return result
                
            elif policy.execution_mode == ExecutionMode.SUGGEST:
                await self.suggest_action(policy, alert, ai_analysis)
                await self.log_decision(policy, alert, None, auto_executed=False)
                return ActionResult(
                    status="suggested",
                    message="Action suggested to analyst"
                )
        
        return ActionResult(
            status="no_action",
            message="No matching policies"
        )
    
    async def execute_action(
        self,
        policy: AutoResponsePolicy,
        alert: Alert,
        ai_analysis: AIAnalysis
    ) -> ActionResult:
        """Execute the configured action."""
        
        action_handlers = {
            AutoActionType.DISABLE_USER: self.handle_disable_user,
            AutoActionType.REVOKE_SESSIONS: self.handle_revoke_sessions,
            AutoActionType.RESET_PASSWORD: self.handle_reset_password,
            AutoActionType.BLOCK_IP: self.handle_block_ip,
            AutoActionType.NOTIFY_ADMIN: self.handle_notify_admin,
            AutoActionType.ADD_TO_WATCHLIST: self.handle_add_to_watchlist,
        }
        
        handler = action_handlers.get(policy.action_type)
        if not handler:
            raise ValueError(f"Unknown action type: {policy.action_type}")
        
        # Execute with timeout and error handling
        try:
            result = await asyncio.wait_for(
                handler(policy.action_config, alert, ai_analysis),
                timeout=30
            )
            
            # Create audit log entry
            await self.create_audit_log(policy, alert, result)
            
            return result
            
        except asyncio.TimeoutError:
            return ActionResult(
                status="failed",
                message="Action timed out"
            )
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return ActionResult(
                status="failed",
                message=str(e)
            )
    
    async def handle_disable_user(
        self,
        config: Dict[str, Any],
        alert: Alert,
        ai_analysis: AIAnalysis
    ) -> ActionResult:
        """Disable a user account."""
        
        # Get Microsoft Graph client for tenant
        graph_client = await self.get_graph_client(alert.tenant_id)
        
        # Disable user
        await graph_client.users.by_id(alert.user_id).patch({
            "accountEnabled": False
        })
        
        # Notify security team
        await self.send_notification(
            tenant_id=alert.tenant_id,
            subject=f"User {alert.user_id} auto-disabled",
            body=f"User was automatically disabled due to alert: {alert.id}"
        )
        
        return ActionResult(
            status="success",
            action="disable_user",
            target=alert.user_id,
            message="User account disabled"
        )
```

---

## 3. Database Schema

### 3.1 Schema Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AI Layer Database Schema                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │   ai_analysis    │◄─────────────────────────────────────────────┐        │
│  ├──────────────────┤                                             │        │
│  │ id (PK)          │                                             │        │
│  │ alert_id (FK)    │──────┐                                     │        │
│  │ model_version    │      │                                     │        │
│  │ risk_score       │      │                                     │        │
│  │ summary          │      │                                     │        │
│  │ recommendations  │      │                                     │        │
│  │ created_at       │      │                                     │        │
│  └──────────────────┘      │                                     │        │
│                            │                                     │        │
│  ┌──────────────────┐      │    ┌──────────────────┐              │        │
│  │   ai_decisions   │      │    │ alert_feedback   │              │        │
│  ├──────────────────┤      │    ├──────────────────┤              │        │
│  │ id (PK)          │      │    │ id (PK)          │              │        │
│  │ alert_id (FK)    │◄─────┼────│ alert_id (FK)    │              │        │
│  │ policy_id (FK)   │      │    │ ai_analysis_id   │──────────────┘        │
│  │ action_taken     │      │    │ analyst_id (FK)  │                       │
│  │ auto_executed    │      │    │ was_accurate     │                       │
│  │ outcome          │      │    │ is_false_positive│                       │
│  │ confidence       │      │    │ feedback_text    │                       │
│  │ executed_at      │      │    │ created_at       │                       │
│  └──────────────────┘      │    └──────────────────┘                       │
│                            │                                               │
│  ┌──────────────────┐      │    ┌──────────────────┐                       │
│  │ user_behavior_   │      │    │    ai_models     │                       │
│  │   baselines      │      │    ├──────────────────┤                       │
│  ├──────────────────┤      │    │ id (PK)          │                       │
│  │ id (PK)          │      │    │ name             │                       │
│  │ user_id (FK)     │◄─────┘    │ version          │                       │
│  │ tenant_id (FK)   │           │ model_type       │                       │
│  │ baseline_data    │           │ training_metrics │                       │
│  │ confidence_score │           │ performance      │                       │
│  │ version          │           │ deployed_at      │                       │
│  │ last_updated     │           │ is_active        │                       │
│  └──────────────────┘           └──────────────────┘                       │
│                                                                              │
│  Relationships:                                                              │
│  • alerts.id ←── ai_analysis.alert_id                                       │
│  • alerts.id ←── ai_decisions.alert_id                                      │
│  • ai_analysis.id ←── alert_feedback.ai_analysis_id                         │
│  • users.id ←── user_behavior_baselines.user_id                             │
│  • ai_models.id ←── ai_decisions.model_version (implicit)                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Table Definitions

#### ai_analysis

```sql
-- Stores AI-generated analysis for security alerts
CREATE TABLE ai_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Analysis content
    summary TEXT NOT NULL,
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
    recommended_severity VARCHAR(20) CHECK (recommended_severity IN ('low', 'medium', 'high', 'critical')),
    false_positive_probability DECIMAL(3,2) CHECK (false_positive_probability >= 0 AND false_positive_probability <= 1),
    
    -- Detailed analysis (JSON)
    risk_factors JSONB NOT NULL DEFAULT '[]',
    remediation_steps JSONB NOT NULL DEFAULT '[]',
    suggested_actions JSONB NOT NULL DEFAULT '[]',
    attack_chain_analysis JSONB,
    
    -- Model metadata
    model_version VARCHAR(50) NOT NULL,
    model_provider VARCHAR(20) NOT NULL DEFAULT 'kimi',
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    
    -- Performance metrics
    processing_time_ms INTEGER,
    api_latency_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '90 days'),
    
    -- Constraints
    CONSTRAINT unique_alert_analysis UNIQUE (alert_id)
);

-- Indexes
CREATE INDEX idx_ai_analysis_tenant ON ai_analysis(tenant_id);
CREATE INDEX idx_ai_analysis_created ON ai_analysis(created_at);
CREATE INDEX idx_ai_analysis_risk_score ON ai_analysis(risk_score);
CREATE INDEX idx_ai_analysis_model ON ai_analysis(model_version);

-- GIN index for JSON searches
CREATE INDEX idx_ai_analysis_risk_factors ON ai_analysis USING GIN (risk_factors);
```

#### ai_decisions

```sql
-- Tracks AI recommendations and their outcomes for audit and learning
CREATE TABLE ai_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    policy_id UUID REFERENCES auto_response_policies(id),
    ai_analysis_id UUID REFERENCES ai_analysis(id),
    
    -- Decision details
    decision_type VARCHAR(50) NOT NULL, -- 'severity_adjustment', 'auto_action', 'suggestion'
    recommended_action VARCHAR(100) NOT NULL,
    recommended_severity VARCHAR(20),
    confidence_score DECIMAL(3,2) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    reasoning TEXT,
    
    -- Execution tracking
    auto_executed BOOLEAN NOT NULL DEFAULT FALSE,
    action_executed VARCHAR(100),
    executed_by VARCHAR(100), -- 'system' or analyst ID
    executed_at TIMESTAMP WITH TIME ZONE,
    
    -- Outcome tracking
    outcome VARCHAR(20), -- 'confirmed_threat', 'false_positive', 'pending', 'cancelled'
    outcome_verified_at TIMESTAMP WITH TIME ZONE,
    outcome_verified_by UUID REFERENCES users(id),
    
    -- Model metadata
    model_version VARCHAR(50) NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_ai_decisions_tenant ON ai_decisions(tenant_id);
CREATE INDEX idx_ai_decisions_alert ON ai_decisions(alert_id);
CREATE INDEX idx_ai_decisions_created ON ai_decisions(created_at);
CREATE INDEX idx_ai_decisions_outcome ON ai_decisions(outcome) WHERE outcome IS NOT NULL;
CREATE INDEX idx_ai_decisions_auto_executed ON ai_decisions(auto_executed, created_at);
```

#### user_behavior_baselines

```sql
-- Stores per-user behavioral baselines for anomaly detection
CREATE TABLE user_behavior_baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- User context
    department VARCHAR(100),
    role VARCHAR(50) NOT NULL,
    
    -- Baseline data (JSON structures)
    time_patterns JSONB NOT NULL DEFAULT '{}',
    location_patterns JSONB NOT NULL DEFAULT '[]',
    app_usage_patterns JSONB NOT NULL DEFAULT '{}',
    admin_action_patterns JSONB NOT NULL DEFAULT '{}',
    data_access_patterns JSONB NOT NULL DEFAULT '{}',
    peer_group_stats JSONB,
    
    -- Statistics
    baseline_period_days INTEGER NOT NULL,
    sample_size INTEGER NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    previous_version_id UUID REFERENCES user_behavior_baselines(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    next_scheduled_update TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '7 days'),
    
    -- Constraints
    CONSTRAINT unique_user_baseline_version UNIQUE (user_id, tenant_id, version)
);

-- Indexes
CREATE INDEX idx_behavior_baselines_user ON user_behavior_baselines(user_id);
CREATE INDEX idx_behavior_baselines_tenant ON user_behavior_baselines(tenant_id);
CREATE INDEX idx_behavior_baselines_confidence ON user_behavior_baselines(confidence_score);
CREATE INDEX idx_behavior_baselines_update ON user_behavior_baselines(next_scheduled_update);

-- GIN indexes for pattern searches
CREATE INDEX idx_behavior_time_patterns ON user_behavior_baselines USING GIN (time_patterns);
CREATE INDEX idx_behavior_location_patterns ON user_behavior_baselines USING GIN (location_patterns);
```

#### alert_feedback

```sql
-- Captures analyst feedback on alerts for learning loop
CREATE TABLE alert_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ai_analysis_id UUID REFERENCES ai_analysis(id),
    
    -- Analyst info
    analyst_id UUID NOT NULL REFERENCES users(id),
    analyst_role VARCHAR(50),
    
    -- Feedback content
    was_accurate BOOLEAN NOT NULL, -- Did the alert represent a real threat?
    is_false_positive BOOLEAN NOT NULL DEFAULT FALSE,
    severity_correct BOOLEAN, -- Was the AI severity assessment correct?
    would_auto_resolve BOOLEAN, -- Would the analyst have accepted auto-resolution?
    
    -- Detailed feedback
    feedback_text TEXT,
    missed_indicators TEXT, -- What did the AI miss?
    incorrect_assumptions TEXT, -- What did the AI get wrong?
    
    -- Time spent
    review_time_seconds INTEGER, -- How long did analyst spend reviewing?
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_accuracy CHECK (
        (was_accurate = TRUE AND is_false_positive = FALSE) OR
        (was_accurate = FALSE AND is_false_positive = TRUE) OR
        (was_accurate IS NULL)
    )
);

-- Indexes
CREATE INDEX idx_alert_feedback_alert ON alert_feedback(alert_id);
CREATE INDEX idx_alert_feedback_analyst ON alert_feedback(analyst_id);
CREATE INDEX idx_alert_feedback_tenant ON alert_feedback(tenant_id);
CREATE INDEX idx_alert_feedback_created ON alert_feedback(created_at);
CREATE INDEX idx_alert_feedback_accuracy ON alert_feedback(was_accurate, is_false_positive);
CREATE INDEX idx_alert_feedback_ai_analysis ON alert_feedback(ai_analysis_id);
```

#### ai_models

```sql
-- Tracks AI model versions and performance metrics
CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Model identification
    name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL, -- 'kimi', 'local', 'openai', etc.
    
    -- Configuration
    config JSONB NOT NULL DEFAULT '{}',
    
    -- Training info
    training_data_start DATE,
    training_data_end DATE,
    training_samples_count INTEGER,
    training_metrics JSONB,
    
    -- Performance metrics
    accuracy DECIMAL(4,3),
    precision_score DECIMAL(4,3),
    recall_score DECIMAL(4,3),
    f1_score DECIMAL(4,3),
    false_positive_rate DECIMAL(4,3),
    
    -- Validation results
    validation_results JSONB,
    
    -- Deployment status
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    deployed_at TIMESTAMP WITH TIME ZONE,
    deployed_by UUID REFERENCES users(id),
    
    -- A/B testing
    traffic_percentage INTEGER CHECK (traffic_percentage >= 0 AND traffic_percentage <= 100),
    ab_test_group VARCHAR(20), -- 'control', 'treatment', null
    
    -- Cost tracking
    avg_cost_per_request DECIMAL(10,6),
    total_requests INTEGER DEFAULT 0,
    total_cost DECIMAL(12,4) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_model_version UNIQUE (name, version)
);

-- Indexes
CREATE INDEX idx_ai_models_active ON ai_models(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_ai_models_type ON ai_models(model_type);
CREATE INDEX idx_ai_models_deployed ON ai_models(deployed_at);
```

---

## 4. API Specifications

### 4.1 API Overview

All AI endpoints are prefixed with `/api/v1/ai/` and require authentication via Bearer token.

### 4.2 Endpoints

#### POST /api/v1/ai/analyze-alert

Trigger AI analysis for a specific alert.

**Request:**
```json
{
  "alert_id": "550e8400-e29b-41d4-a716-446655440000",
  "force_refresh": false,
  "context_depth": "standard"
}
```

**Response (202 Accepted):**
```json
{
  "analysis_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "processing",
  "estimated_seconds": 5,
  "poll_url": "/api/v1/ai/alert-analysis/660e8400-e29b-41d4-a716-446655440001"
}
```

**Response (200 OK - if cached):**
```json
{
  "analysis_id": "660e8400-e29b-41d4-a716-446655440001",
  "alert_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "summary": "Impossible travel detected for user john.doe@company.com",
  "risk_score": 85,
  "recommended_severity": "high",
  "false_positive_probability": 0.05,
  "risk_factors": [
    {
      "name": "impossible_travel",
      "severity": "critical",
      "description": "User logged in from NYC (9:00 AM) and Singapore (9:15 AM)",
      "confidence": 0.98
    },
    {
      "name": "high_value_target",
      "severity": "high",
      "description": "User has access to financial systems",
      "confidence": 0.95
    }
  ],
  "remediation_steps": [
    {
      "order": 1,
      "action": "Immediately revoke all active sessions",
      "automation_available": true,
      "estimated_time": "30 seconds"
    },
    {
      "order": 2,
      "action": "Require password reset on next login",
      "automation_available": true,
      "estimated_time": "1 minute"
    }
  ],
  "suggested_actions": [
    {
      "action": "disable_user",
      "confidence": 0.92,
      "reasoning": "High confidence compromise with clear indicators"
    }
  ],
  "model_version": "kimi-1.5-2024-03",
  "created_at": "2024-03-01T12:34:56Z",
  "processing_time_ms": 2847
}
```

**Error Responses:**
- `404 Not Found`: Alert does not exist
- `403 Forbidden`: User does not have access to this alert's tenant
- `429 Too Many Requests`: Rate limit exceeded

---

#### GET /api/v1/ai/alert-analysis/{analysis_id}

Retrieve AI analysis results by analysis ID.

**Response (200 OK):**
```json
{
  "analysis_id": "660e8400-e29b-41d4-a716-446655440001",
  "alert_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "summary": "...",
  "risk_score": 85,
  "recommended_severity": "high",
  "false_positive_probability": 0.05,
  "risk_factors": [...],
  "remediation_steps": [...],
  "suggested_actions": [...],
  "attack_chain_analysis": {
    "related_alerts": [
      {
        "alert_id": "...",
        "relationship": "same_user",
        "time_delta": "-2 hours"
      }
    ],
    "campaign_indicators": false,
    "blast_radius": "medium"
  },
  "model_version": "kimi-1.5-2024-03",
  "created_at": "2024-03-01T12:34:56Z",
  "expires_at": "2024-05-30T12:34:56Z"
}
```

---

#### POST /api/v1/ai/query

Convert natural language query to SQL and execute.

**Request:**
```json
{
  "query": "Show me all admins who logged in from outside the US this month",
  "tenant_id": "770e8400-e29b-41d4-a716-446655440002",
  "max_results": 100,
  "include_sql": true
}
```

**Response (200 OK):**
```json
{
  "query_id": "880e8400-e29b-41d4-a716-446655440003",
  "original_query": "Show me all admins who logged in from outside the US this month",
  "sql": "SELECT u.email, le.ip_address, le.location, le.timestamp FROM users u JOIN login_events le ON u.id = le.user_id WHERE u.role = 'admin' AND u.tenant_id = '770e8400-e29b-41d4-a716-446655440002' AND le.country != 'US' AND le.timestamp >= DATE_TRUNC('month', CURRENT_DATE) ORDER BY le.timestamp DESC LIMIT 100",
  "description": "Finds all admin users who logged in from countries other than the United States during the current month, showing their email, IP address, location, and login timestamp.",
  "results": [
    {
      "email": "admin@company.com",
      "ip_address": "185.220.101.42",
      "location": "Frankfurt, Germany",
      "timestamp": "2024-03-01T08:23:15Z"
    }
  ],
  "result_count": 1,
  "execution_time_ms": 145,
  "summary": "Found 1 admin user with 1 login from outside the US this month. The user admin@company.com logged in from Frankfurt, Germany on March 1st.",
  "suggested_followups": [
    "Show failed login attempts for these users",
    "What applications did they access?",
    "Compare to logins from US locations"
  ]
}
```

**Error Responses:**
- `400 Bad Request`: Invalid or unsafe query
- `403 Forbidden`: User does not have access to tenant

---

#### POST /api/v1/ai/feedback

Submit analyst feedback on AI-generated analysis.

**Request:**
```json
{
  "alert_id": "550e8400-e29b-41d4-a716-446655440000",
  "ai_analysis_id": "660e8400-e29b-41d4-a716-446655440001",
  "was_accurate": true,
  "is_false_positive": false,
  "severity_correct": true,
  "would_auto_resolve": true,
  "feedback_text": "AI correctly identified the impossible travel. Suggested severity was appropriate.",
  "missed_indicators": null,
  "incorrect_assumptions": null,
  "review_time_seconds": 45
}
```

**Response (201 Created):**
```json
{
  "feedback_id": "990e8400-e29b-41d4-a716-446655440004",
  "status": "recorded",
  "learning_update": {
    "threshold_adjustment": null,
    "model_feedback_recorded": true,
    "baseline_update_scheduled": false
  }
}
```

---

#### GET /api/v1/ai/insights

Get AI-generated security insights and recommendations.

**Query Parameters:**
- `tenant_id` (required): Filter by tenant
- `time_range`: `24h`, `7d`, `30d`, `90d` (default: `7d`)
- `severity`: `low`, `medium`, `high`, `critical` (filter)
- `category`: `threats`, `trends`, `recommendations`, `anomalies`

**Response (200 OK):**
```json
{
  "generated_at": "2024-03-01T12:00:00Z",
  "time_range": "7d",
  "insights": [
    {
      "id": "insight-001",
      "category": "threats",
      "severity": "high",
      "title": "Credential Stuffing Campaign Detected",
      "description": "AI analysis identified a coordinated credential stuffing attack from 12 IP addresses targeting 8 user accounts. All attempts failed due to MFA, but recommend IP blocking.",
      "affected_users": 8,
      "affected_systems": ["Azure AD", "M365"],
      "recommended_actions": [
        "Block IP range 185.220.101.0/24",
        "Enable CAPTCHA for auth attempts",
        "Review password policies"
      ],
      "confidence": 0.94
    },
    {
      "id": "insight-002",
      "category": "trends",
      "severity": "medium",
      "title": "Increase in Off-Hours Access",
      "description": "23% increase in off-hours (10pm-6am) access compared to previous week. Pattern analysis suggests legitimate remote work rather than compromise.",
      "data_points": {
        "current_week": 145,
        "previous_week": 118,
        "percent_change": 22.9
      },
      "confidence": 0.78
    },
    {
      "id": "insight-003",
      "category": "recommendations",
      "severity": "medium",
      "title": "MFA Adoption Opportunity",
      "description": "12 admin users still lack MFA. Based on peer organizations, enabling MFA would reduce account compromise risk by 99.9%.",
      "affected_users": ["admin1@company.com", "admin2@company.com"],
      "estimated_impact": "High",
      "confidence": 0.99
    }
  ],
  "summary": {
    "total_insights": 3,
    "by_severity": {
      "high": 1,
      "medium": 2,
      "low": 0
    },
    "ai_confidence_avg": 0.90
  }
}
```

---

### 4.3 Additional Endpoints

#### GET /api/v1/ai/models

List available AI models and their performance metrics.

**Response:**
```json
{
  "models": [
    {
      "id": "model-001",
      "name": "kimi-alert-analyzer",
      "version": "1.5-2024-03",
      "is_active": true,
      "accuracy": 0.89,
      "false_positive_rate": 0.08,
      "avg_latency_ms": 2500,
      "total_requests": 15432
    }
  ]
}
```

#### GET /api/v1/ai/behavior/{user_id}

Retrieve behavioral baseline for a user.

**Response:**
```json
{
  "user_id": "user@company.com",
  "baseline_version": 3,
  "confidence_score": 0.87,
  "last_updated": "2024-02-25T10:00:00Z",
  "patterns": {
    "typical_login_hours": [8, 9, 10, 13, 14, 15, 16],
    "common_countries": ["US", "CA"],
    "typical_apps": ["Outlook", "SharePoint", "Teams"],
    "admin_actions_per_week": 5
  },
  "anomalies_detected_30d": 2
}
```

---

## 5. Kimi Integration

### 5.1 API Client Design

```python
import httpx
from typing import AsyncGenerator, Optional, Dict, Any
from pydantic import BaseModel
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class KimiMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str

class KimiResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[dict]
    usage: dict

class KimiClient:
    """
    Async client for Kimi API with rate limiting, caching, and error handling.
    """
    
    BASE_URL = "https://api.moonshot.cn/v1"
    
    def __init__(
        self,
        api_key: str,
        model: str = "kimi-k2.5-202501",
        max_retries: int = 3,
        timeout: float = 60.0,
        rate_limit_rpm: int = 60
    ):
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Rate limiting
        self.rate_limit_rpm = rate_limit_rpm
        self._request_times: list[float] = []
        self._rate_limit_lock = asyncio.Lock()
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
        
        # Cache (Redis-backed in production)
        self._cache: Dict[str, Any] = {}
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=self.timeout
        )
        return self
    
    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
    
    async def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits."""
        async with self._rate_limit_lock:
            now = asyncio.get_event_loop().time()
            minute_ago = now - 60
            
            # Remove old requests
            self._request_times = [t for t in self._request_times if t > minute_ago]
            
            # Check if we need to wait
            if len(self._request_times) >= self.rate_limit_rpm:
                sleep_time = self._request_times[0] - minute_ago + 0.1
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            
            self._request_times.append(asyncio.get_event_loop().time())
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=lambda e: isinstance(e, (httpx.TimeoutException, httpx.NetworkError))
    )
    async def generate(
        self,
        messages: list[KimiMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        response_format: Optional[dict] = None,
        use_cache: bool = True
    ) -> KimiResponse:
        """Generate a completion from Kimi API."""
        
        # Check cache
        cache_key = self._get_cache_key(messages, temperature, max_tokens)
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Rate limiting
        await self._wait_for_rate_limit()
        
        # Build request
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        # Make request
        try:
            response = await self._client.post(
                "/chat/completions",
                json=payload
            )
            response.raise_for_status()
            
            result = KimiResponse(**response.json())
            
            # Cache successful response
            if use_cache:
                self._cache[cache_key] = result
            
            return result
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited - wait and retry
                retry_after = int(e.response.headers.get("Retry-After", 60))
                await asyncio.sleep(retry_after)
                raise  # Let retry decorator handle it
            elif e.response.status_code == 400:
                raise ValueError(f"Invalid request: {e.response.text}")
            elif e.response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            else:
                raise KimiAPIError(f"API error: {e.response.status_code}")
    
    async def generate_stream(
        self,
        messages: list[KimiMessage],
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """Stream completion tokens from Kimi API."""
        
        await self._wait_for_rate_limit()
        
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        async with self._client.stream(
            "POST",
            "/chat/completions",
            json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    yield data
    
    def _get_cache_key(
        self,
        messages: list[KimiMessage],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate cache key for request."""
        import hashlib
        content = "|".join([
            m.content for m in messages
        ]) + f"|{temperature}|{max_tokens}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
```

### 5.2 Prompt Templates

#### Alert Analysis Prompt

```python
ALERT_ANALYSIS_PROMPT = """You are a senior cybersecurity analyst analyzing a security alert from a Microsoft 365 environment.

## Alert Details
- **Alert Type**: {alert_type}
- **User**: {user_email}
- **Timestamp**: {timestamp}
- **Severity**: {original_severity}
- **Description**: {alert_description}

## User Context
- **Role**: {user_role}
- **Department**: {user_department}
- **Account Created**: {account_created}
- **Last Login**: {last_login}
- **MFA Status**: {mfa_status}
- **Admin Privileges**: {is_admin}

## Activity Context (Last 30 Days)
- **Typical Login Countries**: {typical_countries}
- **Typical Login Hours**: {typical_hours}
- **Failed Login Attempts**: {failed_logins_30d}
- **Sensitive Data Access**: {sensitive_access_count}
- **Admin Actions**: {admin_actions_30d}

## Current Event Details
- **Action**: {action}
- **Source IP**: {ip_address}
- **Location**: {location}
- **Device**: {device_info}
- **Application**: {application}

## Related Alerts (Last 7 Days)
{related_alerts}

## Tenant Security Posture
- **MFA Enforcement**: {mfa_enforcement}
- **Password Policy**: {password_policy}
- **DLP Policies**: {dlp_policies}

---

Analyze this alert and provide your assessment in the following JSON format:

```json
{{
    "summary": "Concise 2-3 sentence summary of the threat",
    "risk_score": <0-100 integer>,
    "recommended_severity": "low|medium|high|critical",
    "false_positive_probability": <0.0-1.0>,
    "risk_factors": [
        {{
            "name": "factor identifier",
            "severity": "info|low|medium|high|critical",
            "description": "detailed explanation",
            "confidence": <0.0-1.0>
        }}
    ],
    "remediation_steps": [
        {{
            "order": 1,
            "action": "specific action to take",
            "automation_available": true|false,
            "estimated_time": "e.g., '30 seconds', '5 minutes'"
        }}
    ],
    "suggested_actions": [
        {{
            "action": "disable_user|revoke_sessions|reset_password|block_ip|notify_admin|add_to_watchlist|none",
            "confidence": <0.0-1.0>,
            "reasoning": "why this action is recommended"
        }}
    ],
    "attack_chain_indicators": {{
        "is_part_of_campaign": true|false,
        "related_alert_count": <number>,
        "blast_radius": "low|medium|high",
        "recommended_hunt_queries": ["query1", "query2"]
    }}
}}
```

Guidelines:
- Risk score 0-30: Low, 31-50: Medium, 51-75: High, 76-100: Critical
- Consider impossible travel (physics-based), time-of-day anomalies, and privilege escalation
- Flag clear false positives (e.g., known VPN, business travel)
- Prioritize automated remediation steps when confidence > 90%
"""
```

#### Natural Language to SQL Prompt

```python
NL_TO_SQL_PROMPT = """You are an expert SQL query generator for a security analytics database.

## Database Schema

Table: users
- id (UUID): Primary key
- email (TEXT): User email address
- tenant_id (UUID): Organization tenant ID
- role (TEXT): admin, user, guest
- department (TEXT)
- created_at (TIMESTAMP)
- last_login_at (TIMESTAMP)
- mfa_enabled (BOOLEAN)
- account_enabled (BOOLEAN)

Table: login_events
- id (UUID): Primary key
- user_id (UUID): Foreign key to users.id
- tenant_id (UUID)
- timestamp (TIMESTAMP)
- ip_address (INET)
- country (TEXT)
- city (TEXT)
- success (BOOLEAN)
- auth_method (TEXT): password, mfa, sso
- user_agent (TEXT)

Table: alerts
- id (UUID): Primary key
- user_id (UUID): Foreign key to users.id
- tenant_id (UUID)
- rule_id (UUID)
- severity (TEXT): low, medium, high, critical
- status (TEXT): open, acknowledged, resolved, dismissed
- title (TEXT)
- description (TEXT)
- created_at (TIMESTAMP)
- ai_risk_score (INTEGER): 0-100
- ai_recommended_severity (TEXT)

## User Question
"{user_query}"

## Tenant Context
Tenant ID: {tenant_id}
Current Date: {current_date}

---

Generate a PostgreSQL query that answers this question. Follow these rules:
1. Always filter by tenant_id = '{tenant_id}'
2. Use proper table aliases
3. Add appropriate LIMIT (max 1000)
4. Include meaningful ORDER BY
5. Use date/time functions for temporal queries
6. Use proper JOINs for multi-table queries

Respond ONLY with valid JSON:

```json
{{
    "sql": "SELECT ...",
    "description": "What this query does in plain English",
    "expected_columns": ["column1", "column2"],
    "parameters": {{}},
    "estimated_rows": <approximate row count>
}}
```
"""
```

#### Security Insights Prompt

```python
SECURITY_INSIGHTS_PROMPT = """You are a security intelligence analyst reviewing threat data for an organization.

## Analysis Period: {time_range}
## Tenant: {tenant_name}

## Alert Summary
- Total Alerts: {total_alerts}
- By Severity: {severity_breakdown}
- By Type: {type_breakdown}
- AI-Confirmed True Positives: {confirmed_threats}
- False Positives (Analyst Marked): {false_positives}

## Top Risk Factors Detected
{risk_factors}

## User Behavior Anomalies
{behavior_anomalies}

## Attack Patterns Identified
{attack_patterns}

## Compliance Status
{compliance_status}

---

Generate 3-5 actionable security insights in JSON format:

```json
{{
    "insights": [
        {{
            "category": "threats|trends|recommendations|anomalies",
            "severity": "low|medium|high|critical",
            "title": "Concise insight title",
            "description": "Detailed explanation with context",
            "affected_users": ["user1", "user2"],
            "affected_systems": ["system1"],
            "recommended_actions": ["action1", "action2"],
            "confidence": 0.0-1.0,
            "supporting_data": {{}}
        }}
    ]
}}
```

Guidelines:
- Focus on actionable insights, not raw statistics
- Highlight emerging threats and trends
- Provide specific remediation steps
- Include confidence scores based on evidence quality
- Prioritize high-confidence, high-impact findings
"""
```

### 5.3 Rate Limiting and Caching Strategy

#### Rate Limiting Configuration

```python
# Rate limiting tiers
RATE_LIMITS = {
    "alert_analysis": {
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "burst_size": 10
    },
    "nl_query": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "burst_size": 5
    },
    "insights": {
        "requests_per_minute": 10,
        "requests_per_hour": 100,
        "burst_size": 3
    }
}

class RateLimiter:
    """Token bucket rate limiter with Redis backend."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def is_allowed(
        self,
        key: str,
        requests_per_minute: int,
        burst_size: int
    ) -> tuple[bool, dict]:
        """Check if request is allowed under rate limit."""
        
        pipe = self.redis.pipeline()
        now = time.time()
        
        # Token bucket algorithm
        bucket_key = f"rate_limit:{key}"
        
        # Get current tokens
        current = await self.redis.hmget(bucket_key, ["tokens", "last_update"])
        tokens = float(current[0]) if current[0] else burst_size
        last_update = float(current[1]) if current[1] else now
        
        # Add tokens based on time passed
        time_passed = now - last_update
        tokens = min(burst_size, tokens + time_passed * (requests_per_minute / 60))
        
        if tokens >= 1:
            tokens -= 1
            allowed = True
        else:
            allowed = False
        
        # Update bucket
        await self.redis.hmset(bucket_key, {
            "tokens": tokens,
            "last_update": now
        })
        await self.redis.expire(bucket_key, 3600)
        
        reset_time = now + (1 - tokens) / (requests_per_minute / 60)
        
        return allowed, {
            "limit": requests_per_minute,
            "remaining": int(tokens),
            "reset": reset_time
        }
```

#### Caching Strategy

```python
# Cache configuration
CACHE_CONFIG = {
    "alert_analysis": {
        "ttl_seconds": 86400,  # 24 hours
        "key_pattern": "ai:analysis:{alert_id}"
    },
    "nl_query": {
        "ttl_seconds": 300,    # 5 minutes
        "key_pattern": "ai:query:{hash}"
    },
    "user_baseline": {
        "ttl_seconds": 3600,   # 1 hour
        "key_pattern": "ai:baseline:{user_id}"
    },
    "insights": {
        "ttl_seconds": 1800,   # 30 minutes
        "key_pattern": "ai:insights:{tenant_id}:{time_range}"
    }
}

class AIResponseCache:
    """Multi-layer cache for AI responses."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.local_cache: Dict[str, Any] = {}
        self.local_cache_ttl: Dict[str, float] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache (L1 local, L2 Redis)."""
        
        # Check local cache
        if key in self.local_cache:
            if time.time() < self.local_cache_ttl.get(key, 0):
                return self.local_cache[key]
            else:
                del self.local_cache[key]
        
        # Check Redis
        value = await self.redis.get(key)
        if value:
            data = json.loads(value)
            # Populate local cache
            self.local_cache[key] = data
            self.local_cache_ttl[key] = time.time() + 60  # 1 min local TTL
            return data
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600
    ):
        """Set in both cache layers."""
        
        # Local cache
        self.local_cache[key] = value
        self.local_cache_ttl[key] = time.time() + min(ttl_seconds, 60)
        
        # Redis
        await self.redis.setex(
            key,
            ttl_seconds,
            json.dumps(value, default=str)
        )
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern."""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
```

### 5.4 Error Handling and Fallbacks

```python
class AIErrorHandler:
    """Handles AI service errors with graceful fallbacks."""
    
    FALLBACK_RULES = {
        "alert_analysis": {
            "risk_score": 50,  # Medium risk when AI unavailable
            "recommended_severity": "medium",
            "summary": "AI analysis temporarily unavailable. Alert requires manual review.",
            "remediation_steps": [
                {
                    "order": 1,
                    "action": "Manually review alert details",
                    "automation_available": False,
                    "estimated_time": "5 minutes"
                }
            ]
        },
        "nl_query": {
            "error": "Natural language processing temporarily unavailable. Please use structured query interface."
        },
        "insights": {
            "insights": [],
            "summary": "Insights generation temporarily unavailable. Please check back later."
        }
    }
    
    async def handle_error(
        self,
        operation: str,
        error: Exception,
        context: dict
    ) -> dict:
        """Handle AI error and return fallback response."""
        
        logger.error(
            f"AI operation failed: {operation}",
            extra={
                "error": str(error),
                "context": context,
                "operation": operation
            }
        )
        
        # Log to error tracking
        await self.log_error(operation, error, context)
        
        # Return fallback
        fallback = self.FALLBACK_RULES.get(operation, {}).copy()
        fallback["_fallback"] = True
        fallback["_error_type"] = type(error).__name__
        
        return fallback
    
    async def log_error(
        self,
        operation: str,
        error: Exception,
        context: dict
    ):
        """Log error for monitoring and alerting."""
        
        error_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "tenant_id": context.get("tenant_id"),
            "user_id": context.get("user_id")
        }
        
        # Store in error tracking table
        await self.store_error_record(error_record)
        
        # Alert if error rate is high
        await self.check_error_rate_and_alert(operation)
    
    async def check_error_rate_and_alert(self, operation: str):
        """Check error rate and alert if threshold exceeded."""
        
        # Count errors in last 5 minutes
        error_count = await self.get_recent_error_count(operation, minutes=5)
        
        if error_count > 10:  # More than 10 errors in 5 min
            await self.send_alert(
                severity="high",
                message=f"AI service {operation} experiencing high error rate: {error_count} errors in 5 minutes"
            )
```

---

## 6. Learning Loop

### 6.1 Feedback Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Learning Loop Flow                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 1. Alert Resolution                                                   │   │
│  │                                                                       │   │
│  │  Analyst reviews alert and AI analysis                               │   │
│  │       │                                                               │   │
│  │       ▼                                                               │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │  Feedback Captured:                                            │   │   │
│  │  │  • Was it a real threat? (TP/FP determination)                │   │   │
│  │  │  • Was AI severity correct?                                   │   │   │
│  │  │  • Would auto-resolution be accepted?                         │   │   │
│  │  │  • Free text feedback on missed indicators                    │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 2. Feedback Processing                                                │   │
│  │                                                                       │   │
│  │  • Store feedback in alert_feedback table                            │   │
│  │  • Update ai_decisions with outcome                                  │   │
│  │  • Calculate accuracy metrics per model                              │   │
│  │  • Identify patterns in false positives                              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                    ┌───────────────┼───────────────┐                         │
│                    ▼               ▼               ▼                         │
│  ┌──────────────────────┐ ┌──────────────┐ ┌──────────────────┐            │
│  │ 3a. Threshold        │ │ 3b. Baseline │ │ 3c. Model        │            │
│  │    Adjustment        │ │    Update    │ │    Retraining    │            │
│  ├──────────────────────┤ ├──────────────┤ ├──────────────────┤            │
│  │ • Adjust per-rule    │ │ • Recalculate│ │ • Accumulate     │            │
│  │   thresholds based   │ │   user       │ │   training data  │            │
│  │   on FP rate         │ │   baselines  │ │ • Trigger        │            │
│  │ • Update per-user    │ │   weekly     │ │   retraining at  │            │
│  │   sensitivity        │ │ • Detect new │ │   threshold      │            │
│  │ • Tune confidence    │ │   patterns   │ │ • A/B test new   │            │
│  │   thresholds         │ │              │ │   models         │            │
│  └──────────────────────┘ └──────────────┘ └──────────────────┘            │
│           │                     │                     │                      │
│           └─────────────────────┼─────────────────────┘                      │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 4. Model Improvement                                                  │   │
│  │                                                                       │   │
│  │  • Deploy new threshold configurations                               │   │
│  │  • Update behavioral models                                          │   │
│  │  • Retrain AI models with new feedback                               │   │
│  │  • Monitor improvement metrics                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Feedback Processing Pipeline

```python
class LearningLoop:
    """
    Processes analyst feedback to improve AI systems.
    """
    
    async def process_feedback(self, feedback: AlertFeedback):
        """Main entry point for processing analyst feedback."""
        
        # 1. Validate and store feedback
        await self.store_feedback(feedback)
        
        # 2. Update decision outcomes
        await self.update_decision_outcomes(feedback)
        
        # 3. Update model accuracy metrics
        await self.update_model_metrics(feedback)
        
        # 4. Trigger threshold adjustments if needed
        await self.evaluate_threshold_adjustments(feedback)
        
        # 5. Schedule baseline updates if applicable
        await self.schedule_baseline_update(feedback)
        
        # 6. Check for model retraining trigger
        await self.check_retraining_threshold(feedback)
    
    async def evaluate_threshold_adjustments(self, feedback: AlertFeedback):
        """Evaluate if threshold adjustments are needed."""
        
        # Get recent feedback for this rule
        recent_feedback = await self.get_feedback_batch(
            rule_id=feedback.rule_id,
            days=7,
            min_samples=10
        )
        
        if len(recent_feedback) < 10:
            return  # Insufficient data
        
        # Calculate false positive rate
        false_positives = sum(1 for f in recent_feedback if f.is_false_positive)
        fp_rate = false_positives / len(recent_feedback)
        
        # Determine if adjustment needed
        threshold = await self.get_adaptive_threshold(
            rule_id=feedback.rule_id,
            user_id=feedback.user_id
        )
        
        adjustment = None
        
        if fp_rate > 0.7:
            # Too many false positives - increase threshold
            adjustment = ThresholdAdjustment(
                direction="increase",
                magnitude=0.1,
                reason=f"High FP rate: {fp_rate:.1%}"
            )
        elif fp_rate < 0.05 and threshold.adjustment_history:
            # Very low FP rate - might be too strict
            adjustment = ThresholdAdjustment(
                direction="decrease",
                magnitude=0.05,
                reason=f"Low FP rate: {fp_rate:.1%} - may be missing alerts"
            )
        
        if adjustment:
            await self.apply_threshold_adjustment(threshold, adjustment)
            
            # Log the adjustment
            await self.log_threshold_adjustment(
                threshold=threshold,
                adjustment=adjustment,
                feedback_count=len(recent_feedback),
                fp_rate=fp_rate
            )
    
    async def update_model_metrics(self, feedback: AlertFeedback):
        """Update per-model accuracy metrics."""
        
        # Get the AI analysis that was reviewed
        analysis = await self.get_ai_analysis(feedback.ai_analysis_id)
        if not analysis:
            return
        
        # Get model record
        model = await self.get_ai_model(analysis.model_version)
        
        # Calculate metrics
        total_requests = model.total_requests + 1
        
        # Accuracy: Did AI correctly identify threat?
        if feedback.was_accurate is not None:
            correct_predictions = model.correct_predictions or 0
            if feedback.was_accurate:
                correct_predictions += 1
            accuracy = correct_predictions / total_requests
        else:
            accuracy = model.accuracy
        
        # False positive rate
        total_positives = model.total_positives or 0
        false_positives = model.false_positives or 0
        
        if feedback.is_false_positive:
            false_positives += 1
        if feedback.was_accurate or feedback.is_false_positive:
            total_positives += 1
        
        fp_rate = false_positives / total_positives if total_positives > 0 else 0
        
        # Update model record
        await self.update_model_record(
            model_id=model.id,
            updates={
                "total_requests": total_requests,
                "accuracy": accuracy,
                "false_positive_rate": fp_rate,
                "last_feedback_at": datetime.utcnow()
            }
        )
```

### 6.3 Model Retraining Triggers

```python
class RetrainingScheduler:
    """
    Schedules and manages model retraining based on feedback thresholds.
    """
    
    RETRAINING_TRIGGERS = {
        "accuracy_drop": {
            "window_days": 7,
            "threshold": 0.05,  # 5% drop in accuracy
            "min_samples": 100
        },
        "false_positive_spike": {
            "window_days": 7,
            "threshold": 0.15,  # 15% FP rate
            "min_samples": 50
        },
        "scheduled": {
            "interval_days": 30  # Monthly retraining
        },
        "manual": {
            "enabled": True
        }
    }
    
    async def check_retraining_needed(self) -> list[RetrainingJob]:
        """Check if any models need retraining."""
        
        jobs = []
        
        # Get all active models
        models = await self.get_active_models()
        
        for model in models:
            # Check accuracy drop
            accuracy_drop = await self.check_accuracy_drop(model)
            if accuracy_drop.needs_retraining:
                jobs.append(RetrainingJob(
                    model_id=model.id,
                    trigger="accuracy_drop",
                    reason=f"Accuracy dropped by {accuracy_drop.drop_percentage:.1%}",
                    priority="high"
                ))
                continue
            
            # Check FP spike
            fp_spike = await self.check_fp_spike(model)
            if fp_spike.needs_retraining:
                jobs.append(RetrainingJob(
                    model_id=model.id,
                    trigger="false_positive_spike",
                    reason=f"FP rate at {fp_spike.fp_rate:.1%}",
                    priority="high"
                ))
                continue
            
            # Check scheduled retraining
            scheduled = await self.check_scheduled_retraining(model)
            if scheduled.needs_retraining:
                jobs.append(RetrainingJob(
                    model_id=model.id,
                    trigger="scheduled",
                    reason=f"Scheduled retraining ({model.days_since_training} days)",
                    priority="medium"
                ))
        
        return jobs
    
    async def prepare_training_data(
        self,
        model_id: str,
        min_feedback_samples: int = 500
    ) -> TrainingDataset:
        """Prepare training data from feedback history."""
        
        # Get labeled feedback
        feedback = await self.get_labeled_feedback(
            min_samples=min_feedback_samples,
            balanced=True  # Ensure roughly equal TP/FP
        )
        
        # Get alert data for each feedback
        training_samples = []
        for f in feedback:
            alert = await self.get_alert(f.alert_id)
            analysis = await self.get_ai_analysis(f.ai_analysis_id)
            
            training_samples.append(TrainingSample(
                alert_data=alert,
                ai_analysis=analysis,
                feedback=f,
                label=self.get_label(f)  # true_positive, false_positive, etc.
            ))
        
        # Split into train/validation
        train, validation = train_test_split(training_samples, test_size=0.2)
        
        return TrainingDataset(
            train=train,
            validation=validation,
            metadata={
                "total_samples": len(training_samples),
                "label_distribution": self.get_label_distribution(training_samples),
                "date_range": self.get_date_range(training_samples)
            }
        )
```

### 6.4 A/B Testing Framework

```python
class ABTestFramework:
    """
    A/B testing framework for new AI models and rules.
    """
    
    async def create_ab_test(
        self,
        name: str,
        control_model: str,
        treatment_model: str,
        traffic_split: float = 0.1,  # 10% to treatment
        min_samples: int = 100,
        success_metric: str = "accuracy"
    ) -> ABTest:
        """Create a new A/B test."""
        
        test = ABTest(
            id=uuid4(),
            name=name,
            control_model=control_model,
            treatment_model=treatment_model,
            traffic_split=traffic_split,
            min_samples=min_samples,
            success_metric=success_metric,
            status="running",
            started_at=datetime.utcnow()
        )
        
        await self.store_ab_test(test)
        
        # Deploy treatment model with traffic percentage
        await self.deploy_model(
            model_id=treatment_model,
            traffic_percentage=int(traffic_split * 100),
            ab_test_group="treatment"
        )
        
        return test
    
    async def route_request(
        self,
        tenant_id: str,
        user_id: str
    ) -> str:
        """Route request to control or treatment model."""
        
        # Check for active A/B tests
        active_tests = await self.get_active_ab_tests()
        
        for test in active_tests:
            # Consistent routing based on user_id hash
            user_hash = hashlib.sha256(user_id.encode()).hexdigest()
            user_bucket = int(user_hash[:8], 16) % 100
            
            if user_bucket < (test.traffic_split * 100):
                # Treatment group
                await self.log_ab_exposure(test.id, user_id, "treatment")
                return test.treatment_model
        
        # Default to control
        return active_tests[0].control_model if active_tests else "default"
    
    async def evaluate_ab_test(self, test_id: str) -> ABTestResults:
        """Evaluate A/B test results."""
        
        test = await self.get_ab_test(test_id)
        
        # Get metrics for both groups
        control_metrics = await self.get_metrics_for_model(
            test.control_model,
            since=test.started_at
        )
        treatment_metrics = await self.get_metrics_for_model(
            test.treatment_model,
            since=test.started_at
        )
        
        # Statistical significance test
        significance = self.calculate_statistical_significance(
            control_metrics,
            treatment_metrics
        )
        
        # Determine winner
        if significance.p_value < 0.05:
            if treatment_metrics[test.success_metric] > control_metrics[test.success_metric]:
                winner = "treatment"
                recommendation = "promote_treatment"
            else:
                winner = "control"
                recommendation = "keep_control"
        else:
            winner = None
            recommendation = "continue_test"
        
        return ABTestResults(
            test_id=test_id,
            control_metrics=control_metrics,
            treatment_metrics=treatment_metrics,
            statistical_significance=significance,
            winner=winner,
            recommendation=recommendation,
            sample_sizes={
                "control": control_metrics.sample_size,
                "treatment": treatment_metrics.sample_size
            }
        )
    
    async def promote_treatment(self, test_id: str):
        """Promote treatment model to 100% traffic."""
        
        test = await self.get_ab_test(test_id)
        
        # Update treatment model to 100% traffic
        await self.update_model_traffic(test.treatment_model, 100)
        
        # Set control model to 0%
        await self.update_model_traffic(test.control_model, 0)
        await self.deactivate_model(test.control_model)
        
        # Mark test as complete
        await self.complete_ab_test(test_id, winner="treatment")
        
        # Notify stakeholders
        await self.send_notification(
            subject=f"A/B Test Complete: {test.name}",
            body=f"Treatment model {test.treatment_model} promoted to 100% traffic."
        )
```

---

## Appendix: Implementation Timeline

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up Kimi API client with rate limiting
- [ ] Implement Alert Enrichment Service
- [ ] Create ai_analysis table and API endpoints
- [ ] Deploy to staging environment

### Phase 2: Learning (Weeks 3-4)
- [ ] Implement alert_feedback table and endpoints
- [ ] Build Adaptive Threshold Engine
- [ ] Create feedback processing pipeline
- [ ] Add basic learning loop

### Phase 3: Intelligence (Weeks 5-6)
- [ ] Implement NLP Query Engine
- [ ] Build Behavioral Analysis Service
- [ ] Create user_behavior_baselines table
- [ ] Add anomaly detection

### Phase 4: Automation (Weeks 7-8)
- [ ] Implement Auto-Response Engine
- [ ] Create policy configuration UI
- [ ] Build A/B testing framework
- [ ] Add model retraining pipeline

### Phase 5: Production (Week 9)
- [ ] Performance optimization
- [ ] Security review
- [ ] Documentation
- [ ] Production deployment

---

*Document Version: 1.0*
*Last Updated: 2024-03-01*
*Author: SpecterDefence AI Team*
