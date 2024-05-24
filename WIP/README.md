# Work-in-progress readme

This entire directory will be removed from the branch + PR, but it represents notes
and POCs used for developing this branch.

References:

- [Slack discussion thread](https://networktocode.slack.com/archives/C01NWPK6WHL/p1716306578055549)
- [PR](https://github.com/nautobot/nautobot/pull/5746)

## TODO

- Schema generation
   > Glenn M: looking back through the power of git blame at <https://github.com/nautobot/nautobot/pull/1994/files> this was trying to offload some of the GraphQL schema generation work so that it didn’t happen every time we generated the REST API schema. I agree that 618-619 seem redundant at best. IIRC the schema doesn’t actually get generated under graphene v2 until you actually access graphene_settings.SCHEMA for the first time
