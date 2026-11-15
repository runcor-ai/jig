# Snake

Single-page snake game (20x20) with React, TypeScript and Vite. No backend.

- Setup: `npm install`
- Run: `npm run dev`
- Test: `npm test` (Vitest, jsdom, Testing Library)
- Build: `npm run build`

Controls: arrows / WASD to steer, Space to pause. Best score is kept for the page session only.
Game rules are pure functions in `src/game/`; React only renders and dispatches.
