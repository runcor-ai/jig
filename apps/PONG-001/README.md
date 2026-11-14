# Browser Pong

React + TypeScript + Vite Pong: you (left paddle) vs the computer (right). First to 10 wins. No backend.

## Setup

```
npm install
```

## Run

```
npm run dev
```

Controls: W/S or Up/Down arrows move your paddle; Space pauses; the Restart button resets the game.

## Test and build

```
npm test          # vitest run (jsdom)
npm run build     # type-check + production build
```

## Layout

- `src/game/config.ts` constants; `logic.ts` pure `step()` rules; `ai.ts` computer opponent
- `src/hooks/useKeyboard.ts`, `useGameLoop.ts` input and rAF loop (dt clamped to 50 ms)
- `src/components/Playfield.tsx` DOM rendering; `src/App.tsx` wiring
- `src/__tests__/` unit and component tests
