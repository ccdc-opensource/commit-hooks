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
* Missing or non-compliant CCDC copyright and license headers (when using the GitHub Action or local copywrite integration)

The commit will also be flagged if the commit message does not include a Jira
ID (unless marked with NO_JIRA or a Copilot Autofix co-author line), or if the
size of new or modified files exceeds a threshold.


# GitHub Actions

This repository provides a composite GitHub Action for validating copyright
headers and file compliance rules in CI.

## Usage

```yaml
- name: Extract commit message
  shell: bash
  run: |
    echo 'commit_message<<EOF' >> "$GITHUB_ENV"
    git log --format=%B -n 1 HEAD >> "$GITHUB_ENV"
    echo 'EOF' >> "$GITHUB_ENV"

- uses: ccdc-opensource/commit-hooks@main
  with:
    commitMessage: ${{ env.commit_message }}
    # Optional: enable CCDC license header validation on PR changed files
    licenseCheck: true  # default: false (opt-in)
```

A complete workflow template for CI is available in [templates/compliance.yml](templates/compliance.yml).

# Native Git Hooks

To enable CCDC commit checks (Jira ID, CRLF, line endings, DO NOT COMMIT, file size, and automatic copyright headers) globally for all repositories on your machine:

1. Clone this repository.
2. Run:
   ```bash
   git config --global core.hooksPath <path-to-cloned-repo>/main
   ```
3. (Optional) Install `copywrite` to automatically add and format CCDC copyright headers on commit:
   * **Windows:** `choco install copywrite`
   * **macOS:** `brew install hashicorp/tap/copywrite`
   * **Linux:** `go install github.com/hashicorp/copywrite@latest`

> **Note:** If `copywrite` is not installed on your machine, native hooks will continue to run all other standard checks and display a gentle warning without failing your commit.

## Configuring Copywrite Behavior

Developers can customise the copywrite hook using Git configuration:

* **Enable / Disable Copywrite:**
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
