Enhanced the `prepare_release` GitHub workflow to allow explicitly providing a previous tag to compare against.
Fixed the `prepare_release` GitHub workflow not bumping the version when creating a prerelease. It still skips bumping the version **if** the version is a non-"0" prerelease number **and** a corresponding GitHub release tag doesn't already exist.
