#!/bin/bash
# Script to retrieve the API password from Kubernetes secret

NAMESPACE="kube-market-app"
SECRET_NAME="marketapi-auth"

echo "=== MarketApp API Credentials ==="
echo ""
echo "Username: $(kubectl get secret $SECRET_NAME -n $NAMESPACE -o jsonpath='{.data.username}' | base64 -d)"
echo "Password: $(kubectl get secret $SECRET_NAME -n $NAMESPACE -o jsonpath='{.data.password}' | base64 -d)"
echo ""
echo "=== Usage Example ==="
echo "curl -u admin:PASSWORD https://your-domain.com/marketapi/v1/networth?latest=true"
