.PHONY: test-openshift-4
test-openshift-4:
	pip3 install uv && uv pip install --no-cache -r requirements.txt && PYTHONPATH=$(CURDIR) python3 app.py