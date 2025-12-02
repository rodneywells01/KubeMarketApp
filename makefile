run:
	flask --app main run
open:
	open http://0.0.0.1:5001

# Local Docker development
docker:
	docker build -t flask-app .
	@echo "Building and starting Flask app..."
	docker run -p 5001:5000 flask-app
	@echo "Flask app running at http://localhost:5001"

# GitHub Container Registry targets
IMAGE_NAME = ghcr.io/rodneywells01/kubermarketapp
GIT_SHA = $(shell git rev-parse --short HEAD)
GIT_TAG = $(shell git describe --tags --abbrev=0 2>/dev/null || echo "v0.1.0")

.PHONY: build-ghcr
build-ghcr:
	@echo "Building image for GHCR..."
	docker build -t $(IMAGE_NAME):$(GIT_SHA) -t $(IMAGE_NAME):latest .
	@echo "Built: $(IMAGE_NAME):$(GIT_SHA)"
	@echo "Built: $(IMAGE_NAME):latest"

.PHONY: push-ghcr
push-ghcr:
	@echo "Pushing to GHCR..."
	docker push $(IMAGE_NAME):$(GIT_SHA)
	docker push $(IMAGE_NAME):latest
	@echo "Pushed $(IMAGE_NAME):$(GIT_SHA)"
	@echo "Pushed $(IMAGE_NAME):latest"

.PHONY: login-ghcr
login-ghcr:
	@echo "Login to GHCR with: echo \$$GITHUB_TOKEN | docker login ghcr.io -u rodneywells01 --password-stdin"
	@echo "Or create token at: https://github.com/settings/tokens"

.PHONY: release
release: build-ghcr push-ghcr
	@echo "Released $(IMAGE_NAME):$(GIT_SHA)"