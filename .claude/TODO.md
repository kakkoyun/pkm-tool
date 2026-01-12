# TODO

## Feature

TBD

## Bug

- [ ] Fix Whoop bug:
  Output:

```text
uv run pkm aggregate --date yesterday                                                                                                                                                                                                                                                                                                                                             (docker-desktop)
2026-01-12T13:09:44.494796Z [info     ] pkm_tool_started               [pkm_tool.cli] command=aggregate config_path=None date_input=yesterday exclude_weekends=False from_date=None no_auto_oauth=False no_preflight=False non_interactive=False output_format=markdown to_date=None verbose=False
2026-01-12T13:09:44.496346Z [info     ] config_file_found              [pkm_tool.config] path=/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.pkm.yaml
2026-01-12T13:09:44.496435Z [info     ] loading_config_file            [pkm_tool.config] path=/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.pkm.yaml

Pre-flight Authentication Check
----------------------------------------
  -      Apple Calendar     No authentication required
  OK     GitHub             Token valid (no expiration)
  -      Things             No authentication required
  X      Atlassian          Missing: api_token
  OK     Wakatime           Token valid (no expiration)
  -      Google Docs        Disabled in configuration
  X      Whoop              No token stored (OAuth configured)

Atlassian: Missing: api_token
2026-01-12T13:09:44.510507Z [info     ] config_file_found              [pkm_tool.config] path=/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.pkm.yaml
2026-01-12T13:09:44.510599Z [info     ] loading_config_file            [pkm_tool.config] path=/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.pkm.yaml
Atlassian base URL [https://datadoghq.atlassian.net]:
Atlassian email [kemal.akkoyun@datadoghq.com]:
Atlassian API token:
Atlassian API token:
Authentication failed for Atlassian

Whoop: No token stored (OAuth configured)

🌐 Opening browser to authenticate Whoop...
2026-01-12T13:09:50.494492Z [info     ] oauth_callback_server_started  [pkm_tool.auth.oauth.callback_server] callback_url=http://localhost:8000/callback port=8000
2026-01-12T13:09:50.494683Z [info     ] whoop_oauth_flow_started       [pkm_tool.auth.oauth.whoop] auth_url='https://api.prod.whoop.com/oauth/oauth2/auth?client_id=5308cd77-9117-47da-89bd-51c488fe862d&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback&response_type=code&scope=read%3Arecovery+read%3Asleep+read%3Aworkout+offline&state=PYFGt0nGe2qm5NnCBmHBF4xm7wyvJikqCgSyHSxO9oM' redirect_uri=http://localhost:8000/callback

🔐 Whoop Authentication Required
Opening browser for Whoop login...

→ https://api.prod.whoop.com/oauth/oauth2/auth?client_id=5308cd77-9117-47da-89bd-51c488fe862d&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback&response_type=code&scope=read%3Arecovery+read%3Asleep+read%3Aworkout+offline&state=PYFGt0nGe2qm5NnCBmHBF4xm7wyvJikqCgSyHSxO9oM

If browser doesn't open, visit the URL above.
Waiting for authentication...
2026-01-12T13:10:45.143508Z [info     ] oauth_callback_success         [pkm_tool.auth.oauth.callback_server] has_code=True state=PYFGt0nGe2qm5NnCBmHBF4xm7wyvJikqCgSyHSxO9oM
2026-01-12T13:10:45.143806Z [info     ] whoop_oauth_exchange_code      [pkm_tool.auth.oauth.whoop]
HTTP Request: POST https://api.prod.whoop.com/oauth/oauth2/token "HTTP/1.1 200 OK"
✅ Whoop authentication successful!
2026-01-12T13:10:45.640005Z [info     ] oauth_callback_server_stopped  [pkm_tool.auth.oauth.callback_server]
2026-01-12T13:10:45.643254Z [info     ] auth_token_saved               [pkm_tool.auth.manager] expires_at=2026-01-12T14:10:45.640545+00:00 source=whoop
2026-01-12T13:10:45.643879Z [info     ] preflight_oauth_interactive_success [pkm_tool.auth.preflight] source=whoop

Some sources still need configuration:
  - Atlassian: Missing: api_token
Proceed with available sources? [Y/n]:
2026-01-12T13:10:52.960913Z [info     ] starting_data_aggregation      [pkm_tool.cli] target_date=2026-01-11
2026-01-12T13:10:52.961244Z [info     ] aggregate_data_started         [pkm_tool.aggregator] target_date=2026-01-11
2026-01-12T13:10:52.961946Z [info     ] config_file_found              [pkm_tool.config] path=/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.pkm.yaml
2026-01-12T13:10:52.962069Z [info     ] loading_config_file            [pkm_tool.config] path=/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.pkm.yaml
2026-01-12T13:10:52.968551Z [info     ] fetching_source                [pkm_tool.aggregator] enabled=True source=apple_calendar
2026-01-12T13:10:53.106510Z [error    ] apple_calendar_applescript_error [pkm_tool.sources.apple_calendar] returncode=1 stderr='98:119: execution error: Calendar got an error: Can’t get date "January 11, 2026". (-1728)'
2026-01-12T13:10:53.106878Z [info     ] source_fetch_completed         [pkm_tool.aggregator] duration_seconds=0.14 items_count=0 source=apple_calendar
2026-01-12T13:10:53.106932Z [info     ] fetching_source                [pkm_tool.aggregator] enabled=True source=github
2026-01-12T13:10:53.395648Z [info     ] github_authenticated           [pkm_tool.sources.github] username=kakkoyun
2026-01-12T13:11:01.784419Z [info     ] github_activities_fetched      [pkm_tool.sources.github] activity_count=1
2026-01-12T13:11:01.784535Z [info     ] source_fetch_completed         [pkm_tool.aggregator] duration_seconds=8.68 items_count=1 source=github
2026-01-12T13:11:01.784577Z [info     ] fetching_source                [pkm_tool.aggregator] enabled=True source=atlassian
2026-01-12T13:11:01.784868Z [warning  ] atlassian_credentials_missing  [pkm_tool.sources.atlassian] has_base_url=True has_token=False has_username=True
2026-01-12T13:11:01.784909Z [info     ] source_fetch_completed         [pkm_tool.aggregator] duration_seconds=0.00 items_count=0 source=atlassian
2026-01-12T13:11:01.784938Z [info     ] fetching_source                [pkm_tool.aggregator] enabled=True source=things
2026-01-12T13:11:02.831252Z [info     ] things_tasks_fetched           [pkm_tool.sources.things] task_count=13
2026-01-12T13:11:02.831351Z [info     ] source_fetch_completed         [pkm_tool.aggregator] duration_seconds=1.05 items_count=13 source=things
2026-01-12T13:11:02.831389Z [info     ] source_skipped_weekend         [pkm_tool.aggregator] source=wakatime
2026-01-12T13:11:02.831411Z [info     ] fetching_source                [pkm_tool.aggregator] enabled=True source=whoop
2026-01-12T13:11:02.837827Z [error    ] whoop_recovery_fetch_failed    [pkm_tool.sources.whoop] error='[Errno 8] nodename nor servname provided, or not known'
Traceback (most recent call last):
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 101, in map_httpcore_exceptions
    yield
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 250, in handle_request
    resp = self._pool.handle_request(req)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection_pool.py", line 256, in handle_request
    raise exc from None
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection_pool.py", line 236, in handle_request
    response = connection.handle_request(
        pool_request.request
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection.py", line 101, in handle_request
    raise exc
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection.py", line 78, in handle_request
    stream = self._connect(request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection.py", line 124, in _connect
    stream = self._network_backend.connect_tcp(**kwargs)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_backends/sync.py", line 207, in connect_tcp
    with map_exceptions(exc_map):
         ~~~~~~~~~~~~~~^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_exceptions.py", line 14, in map_exceptions
    raise to_exc(exc) from exc
httpcore.ConnectError: [Errno 8] nodename nor servname provided, or not known

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/src/pkm_tool/sources/whoop.py", line 131, in fetch_whoop_recovery
    response = client.get(
        "https://api.whoop.com/v1/recovery",
        params={"start": start_str, "end": end_str},
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1053, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 825, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 914, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 942, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 979, in _send_handling_redirects
    response = self._send_single_request(request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1014, in _send_single_request
    response = transport.handle_request(request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_httpx.py", line 177, in handle_request
    internal_response = self._cache_proxy.handle_request(internal_request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_cache.py", line 61, in handle_request
    return self._handle_request_respecting_spec(request)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_cache.py", line 160, in _handle_request_respecting_spec
    state = self._handle_cache_miss(state)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_cache.py", line 184, in _handle_cache_miss
    response = self.send_request(state.request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_httpx.py", line 188, in request_sender
    httpx_response = self.next_transport.handle_request(httpx_request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 249, in handle_request
    with map_httpcore_exceptions():
         ~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 118, in map_httpcore_exceptions
    raise mapped_exc(message) from exc
httpx.ConnectError: [Errno 8] nodename nor servname provided, or not known
2026-01-12T13:11:02.849354Z [error    ] whoop_sleep_fetch_failed       [pkm_tool.sources.whoop] error='[Errno 8] nodename nor servname provided, or not known'
Traceback (most recent call last):
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 101, in map_httpcore_exceptions
    yield
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 250, in handle_request
    resp = self._pool.handle_request(req)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection_pool.py", line 256, in handle_request
    raise exc from None
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection_pool.py", line 236, in handle_request
    response = connection.handle_request(
        pool_request.request
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection.py", line 101, in handle_request
    raise exc
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection.py", line 78, in handle_request
    stream = self._connect(request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection.py", line 124, in _connect
    stream = self._network_backend.connect_tcp(**kwargs)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_backends/sync.py", line 207, in connect_tcp
    with map_exceptions(exc_map):
         ~~~~~~~~~~~~~~^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_exceptions.py", line 14, in map_exceptions
    raise to_exc(exc) from exc
httpcore.ConnectError: [Errno 8] nodename nor servname provided, or not known

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/src/pkm_tool/sources/whoop.py", line 209, in fetch_whoop_sleep
    response = client.get(
        "https://api.whoop.com/v1/sleep",
        params={"start": start_str, "end": end_str},
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1053, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 825, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 914, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 942, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 979, in _send_handling_redirects
    response = self._send_single_request(request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1014, in _send_single_request
    response = transport.handle_request(request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_httpx.py", line 177, in handle_request
    internal_response = self._cache_proxy.handle_request(internal_request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_cache.py", line 61, in handle_request
    return self._handle_request_respecting_spec(request)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_cache.py", line 160, in _handle_request_respecting_spec
    state = self._handle_cache_miss(state)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_cache.py", line 184, in _handle_cache_miss
    response = self.send_request(state.request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_httpx.py", line 188, in request_sender
    httpx_response = self.next_transport.handle_request(httpx_request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 249, in handle_request
    with map_httpcore_exceptions():
         ~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 118, in map_httpcore_exceptions
    raise mapped_exc(message) from exc
httpx.ConnectError: [Errno 8] nodename nor servname provided, or not known
2026-01-12T13:11:02.856594Z [error    ] whoop_workouts_fetch_failed    [pkm_tool.sources.whoop] error='[Errno 8] nodename nor servname provided, or not known'
Traceback (most recent call last):
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 101, in map_httpcore_exceptions
    yield
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 250, in handle_request
    resp = self._pool.handle_request(req)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection_pool.py", line 256, in handle_request
    raise exc from None
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection_pool.py", line 236, in handle_request
    response = connection.handle_request(
        pool_request.request
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection.py", line 101, in handle_request
    raise exc
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection.py", line 78, in handle_request
    stream = self._connect(request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_sync/connection.py", line 124, in _connect
    stream = self._network_backend.connect_tcp(**kwargs)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_backends/sync.py", line 207, in connect_tcp
    with map_exceptions(exc_map):
         ~~~~~~~~~~~~~~^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpcore/_exceptions.py", line 14, in map_exceptions
    raise to_exc(exc) from exc
httpcore.ConnectError: [Errno 8] nodename nor servname provided, or not known

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/src/pkm_tool/sources/whoop.py", line 270, in fetch_whoop_workouts
    response = client.get(
        "https://api.whoop.com/v1/workout",
        params={"start": start_str, "end": end_str},
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1053, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 825, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 914, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 942, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 979, in _send_handling_redirects
    response = self._send_single_request(request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1014, in _send_single_request
    response = transport.handle_request(request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_httpx.py", line 177, in handle_request
    internal_response = self._cache_proxy.handle_request(internal_request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_cache.py", line 61, in handle_request
    return self._handle_request_respecting_spec(request)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_cache.py", line 160, in _handle_request_respecting_spec
    state = self._handle_cache_miss(state)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_cache.py", line 184, in _handle_cache_miss
    response = self.send_request(state.request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/hishel/_sync_httpx.py", line 188, in request_sender
    httpx_response = self.next_transport.handle_request(httpx_request)
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 249, in handle_request
    with map_httpcore_exceptions():
         ~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "/Users/kemal.akkoyun/Workspace/Projects/Personal/pkm-tool/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 118, in map_httpcore_exceptions
    raise mapped_exc(message) from exc
httpx.ConnectError: [Errno 8] nodename nor servname provided, or not known
2026-01-12T13:11:02.858139Z [info     ] source_fetch_completed         [pkm_tool.aggregator] duration_seconds=0.03 items_count=0 recovery_count=0 sleep_count=0 source=whoop workout_count=0
2026-01-12T13:11:02.858190Z [info     ] aggregate_data_completed       [pkm_tool.aggregator] target_date=2026-01-11
2026-01-12T13:11:02.858215Z [info     ] data_aggregation_completed     [pkm_tool.cli] target_date=2026-01-11
# Daily Report - 2026-01-11

## 🐙 GitHub Activities

- 🔀 **04:06** [ROCm/HIPIFY](https://github.com/ROCm/HIPIFY) - Untitled PR
  - Action: assigned

## ✅ Things - Completed Tasks

- **09:35** Go to Groceries or Order Online #Life, #Errand
- **09:35** Build a routine for Atlas #Atlas Robin
- **09:35** Do more things TOGETHER  #Mantra, #Life, #Rüya
- **09:35** Be there for her #Mantra, #Rüya
- **09:35** Strategical thinking over tactical  #Mantra
- **09:35** flow: READ -> WRITE | EXERCISE  #Mantra, #Planning
- **09:35** Consistency over intensity #Mantra, #Mental Health
- **09:35** Slow Productivity  #Mantra
- **09:35** capture: Record your ideas by speaking #Reminder
- **09:35** What is wrong with my situation? #Mantra, #Productivity
- **09:45** Ping Sister #Family
- **09:46** Take your supplements (+ CREATINE) #Reminder, #Daily
- **21:08** photo: Record valuable moments #Family

2026-01-12T13:11:02.858357Z [info     ] pkm_tool_completed             [pkm_tool.cli] output_format=markdown
```
