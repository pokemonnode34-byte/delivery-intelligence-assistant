# Copilot Implementation Instructions

You are implementing the Delivery Intelligence Assistant project.

You MUST follow the project phase specification exactly.

Primary specification file:

docs/phase_0_foundations.md

---

## Global Rules

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

---

## Security Rules

- Never print tokens
- Never log tokens
- Never store secrets in plain files
- Always mask secrets in logs

---

## Implementation Strategy

Follow the spec in strict sequence:

Step-by-step.

Never implement multiple steps at once.

After completing a step:

- Verify validation commands
- Ensure tests pass
- Confirm structure matches spec

Then stop.

Wait for next instruction.

---

## Future Compatibility

Design code so that future phases may support:

- GitLab Tasks
- Work Items
- Issues

Do not assume Issues are the only work entity.

---

## Coding Philosophy

Prefer:

- clarity over cleverness
- explicit over implicit
- maintainable over compact
- tested over assumed
