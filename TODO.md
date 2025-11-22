# TODO

## Features

### Phase 0

- [x] Add subcommands to the CLI for each datasource, so that we can use the CLI to get data from each datasource separately.

### Phase 1

- [x] Feature: Add Whoop integration

### Phase 2

- [x] Feature: Support day ranges
- [x] Feature: Add an option to exclude weekend (all, and for certain datasources, this could go to config)

### Phase 3

- [x] Authentication: Add a way to authenticate with the datasources, prompting and opening webpages to
  authenticate and storing the tokens in a secure way (OAuth2, API Key, etc.)
- [x] Authentication: Implement a way to encrypt the secrects (git crypt? or 1password? or pgp, ideally in repo
  is good, this is a personal repo)
- [x] Authentication: Add a tiny sqlite db to keep track of the tokens so that we know when to refresh them

### Phase 4

- [ ] Feature: Add a mode to run as an MCP server `pkm mcp ...`
- [ ] Feature: Add a mode to run as a web server `pkm server ...` that serves a REST API and a web UI using FastAPI and Streamlit.

## Plumbing

- [ ] Make sure code is properly typed with ty everywhere!
- [ ] This tool never released, we don't have legacy or need to migrate clean the codebase and docs!
- [ ] Make sure we have consistent patterns and conventions throughout the codebase!
