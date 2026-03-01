{{/*
Expand the name of the chart.
*/}}
{{- define "specterdefence.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
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
{{- end }}

{{/*
Selector labels
*/}}
{{- define "specterdefence.selectorLabels" -}}
app.kubernetes.io/name: {{ include "specterdefence.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
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
Validation helper - ensure at least one secret source is enabled
*/}}
{{- define "specterdefence.validateSecrets" -}}
{{- if not (or .Values.secrets.existingSecret.enabled .Values.secrets.externalSecrets.enabled .Values.secrets.helmManaged.enabled) }}
{{- fail "At least one secret source must be enabled. Set secrets.existingSecret.enabled=true, secrets.externalSecrets.enabled=true, or secrets.helmManaged.enabled=true" }}
{{- end }}
{{- end }}
