# Nautobot Security

Nautobot's development team is strongly committed to responsible reporting and disclosure of security-related issues, as outlined below and in the [SECURITY.md](https://github.com/nautobot/nautobot/blob/main/SECURITY.md) published to GitHub.

## Security Tools Used

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

## Security Vulnerability Reporting

We appreciate the time security researchers and users contribute to reporting vulnerabilities to the Nautobot Community.

If you feel your report is safe for public disclosure (a CVE related to a dependency, or a low-risk bug) please feel free to open a bug [issue on GitHub](https://github.com/nautobot/nautobot/issues/new/choose).

If you are unsure of the severity of your report or you feel it should not be publicly disclosed until a fix has been released, you can also email [`security@nautobot.com`](mailto:security@nautobot.com) with the security details.

You may encrypt your email with the GPG keys of the security response members below. While accepted, encryption using GPG is NOT mandatory to make a disclosure.

!!! tip "When Should I Report a Vulnerability?"
    - You think you discovered a potential security vulnerability in Nautobot
    - You are unsure how a vulnerability affects Nautobot
    - You think you discovered a vulnerability in another project that Nautobot depends on

!!! warning "When Should I NOT Report a Vulnerability?"
    - You need help configuring Nautobot security settings (such as external authentication)
    - You need help applying security related updates
    - Your issue is not security related

### Security Response Team

Below are the current team members responsible for receiving and triaging Nautobot security issues.

- Glenn Matthews (**[@glennmatthews](https://github.com/glennmatthews)**) `<glenn.matthews@networktocode.com>` [[4096R/C3DF1C5D9727F82ACF8F743238BF0D0E68B9F76C]](https://keybase.io/glennmatthews/pgp_keys.asc)
- Bryan Culver (**[@bryanculver](https://github.com/bryanculver)**) `<bryan.culver@networktocode.com>` [[4096R/810BA9FC788A8B2C9EB9559C834D7494DEDB1DD8]](https://keybase.io/bryanculver/pgp_keys.asc)
- John Anderson (**[@lampwins](https://github.com/lampwins)**) `<john.anderson@networktocode.com>`
- Jonathan Swisher (**[@LoneStar-Swish](https://github.com/LoneStar-Swish)**) `<jonathan.swisher@networktocode.com>` [[4096R/E0B0E95E80BF2E652BABA4C67BC452A3795882D6]](https://keybase.io/jswisher/pgp_keys.asc)

### Security Vulnerability Response

Each report is acknowledged and analyzed by security response members within five (5) working days.

Any vulnerability information shared with security response members stays within the Nautobot project and will not be disseminated to other projects unless it is necessary to get the issue fixed.

As the security issue moves from triage, to identified fix, to release planning we will keep the reporter updated.

### Public Disclosure Timing

A public disclosure date can be negotiated by the Nautobot maintainers and the bug submitter. We prefer to fully disclose the bug as soon as possible once a user mitigation is available. It is reasonable to delay disclosure when the bug or the fix is not yet fully understood, the solution is not well-tested, or for vendor coordination. The timeframe for disclosure is from immediate (especially if it's already publicly known) to a few weeks. For a vulnerability with a straightforward mitigation, we expect report date to disclosure date to be on the order of ten (10) days. The Nautobot maintainers hold the final say when setting a disclosure date.

Accepted disclosures [will be published on GitHub](https://github.com/nautobot/nautobot/security/advisories?state=published) and will also be added to the [Nautobot documentation](notices.md).
