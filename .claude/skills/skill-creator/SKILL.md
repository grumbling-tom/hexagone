---
name: skill-creator
description: Guides creation of new agent skills for this repository. Use when a user wants to create, design, or scaffold a new skill. Enforces quality via structured questioning before files are written.
---


# Skill Creator


You are a skill architect. Your job is to ensure every skill added to this repository is well-scoped, robust, and genuinely useful. You do this by asking the right questions first, then generating the skill only after the answers are clear.


Most great skills start small — a few lines of instruction and a single gotcha — and grow as the agent hits new edge cases. Match your process intensity to the skill's complexity.


## Skill Categories


Use these categories to help classify and guide skill design. The best skills fit cleanly into one category:


1. **Library & API Reference** — How to correctly use a library, CLI, or SDK. Often includes reference snippets and gotchas.
2. **Product Verification** — How to test or verify code is working. Often paired with tools like Playwright, tmux, etc.
3. **Data Fetching & Analysis** — Connects to data and monitoring stacks. May include helper libraries, dashboard IDs, credentials config.
4. **Business Process & Team Automation** — Automates repetitive workflows into one command (standups, ticket creation, recaps).
5. **Code Scaffolding & Templates** — Generates boilerplate for specific functions in the codebase.
6. **Code Quality & Review** — Enforces code quality, review practices, or testing standards.
7. **CI/CD & Deployment** — Helps fetch, push, deploy, or babysit PRs through CI.
8. **Runbooks** — Takes a symptom (alert, error, Slack thread) and walks through investigation to produce a report.
9. **Infrastructure Operations** — Routine maintenance and operational procedures, often with destructive-action guardrails.


## Process


### Quick Mode vs Full Mode


**Quick mode** — Use when the skill idea is simple, well-scoped, and low-risk (e.g., a library reference skill or a simple scaffolding template). Run Phase 1 questions 1-2 only, then skip to Phase 4 and Phase 5. Most skills should start here and evolve.


**Full mode** — Use when the skill involves destructive operations, complex branching logic, or high blast radius. Run all phases.


Ask the user which mode fits, or recommend one based on their description.


### Phase 1: Intent & Classification


Before accepting the skill idea at face value, challenge it:


1. **What problem does this skill solve?** Push for a concrete scenario: "A developer is doing ___ and currently has to ___, this skill would ___."


2. **What does the agent do differently with this skill vs without it?** If the agent can already do the task reasonably well from general knowledge, the skill may not be needed. Focus on procedural knowledge, domain context, or guardrails the agent lacks. Remember: don't state the obvious — focus on information that pushes Claude out of its normal way of thinking.


3. **Which category does this fit?** (See categories above.) If it doesn't fit any cleanly, that's a signal the scope may be unclear or it may be straddling multiple concerns.


For **full mode only**, also ask:


4. **Give me three concrete prompts a user would type that should trigger this skill.** If the user struggles, the scope is unclear.


5. **What should the skill explicitly NOT do?** Boundaries prevent scope creep.


6. **Does this skill compose with existing skills?** Check the `.claude/skills/` directory. The skill might reference other skills by name, or other skills might want to call this one.


### Phase 2: Design Challenge (Full Mode Only)


Stress-test the design:


7. **What happens when the skill is wrong?** If the blast radius is high (production deployments, data mutations), the skill needs stronger guardrails, confirmation steps, or dry-run modes.


8. **What inputs vary between uses?** If too many things vary, the skill may be trying to do too much. If nothing varies, it might be a script, not a skill. For inputs that vary per-user but are stable across invocations (e.g., Slack channel, team name), use the **config.json pattern** (see below).


9. **Can you draw the decision tree?** If there are more than 3-4 decision points, split the skill or use reference files for variant-specific details.


10. **What external dependencies does this skill assume?** Tools, CLIs, APIs, permissions, environment variables. Each dependency is a failure point. If the skill requires specific packages or runtimes, declare them in the `dependencies` frontmatter field.


11. **How will you know the skill is working well?** Push for observable, testable success criteria.


### Phase 3: Structure Decision


Based on the answers, determine the right structure:


- **Simple skill** (SKILL.md only): Instructions fit in under 200 lines with no branching.
- **Skill with references**: Multiple variants, frameworks, or domain-specific detail that should load on demand via `references/` files.
- **Skill with scripts**: Repetitive, deterministic operations that benefit from executable code in `scripts/`. Note: scripts cannot install packages at runtime — all dependencies must be pre-installed and declared in the `dependencies` field.
- **Skill with data storage**: The skill needs to remember state across invocations (see Data Storage below).
- **Skill with on-demand hooks**: The skill should activate hooks only when invoked (see On-Demand Hooks below).
- **Not a skill**: Redirect the user to write a script, document, or CLAUDE.md instruction instead.


Present your recommendation and justify it.


### Phase 4: Draft & Review


Generate the skill files, then critique your own output against these checks:


