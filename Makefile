.PHONY: infra infra-down up down api worker worker-install web web-install test

infra: ## start postgres + redis
	docker compose up -d postgres redis

infra-down:
	docker compose down

up: ## build & run api + worker + infra in docker
	docker compose up --build

down:
	docker compose down

api: ## run api locally (needs JDK 21 + Maven; otherwise use `make up`)
	cd api && mvn spring-boot:run

worker-install:
	python3 -m pip install -e "./worker[dev]"

worker: ## run worker locally against `make infra`
	cd worker && python3 -m lectern_worker.main

web-install:
	npm install --prefix web

web: ## next.js dev server on :3000
	npm run dev --prefix web

test: ## fast local checks (worker tests; api tests run in docker/CI)
	cd worker && python3 -m pytest -q
