PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
.DEFAULT_GOAL := help
.PHONY: help doctor up verify status down test review
help:
	@echo 'WattShift: doctor | up | verify | status | test | review'
	@echo 'make down deletes only the wattshift kind cluster and its local data.'
doctor:
	$(PYTHON) scripts/cluster.py doctor
up:
	$(PYTHON) scripts/deploy.py up
verify:
	$(PYTHON) scripts/cluster.py verify
status:
	$(PYTHON) scripts/cluster.py status
down:
	$(PYTHON) scripts/cluster.py down
test:
	$(PYTHON) -m pytest -q
review: test
	$(PYTHON) scripts/review.py

.PHONY: cluster-up stack-up stack-lite stack-verify backend api frontend-build refresh ingest export demo-jobs grafana gpu
cluster-up:
	$(PYTHON) scripts/cluster.py up
stack-up:
	$(PYTHON) scripts/deploy.py up
stack-lite:
	$(PYTHON) scripts/deploy.py lite
stack-verify:
	$(PYTHON) scripts/deploy.py verify
backend:
	$(PYTHON) -m pip install -r requirements.lock.txt
api:
	$(PYTHON) -m uvicorn wattshift.api:app --host 127.0.0.1 --port 8000
frontend-build:
	cd apps/console && npm ci && npm test && npm run test:ui && npm run build
refresh:
	$(PYTHON) -m wattshift.refresh
ingest:
	$(PYTHON) -m wattshift.ingest
export:
	$(PYTHON) -m wattshift.export
	cp data/processed/console.json apps/console/public/data/console.json
demo-jobs:
	$(PYTHON) scripts/demo_jobs.py | kubectl --kubeconfig .local/kubeconfig --context kind-wattshift apply -f -
grafana:
	kubectl --kubeconfig .local/kubeconfig --context kind-wattshift -n wattshift port-forward service/wattshift-grafana 3000:3000
gpu:
	$(PYTHON) -m wattshift.gpu --seconds 60
