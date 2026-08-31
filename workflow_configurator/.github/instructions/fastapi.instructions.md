---
name: FastAPI Boundaries
description: FastAPI routing, validation, dependency injection, security, concurrency, and endpoint testing rules.
applyTo: ['app/**', 'api/**', 'backend/**']
---

# FastAPI Boundaries

- Keep transport parsing and response shaping in routers; put reusable business
  behavior behind service interfaces.
- Define request and response models explicitly and avoid exposing persistence
  models as public API contracts.
- Inject request-scoped sessions, authentication, settings, and clients. Do not
  keep mutable request state in module globals.
- Use async handlers only when the full called path is non-blocking. Send CPU
  work to a process or worker system; use thread offloading only for unavoidable
  blocking I/O with understood cancellation behavior.
- Map domain failures to consistent HTTP errors in one boundary layer. Do not
  return success status codes with error payloads.
- Enforce authorization at every protected route, parameterize database queries,
  and bound pagination and uploaded/request body sizes.
- API contract changes require consumer updates or an explicit compatibility and
  rollout plan.
- Test each endpoint's success path, validation failure, and relevant auth or
  authorization failure.
