.PHONY: run install format clean
run:
	python app.py

install:
	pip install -r requirements.txt

format:
	black app.py

clean:
	find ./data -type f -name "*backup*.sqlite" -delete
	find ./data -type f -name "backup_before_restore_*.sqlite" -delete


