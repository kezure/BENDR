DOT_ENV=.env
GITHUB_NETRC=${HOME}/.netrc
GITHUB_NETRC_CI=${GITHUB_WORKSPACE}/netrc

PACKAGE_NAME=dn3

precommit-install:
	poetry run pre-commit install

precommit-update:
	poetry run pre-commit autoupdate

check:
	poetry run pre-commit run --all-files

pre-chown:
	sudo chown -R ${USER}:${USER} tests/

pytest:
	poetry run pytest -s

pytest-dist:
	poetry run pytest -s -n auto

pytest-dist-all:
	poetry run pytest -s -n auto --runslow

coverage-pytest:
	poetry run pytest --cov-report lcov --cov=${PACKAGE_NAME} -s --runslow

coverage-pytest-dist:
	poetry run pytest --cov-report lcov --cov=${PACKAGE_NAME} -s -n auto --runslow

coverage-report:
	poetry run coverage report -m

coverage:
	@make coverage-pytest
	@make coverage-report

coverage-dist:
	@make coverage-pytest-dist
	@make coverage-report

sphinx-apidoc:
	poetry run sphinx-apidoc -F -o docs/source ${PACKAGE_NAME}/

sphinx:
	poetry run sphinx-build docs/source docs/build