- **Description field**: This is not a summary — it's a trigger description. The model reads it to decide "should I invoke this skill?" Write it as: what the skill does + when to use it. Include key trigger phrases.
- **Flexibility calibration**: Match prescriptiveness to skill type. Runbooks and verification skills should be precise and step-by-step. Library references and code quality skills should give Claude information and flexibility to adapt. Avoid railroading Claude with overly rigid instructions for flexible skills.
- **Gotchas section**: Every skill should have a Gotchas section, even if it starts with just one entry. This is the highest-signal content — it captures failure modes the agent hits in practice and should grow over time.
- **Progressive disclosure**: Is the most critical decision-making context at the top? Are detailed procedures, references, and edge cases split into separate files where appropriate? Tell Claude what files exist in the skill directory so it reads them at the right time.
- **Example check**: At least one concrete example showing input and expected output.
- **Negative space check**: Could following these instructions produce a harmful or destructive result? Add explicit warnings or confirmation gates.
- **Secrets check**: Never hardcode API keys, passwords, tokens, or credentials. Use environment variables or MCP connections.
- **Token budget check**: Is the SKILL.md body under 500 lines? If not, split content into reference files.
- **Overlap check**: Does this skill overlap with or compose well with existing skills in `.claude/skills/`?


Present the critique alongside the draft.


### Phase 5: File Creation


Only after review is acknowledged, create the skill:


1. Create the directory: `.claude/skills/<skill-name>/`
2. Write `SKILL.md` with validated frontmatter and instructions
3. Create any `references/`, `scripts/`, or `assets/` subdirectories as determined in Phase 3
4. If the skill needs per-user setup, create a `config.json.example` with documented fields
5. Confirm the skill is visible by listing the `.claude/skills/` directory


## Skill File Format


Every `SKILL.md` must follow this structure:


```markdown
---
name: <lowercase-hyphenated-name>    # Required. Max 64 characters.
description: <trigger description>   # Required. Max 200 characters. What it does AND when to trigger it.
dependencies: <package specs>        # Optional. Runtime packages needed (e.g., "python>=3.8, pandas>=1.5.0").
---


# <Skill Name>


<High-level context: what this skill does and the key decisions the agent must make>


<Detailed procedures, steps, and commands>


## Gotchas


<Known failure modes, edge cases, and things Claude gets wrong. Start with at least one. Add more over time as the agent hits new issues.>


## Example


<At least one concrete input/output example>
```


## Patterns & Techniques


### Config.json Pattern


For skills that need per-user setup (e.g., which Slack channel, which environment), store configuration in a `config.json` file in the skill directory. If the config file doesn't exist when the skill is invoked, instruct the agent to ask the user for the required values and create it.


Include a `config.json.example` in the skill directory documenting all fields.


### Data Storage


Some skills benefit from storing data across invocations — logs, history, cached results. Examples:
- A standup skill that keeps a `standups.log` so it can diff against yesterday
- A runbook skill that logs investigation results for post-incident review


Store persistent data in `${CLAUDE_PLUGIN_DATA}` (a stable folder per plugin) rather than in the skill directory itself, which may be overwritten on upgrade.


### Progressive Disclosure via File System


A skill is a folder, not just a markdown file. Use the file system for context engineering:
- `references/` — API docs, function signatures, detailed specs Claude reads on demand
- `scripts/` — Executable code Claude can run or compose with
- `assets/` — Templates, example outputs, config schemas
- `examples/` — Sample inputs/outputs for complex workflows


Tell Claude what files exist and when to read them. It will load them at appropriate times rather than front-loading everything.


### On-Demand Hooks


Skills can register hooks that activate only when the skill is invoked and last for the session duration. Use this for opinionated guardrails you don't want running all the time.


Examples:
- `/careful` — blocks `rm -rf`, `DROP TABLE`, force-push via PreToolUse matcher on Bash
- `/freeze` — blocks Edit/Write outside a specific directory during debugging


### Composing Skills


Skills can reference other skills by name. The agent will invoke them if they are installed. When designing a skill, consider:
- What existing skills could this one call?
- What future skills might want to call this one?
- Keep skills single-purpose to maximize composability.


## Quality Standards


- **Imperative voice**: Write instructions as commands, not suggestions.
- **No filler**: Every sentence must carry information the agent cannot infer. Remove anything a competent developer would already know.
- **Concrete over abstract**: Use exact commands, file paths, and examples instead of general guidance.
- **Flexibility where appropriate**: For reference and quality skills, give Claude information and room to adapt. For runbooks and verification, be precise. Avoid railroading.
- **Fail-safe defaults**: When the skill involves destructive operations, default to dry-run or preview mode.
- **No secrets**: Never hardcode credentials. Use environment variables or MCP connections.
- **No README, CHANGELOG, or auxiliary docs**: The skill directory contains only what the agent needs at runtime.
- **Start small, iterate**: A minimal skill with one gotcha is better than a comprehensive skill that never ships. Skills should grow organically as the agent hits new edge cases.
