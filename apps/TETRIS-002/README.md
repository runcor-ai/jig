# Falling Blocks

A browser falling-block puzzle game. React + TypeScript + Vite, no backend.

## Setup
    npm install

## Run
    npm run dev

## Test
    npm test            # vitest run (jsdom)

## Build
    npm run build

## Controls
← → move · ↑ rotate · ↓ soft drop · Space hard drop · P pause

## Layout
All rules are pure functions in `src/game/` (`pieces`, `board`, `scoring`, `game` reducer
`reduce(state, action, rng)`). Components and hooks only render state and map keys/timers to actions.
Scoring is 100/300/500/800, level = floor(rows/10)+1, gravity = max(100, 1000-(level-1)*100) ms.
