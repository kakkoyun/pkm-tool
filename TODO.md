# TODO

## Features

### Phase 0

- [ ] Add subcommands to the CLI for each datasource, so that we can use the CLI to get data from each datasource separately.

### Phase 1

- [ ] Authentication: Add a way to authenticate with the datasources, prompting and opening webpages to authenticate and storing the tokens in a secure way (OAuth2, API Key, etc.)
- [ ] Authentication: Implement a way to encrypt the secrects (git crypt? or 1password? or pgp, ideally in repo is good, this is a personal repo)
- [ ] Authentication: Add a tiny sqlite db to keep track of the tokens so that we know when to refresh them

### Phase 2

- [ ] Feature: Support day ranges
- [ ] Feature: Add an option to exclude weekend (all, and for certain datasources, this could go to config)

### Phase 3

- [ ] Feature: Add Whoop integration

### Phase 4

- [ ] Feature: Add a mode to run as an MCP server `pkm mcp ...`
- [ ] Feature: Add a mode to run as a web server `pkm server ...`

## Plumbing

- [ ] Introduce structured logging, add extensive logs for troubleshooting
- [ ] Create a `.config` directory in the home directory and put the config file there. Update all the tooling to use this new location.
- [ ] Testing: Add snapshot testing for commands and CLI output
- [ ] Testing: API response recording and playback, mocking
- [ ] Testing: Add compherensive integration tests
