# Nautobot Development

Nautobot is maintained as a [GitHub project](https://github.com/nautobot/nautobot) under the Apache 2 license. Users are encouraged to submit GitHub issues for feature requests and bug reports.

## Governance

Nautobot is a community-based Free Open Source Software (FOSS) project sponsored by [Network to Code (NTC)](https://www.networktocode.com). As a network automation solution provider, Network to Code works with its clients around the world to craft and build network automation strategies and solutions, often tightly integrated with Nautobot serving as a Source of Truth and Network Automation Platform. The direction of this project will be shaped by the community as well as by input from NTC customers; independent of where requests come from, contributors will need to follow the Contributing Guidelines.

The Nautobot Core Team is responsible for the direction and execution of the code that gets committed to the project. 

The following individuals are on the Nautobot Core Team:

  * John Anderson
  * Glenn Matthews
  * Jathan McCollum
  * Jason Edelman

## Contributing

We welcome many forms of contributions to Nautobot.  While we understand most contributions will commonly come from developers, we encourage others to contribute in the form of docs, tutorials, and user guides.  If you have other ideas for contributing, don't hesitate to open an issue or have a discussion in one of the forums below. 

### Release Management

In order to best understand how to contribute and where to open an issue or discussion, you should understand how work moves from idea to feature and how the roadmap is structured.

There are three major "buckets" of work to be aware of within the lifecycle of getting contributions committed and released:

* **Current** - Work that is planned for the release currently being developed.
* **Near Term** - Work that is planned for one of the next two releases after the one currently being developed.
* **Future** - Work that needs more discussion and/or will be planned for a version three or more releases later.

The following provides more detail on these.

#### Current 

* Current tickets (GitHub issues) that are being worked on for the _current_ release or bugs that are found and will be fixed in the _current_ release.
* Uses `current` label on GitHub.
* The GitHub **Release Milestone** will track items for the _current_ release.

> Note: Release window and date will be updated per [Release Management](release-management).

#### Near Term

* Current tickets (GitHub issues) that are estimated to complete in one of the next two releases, e.g. 3-6 months to get into core, if accepted.
* GitHub discussions are used to create one or more GitHub issues when and if something moves from _Future_ to _Near Term_.
* Uses `near-term` label on GitHub.


#### Future

* Work that is for 3+ releases away or work that needs more free form discussions and brainstorming to better scope future bodies of work.
* Estimated 7+ months to get into core, if accepted.
* GitHub Discussions are used for collaborating on _future_ work.
* If a GitHub issue is opened and is deemed that it is out of scope for _Current_ or _Near Term_, it will be converted into a GitHub Discussion.
* GitHub Discussions will be closed when the topic/feature moves from _Future_ to _Near Term_.

Over time, the process of moving work from _Future_ to _Near Term_ to _Current_ will continue to get further refined. 

Please read through the [Nautobot Roadmap](https://www.networktocode.com/nautobot/roadmap) so you can understand the current backlog and roadmap and which items are already in _Current, Near Term, and Future_.

### Release Schedule 
Here is what you need to know about Nautobot releases:

* The initial launch of Nautobot is version 1.0.0beta1 (major.minor.patch) released on February 24, 2021.
* The core team estimates quarterly releases with the majority of them being minor releases.
* It is an aspirational goal that there will be no more than one major release per year as major releases do indicate a break in backwards compatibility. 
* Patch releases will be released as needed without a defined schedule.
* Patch releases will be used for bugs, security vulnerabilities, backports, and other issues as they arise.
* Given the core team is estimating quarterly releases, there will not be firm dates for releases.  
* In order to provide more visibility into the development and release schedule of Nautobot, there will be structured notifications as follows:
  * At the start of a release cycle, the estimated timeframe for release will be a 4-6 week window.
  * Halfway through the release cycle (~6 weeks), the estimated timeframe for release will be narrowed to a 3-4 week window
  * After 8-9 weeks within the development cycle, the estimated timeframe for release will be narrowed further to a 2 week window.
  * The final notification will be provided 3-5 days before the release drops.
* The dates and notifications will occur by updating the GitHub Release Milestone and on Slack.

For 2021, the team estimates there will be three more releases with no more than one of them being a major release.

### Long Term Support (LTS)

It is the core team’s intention to have a Long Term Support (LTS) version of Nautobot.  The initial target release for the LTS version is the end of 2021, which will be the third or fourth release of Nautobot. Being that Nautobot is a new and open source community-based project, the goal is to collect as much feedback as possible within the first 3-6 months that will help finalize the correct LTS model.

### Deprecation Policy

The deprecation policy will be such that there will be at least one release that makes users aware of a feature that will be deprecated in the next release.

### Versioning 

Semantic Versioning ([SemVer](https://semver.org/)) is used for Nautobot versioning.

### Contributor Workflow

The following documents the lifecycle of work within Nautobot.

1. Open/request a feature enhancement or file a bug
  a. If bug, see [here](#reporting-bugs)
  b. If feature request or enhancement, continue.
2. Review the [Nautobot Roadmap](https://www.networktocode.com/nautobot/roadmap)
  a. Find an item that matches your request? Comment on the corresponding GitHub Issue or GitHub Discussion.
  b. Don't see a match for your request? Continue.
3. Open a GitHub Issue
  a. The issue will be reviewed. Based on the request, it will get labeled as  `current`, `near-term`, `future`.  
  b. It will likely only stay in _current_ if it is trivial and quick work.
  c. If it gets labeled as _future_, the issue will be closed in the next batch of issues that get migrated and converted to GitHub discussions.
 
For any issue that receives a label of `current` or `near-term`, it will also receive a label of `status: accepted` or `status: blocked`.

If you follow these steps, there **will** be a GitHub Issue opened prior to submitting a Pull Request (PR).  However, we're quite aware that a PR may come in without ever being discussed in an Issue or Discussion.  While we do not advocate for this, you should be aware of the process that will be followed for those circumstances. 

Should this happen and if you followed the project guidelines, have ample tests, code quality, you will first be acknowledged for your work.  So, thank you in advance! After that, the PR will be quickly reviewed to ensure that it makes sense as a contribution to the project, and to gauge the work effort or issues with merging into _current_.  If the effort required by the core team isn’t trivial, it’ll likely still be a few weeks before it gets thoroughly reviewed and merged, thus it won't be uncommon to move it to _near term_ with a `near-term` label.  It will just depend on the current backlog.



### Communication

Communication among the contributors should always occur via public channels. The following outlines the best ways to communicate and engage on all things Nautobot.

#### Slack

* [**#nautobot** on Network to Code Slack](http://slack.networktocode.com/) - Good for quick chats. Avoid any discussion that might need to be referenced later on, as the chat history is not retained long.

#### GitHub

* [GitHub issues](https://github.com/nautobot/nautobot/issues) - All feature requests, bug reports, and other substantial changes should be documented in an issue.
* [GitHub discussions](https://github.com/nautobot/nautobot/discussions) - The preferred forum for general discussion and support issues. Ideal for shaping a feature request prior to submitting an issue.

GitHub's discussions are the best place to get help or propose rough ideas for
new functionality. Their integration with GitHub allows for easily cross-
referencing and converting posts to issues as needed. There are several
categories for discussions:

* **General** - General community discussion.
* **Ideas** - Ideas for new functionality that isn't yet ready for a formal
  feature request. These ideas are what will be in scope to review when moving work from _Future_ to _Near Term_ as stated in the previous section.
* **Q&A** - Request help with installing or using Nautobot.


### Contributing to Nautobot 

#### Reporting Bugs

* First, ensure that you're running the [latest stable version](https://github.com/nautobot/nautobot/releases)
of Nautobot. If you're running an older version, it's possible that the bug has
already been fixed.

* Next, check the GitHub [issues list](https://github.com/nautobot/nautobot/issues)
to see if the bug you've found has already been reported. If you think you may
be experiencing a reported issue that hasn't already been resolved, please
click "add a reaction" in the top right corner of the issue and add a thumbs
up (+1). You might also want to add a comment describing how it's affecting your installation. This will allow us to prioritize bugs based on how many users are affected.

* When submitting an issue, please be as descriptive as possible. Be sure to
provide all information request in the issue template, including:

    * The environment in which Nautobot is running
    * The exact steps that can be taken to reproduce the issue
    * Expected and observed behavior
    * Any error messages generated
    * Screenshots (if applicable)

* Please avoid prepending any sort of tag (e.g. "[Bug]") to the issue title.
The issue will be reviewed by a maintainer after submission and the appropriate
labels will be applied for categorization.

* Keep in mind that bugs are prioritized based on their severity and how much
work is required to resolve them. It may take some time for someone to address
your issue.

#### Feature Requests

* First, check the GitHub [issues
list](https://github.com/nautobot/nautobot/issues) and
[Discussions](https://github.com/nautobot/nautobot/discussions) to see if the
feature you're requesting is already listed. You can greater visibility on the
committed by looking at the [Nautobot
Roadmap](https://www.networktocode.com/nautobot/roadmap) (Be sure to search
closed issues as well, since some feature requests have not have been accepted.)
If the feature you'd like to see has already been requested and is open, click
"add a reaction" in the top right corner of the issue and add a thumbs up (+1).
This ensures that the issue has a better chance of receiving attention. Also
feel free to add a comment with any additional justification for the feature.
(However, note that comments with no substance other than a "+1" will be deleted. Please use GitHub's reactions feature to indicate your support.)

* Before filing a new feature request, consider starting with a GitHub
Discussion. Feedback you receive there will help validate and shape the proposed feature before filing a formal issue. If the feature request does not get accepted into the _current_ or _near term_ backlog, it will get converted to a Discussion anyway.

* Good feature requests are very narrowly defined. Be sure to thoroughly
describe the functionality and data model(s) being proposed. The more effort you put into writing a feature request, the better its chance is of being
implemented. Overly broad feature requests will be closed.

* When submitting a feature request on GitHub, be sure to include all
information requested by the issue template, including:

    * A detailed description of the proposed functionality
    * A use case for the feature; who would use it and what value it would add to Nautobot
    * A rough description of changes necessary to the database schema (if applicable)
    * Any third-party libraries or other resources which would be involved
    * Please avoid prepending any sort of tag (e.g. "[Feature]") to the issue title.

The issue will be reviewed by a moderator after submission and the appropriate
labels will be applied for categorization.

#### Submitting Pull Requests

* If you're interested in contributing to Nautobot, be sure to check out our
[getting started](https://Nautobot.readthedocs.io/en/stable/development/getting-started/)
documentation for tips on setting up your development environment.

* It is recommended to open an issue **before** starting work on a pull request, and discuss your idea with the Nautobot maintainers before beginning work. This will help prevent wasting time on something that might we might not be able to implement. When suggesting a new feature, also make sure it won't conflict with any work that's already in progress.

* Once you've opened or identified an issue you'd like to work on, ask that it
be assigned to you so that others are aware it's being worked on. A maintainer
will then mark the issue as "accepted."

* All new functionality must include relevant tests where applicable.

* When submitting a pull request, please be sure to work off of the `develop`
branch, rather than `main`. The `develop` branch is used for ongoing
development, while `main` is used for tagging stable releases.

* In most cases, it is not necessary to add a changelog entry: A maintainer will take care of this when the PR is merged. (This helps avoid merge conflicts
resulting from multiple PRs being submitted simultaneously.)

* All code submissions should meet the following criteria (CI will enforce
these checks):

    * Python syntax is valid
    * All unit tests pass successfully
    * PEP 8 compliance is enforced, with the exception that lines may be
      greater than 80 characters in length

## Project Structure

All development of the current Nautobot release occurs in the `develop` branch; releases are packaged from the `main` branch. The `main` branch should _always_ represent the current stable release in its entirety, such that installing Nautobot by either downloading a packaged release or cloning the `main` branch provides the same code base.

Nautobot components are arranged into functional subsections called _apps_ (a carryover from Django vernacular). Each app holds the models, views, and templates relevant to a particular function:

* `circuits`: Communications circuits and providers (not to be confused with power circuits)
* `dcim`: Datacenter infrastructure management (sites, racks, and devices)
* `extras`: Additional features not considered part of the core data model
* `ipam`: IP address management (VRFs, prefixes, IP addresses, and VLANs)
* `tenancy`: Tenants (such as customers) to which Nautobot objects may be assigned
* `users`: Authentication and user preferences
* `utilities`: Resources which are not user-facing (extendable classes, etc.)
* `virtualization`: Virtual machines and clusters
