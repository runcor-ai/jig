export const WIDTH = 800;
export const HEIGHT = 500;
export const PADDLE_W = 12;
export const PADDLE_H = 80;
export const BALL_SIZE = 12;
export const PADDLE_MARGIN = 20;
export const LEFT_PADDLE_X = PADDLE_MARGIN;
export const RIGHT_PADDLE_X = WIDTH - PADDLE_MARGIN - PADDLE_W;

/** px per second */
export const PLAYER_SPEED = 400;
export const BALL_START_SPEED = 320;
export const BALL_MAX_SPEED = 720;
/** maximum vertical ball speed (px/s) produced by a paddle hit */
export const MAX_VY = 400;
/** multiplier applied to horizontal speed on each paddle hit */
export const SPEEDUP = 1.06;
/** AI speed (px/s) - strictly below MAX_VY so the AI is beatable */
export const AI_SPEED = 260;
export const AI_DEAD_ZONE = 10;
export const WIN_SCORE = 10;
/** delta-time cap in milliseconds */
export const DT_CAP_MS = 50;
