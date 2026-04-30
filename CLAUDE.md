# Claude Agent Guidance

Use the agent profiles in .github/agents to scope work by role. Choose the best matching agent for each task and focus changes within the listed key files.

Quality gates:
- ruff check .
- pytest -q
- ansible-lint ansible/playbooks/remediate_latency.yml
- ansible-playbook --syntax-check -i ansible/inventory/hosts.yml ansible/playbooks/remediate_latency.yml
