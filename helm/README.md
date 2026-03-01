# SpecterDefence Helm Chart

This Helm chart deploys SpecterDefence on a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.12+

## Installing the Chart

```bash
helm install specterdefence ./helm
```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `specterdefence` |
| `image.tag` | Image tag | `Chart.AppVersion` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `8000` |
| `ingress.enabled` | Enable ingress | `false` |
| `config.debug` | Debug mode | `false` |

## Upgrading

```bash
helm upgrade specterdefence ./helm
```

## Uninstalling

```bash
helm uninstall specterdefence
```
