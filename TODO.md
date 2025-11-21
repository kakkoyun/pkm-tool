# TODO

## Features

### Phase 0

- [x] Add subcommands to the CLI for each datasource, so that we can use the CLI to get data from each datasource separately.

### Phase 1

- [ ] Feature: Add Whoop integration

### Phase 2

- [ ] Feature: Support day ranges
- [ ] Feature: Add an option to exclude weekend (all, and for certain datasources, this could go to config)

### Phase 3

- [ ] Authentication: Add a way to authenticate with the datasources, prompting and opening webpages to
  authenticate and storing the tokens in a secure way (OAuth2, API Key, etc.)
- [ ] Authentication: Implement a way to encrypt the secrects (git crypt? or 1password? or pgp, ideally in repo
  is good, this is a personal repo)
- [ ] Authentication: Add a tiny sqlite db to keep track of the tokens so that we know when to refresh them

### Phase 4

- [ ] Feature: Add a mode to run as an MCP server `pkm mcp ...`
- [ ] Feature: Add a mode to run as a web server `pkm server ...` that serves a REST API and a web UI using FastAPI and Streamlit.

## Plumbing

- [ ] TBD
