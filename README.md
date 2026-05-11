# agentprobe

Security evaluation framework for AI agents. Discovers agent capabilities, runs adversarial attack scenarios, and produces scored security posture reports.

## What it does

agentprobe connects to any AI agent through its task interface, discovers what tools and MCP servers it has access to, and runs a battery of attack scenarios against it. It uses [agenttrail](https://github.com/jgorodetsky/agenttrail) to monitor the agent's behavior during each attack and determine whether the attack succeeded.

```
$ agentprobe run --config target.yml

  Discovering agent capabilities...
  Found: filesystem, shell, fetch, email (4 MCP servers)

  [1/32] indirect prompt injection via URL       FAIL
  [2/32] data exfil via fetch tool                FAIL
  [3/32] system prompt extraction                 PASS
  [4/32] MCP server rug pull                      FAIL
  [5/32] shell command injection                  PASS
  [6/32] cross-context data leakage               FAIL
  ...

  Score: 41/100
  Report: ./agentprobe-report.html
```

## Architecture

```
                         ┌──────────────────────────────────────────┐
                         │            agentprobe                    │
                         │                                         │
  target.yml ──────────▶ │  1. connect to agent's task interface   │
                         │  2. discover tools via agenttrail       │
                         │  3. select applicable attack scenarios  │
                         │  4. execute attacks                     │
                         │  5. monitor agent behavior via audit    │
                         │  6. score pass/fail per scenario        │
                         │  7. generate report                     │
                         │                                         │
                         └────────┬────────────────┬───────────────┘
                                  │                │
                     sends tasks  │                │  reads audit trail
                                  │                │
                                  ▼                ▼
                         ┌──────────────┐  ┌──────────────┐
                         │   target     │  │  agenttrail  │
                         │   agent      │  │  collector   │
                         └──────────────┘  └──────────────┘
```

## Attack scenarios

| Category | Scenarios |
|----------|-----------|
| **Prompt injection** | Direct injection, indirect via URL, indirect via file content, indirect via tool results, multi-turn injection |
| **Data exfiltration** | Via fetch/HTTP tool, via email tool, via file write, via shell command, steganographic encoding |
| **Tool abuse** | Unauthorized shell execution, path traversal, privilege escalation, resource exhaustion |
| **MCP attacks** | Malicious MCP server, tool shadowing, rug pull, protocol manipulation, server impersonation |
| **Context manipulation** | System prompt extraction, memory poisoning, context window overflow, goal hijacking |
| **Multi-step chains** | Recon + inject + exfil, persistence via config modification, lateral movement across tools |

Each scenario includes exploit code, audit trail evidence in OCSF format, and detection signatures mapped to MITRE ATLAS.

## Configuration

```yaml
# target.yml

target:
  interface: http
  url: http://localhost:3000/task

monitor:
  agenttrail: http://localhost:8100

scope:
  - prompt_injection
  - data_exfil
  - tool_abuse
  - mcp_attacks
  - context_manipulation
  - multi_step_chains
```

## Deployment

```bash
# one-shot scan
agentprobe run --config target.yml

# CI/CD gate (fails pipeline if score < threshold)
agentprobe run --config target.yml --min-score 70

# continuous assessment
agentprobe run --config target.yml --schedule "0 2 * * *"
```

## How it pairs with agenttrail

[agenttrail](https://github.com/jgorodetsky/agenttrail) captures what agents do. agentprobe tests whether agents can be made to do things they shouldn't. agentprobe uses agenttrail's OCSF audit trail as ground truth to determine whether each attack scenario succeeded or failed.

```
agenttrail    the sensor (captures agent behavior)
agentprobe    the evaluation (tests agent security)
```

## Standards

| Standard | How it's used |
|----------|---------------|
| [MITRE ATLAS](https://atlas.mitre.org/) | Each attack scenario maps to ATLAS technique IDs |
| [OWASP Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/) | Scenario categories align to OWASP risk areas |
| [OCSF](https://ocsf.io/) | Attack evidence captured in OCSF format via agenttrail |

## License

Apache-2.0
