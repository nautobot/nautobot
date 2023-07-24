# Migration Guide to Upgrade an App from V1 to V2

## Model Updates

### Core

#### Replace the Usage of Slugs with Natural Keys

### DCIM

#### Replace Site and Region with Location Model

### Extras

#### Replace Role Related Models with Generic Role Model

#### Update Job and Job related models

#### Update CustomField, ComputedField, and Relationship

### IPAM

#### Replace Aggregate with Prefix

#### Update Prefix to specify a namespace Namespace

#### Update IPAddress to specify a parent Prefix

## Code Updates

### Update Code Import Locations

### Replace PluginMenuItem with NavMenueItem

### Replace DjangoFilterBackend with NautobotFilterBackend

### Remove all CSV Import Forms

### Remove all Nested Serializers

### Update all Serializer Meta Attributes

## Dependency Updates

### Nautobot Version

### Python Version

### Pylint Version

### pylint-nautobot
