# Falling Blocks

A client-only falling-block puzzle game built with React, TypeScript and Vite.
All rules are pure functions in `src/game`; React only renders state and turns key/timer events into reducer actions.

## Setup

```
npm install
```

## Run

```
npm run dev      # development server
npm run build    # type-check and production build
```

## Test

```
npm test
```

## Controls

Left/Right move, Up rotate, Down soft drop, Space hard drop, P pause.

## Rules

10x20 board; clears score 100/300/500/800 (not multiplied by level); level = 1 + floor(rows/10);
gravity interval = max(100, 1000 - (level-1)*80) ms. Soft/hard drop award no points.
