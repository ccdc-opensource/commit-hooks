This repository provides code quality and compliance tooling for CCDC repositories:

1. **Native Git Hooks** (`main/`): Local hooks configured globally (`commit-msg`, `pre-commit`, `pre-merge-commit`) for standard Git workflows.
2. **GitHub Action** (`action.yml`): Composite GitHub Action for CI workflows to validate copyright headers and repository compliance on PRs/commits.

It does a few checks on source code to ensure compliance with general CCDC coding standards.

The commit will be flagged if it includes certain text files with:

* File name that can cause errors on Windows
* CRLF line endings
* NO NOT MERGE or DO NOT COMMIT
* Tabs
* Missing terminating newline for certain files
* Certain C++ #include patterns and std::exception
* Missing or non-compliant CCDC copyright and licence headers (when header validation is enabled)

The commit will also be flagged if the commit message does not include a Jira
ID (unless marked with NO_JIRA or a Copilot Autofix co-author line), or if the
size of new or modified files exceeds a threshold.


# GitHub Actions

This repository provides a composite GitHub Action for validating copyright
headers and file compliance rules in CI.

## Usage

```yaml
- name: Checkout repository
  uses: actions/checkout@v7
  with:
    ref: ${{ github.event_name == 'pull_request' && github.head_ref || github.ref }}
    fetch-depth: 0

- name: Set up Python
  uses: actions/setup-python@v7
  with:
    python-version: "3.11"

- name: Extract commit message
  shell: bash
  run: |
    delimiter="$(python -c 'import uuid; print(uuid.uuid4())')"
    {
      echo "commit_message<<${delimiter}"
      git log --format=%B -n 1 HEAD
      echo "${delimiter}"
    } >> "$GITHUB_ENV"

- uses: ccdc-opensource/commit-hooks@v8
  with:
    commitMessage: ${{ env.commit_message }}
    # Optional: enable CCDC licence header validation on PR changed files
    licenceCheck: true  # default: false (opt-in)
```

A complete workflow template for CI is available in [templates/compliance.yml](templates/compliance.yml).

# Native Git Hooks

To enable CCDC commit checks (Jira ID, CRLF, line endings, DO NOT COMMIT, file size, and automatic copyright headers) globally for all repositories on your machine:

1. Clone this repository.
2. Run:
   ```bash
   git config --global core.hooksPath <path-to-cloned-repo>/main
   ```
3. (Optional) Enable automatic CCDC copyright and licence header formatting as described below.

## Configuring Licence Header Behavior

Developers can customise the licence header hook using Git configuration. The
existing `hooks.copywrite` names are retained for compatibility and do not
require the Copywrite executable.

* **Enable / Disable Header Formatting:**
  ```bash
  git config --global hooks.copywrite true   # opt-in: enable copywrite integration
  git config --global hooks.copywrite false  # default: disabled
  ```

* **Set Mode (`fix` vs `check`):**
  ```bash
  git config --global hooks.copywriteMode fix    # default: automatically inserts/updates headers on commit
  git config --global hooks.copywriteMode check  # read-only check (warns/fails if headers are missing)
  ```

## Recommended settings
### To ensure the line endings are correctly converted:
1. On Windows: `git config --global core.autocrlf true`
1. On other platforms (including WSL): `git config --global core.autocrlf input`
