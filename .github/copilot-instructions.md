# Copilot Implementation Instructions

You are implementing the **Delivery Intelligence Assistant** project.

You MUST follow the project phase specification exactly.

Primary specification file:

docs/phase_0_foundations.md

---

# Global Implementation Rules

1. Implement ONLY the requested step.
2. Never skip steps.
3. Never reorder steps.
4. Never add extra frameworks or dependencies.
5. Never generate files outside the spec.
6. Always follow the defined directory structure.
7. Always run validation commands listed in the step.
8. Always write unit tests when required.
9. Never expose secrets in:
   - logs
   - repr
   - str
   - exception messages
   - test output
10. Always use UTC timestamps.
11. Always prefer simple, explicit implementations.
12. Do not optimize prematurely.
13. Do not refactor beyond the current step.
14. If uncertain, implement the safest minimal version.
15. Always validate behavior before continuing to the next step.

---

# Security Rules

Security is mandatory.

Never:

- Print tokens
- Log tokens
- Store secrets in plain files
- Expose secrets in stack traces
- Include secrets in test fixtures

Always:

- Mask sensitive values
- Validate environment variables
- Fail safely when secrets are missing

---

# Implementation Strategy

Follow the spec in strict sequence.

Step-by-step.

Never implement multiple steps at once.

After completing a step:

1. Run validation commands
2. Confirm tests pass
3. Verify structure matches spec
4. Confirm typing passes
5. Confirm linting passes

Then STOP.

Wait for next instruction.

---

# Compatibility Strategy

Design code to support future evolution.

Future phases may support:

- GitLab Tasks
- GitLab Work Items
- GitLab Issues

Do NOT assume Issues are the only planning entity.

All work entities must be abstractable.

---

# Logging Rules

Logging must be:

- Structured
- Predictable
- Safe

Never:

- Log secrets
- Log raw tokens
- Log full environment dumps

Always:

- Mask sensitive values
- Use consistent formatting
- Make logging initialization idempotent

---

# Testing Rules

Tests are mandatory.

Every module requiring logic must include:

- Unit tests
- Edge case tests
- Failure tests

Tests must be:

- Deterministic
- Repeatable
- Independent

No test may depend on:

- External services
- Network availability
- Live API calls

---

# Configuration Rules

Configuration must:

- Be validated
- Be explicit
- Use environment overrides
- Reject invalid values

Never:

- Assume defaults silently
- Ignore missing required configuration

---

# Coding Philosophy

Always prefer:

- clarity over cleverness
- explicit over implicit
- maintainable over compact
- tested over assumed
- readable over optimized

Code must be:

- understandable
- reviewable
- extensible
- safe
