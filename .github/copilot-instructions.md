# KubeMarketApp - AI Coding Agent Instructions

## Project Overview
KubeMarketApp is a Flask-based web application designed for Kubernetes deployment with Helm charts. This is a learning/demo project combining Python web development with cloud-native deployment practices.

## Architecture

### Application Layer
- **Flask App** (`main.py`): Simple "Hello World" web server
  - Single route at `/` returning HTML
  - Runs on port 5000 (containerized) / 5001 (local dev)
  - Dependencies: `flask>=3.11`, `requests>=2.32.3`

### Containerization
- **Dockerfile**: Python 3.11-slim base with Flask
  - Exposes port 5001
  - Sets `FLASK_APP=main.py` and `FLASK_RUN_HOST=0.0.0.0`
  - Uses `flask run` as entry point (not production-ready)

### Kubernetes/Helm
- **Helm Chart** (`mychart/`): Standard chart structure for deploying the app
  - Chart name: `mychart`, version: `0.1.0`
  - **Important**: `values.yaml` uses nginx as default image - must override for Flask app
  - Templates follow standard Helm patterns with helper functions in `_helpers.tpl`
  - Includes: Deployment, Service, Ingress, HPA, ServiceAccount
  - Default service: ClusterIP on port 80 (mismatch with Flask port 5000)

### Scripts
- `scripts/cluster-bootstrap.sh`: ArgoCD installation commands using Helm
- `scripts/run.sh`: Wrapper for `flask --app main run`

## Developer Workflows

### Local Development
```bash
# Direct Flask execution
flask --app main run          # Or use: make run
open http://0.0.0.1:5001     # Or use: make open
```

### Docker Workflow
```bash
make docker                   # Builds image as 'flask-app', runs on port 5001:5000
```

### Helm Deployment
No direct Helm commands in makefile. Manual deployment would require:
- Building and pushing custom Flask image
- Overriding `values.yaml` image.repository and image.tag
- Adjusting service port from 80 to match Flask (5000)

## Critical Discrepancies to Address

### Port Mismatches
- **Local dev**: Port 5001 (makefile)
- **Dockerfile**: Exposes 5001, but Flask runs on 5000 inside container
- **Docker compose**: Maps 5001:5000
- **Helm service**: Port 80, containerPort 80 in deployment
- **Fix needed**: Align Helm templates with Flask's port 5000

### Image Configuration
- **values.yaml** uses `nginx` as repository - must override to use custom Flask image
- No image registry or tagging strategy defined
- **When modifying**: Update `values.yaml` or provide override values

### Helm Template Assumptions
- Deployment expects containerPort 80, but Flask serves on 5000
- Liveness/readiness probes point to port 80 (will fail with Flask)
- **When editing templates**: Update `deployment.yaml` containerPort and probes

## Project Conventions

### Dependency Management
- Uses `pyproject.toml` (modern Python packaging)
- Project name: `marketapp`, requires Python >=3.11
- No lock file - use `pip install -e .` for dev or `pip install flask requests` directly

### Makefile Style
- Simple targets: `run`, `open`, `docker`
- No test, lint, or deployment targets
- Commands are direct (no @ prefix, output visible)

### Helm Templating
- Standard Go templating with helper functions from `_helpers.tpl`
- Uses `.Values` for configuration, `.Chart` for metadata
- Conditional rendering with `{{- if }}` for optional features (autoscaling, ingress)
- Label templates: `mychart.labels`, `mychart.selectorLabels`, `mychart.fullname`

## When Making Changes

### Adding Flask Routes
- Edit `main.py` directly
- No routing patterns established yet - follow Flask conventions
- Rebuild Docker image after changes

### Modifying Kubernetes Config
1. Edit `mychart/values.yaml` for configuration changes
2. Edit template files in `mychart/templates/` for structural changes
3. Test template rendering: `helm template mychart/`
4. Validate: `helm lint mychart/`

### Adding Dependencies
1. Update `pyproject.toml` dependencies array
2. Update `Dockerfile` RUN command to include new packages
3. Rebuild Docker image

### ArgoCD Integration
- Bootstrap script in `scripts/cluster-bootstrap.sh` installs ArgoCD
- No ArgoCD application manifests present yet
- When creating: Define app pointing to this Helm chart

## Key Files Reference
- `main.py`: Application entrypoint
- `Dockerfile`: Container build instructions
- `mychart/values.yaml`: Helm configuration defaults (needs Flask-specific overrides)
- `mychart/templates/deployment.yaml`: Pod specification (needs port correction)
- `makefile`: Development shortcuts
