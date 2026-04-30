## Summary
Describe the change and why it is needed.

## Testing
- [ ] `pytest -q`
- [ ] `ruff check .`
- [ ] `ansible-lint ansible/playbooks/remediate_latency.yml`
- [ ] `ansible-playbook --syntax-check -i ansible/inventory/hosts.yml ansible/playbooks/remediate_latency.yml`

## Risk
What could go wrong? What is the rollback plan?

## Checklist
- [ ] Documentation updated
- [ ] New code has tests
- [ ] No secrets committed
