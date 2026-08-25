This repository provides code quality and compliance tooling that serves three purposes:

1. **Native Git Hooks** (`main/`): Local hooks for standard Git workflow (`commit-msg`, `pre-commit`, `pre-merge-commit`).
2. **`pre-commit` Integration** (`.pre-commit-hooks.yaml`): Hooks for the [`pre-commit`](https://pre-commit.com/) framework (`copywrite-fix`, `copywrite-check`).
3. **GitHub Action** (`action.yml`): Composite GitHub Action for CI workflows to validate copyright headers and repository compliance on PRs/commits.

It does a few checks on source code to ensure compliance with general CCDC coding standards.

The commit will be flagged if it includes certain text files with:

* File name that can cause errors on Windows
* CRLF line endings
* NO NOT MERGE or DO NOT COMMIT
* Tabs
* Missing terminating newline for certain files
* Certain C++ #include patterns and std::exception
* Missing or non-compliant CCDC copyright and license headers when using the GitHub Action or `pre-commit` integration

The commit will also be flagged if the commit message does not include a Jira
ID (unless marked with NO_JIRA or a Copilot Autofix co-author line), or if the
size of new or modified files exceeds a threshold.


# GitHub Actions

This repository provides a composite GitHub Action for validating copyright
headers and file compliance rules in CI.

## Usage

```yaml
- uses: ccdc-opensource/commit-hooks@v7
  with:
    commitMessage: ${{ github.event.head_commit.message }}
```

## Scenarios
### Check files in pull request for merge to main
```yaml
name: Check pull request files
on:
  pull_request
    branches: [ main ]
jobs:
  Pull-request-files-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          ref: ${{ github.head_ref }}
          fetch-depth: 0
      - uses: actions/setup-python@v7
        with:
          python-version: "3.11"
      - name: Get the commit message
        run: |
          echo "commit_message=$(git log --format=%B -n 1 ${{ github.event.after }})" >> $GITHUB_ENV
        shell: bash
      - uses: ccdc-opensource/commit-hooks@v8
        with:
          commitMessage: ${{ env.commit_message }}
```

# commit-hooks
You can use this as git hooks for local repositories.

A set of hooks include:
* commit-msg
* pre-commit
* pre-merge-commit

## Setting up Core Git Hooks

1. Clone this repository.
2. Configure Git to use the hooks:

```bash
git config --global core.hooksPath <path-to-cloned-repo>/main
```

This enables the CCDC commit hooks for all repositories on your machine.

## Using with `pre-commit`

This repository also provides hooks compatible with the
[`pre-commit`](https://pre-commit.com/) framework for managing copyright
headers using [HashiCorp Copywrite](https://github.com/hashicorp/copywrite).

### Available Hooks

* **`copywrite-fix`** *(recommended for local development)*:
  Automatically inserts or updates the CCDC copyright and licence headers
  in newly added or modified files.

* **`copywrite-check`**:
  Validates copyright and licence headers across tracked files and fails if
  any files are non-compliant. This hook is well suited for CI/CD pipelines
  and verification workflows.

### Example Configuration

Add the following to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/ccdc-opensource/commit-hooks
    rev: <tag-or-sha>
    hooks:
      # Automatically inserts or updates headers
      - id: copywrite-fix

      # Optional: validates compliance after formatting
      # - id: copywrite-check
```

### Copywrite Prerequisite

The `copywrite-check` and `copywrite-fix` hooks require the `copywrite`
CLI to be available on your `PATH`.

**macOS / Linux (Homebrew)**

```bash
brew install hashicorp/tap/copywrite
```

**Go**

```bash
go install github.com/hashicorp/copywrite@latest
```

**Direct download**

Binary releases are available from:

[HashiCorp Copywrite Releases](https://github.com/hashicorp/copywrite/releases)

### Recommended Usage

For the best developer experience:

* Use **`copywrite-fix`** locally to automatically insert or update headers.
* Use **`copywrite-check`** in CI/CD pipelines to enforce compliance.

This ensures that copyright and licence headers are automatically maintained
while also preventing non-compliant changes from being merged.

## Recommended settings
### To ensure the line endings are correctly converted:
1. On Windows: `git config --global core.autocrlf true`
1. On other platforms (including WSL): `git config --global core.autocrlf input`
