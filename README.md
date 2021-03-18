This repository contains files that can be used as local git hooks and a github
action.

It does a few checks on source codes to ensure compliance with some general
CCDC coding standard.

# Github action

## Usage
```yaml
- uses: ccdc-opensource/commit-hooks@v1
  with:
    # Comma separated list of files
    # Default: ''
    files: ''

    # Whether the list of files are new files (1) or modified files (0)
    # Default: 0
    new_files: ''
```

## Scenarios
### Check all modified files
```yaml
      - id: files
        uses: jitterbit/get-changed-files@v1
        with:
          format: 'csv'
      - id: check_modified_files
        uses: ccdc-opensource/commit-hooks@v1
        with:
          files: ${{ steps.files.outputs.modified }}
          new_files: 0
```

# commit-hooks
You can use this as git hooks for local repositories.

A set of hooks include:
* commit-msg
* pre-commit
* pre-merge-commit

## Setting up
1. Clone this repo
1. `git config --global core.hooksPath <this repo location>/main`

## Recommended settings
### To ensure the line endings are correctly converted:
1. On Windows: `git config --global core.autocrlf true`
1. On other platforms (including WSL): `git config --global core.autocrlf input`
