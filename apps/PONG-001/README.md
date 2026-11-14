# Pong

Single-player browser Pong built with React + TypeScript + Vite. Client-only; no backend.

## Setup

```
npm install
```

## Run

```
npm run dev      # dev server
npm run build    # type-check (strict) and production build
```

## Test

```
npm test         # Vitest (jsdom), runs once
```

## Controls

- **W / ArrowUp**: paddle up; **S / ArrowDown**: paddle down (left paddle)
- **Space**: start, pause, resume (does not restart after game over)
- **Restart** button: appears at game over

First to 10 wins. The computer paddle is speed-limited, reacts about 200 ms late and has a dead zone.

## Layout

- `src/game/` pure logic: `constants`, `types`, `state` (`createInitialState`, `resetBall`, `applyCommand`), `step`, `ai`
- `src/hooks/` `useGameLoop` (rAF, dt clamped to 1/30 s), `useKeyboard`
- `src/components/` `Game`, `Playfield`
