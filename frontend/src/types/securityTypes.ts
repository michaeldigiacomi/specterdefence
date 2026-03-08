// ============================================
// Conditional Access Policies Types
// ============================================

export type PolicyState = 'enabled' | 'disabled' | 'reportOnly';
export type ChangeType = 'created' | 'updated' | 'deleted' | 'enabled' | 'disabled' | 'baseline_drift';
export type CASeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface CAPolicy {
  id: string;
  tenant_id: string;
  policy_id: string;
  display_name: string;
  description: string | null;
  state: PolicyState;
  grant_controls: string[];
  is_mfa_required: boolean;
  applies_to_all_users: boolean;
  applies_to_all_apps: boolean;
  is_baseline_policy: boolean;
  baseline_compliant: boolean;
  security_score: number;
  created_at: string;
  updated_at: string;
  last_scan_at: string;
}

export interface CAPolicyListResponse {
  items: CAPolicy[];
  total: number;
  limit: number;
  offset: number;
}

export interface CAPolicyChange {
  id: string;
  policy_id: string;
  tenant_id: string;
  change_type: ChangeType;
  changed_by: string | null;
  changed_by_email: string | null;
  changes_summary: string[];
  security_impact: string;
  mfa_removed: boolean;
  detected_at: string;
}

export interface CAPolicyChangeListResponse {
  items: CAPolicyChange[];
  total: number;
  limit: number;
  offset: number;
}

export interface CAPolicyAlert {
  id: string;
  policy_id: string;
  tenant_id: string;
  alert_type: ChangeType;
  severity: CASeverity;
  title: string;
  description: string;
  is_acknowledged: boolean;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  created_at: string;
}

export interface CAPolicyAlertListResponse {
  items: CAPolicyAlert[];
  total: number;
  limit: number;
  offset: number;
}

export interface CAPolicySummary {
  total_policies: number;
  enabled: number;
  disabled: number;
  report_only: number;
  mfa_policies: number;
  baseline_policies: number;
  baseline_compliant: number;
  baseline_violations: number;
  recent_changes: number;
  high_severity_alerts: number;
  policies_covering_all_users: number;
  policies_covering_all_apps: number;
}

// ============================================
// Mailbox Rules Types
// ============================================

export type RuleType = 'forwarding' | 'auto_reply' | 'redirect' | 'move_to_folder' | 'delete' | 'mark_as_read' | 'custom';
export type RuleStatus = 'active' | 'suspicious' | 'malicious' | 'benign' | 'disabled';
export type RuleSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface MailboxRule {
  id: string;
  tenant_id: string;
  user_email: string;
  rule_id: string;
  rule_name: string;
  rule_type: string;
  is_enabled: boolean;
  status: string;
  severity: string;
  forward_to: string | null;
  forward_to_external: boolean;
  external_domain: string | null;
  redirect_to: string | null;
  is_hidden_folder_redirect: boolean;
  has_suspicious_patterns: boolean;
  created_outside_business_hours: boolean;
  created_by_non_owner: boolean;
  created_by: string | null;
  detection_reasons: string[];
  rule_created_at: string | null;
  rule_modified_at: string | null;
  last_scan_at: string;
  created_at: string;
  updated_at: string;
}

export interface MailboxRuleListResponse {
  items: MailboxRule[];
  total: number;
  limit: number;
  offset: number;
}

export interface MailboxRuleAlert {
  id: string;
  rule_id: string;
  tenant_id: string;
  user_email: string;
  alert_type: string;
  severity: string;
  title: string;
  description: string;
  is_acknowledged: boolean;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  created_at: string;
}

export interface MailboxRuleAlertListResponse {
  items: MailboxRuleAlert[];
  total: number;
  limit: number;
  offset: number;
}

export interface MailboxRuleSummary {
  total_suspicious: number;
  total_malicious: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  recent_alerts: number;
}

// ============================================
// MFA Report Types
// ============================================

export type MFAStrengthLevel = 'strong' | 'moderate' | 'weak' | 'none';
export type ComplianceStatus = 'compliant' | 'non_compliant' | 'exempt' | 'pending';

