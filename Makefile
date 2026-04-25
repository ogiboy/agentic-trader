.PHONY: setup check check-python check-node build webgui docs tui clean

setup:
	pnpm run setup

check:
	pnpm check

check-python:
	pnpm check:python

check-node:
	pnpm check:node

build:
	pnpm build

webgui:
	pnpm dev:webgui

docs:
	pnpm dev:docs

tui:
	pnpm start:tui

clean:
	pnpm clean
