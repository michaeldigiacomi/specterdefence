#!/bin/bash
# Quick fix script for password persistence issue
# This reduces replicas to 1 to ensure SQLite database consistency

echo "🔧 SpecterDefence Password Persistence Quick Fix"
echo "================================================="
echo ""
echo "Problem: With 2 pods using SQLite, each pod has its own database."
echo "Solution: Reduce replicas to 1 until PostgreSQL is deployed."
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl and configure access to your cluster."
    exit 1
fi

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

echo "✓ Connected to Kubernetes cluster"
echo ""

# Scale down to 1 replica
echo "→ Scaling specterdefence deployment to 1 replica..."
kubectl scale deployment specterdefence --replicas=1 -n specterdefence

if [ $? -eq 0 ]; then
    echo "✓ Deployment scaled to 1 replica"
else
    echo "❌ Failed to scale deployment"
    exit 1
fi

# Wait for the pod to be ready
echo ""
echo "→ Waiting for pod to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=specterdefence -n specterdefence --timeout=60s

if [ $? -eq 0 ]; then
    echo "✓ Pod is ready"
else
    echo "⚠️  Pod may not be ready yet. Check status with: kubectl get pods -n specterdefence"
fi

echo ""
echo "================================================="
echo "✅ Quick fix applied!"
echo ""
echo "Password changes should now persist correctly."
echo ""
echo "For a permanent fix (multi-pod support), deploy PostgreSQL:"
echo "  kubectl apply -f k8s/postgres.yaml"
echo ""
echo "Then run the migration script:"
echo "  python scripts/migrate_to_postgres.py"
echo ""
echo "Finally, update your DATABASE_URL secret and scale back to 2 replicas."
echo ""
