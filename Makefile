.DEFAULT_GOAL := help

.PHONY: help bootstrap bootstrap-dry-run setup setup-tools app-doctor app-setup app-start app-stop app-update setup-camofox fetch-camofox check-camofox setup-node setup-research-flow setup-research-crewai check check-python check-research-flow check-research-crewai check-node build qa qa-prompts qa-quality qa-sonar version-plan release-preview sonar sonar-local sonar-cloud sonar-py sonar-js sonar-start sonar-stop sonar-status sonar-secret-check sonarcloud-secret-check sonar-mcp-dry-run sonar-mcp-status sonar-mcp-install-wrapper run-research-flow run-research-crewai start-camofox webgui docs tui clean clean-deps clean-all

help:
	@printf '%s\n' \
		'Agentic Trader aliases:' \
		'  make bootstrap    inspect/install system tools with prompts' \
		'  make bootstrap-dry-run show system-tool installer actions' \
		'  make setup        install Python and Node dependencies' \
		'  make setup-tools  show runtime/tool setup status' \
		'  make app-doctor   read setup, provider, V1, and app-owned service readiness' \
		'  make app-setup    preview setup lifecycle or run explicit core repair with ARGS="--core --yes"' \
		'  make app-start    preview/start selected app-owned services with ARGS="--webgui --yes"' \
		'  make app-stop     preview/stop selected app-owned services with ARGS="--all --yes"' \
		'  make app-update   preview/update selected dependency owners with ARGS="--core --build --status --yes"' \
		'  make setup-camofox install optional Camofox helper deps without browser download' \
		'  make fetch-camofox download/update optional Camoufox browser binary' \
		'  make check-camofox syntax-check the optional Camofox helper' \
		'  make setup-node   install and verify root/webgui/docs/tui Node deps' \
		'  make setup-research-flow install CrewAI Flow sidecar dependencies' \
		'  make check        run Python and Node checks' \
		'  make check-research-flow run CrewAI Flow sidecar smoke checks' \
		'  make build        build webgui/docs and check TUI' \
		'  make qa           run terminal smoke QA' \
		'  make qa-prompts   lint prompt, agent, and instruction markdown files' \
		'  make sonar        run local Sonar scan' \
		'  make run-research-flow run the gated CrewAI Flow sidecar placeholder' \
		'  make start-camofox start optional loopback/auth Camofox helper' \
		'  make webgui       start Web GUI dev server' \
		'  make docs         start docs dev server' \
		'  make tui          start terminal UI' \
		'  make clean        remove local build/test artifacts' \
		'  make clean-deps   remove installed dependency directories' \
		'  make clean-all    remove artifacts and installed dependencies'

bootstrap:
	pnpm run bootstrap

bootstrap-dry-run:
	pnpm run bootstrap:dry-run

setup:
	pnpm run setup

setup-tools:
	pnpm run setup:tools

app-doctor:
	pnpm run app:doctor -- $(ARGS)

app-setup:
	pnpm run app:setup -- $(ARGS)

app-start:
	pnpm run app:start -- $(ARGS)

app-stop:
	pnpm run app:stop -- $(ARGS)

app-update:
	pnpm run app:update -- $(ARGS)

setup-camofox:
	pnpm run setup:camofox

fetch-camofox:
	pnpm run fetch:camofox

check-camofox:
	pnpm run check:camofox

setup-node:
	pnpm run setup:node

setup-research-flow:
	pnpm run setup:research-flow

setup-research-crewai: setup-research-flow

check:
	pnpm run check

check-python:
	pnpm run check:python

check-research-flow:
	pnpm run check:research-flow

check-research-crewai: check-research-flow

check-node:
	pnpm run check:node

build:
	pnpm run build

qa:
	pnpm run qa

qa-prompts:
	pnpm run qa:prompts

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

run-research-flow:
	pnpm run run:research-flow

run-research-crewai: run-research-flow

start-camofox:
	pnpm run start:camofox

webgui:
	pnpm run dev:webgui

docs:
	pnpm run dev:docs

tui:
	pnpm run start:tui

clean:
	pnpm run clean

clean-deps:
	pnpm run clean:deps

clean-all:
	pnpm run clean:all
