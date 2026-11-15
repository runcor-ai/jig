# Pong (player vs computer)

Single-page React + TypeScript + Vite Pong. No backend.

- Left paddle (you): `W`/`S` or `ArrowUp`/`ArrowDown`.
- Right paddle: computer (260 px/s, 150 ms reaction delay, 10 px dead zone).
- `Space` starts, pauses and resumes. First to 10 wins; a Restart button appears at game end.

## Setup and run

```
npm install
npm run dev      # development server
npm run build    # type-check + production build into dist/
npm test         # vitest run (jsdom)
```

JUnit report: `npx vitest run --reporter=junit --outputFile=test-results/junit.xml`

## Layout

- `src/game/` pure, deterministic rules (`constants`, `state`, `step`, `ai`, `controls`); rng is injected.
- `src/hooks/` keyboard and requestAnimationFrame hooks.
- `src/components/Game.tsx` DOM rendering; `src/__tests__/` tests.
