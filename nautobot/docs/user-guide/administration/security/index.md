# Nautobot Security and Maintenance Policy

This document outlines how we approach security updates and maintenance for Nautobot, balancing the need to protect users against vulnerabilities with our commitment to system stability and predictable upgrade paths. We detail our proactive monitoring practices, explain how we handle security updates across different release types, clarify what we can and cannot control in our dependency chain and container images, and provide guidance on when you may need to take additional steps to meet your organization's specific security requirements. Our goal is transparency about our security processes so you can make informed decisions about deploying and maintaining Nautobot in your environment.

---

We recognize that security vulnerabilities are an inevitable part of maintaining software that depends on a complex ecosystem of libraries, frameworks, and system packages. Our approach to security updates aims to balance the urgent need to protect our users against known threats with the equally important goals of maintaining system stability, ensuring predictable upgrade paths, and avoiding unexpected breaking changes that could disrupt production environments.

## Monitoring and Response to Vulnerabilities

We actively monitor both our direct dependencies (the packages Nautobot explicitly requires) and indirect dependencies (the packages our dependencies bring along) for security vulnerabilities. When vulnerabilities receive a CVE designation and are classified as critical by industry-standard vulnerability databases like the National Vulnerability Database, we evaluate them promptly and typically release proactive updates to address them.

Many dependency vulnerabilities can actually be addressed in your existing Nautobot installation without waiting for a new Nautobot release. Because we generally allow patch-level updates to our dependencies (following semantic versioning principles), you can often remediate issues simply by running `pip install --upgrade` on the affected package. We design our dependency specifications to give you this flexibility while maintaining compatibility with the Nautobot version you're running.

### Our proactive monitoring tools

* **Mend Renovate:** Automatically updates library dependencies on a regular cadence, typically updating patch versions in patch releases and minor/major versions in minor/major releases
* **GitHub Dependabot:** Notifies us when security issues are identified in dependencies and when updated libraries containing security fixes are available
* **Snyk:** Continuously monitors the Nautobot codebase for potential security vulnerabilities
* **Ruff:** Linting tool that proactively detects potential security vulnerabilities in new or updated code through security-focused rule sets

## Long-Term Maintenance Release Policy

For Long-Term Maintenance (LTM) releases, we follow a measured approach to security updates that prioritizes stability alongside security. We actively monitor for critical vulnerabilities affecting LTM branches and will release patches on an as-needed basis when those vulnerabilities can be addressed without introducing breaking changes.

### What we will backport to LTM releases

* Data loss and CVE-related fixes from the active release cycle
* Dependency security updates that don't require breaking changes (for example, upgrading from Django 4.2.10 to 4.2.15)
* Other fixes evaluated case-by-case based on risk and impact
* Developer-centric features that ease transitions to the next major release, if they alleviate backwards incompatible changes

### What we will not backport

* Core features from newer releases
* Major version updates to framework dependencies like Django or Django REST Framework (for example, jumping from Django 4.2 to Django 5.2)
* Updates that would introduce behavioral changes or incompatibilities
* General enhancements or minor performance improvements, whether developer or UX centric

When a vulnerability requires a breaking change to remediate in an LTM branch, we may choose alternative mitigation strategies, such as backporting specific security fixes to our implementation or applying selective patches that address the vulnerability without requiring the full major version upgrade.

### Django end-of-support considerations

We recognize that LTM releases may outlive the official Django support lifecycle for their bundled Django version. For example, Nautobot 2.4 LTM uses Django 4.2, which reaches end-of-life in April 2026. While we cannot guarantee patches for all Django vulnerabilities discovered after Django's official support ends, we will continue to investigate critical vulnerabilities in Django on a case-by-case basis while the Nautobot LTM series remains active. Where feasible, we will attempt to backport security patches to maintain protection for our users. However, this extended security maintenance is provided on a best-effort basis and may not be possible for all vulnerabilities, particularly those requiring extensive changes to Django's internals or those that would introduce breaking changes to the framework's behavior.

We will aim to soften future breaking changes stemming from our major frameworks (Django, DRF, Celery) by attempting to “bridge the gap“: expanding where possible, configuration or code that would support both the old and new style to work in the LTM version such that changes can safely be made before upgrading.

## Dependency Version Management

Our philosophy around dependency updates in patch **and minor** releases is designed to eliminate surprises:

### Dependency on Django, Django REST Framework (DRF), and Celery

* Breaking changes carry the same weight as Nautobot Core breaking changes—most App developers depend on these libraries directly, making downstream mitigation difficult
* Major version updates reserved for Nautobot minor releases at minimum, never patch releases
* We use Django LTS releases exclusively, aligning maintenance windows with Django's long-term support schedule
* We aim to bridge breaking changes into earlier releases or delay adoption to give developers transition time where feasible
* CVE fixes may be backported to supported branches, but major Django upgrades will not occur in patch releases

### Other Direct Dependencies

