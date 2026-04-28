.DEFAULT_GOAL := help

.PHONY: help setup check check-python check-node build qa qa-quality qa-sonar version-plan release-preview sonar sonar-local sonar-cloud sonar-py sonar-js sonar-start sonar-stop sonar-status sonar-secret-check sonarcloud-secret-check sonar-mcp-dry-run sonar-mcp-status sonar-mcp-install-wrapper webgui docs tui clean

help:
	@printf '%s\n' \
		'Agentic Trader aliases:' \
		'  make setup        install Python and Node dependencies' \
		'  make check        run Python and Node checks' \
		'  make build        build webgui/docs and check TUI' \
		'  make qa           run terminal smoke QA' \
		'  make sonar        run local Sonar scan' \
		'  make webgui       start Web GUI dev server' \
		'  make docs         start docs dev server' \
		'  make tui          start terminal UI' \
		'  make clean        remove local build/test artifacts'

setup:
	pnpm run setup

check:
	pnpm run check

check-python:
	pnpm run check:python

check-node:
	pnpm run check:node

build:
	pnpm run build

qa:
	pnpm run qa

qa-quality:
	pnpm run qa:quality

qa-sonar:
	pnpm run qa:sonar

version-plan:
	pnpm run version:plan

release-preview:
	pnpm run release:preview

sonar:
	pnpm run sonar

sonar-local:
	pnpm run sonar:local

sonar-cloud:
	pnpm run sonar:cloud

sonar-py:
	pnpm run sonar:py

sonar-js:
	pnpm run sonar:js

sonar-start:
	pnpm run sonar:start

sonar-stop:
	pnpm run sonar:stop

sonar-status:
	pnpm run sonar:status

sonar-secret-check:
	pnpm run secret:sonar:check

sonarcloud-secret-check:
	pnpm run secret:sonarcloud:check

sonar-mcp-dry-run:
	pnpm run mcp:sonarqube:dry-run

sonar-mcp-status:
	pnpm run mcp:sonarqube:status

sonar-mcp-install-wrapper:
	pnpm run mcp:sonarqube:install-wrapper

webgui:
	pnpm run dev:webgui

docs:
	pnpm run dev:docs

tui:
	pnpm run start:tui

clean:
	pnpm run clean
