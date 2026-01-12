# TODO

## Features

TBD

## Bug Fixes

- [ ] Atlassian: Token refresh does NOT work. It prompts for the setup again. Setup shouldn't be triggered if we have stored the client credentials. And the token should be refreshed in the background without prompting or opening browser if it is possible.
- [ ] Wakatime: Why are the test fixtures getting printed on real life usage?
- [ ] Apple Calendar: It consistently times out. `iCalBuddy` super fast and just works. How did we mess up?
- [ ] GitHub: The 

## Completed (2026-01-12)

- [x] GitHub activities still showing non-user activities
  - **Root cause**: `/events` API endpoint returns events from followed users and watched repos
  - **Solution**: Added actor filtering to verify `event.actor.login == authenticated_user.login`
  - **Files**: [src/pkm_tool/sources/github.py](src/pkm_tool/sources/github.py), [tests/fixtures/github_fixtures.py](tests/fixtures/github_fixtures.py)

- [x] Wakatime showing non-existent project "awesome-app"
  - **Root cause**: Test data in mock fixture (not a production bug)
  - **Solution**: Changed "awesome-app" to "pkm-tool-backend" in test fixtures
  - **Files**: [tests/fixtures/wakatime_fixtures.py](tests/fixtures/wakatime_fixtures.py)

- [x] Whoop data incomplete
  - **Root cause**: Data fetched correctly but formatter only displayed subset
  - **Solution**: Enhanced formatter to show Recovery (SpO2, skin temp), Sleep (awake, disturbances, performance), Workouts (max HR, calories)
  - **Files**: [src/pkm_tool/formatters.py](src/pkm_tool/formatters.py)

---

!! NOT NOW !!


## Future

Maybe funneling CLIs is easier than implementing all the datasource APIs (or as a fallback):

Github: `gh`
Atlassin: `?`
Apple Calendar: `iCalBuddy`
Things3: Official CLI
Google Docs: `?`
Whoop: Does not have a CLI
Wakatime: `wakatime-cli` Official CLI
