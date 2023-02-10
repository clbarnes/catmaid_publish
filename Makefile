.PHONY: format
format:
	isort . \
	&& black .

.PHONY: lint
lint:
	black --check .
	isort --check .
	flake8 .

lint-type: lint
	mypy .

.PHONY: test
test:
	pytest --verbose

.PHONY: install
install:
	pip install .

.PHONY: install-dev
install-dev:
	pip install -r requirements.txt \
	&& pip install -e ".[dev]"

.PHONY: container
container:
	sudo apptainer build --bind "$(shell pwd)/.git:/project/.git" catmaid_publish.sif ./Apptainer

.PHONY: readme
readme:
	catmaid_publish --help | p2c --tgt _catmaid_publish README.md

.PHONY: clean-docs
clean-docs:
	rm -rf docs/catmaid_publish

.PHONY: docs
docs: clean-docs
	pdoc3 --html --output-dir docs/ catmaid_publish