export interface MFAUser {
  id: string;
  tenant_id: string;
  user_id: string;
  user_principal_name: string;
  display_name: string;
  is_mfa_registered: boolean;
  mfa_methods: string[];
  primary_mfa_method: string | null;
  mfa_strength: MFAStrengthLevel;
  is_admin: boolean;
  admin_roles: string[];
  compliance_status: ComplianceStatus;
  compliance_exempt: boolean;
  exemption_reason: string | null;
  first_mfa_registration: string | null;
  last_mfa_update: string | null;
  account_enabled: boolean;
  user_type: string;
  created_at: string;
  updated_at: string;
  needs_attention: boolean;
}

export interface MFAUserListResponse {
  items: MFAUser[];
  total: number;
  limit: number;
  offset: number;
}

export interface MFAEnrollmentSummary {
  tenant_id: string;
  snapshot_date: string;
  total_users: number;
  mfa_registered_users: number;
  non_compliant_users: number;
  total_admins: number;
  admins_with_mfa: number;
  admins_without_mfa: number;
  fido2_users: number;
  authenticator_app_users: number;
  sms_users: number;
  voice_users: number;
  strong_mfa_users: number;
  moderate_mfa_users: number;
  weak_mfa_users: number;
  exempt_users: number;
  mfa_coverage_percentage: number;
  admin_mfa_coverage_percentage: number;
  compliance_rate: number;
  meets_admin_requirement: boolean;
  meets_user_target: boolean;
}

export interface MFAEnrollmentTrend {
  date: string;
  total_users: number;
  mfa_registered_users: number;
  mfa_coverage_percentage: number;
  admin_mfa_coverage_percentage: number;
}

export interface MFAEnrollmentTrendsResponse {
  tenant_id: string;
  trends: MFAEnrollmentTrend[];
  period_days: number;
}

export interface MFAMethodDistribution {
  method_type: string;
  count: number;
  percentage: number;
}

export interface MFAMethodsDistributionResponse {
  tenant_id: string;
  total_mfa_users: number;
  distribution: MFAMethodDistribution[];
}

export interface MFAStrengthDistribution {
  strength_level: MFAStrengthLevel;
  count: number;
  percentage: number;
}

export interface MFAStrengthDistributionResponse {
  tenant_id: string;
  distribution: MFAStrengthDistribution[];
  strong_mfa_percentage: number;
  moderate_mfa_percentage: number;
  weak_mfa_percentage: number;
  no_mfa_percentage: number;
}

export interface AdminsWithoutMFAResponse {
  items: MFAUser[];
  total: number;
  message: string;
}

// ============================================
// OAuth Applications Types
// ============================================

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AppStatus = 'approved' | 'suspicious' | 'malicious' | 'revoked' | 'pending_review';
export type PublisherType = 'microsoft' | 'verified' | 'unverified' | 'unknown';

export interface OAuthApp {
  id: string;
  tenant_id: string;
  app_id: string;
  display_name: string;
  description: string | null;
  publisher_name: string | null;
  publisher_id: string | null;
  publisher_type: string;
  is_microsoft_publisher: boolean;
  is_verified_publisher: boolean;
  risk_level: string;
  status: string;
  risk_score: number;
  permission_count: number;
  high_risk_permissions: string[];
  has_mail_permissions: boolean;
  has_user_read_all: boolean;
  has_group_read_all: boolean;
  has_files_read_all: boolean;
  has_calendar_access: boolean;
  has_admin_consent: boolean;
  consent_count: number;
  admin_consented: boolean;
  is_new_app: boolean;
  is_internal: boolean;
  audience: string | null;
  detection_reasons: string[];
  app_created_at: string | null;
  first_seen_at: string;
  last_scan_at: string;
  created_at: string;
  updated_at: string;
}

export interface OAuthAppListResponse {
  items: OAuthApp[];
  total: number;
  limit: number;
  offset: number;
}

export interface OAuthAppAlert {
  id: string;
  app_id: string;
  tenant_id: string;
  alert_type: string;
  severity: string;
  title: string;
  description: string;
  is_acknowledged: boolean;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  created_at: string;
}

export interface OAuthAppAlertListResponse {
  items: OAuthAppAlert[];
  total: number;
  limit: number;
  offset: number;
}

export interface OAuthAppsSummary {
  total_apps: number;
  by_risk_level: Record<string, number>;
  by_status: Record<string, number>;
  mail_access_apps: number;
  unverified_publisher_apps: number;
  total_alerts: number;
  unacknowledged_alerts: number;
}
