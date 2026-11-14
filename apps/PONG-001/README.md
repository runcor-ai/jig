# Browser Pong

A single-page Pong game (React + TypeScript + Vite). You control the left paddle against a computer-controlled right paddle. No backend, no persistence.

## Install
```
npm install
```
## Run
```
npm run dev
```
## Test
```
npm test
```
JUnit output is written to `test-results/junit.xml`.
## Build
```
npm run build
```
Output: `dist/index.html`.

## Controls
- ArrowUp / W: move up
- ArrowDown / S: move down
- Space: start, pause / resume
- Restart button: reset the game at any time

## Rules
- First side to 10 points wins (no win-by-two).
- Ball bounces off walls and paddles; the bounce angle depends on where it hits the paddle, and it speeds up on each hit up to a maximum.
- If the ball passes a side's edge, the other side scores and the ball is served from the centre (first serve toward the player, then alternating).
- The game pauses automatically when the tab is hidden.
- The computer paddle has a capped speed, so it can be beaten.
