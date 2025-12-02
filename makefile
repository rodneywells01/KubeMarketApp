run:
	flask --app main run
open:
	open http://0.0.0.1:5001

docker:
	docker build -t flask-app .
	@echo "Building and starting Flask app..."
	docker run -p 5001:5000 flask-app
	@echo "Flask app running at http://localhost:5001"