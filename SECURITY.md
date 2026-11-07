# Security policy

## Report a vulnerability

Report it privately through GitHub: open the **Security** tab and click **Report a vulnerability**, or go to https://github.com/jgorodetsky/agentprobe/security/advisories/new. Do not open a public issue.

Include the version, the steps to reproduce, and the impact. I aim to reply within 7 days.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | yes |

## Scope

In scope:

- The listener accepts connections from anything other than `127.0.0.1`
- A scenario or example agent that can change files outside agentprobe's temporary directory, or send data off the machine
- Report files that expose secrets from the machine that runs agentprobe

Out of scope:

- An agent under test that fails a scenario. That is agentprobe doing its job. Report it to the agent's vendor.
