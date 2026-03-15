# Frontend Development Standards

This document outlines the coding standards and best practices for the SpecterDefence frontend application.

## Overview

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Testing**: Vitest
- **State Management**: Zustand + React Query

---

## TypeScript Configuration

We enforce **strict TypeScript settings** to catch errors at compile time:

### Enabled Strict Rules

| Rule | Description |
|------|-------------|
| `strict: true` | Master switch for all strict type-checking options |
| `noImplicitAny: true` | Disallow implicit `any` types |
| `strictNullChecks: true` | Strict null and undefined checking |
| `strictFunctionTypes: true` | Strict function type checking |
| `strictBindCallApply: true` | Strict checking for bind/call/apply |
| `strictPropertyInitialization: true` | Ensure class properties are initialized |
| `noImplicitThis: true` | Disallow implicit `any` for `this` |
| `noUnusedLocals: true` | Error on unused local variables |
| `noUnusedParameters: true` | Error on unused function parameters |
| `noImplicitReturns: true` | Error when not all code paths return |
| `noUncheckedIndexedAccess: true` | Add `undefined` to indexed access types |
| `exactOptionalPropertyTypes: true` | Distinguish between `undefined` and missing properties |
| `noImplicitOverride: true` | Require `override` keyword when overriding |
| `noPropertyAccessFromIndexSignature: true` | Use bracket notation for index signatures |

**Goal**: Zero TypeScript errors, zero `any` types.

---

## ESLint Rules

We use ESLint with TypeScript, React, and accessibility plugins.

### Key Rules

| Category | Rule | Severity |
|----------|------|----------|
| **Type Safety** | `@typescript-eslint/no-explicit-any` | Error |
| **Type Safety** | `@typescript-eslint/no-unsafe-assignment` | Error |
| **Type Safety** | `@typescript-eslint/no-unsafe-member-access` | Error |
| **Type Safety** | `@typescript-eslint/no-unsafe-call` | Error |
| **Type Safety** | `@typescript-eslint/no-unsafe-return` | Error |
| **Type Safety** | `@typescript-eslint/strict-boolean-expressions` | Error |
| **React** | `react-hooks/rules-of-hooks` | Error |
| **React** | `react-hooks/exhaustive-deps` | Error |
| **Code Quality** | `no-console` (except error/warn) | Error |
| **Imports** | `import/order` | Error |
| **Imports** | `import/no-duplicates` | Error |
| **Accessibility** | `jsx-a11y/anchor-is-valid` | Error |
| **Accessibility** | `jsx-a11y/click-events-have-key-events` | Error |
| **Accessibility** | `jsx-a11y/no-static-element-interactions` | Error |

**Goal**: Zero ESLint warnings or errors.

---

## Code Style (Prettier)

```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "bracketSpacing": true,
  "arrowParens": "avoid",
  "endOfLine": "lf"
}
```

---

## Import Ordering

Imports must follow this order:

1. **React** imports
2. **External** library imports (e.g., axios, date-fns)
3. **Internal** absolute imports (e.g., `@/components`)
4. **Relative** imports (parent, sibling, index)

With a blank line between each group, alphabetized within groups.

```typescript
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

import { Button } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';

import { formatDate } from '../utils/date';
import { Sidebar } from './Sidebar';
```

---

## React Hooks Best Practices

### Rules of Hooks

- Only call hooks at the top level (not inside loops, conditions, or nested functions)
- Only call hooks from React function components or custom hooks

### Exhaustive Dependencies

The `exhaustive-deps` rule is **enforced**. Always include all dependencies in dependency arrays:

```typescript
// ✅ Good
useEffect(() => {
  fetchData(userId);
}, [userId]);

// ❌ Bad - missing dependency
useEffect(() => {
  fetchData(userId);
}, []);

// ✅ Good - use callback for stable references
const fetchData = useCallback(() => {
  api.getUser(userId);
}, [userId]);

useEffect(() => {
  fetchData();
}, [fetchData]);
```

---

## Console Usage

**Production code must not contain `console.log` statements.**

Allowed:
- `console.error()` - For actual errors
- `console.warn()` - For warnings

Use a proper logging utility for debugging in production.

---

## Accessibility (a11y)

All UI components must be accessible:

- Use semantic HTML elements
- Provide `alt` text for images
- Ensure keyboard navigation works
- Use ARIA labels where necessary
- Maintain sufficient color contrast

---

## Git Workflow

### Pre-commit Hooks

Husky + lint-staged runs on every commit:

1. ESLint auto-fix
2. Prettier formatting
3. TypeScript type-checking

### Before Committing

Always run the validation command:

```bash
npm run validate
```

This runs:
- Type checking (`tsc --noEmit`)
- Linting (`eslint`)
- Format checking (`prettier --check`)

---

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run build:ci` | Build with CI validation (strict) |
| `npm run type-check` | TypeScript type checking only |
| `npm run lint` | Run ESLint |
| `npm run lint:fix` | Run ESLint with auto-fix |
| `npm run format` | Format code with Prettier |
| `npm run format:check` | Check formatting without modifying |
| `npm run validate` | Run all checks (type, lint, format) |
| `npm test` | Run tests in watch mode |
| `npm run test -- --run` | Run tests once |

---

## CI/CD

The GitHub Actions workflow enforces:

1. **TypeScript compilation** - Must pass with zero errors
2. **ESLint** - Must pass with zero warnings
3. **Prettier** - Must pass with zero formatting issues
4. **Tests** - All tests must pass
5. **Build** - Production build must succeed

**Any failure blocks the PR from being merged.**

---

## File Organization

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # Primitive UI components (Button, Input, etc.)
│   └── features/       # Feature-specific components
├── hooks/              # Custom React hooks
├── lib/                # Utility libraries and configurations
├── services/           # API service functions
├── stores/             # Zustand stores
├── types/              # TypeScript type definitions
└── utils/              # Utility functions
```

---

## Enforcing Standards

The configuration is intentionally strict. If you encounter errors:

1. **Type errors**: Fix the underlying type issues, don't use `any`
2. **Lint errors**: Most can be auto-fixed with `npm run lint:fix`
3. **Format errors**: Run `npm run format` to auto-fix
4. **Missing dependencies**: Carefully review and add to dependency arrays

When in doubt, ask for help rather than disabling rules.
