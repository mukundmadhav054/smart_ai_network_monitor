# Contributing

Thanks for helping improve Smart AI Network Monitor.

## Quick Start

1. Fork and clone the repo.
2. Create a new branch for your change.
3. Follow the setup steps in README.

## Development Setup

~~~bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt
~~~

## Code Style

- Python: format and lint with ruff.
- Ansible: run ansible-lint and syntax check for playbooks.
- Keep changes minimal and focused on a single concern.

## Tests

~~~bash
ruff check .
pytest -q
ansible-lint ansible/playbooks/remediate_latency.yml
ansible-playbook --syntax-check -i ansible/inventory/hosts.yml ansible/playbooks/remediate_latency.yml
~~~

## Commit Guidelines

- Use clear, descriptive commit messages.
- Keep commits small and logically grouped.

## Pull Requests

- Describe what changed and why.
- Include tests or notes on how the change was validated.
- Link any relevant issues.

## Reporting Issues

Use the bug report template in .github/ISSUE_TEMPLATE.

