# Closes: #DNE

## What's Changed

- Added `invoke unittest-parallel`.
    - Test outputs are stored in `test-results` directory.
- Added `invoke ps`.
- Added `invoke export`.
- Added `invoke 

## Considerations

- [Non-durable Django Postgres Testing](https://docs.djangoproject.com/en/3.2/ref/databases/#speeding-up-test-execution-with-non-durable-settings).
- Parallelize other Jobs (pylint takes a lot of time) to spare GH workers.

## TO-DO

- [ ] Is there a ticket for this PR?
- [ ] Display merged test results.
- [ ] Implement to CI.
