# Agent: Ansible

## Purpose
Own remediation workflows and device configuration changes with safe defaults.

## Skills
- Ansible playbooks and roles
- Idempotent configuration patterns
- Ansible linting and syntax validation
- Jinja2 template rendering

## Key Files
- ansible/inventory/hosts.yml
- ansible/playbooks/remediate_latency.yml
- ansible/roles/common/tasks/main.yml
- ansible/templates/qos.j2
- intent/intents.yml

## Typical Tasks
- Add new remediation actions and safe checks.
- Improve rollback handling and backups.
- Adapt templates for vendor-specific device CLIs.
