# Pong

Single-player Pong in React + TypeScript + Vite. Client-only.

- Player (left paddle): `W`/`S` or `ArrowUp`/`ArrowDown`
- `Space` starts, pauses and resumes. First to 10 wins; a Restart button appears at the end.

## Setup / run / test

```
npm install
npm run dev      # start the dev server
npm test         # run the Vitest suite (jsdom)
npm run build    # type-check and build
```

Game rules are pure functions in `src/game` (no React/DOM); tuning values are in `src/game/constants.ts`.