* Major version bumps to other direct dependencies can occur in patch releases as needed, such as adopting new functionality or vulnerability remediation
* We perform a documentation and changelog evaluation ("paper evaluation") on major direct dependency updates, as well as routine automated test coverage, to assess reasonableness, but likely won't block updates on that analysis
* As deemed necessary from paper analysis we will  expand the support matrix (allowing both old and new versions) rather than forcing immediate upgrades
* Breaking changes identified through analysis will be communicated in release notes
* While Django/DRF/Celery are expected to be used in a myriad of ways—and therefore, as noted above are handled with special care and only updated beyond patch at least minor releases—we do not evaluate all possible uses of other direct dependencies within custom code or Apps. Known or expected breaking changes will be communicated, but adoption will not be delayed to accommodate third-party implementations
* In general we do not expect to remove any direct dependency in any patch release of Nautobot

### Indirect Dependencies

* Fall outside our impact analysis scope
* We may temporarily specify version ranges for indirect dependencies to ensure we pull secure versions
* We avoid pinning every indirect dependency to prevent rigid dependency trees (standard Python packaging practice)
* Administrators and App developers concerned with specific indirect dependencies (vulnerabilities or compatibility) should manage those constraints independently

### Custom App-Introduced Dependencies

* We do not manage or analyze dependencies introduced by Custom Apps
* Conflicts between App dependencies and Nautobot's dependency tree are the Custom App developer's responsibility

## Container Image Security Practices

Our official Docker images are built on the `python-slim` base image maintained by the Docker community, which uses Debian Linux as its foundation. This base image philosophy emphasizes minimalism, including only the essential packages needed to run Python applications.

### Our Build Process

* Every image build runs `apt update` and `apt upgrade` as the very first step
* This ensures security patches released since the upstream Python image was built are incorporated into our images
* Our images often include security fixes more recent than the base images they're built from

### Important Limitations

* We do not maintain custom security patches for packages we do not maintain  when upstream maintainers haven't patched them
* Debian maintains its own security team with its own classification system for vulnerability severity and patching timelines
* We rely on upstream security maintenance rather than backporting patches ourselves, which could introduce instability
* We do not rebuild container images of older versions of Nautobot with newer dependencies

We understand that some organizations have specific requirements around container security, such as needing rootless containers, distro-less images, or other specialized configurations. While we provide a stable, well-maintained baseline that works for most deployments, we recognize it may not fit every security posture. If your environment requires these specialized configurations, you can use our Dockerfile as a reference implementation showing exactly how to install Nautobot, configure its dependencies, and start its services in your custom implementation.
Development and pre-release containers (`nautobot-dev`, etc.) are not formal releases. They follow similar build processes as production containers, but performance regressions and configuration changes are expected and not prioritized for remediation.

## Reporting Security Vulnerabilities

We take security reports seriously and respond to each within five (5) working days. For low-risk issues or CVE-related dependency vulnerabilities, you can open a bug [issue on GitHub](https://github.com/nautobot/nautobot/issues/new/choose). For sensitive security concerns or issues where you're unsure of the severity, email <security@nautobot.com> with the details.

For complete information about our vulnerability reporting process, disclosure timelines, the security response team, and when to report through different channels, please see our full [Security Policy](https://github.com/nautobot/nautobot/blob/main/SECURITY.md) in the Nautobot documentation.

## Support and Assistance

If you need help configuring Nautobot security settings, applying security updates, or have general support questions, please reach out through our standard support channels rather than the security reporting process. For Network to Code customers, enterprise support is available through your existing support agreement. Community users can seek assistance in the `#nautobot` channel in our Slack workspace or through GitHub discussions.

---

This balanced approach lets us respond quickly to critical security issues while maintaining the stability and predictability that production environments require. We're committed to transparency about what we can control, what we monitor, and where you may need to take additional steps to meet your organization's specific security requirements.

---

## More Information on Security Tools Used

The Nautobot development team currently makes use of the following tools, among others, to help ensure Nautobot's security:

### Mend Renovate

We use [Renovate](https://docs.renovatebot.com/) to automatically keep Nautobot's library dependencies appropriately updated on a regular cadence. In general we use Renovate to update library patch versions in Nautobot patch releases, and update libraries to their latest minor or major releases (where appropriate and possible) in Nautobot minor/major releases, but of course there may be exceptions depending on the versioning methodology of each library.

A representative example pull request opened by Renovate is [#6689](https://github.com/nautobot/nautobot/pull/6689).

### GitHub Dependabot

We use [Dependabot](https://docs.github.com/en/code-security/dependabot) to automatically notify us when security issues are identified in Nautobot's library dependencies as well as when an updated library is available containing a security fix.

A representative example pull request opened by Dependabot is [#6073](https://github.com/nautobot/nautobot/pull/6073).

### Snyk

We use [Snyk](https://snyk.io/) to monitor the Nautobot code base on an ongoing basis for potential security vulnerabilities.

An example of a security improvement resulting from Snyk code analysis is [#5054](https://github.com/nautobot/nautobot/pull/5054).

### Ruff

We use [Ruff](https://docs.astral.sh/ruff/) as a linting tool, in part to proactively detect potential security vulnerabilities in updated or newly introduced code through its security-related rule sets, such as ["S"](https://docs.astral.sh/ruff/rules/#flake8-bandit-s).
