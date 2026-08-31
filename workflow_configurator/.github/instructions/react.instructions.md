---
name: React And TypeScript
description: React component, state, API boundary, accessibility, and behavior-test conventions.
applyTo: ['frontend/**/*.{ts,tsx,js,jsx}', 'web/**/*.{ts,tsx,js,jsx}', 'ui/**/*.{ts,tsx,js,jsx}']
---

# React And TypeScript

- Follow the repository's TypeScript strictness and established component,
  routing, styling, and data-fetching libraries.
- Use `unknown` plus narrowing at untrusted boundaries. Avoid adding `any` or
  unchecked type assertions to silence contract errors.
- Keep backend access in the established API client layer and regenerate or
  update API types when backend schemas change.
- Keep server state in the project's query/cache layer. Do not mirror remote data
  into component state without a specific synchronization requirement.
- Model loading, error, empty, success, and mutation states explicitly.
- Use semantic elements, associated labels, visible focus, and keyboard-operable
  controls. Preserve reduced-motion preferences.
- Keep fixed-format controls dimensionally stable so loading text, icons, and
  dynamic labels do not shift the surrounding layout.
- Test observable behavior through roles, labels, and user actions; use snapshots
  only when the serialized output itself is the contract.
