# Modern React Architecture and State Management

## Overview
React utilizes a declarative, component-driven model where the user interface is a pure function of state. Developing scalable frontend architectures requires careful separation of concerns between local UI state, shared application state, and server cache state.

## Component Lifecycle and Core Hooks
1. **`useState`:** Manages isolated component-level state. State updates are scheduled and batched across event loops for optimal rendering performance.
2. **`useEffect`:** Handles synchronization with external systems (such as browser APIs, timers, and network subscriptions). Effect dependencies must be declared exhaustively to prevent stale closures and infinite render loops.
3. **`useCallback` and `useMemo`:** Provide referential stability across re-renders. `useCallback` caches function references passed as props to memoized child components (`React.memo`), while `useMemo` caches the result of expensive mathematical or collection operations.
4. **`useRef`:** Stores mutable values that persist across renders without triggering a re-render when mutated. Common use cases include DOM node references and interval IDs.

## Reconciliation and Key Prop Stability
React's reconciliation algorithm uses the Virtual DOM to compute minimal DOM mutations. When rendering lists of items, each item must possess a unique, stable `key` prop. Using array indexes as keys causes bugs in dynamic lists (e.g. insertions, deletions, sorting) because React assumes unchanged DOM nodes based on matching index positions.

## State Management Strategies
- **Local State (`useState`):** Ideal for UI toggles, input values, and modal open/close states.
- **Context API (`useContext`):** Appropriate for low-frequency global values such as theme preferences, locale, and authenticated user identity. Context is not optimized for high-frequency updates, as every consumer re-renders when the context value object changes reference.
- **Dedicated State Stores (Zustand / Redux):** Recommended for complex, cross-cutting application workflows requiring fine-grained selectors and predictable state transitions.

## Code Splitting and Error Boundaries
Production React applications should implement code splitting using `React.lazy` and `Suspense` to reduce initial bundle sizes. Class-based Error Boundaries capture unhandled runtime JavaScript exceptions in child component trees, preventing white-screen crashes and presenting recovery fallbacks.

