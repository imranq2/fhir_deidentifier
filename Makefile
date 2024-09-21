build:
	docker compose build --progress plain

.PHONY:shell
shell: ## Brings up the bash shell in dev docker
	docker compose --progress=plain build --parallel
	docker compose --progress=plain run --rm --name de-identifier-shell fhir-de-identifier /bin/sh

# config file format: https://github.com/microsoft/Tools-for-Health-Data-Anonymization/blob/master/docs/FHIR-anonymization.md#fhir-path-rules

.PHONY: run
run:
	rm -rf ./data/output/* && \
	docker compose run --rm --name de-identifier-shell fhir-de-identifier anonymize -r -i /data/input/large/ -o /data/output/large/ -c /data/config/config.json -v && \
	make find_text

.PHONY: find_text
find_text:
	python3 find_text_in_files.py data/output/large large

.PHONY: up
up:
	docker compose up
