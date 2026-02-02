#!/bin/bash
# Restart the KubeMarketApp deployment to pick up config/secret changes

kubectl rollout restart deployment -n kube-market-app
kubectl rollout status deployment/kube-market-app-mychart -n kube-market-app
