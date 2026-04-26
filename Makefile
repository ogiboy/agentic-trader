.PHONY: setup check check-python check-node build qa qa-quality qa-sonar sonar sonar-local sonar-cloud sonar-py sonar-js sonar-start sonar-stop sonar-status sonar-secret-check sonarcloud-secret-check sonar-mcp-dry-run webgui docs tui clean

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

webgui:
	pnpm run dev:webgui

docs:
	pnpm run dev:docs

tui:
	pnpm run start:tui

clean:
	pnpm run clean
