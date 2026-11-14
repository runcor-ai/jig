import { useCallback, useEffect, useRef } from 'react';

const UP = ['ArrowUp', 'w', 'W'];
const DOWN = ['ArrowDown', 's', 'S'];

/** Tracks held keys on window. getDirection() returns -1 (up), 0, or 1 (down). */
export function useKeyboard(onTogglePause?: () => void) {
  const held = useRef<Set<string>>(new Set());
  const pauseRef = useRef(onTogglePause);
  pauseRef.current = onTogglePause;

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault();
        if (!e.repeat) pauseRef.current?.();
        return;
      }
      if (UP.includes(e.key) || DOWN.includes(e.key)) {
        e.preventDefault();
        held.current.add(e.key);
      }
    };
    const up = (e: KeyboardEvent) => {
      held.current.delete(e.key);
    };
    const blur = () => held.current.clear();
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    window.addEventListener('blur', blur);
    return () => {
      window.removeEventListener('keydown', down);
      window.removeEventListener('keyup', up);
      window.removeEventListener('blur', blur);
    };
  }, []);

  const getDirection = useCallback((): -1 | 0 | 1 => {
    const isUp = UP.some((k) => held.current.has(k));
    const isDown = DOWN.some((k) => held.current.has(k));
    if (isUp === isDown) return 0;
    return isUp ? -1 : 1;
  }, []);

  return { getDirection };
}
