.PHONY: run install dev format clean setup

# Production run for OpenShift
run:
	python app.py --host=0.0.0.0 --port=$${PORT:-8080}

# Development run
dev:
	python app.py

# Install dependencies
install:
	pip install --no-cache-dir -r requirements.txt

# Setup for OpenShift deployment
setup: install
	mkdir -p data
	chmod 755 data

# Format code
format:
	black app.py

# Clean backup files
clean:
	find ./data -type f -name "*backup*.sqlite" -delete 2>/dev/null || true
	find ./data -type f -name "backup_before_restore_*.sqlite" -delete 2>/dev/null || true


