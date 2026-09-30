<p align="center">
    <a href="https://github.com/lupaxa-gh-toolbox">
        <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/gh-toolbox/readme-logo.png" alt="Organisation Logo" />
    </a>
</p>

<h1 align="center">GitHub Token Validator</h1>

**GitHub Token Validator** takes a GitHub token and reports what that token is allowed to do. It sends read-only `GET` requests. It does not list repositories, organisations, or other resources, and it never prints the token.

## Installation

Requires Python 3.11 or newer.

```bash
pip install lupaxa-github-token-validator
```

Two commands are installed. They do the same work.

```bash
gtv --version
github-token-validator --version
```

The shorter `gtv` command is used in the examples below.

## Token

`gtv` reads `GITHUB_TOKEN`. `--token` overrides that variable. A blank `--token` does not fall back to the environment. Surrounding whitespace is removed before the token is classified or sent.

```bash
export GITHUB_TOKEN="your-token"
gtv
```

```bash
gtv --token "$OTHER_TOKEN"
```

## Which flags a token needs

Classic, OAuth, and user-to-server tokens return their scopes in the `X-OAuth-Scopes` header, so `--org` and `--repo` are optional.

Fine-grained, installation, and unknown tokens do not, so they need at least one of those flags before any request is sent.

A refresh token makes no request.

| Prefix         | Kind                                      | Needs a target |
| -------------- | ----------------------------------------- | -------------- |
| `ghp_`         | Classic personal access token             | No             |
| `github_pat_`  | Fine-grained personal access token        | Yes            |
| `gho_`         | OAuth access token                        | No             |
| `ghu_`         | GitHub App user-to-server token           | No             |
| `ghs_`         | GitHub App installation or Actions token  | Yes            |
| `ghr_`         | Refresh token                             | No             |
| anything else  | Unknown                                   | Yes            |

Passing `--org` checks only that organisation. Passing `--repo` checks only that repository. Passing both checks both. The tool never looks up further targets.

`--org` is one name. Surrounding spaces are removed. A blank name, a space inside the name, or a `/` is rejected.

`--repo` is exactly `OWNER/NAME`: one slash, both sides non-empty, and no whitespace.

## Examples

A classic, OAuth, or user-to-server token. The scope table is the permission report. Account checks still run.

```bash
gtv
gtv --timeout 30
```

The same token, plus one named target. Only the catalog you name is probed.

```bash
gtv --org lupaxa-gh-toolbox
gtv --repo lupaxa-gh-toolbox/github-token-validator
gtv --org lupaxa-gh-toolbox --repo lupaxa-gh-toolbox/github-token-validator
```

A fine-grained token, an installation or Actions token, or an unknown token. At least one target is required.

```bash
gtv --repo lupaxa-gh-toolbox/github-token-validator
gtv --org lupaxa-gh-toolbox
```

Omitting both flags exits 2 and prints a message such as `Fine-grained personal access token requires --org or --repo.` The token is not included in that message.

A refresh token (`ghr_`) prints a short summary and exits 2. It does not call the API.

## Flags

| Flag                | Meaning                                                                                              |
| ------------------- | ---------------------------------------------------------------------------------------------------- |
| `-h`, `--help`      | Help, then exit 0                                                                                    |
| `-V`, `--version`   | Version, then exit 0                                                                                 |
| `-t`, `--token`     | Token. Overrides `GITHUB_TOKEN`. A blank value does not fall back to the environment                 |
| `-T`, `--timeout`   | Seconds per request. Default 10. Must be an integer greater than 0                                   |
| `--org NAME`        | One organisation. Required for fine-grained, installation, and unknown tokens unless `--repo` is set |
| `--repo OWNER/NAME` | One repository, as `OWNER/NAME`. Required for those same tokens unless `--org` is set                |

## Report

A completed run prints Rich tables.

**Summary.** Token kind, login from `GET /user`, the raw scope header, and the rate-limit limit, used count, remaining count, and reset time in UTC (`YYYY-MM-DD HH:MM:SS`).

**Scopes.** Classic, OAuth, and user-to-server tokens list each `X-OAuth-Scopes` value, in header order, with a short description. An unknown scope is `No local description.`

A missing or blank header is `none`, with the text `GitHub sent no scopes.`

Fine-grained tokens do not return OAuth scopes. That row says `Fine-grained tokens do not return OAuth scopes.`

Installation and Actions tokens list `X-Accepted-GitHub-Permissions` as a permission and its access, such as `read` or `write`. A missing header is `none`, with the text `GitHub sent no accepted permissions.`

**Account permissions.** Run for every API token except installation and Actions tokens, which are not user tokens:

- Profile, Emails, Following, Organisations, Org membership roles
- Gists, Notifications
- Public keys, GPG keys, SSH signing keys
- Packages, Repository list, Codespaces, Installations

**Target permissions.** Printed only when `--org` or `--repo` was passed.

Organisation checks: Organisation, Members, Hooks, Audit log, Actions permissions, Packages.

Repository checks: Repository, Contents, Hooks, Workflows, Deployments, Invitations, Code scanning, Commits.

List requests use `per_page=1`. Response bodies are discarded except the login on `GET /user`, so names, paths, messages, and other resource details are not printed.

| Result            | Meaning                          |
| ----------------- | -------------------------------- |
| `granted`         | HTTP 200 or 204                  |
| `denied`          | HTTP 403                         |
| `not applicable`  | HTTP 404                         |
| `error N`         | Any other HTTP status            |

If GitHub rejects the token (HTTP 401), a rate limit stops the run, or a request times out or cannot connect, the run stops and exits 1.

A rate limit is HTTP 429, or HTTP 403 when `X-RateLimit-Remaining` is `0` or `Retry-After` is set. A 403 that is only a permission denial stays a `denied` row.

On the first request, only that error is printed. On a later request, the tables gathered so far are printed, then the error.

## Exit codes

| Code | Meaning                                                                                                              |
| ---- | -------------------------------------------------------------------------------------------------------------------- |
| 0    | The report completed, including rows that are denied, not applicable, or an HTTP error                               |
| 1    | The token was rejected, the rate limit stopped the run, or a request timed out or could not connect                  |
| 2    | Missing token, refresh token, missing target, invalid `--org`, `--repo`, or `--timeout`, or an unrecognized argument |
| 130  | Keyboard interrupt                                                                                                   |

An unrecognized argument is rejected without printing the argument values.

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
