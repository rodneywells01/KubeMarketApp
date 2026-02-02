# Authentication Setup for MarketApp API

## Overview

The MarketApp API now requires HTTP Basic Authentication for all `/marketapi/v1/*` endpoints. Credentials are securely stored in Kubernetes secrets and injected into the application as environment variables.

## Architecture

- **Authentication Method**: HTTP Basic Auth
- **Credential Storage**: Kubernetes Secret (`marketapi-auth`)
- **Implementation**: Flask-HTTPAuth library
- **Security**: All traffic secured via HTTPS with cert-manager/Let's Encrypt

## Kubernetes Secret Setup

### View Current Credentials

```bash
# Use the helper script
./scripts/get-api-password.sh

# Or manually:
kubectl get secret marketapi-auth -n kube-market-app -o jsonpath='{.data.username}' | base64 -d
kubectl get secret marketapi-auth -n kube-market-app -o jsonpath='{.data.password}' | base64 -d
```

### Rotate/Update Password

```bash
# Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# Update the secret
kubectl create secret generic marketapi-auth \
  --from-literal=username=admin \
  --from-literal=password=$NEW_PASSWORD \
  -n kube-market-app \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up new credentials
kubectl rollout restart deployment/kube-market-app-mychart -n kube-market-app
```

### Use Hashed Passwords (More Secure)

```bash
# Generate a password hash
cd KubeMarketApp
pipenv run python -c "from auth import get_password_hash; print(get_password_hash('your_password'))"

# Create secret with hash instead
kubectl create secret generic marketapi-auth \
  --from-literal=username=admin \
  --from-literal=password_hash='pbkdf2:sha256:...' \
  -n kube-market-app \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Usage

### API Access

```bash
# Using curl
curl -u admin:PASSWORD https://your-domain.com/marketapi/v1/networth?latest=true

# Using curl with explicit header
curl -H "Authorization: Basic $(echo -n admin:PASSWORD | base64)" \
  https://your-domain.com/marketapi/v1/networth?latest=true
```

### From Python

```python
import requests
from requests.auth import HTTPBasicAuth

response = requests.get(
    'https://your-domain.com/marketapi/v1/networth?latest=true',
    auth=HTTPBasicAuth('admin', 'your-password')
)
print(response.json())
```

### From Browser

Simply navigate to `https://your-domain.com/marketapi/v1/networth?latest=true` - your browser will prompt for username and password.

## Local Development

### Setup

```bash
# Set environment variables
export API_USERNAME=admin
export API_PASSWORD=testpass123

# Run the app
pipenv run flask --app main run
```

### Testing

```bash
# Without credentials (should return 401)
curl http://localhost:5000/marketapi/v1/networth?latest=true

# With credentials (should succeed)
curl -u admin:testpass123 http://localhost:5000/marketapi/v1/networth?latest=true
```

## Configuration

### Environment Variables

The application reads these environment variables (injected from Kubernetes secrets):

- `API_USERNAME`: Username for authentication
- `API_PASSWORD`: Plain text password (simpler, less secure)
- `API_PASSWORD_HASH`: Hashed password (more secure, recommended for production)

### Helm Values

Configure the secret name in `values.yaml`:

```yaml
auth:
  secretName: "marketapi-auth"  # Name of the K8s secret
```

## Security Considerations

### ✅ Strengths

- Credentials never stored in source code or git
- HTTPS encryption protects credentials in transit
- Simple, widely-supported authentication method
- Easy to rotate credentials without code changes

### ⚠️ Best Practices

1. **Always use HTTPS** - HTTP Basic Auth sends base64-encoded credentials (not encrypted)
2. **Use strong passwords** - Generate with `openssl rand -base64 32`
3. **Rotate regularly** - Update passwords periodically
4. **Consider hashed passwords** - Use `API_PASSWORD_HASH` for production
5. **Limit access** - Only share credentials with authorized users

### 🔄 Credential Rotation Schedule

- **Development**: As needed
- **Production**: Every 90 days recommended

## Troubleshooting

### Authentication Not Working

```bash
# Check if secret exists
kubectl get secret marketapi-auth -n kube-market-app

# Verify secret data
kubectl describe secret marketapi-auth -n kube-market-app

# Check pod logs
kubectl logs -n kube-market-app -l app.kubernetes.io/name=mychart --tail=50

# Look for this message on startup:
# INFO:main:✓ API authentication is configured and enabled
```

### 401 Unauthorized Errors

- Verify you're using the correct username and password
- Check that the secret is properly mounted to the pod
- Ensure the pod has been restarted after secret changes

### Authentication Disabled Warning

If you see `⚠ API authentication is NOT configured`, check:

```bash
# Verify environment variables in pod
kubectl exec -n kube-market-app deployment/kube-market-app-mychart -- env | grep API_
```

## Alternative Authentication Methods

### Option 1: API Key (Future Enhancement)

```yaml
# Future: Use API keys instead of username/password
headers:
  X-API-Key: your-secret-key
```

### Option 2: JWT Tokens (Future Enhancement)

```yaml
# Future: Login endpoint returns JWT token
POST /marketapi/v1/auth/login
GET /marketapi/v1/networth (with Bearer token)
```

## Files Changed

- `auth.py` - New authentication module
- `config.py` - Added `AuthConfig` class
- `main.py` - Added `@auth.login_required` decorator
- `mychart/templates/deployment.yaml` - Inject secrets as env vars
- `mychart/values.yaml` - Auth configuration
- `Pipfile` - Added Flask-HTTPAuth dependency
