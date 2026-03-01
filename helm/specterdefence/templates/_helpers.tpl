{{/*
Expand the name of the chart.
*/}}
{{- define "specterdefence.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "specterdefence.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "specterdefence.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "specterdefence.labels" -}}
helm.sh/chart: {{ include "specterdefence.chart" . }}
{{ include "specterdefence.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- if .Values.global.environment }}
environment: {{ .Values.global.environment }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "specterdefence.selectorLabels" -}}
app.kubernetes.io/name: {{ include "specterdefence.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
API specific labels
*/}}
{{- define "specterdefence.apiLabels" -}}
{{ include "specterdefence.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
API selector labels
*/}}
{{- define "specterdefence.apiSelectorLabels" -}}
{{ include "specterdefence.selectorLabels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
Frontend specific labels
*/}}
{{- define "specterdefence.frontendLabels" -}}
{{ include "specterdefence.labels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Frontend selector labels
*/}}
{{- define "specterdefence.frontendSelectorLabels" -}}
{{ include "specterdefence.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Collector specific labels
*/}}
{{- define "specterdefence.collectorLabels" -}}
{{ include "specterdefence.labels" . }}
app.kubernetes.io/component: collector
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "specterdefence.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "specterdefence.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Determine the secret name to use based on configuration
*/}}
{{- define "specterdefence.secretName" -}}
{{- if .Values.secrets.existingSecret.enabled }}
{{- .Values.secrets.existingSecret.name }}
{{- else if .Values.secrets.externalSecrets.enabled }}
{{- include "specterdefence.fullname" . }}-secrets
{{- else if .Values.secrets.helmManaged.enabled }}
{{- include "specterdefence.fullname" . }}-secrets
{{- else }}
{{- include "specterdefence.fullname" . }}-secrets
{{- end }}
{{- end }}

{{/*
API fullname
*/}}
{{- define "specterdefence.apiFullname" -}}
{{- printf "%s-api" (include "specterdefence.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Frontend fullname
*/}}
{{- define "specterdefence.frontendFullname" -}}
{{- printf "%s-frontend" (include "specterdefence.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Collector fullname
*/}}
{{- define "specterdefence.collectorFullname" -}}
{{- printf "%s-collector" (include "specterdefence.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Validation helper - ensure at least one secret source is enabled
*/}}
{{- define "specterdefence.validateSecrets" -}}
{{- if not (or .Values.secrets.existingSecret.enabled .Values.secrets.externalSecrets.enabled .Values.secrets.helmManaged.enabled) }}
{{- fail "At least one secret source must be enabled. Set secrets.existingSecret.enabled=true, secrets.externalSecrets.enabled=true, or secrets.secrets.helmManaged.enabled=true" }}
{{- end }}
{{- end }}

{{/*
Get the API image tag
*/}}
{{- define "specterdefence.apiImageTag" -}}
{{- .Values.api.image.tag | default .Chart.AppVersion }}
{{- end }}

{{/*
Get the frontend image tag
*/}}
{{- define "specterdefence.frontendImageTag" -}}
{{- .Values.frontend.image.tag | default .Chart.AppVersion }}
{{- end }}

{{/*
Get the collector image tag
*/}}
{{- define "specterdefence.collectorImageTag" -}}
{{- .Values.collector.image.tag | default .Values.api.image.tag | default .Chart.AppVersion }}
{{- end }}

{{/*
Get the API image repository
*/}}
{{- define "specterdefence.apiImageRepository" -}}
{{- .Values.api.image.repository }}
{{- end }}

{{/*
Get the frontend image repository
*/}}
{{- define "specterdefence.frontendImageRepository" -}}
{{- .Values.frontend.image.repository }}
{{- end }}

{{/*
Get the collector image repository
*/}}
{{- define "specterdefence.collectorImageRepository" -}}
{{- .Values.collector.image.repository | default .Values.api.image.repository }}
{{- end }}

{{/*
Database URL - use from secrets or construct from PostgreSQL subchart
*/}}
{{- define "specterdefence.databaseUrl" -}}
{{- if .Values.api.config.databaseUrl }}
{{- .Values.api.config.databaseUrl }}
{{- else if .Values.postgresql.enabled }}
{{- $pgHost := include "postgresql.v1.primary.fullname" (dict "Values" .Values.postgresql "Chart" (dict "Name" "postgresql") "Release" .Release) }}
{{- printf "postgresql://%s:%s@%s:5432/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password $pgHost .Values.postgresql.auth.database }}
{{- else }}
{{- "sqlite:///./specterdefence.db" }}
{{- end }}
{{- end }}

{{/*
Redis URL - construct from Redis subchart
*/}}
{{- define "specterdefence.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- $redisHost := include "redis.v1.masterHost" (dict "Values" .Values.redis "Chart" (dict "Name" "redis") "Release" .Release) }}
{{- printf "redis://%s:6379/0" $redisHost }}
{{- else }}
{{- "" }}
{{- end }}
{{- end }}

{{/*
API service name
*/}}
{{- define "specterdefence.apiServiceName" -}}
{{- printf "%s" (include "specterdefence.apiFullname" .) }}
{{- end }}

{{/*
Frontend service name
*/}}
{{- define "specterdefence.frontendServiceName" -}}
{{- printf "%s" (include "specterdefence.frontendFullname" .) }}
{{- end }}
