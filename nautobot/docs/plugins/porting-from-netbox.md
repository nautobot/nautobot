# Porting NetBox Plugins to Nautobot

Given an existing NetBox plugin, it will range from straightforward to very complicated to create a port of this plugin that's compatible with Nautobot, though in general it should be easier than developing a comparable plugin entirely from scratch. Of course, it would be impossible to provide a generalized, step-by-step guide that would cover all possibilities, but this document at least documents some known tips and tricks for this purpose.

## Updating Python module import paths

The most likely first issue you will encounter will be a module import problem, and in most cases a simple change to the name of imported modules will suffice:

- `circuits.* -> nautobot.circuits.*`
- `dcim.* -> nautobot.dcim.*`
- `extras.* -> nautobot.extras.*`
- `ipam.* -> nautobot.ipam.*`
- `netbox.* -> nautobot.core.*`
- `tenancy.* -> nautobot.tenancy.*`
- `utilities.* -> nautobot.utilities.*`
- `virtualization.* -> nautobot.virtualization.*`

## Regenerating database migrations

In general, your migrations files will not port over easily; you will probably want to delete and re-generate them (`nautobot-server makemigrations <plugin-name>`) instead.
