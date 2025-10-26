.PHONY: Pipfile.lock
Pipfile.lock:
	docker compose --progress=plain build
	docker compose --progress=plain run --rm --name de-identifier-shell dev sh -c "rm -f Pipfile.lock && pipenv lock --dev"

build:
	docker compose build --parallel

.PHONY:shell
shell: build ## Brings up the bash shell in dev docker
	docker compose --progress=plain run --rm --name de-identifier-shell dev sh

.PHONY:update
update: Pipfile.lock  ## Updates all the packages using Pipfile
	make build

# config file format: https://github.com/microsoft/Tools-for-Health-Data-Anonymization/blob/master/docs/FHIR-anonymization.md#fhir-path-rules

.PHONY: run
run: build
	python3 data/config/scripts/merge_configs.py && \
	rm -rf ./data/output/* && \
	docker compose run --rm --name de-identifier-shell dev anonymize -r --validateInput --validateOutput \
	-i /data/input/large/ -o /data/output/large/ -c /data/config/merged/merged.json -v && \
	make find_text

.PHONY: find_text
find_text:
	python3 find_text_in_files.py data/output/large bailey

.PHONY: up
up: build
	docker compose --progress=plain up

.PHONY: down
down:
	docker compose --progress=plain down


.PHONY: validate
validate:
	docker compose -f docker-compose-validate.yml down
	docker compose -f docker-compose-validate.yml up -d
	@#./scripts/wait-for-healthy.sh fhir_deidentifier-fhir-validator-1 500
	docker compose -f docker-compose-validate.yml exec validate-script sh -c "pip install --root-user-action=ignore --upgrade pip && pip install --root-user-action=ignore requests && python validate.py /data/output/large"
	docker compose -f docker-compose-validate.yml down
