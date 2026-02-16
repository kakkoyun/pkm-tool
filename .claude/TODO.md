# TODO

## Features

TBD

## Bug Fixes

- [ ] Atlassian: Token refresh does NOT work. It prompts for the setup again. Setup shouldn't be triggered if we have
  stored the client credentials. The token should be refreshed in the background without prompting or opening browser if
  it is possible.
- [ ] Wakatime: Why are the test fixtures getting printed on real life usage?
- [ ] Apple Calendar: It consistently times out. `iCalBuddy` super fast and just works. How did we mess up?
- [ ] GitHub: The whole approach could be wrong. I review PRs and opened a PR today I don't see anything. Check the
  docs. How we can do this? Github MCP was doing it.

______________________________________________________________________

!! NOT NOW !!

## Future

Maybe funneling CLIs is easier than implementing all the datasource APIs (or as a fallback):

- Github: `gh` <https://cli.github.com/>
- Atlassian: `?` <https://developer.atlassian.com/cloud/acli/reference/commands/>
- Apple Calendar: `iCalBuddy` <https://hasseg.org/icalBuddy/w>
- Things3: Official CLI <https://github.com/thingsapi/things-cli>
- Google Docs: `?`. NADA.
- Whoop: Does not have a CLI.
- Wakatime: `wakatime-cli` Official CLI <https://github.com/wakatime/wakatime-cli>
