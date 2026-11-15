import { useEffect, useRef, useState } from 'react';
import type { Input } from '../game/state';

export type Direction = 'up' | 'down' | 'none';

const UP_KEYS = ['w', 'arrowup'];
const DOWN_KEYS = ['s', 'arrowdown'];

const isSpace = (e: KeyboardEvent) => e.code === 'Space' || e.key === ' ';

/** Tracks held movement keys (W/S/arrows) and reports Space presses (ignoring key repeat). */
export function useKeyboard(onSpace: () => void) {
  const inputRef = useRef<Input>({ up: false, down: false });
  const [direction, setDirection] = useState<Direction>('none');
  const onSpaceRef = useRef(onSpace);
  onSpaceRef.current = onSpace;

  useEffect(() => {
    const held = new Set<string>();
    const sync = () => {
      const up = UP_KEYS.some((k) => held.has(k));
      const down = DOWN_KEYS.some((k) => held.has(k));
      inputRef.current = { up, down };
      setDirection(up === down ? 'none' : up ? 'up' : 'down');
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (isSpace(e)) {
        e.preventDefault();
        if (!e.repeat) onSpaceRef.current();
        return;
      }
      const k = e.key.toLowerCase();
      if (UP_KEYS.includes(k) || DOWN_KEYS.includes(k)) {
        e.preventDefault();
        held.add(k);
        sync();
      }
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (held.delete(e.key.toLowerCase())) sync();
    };
    const onBlur = () => {
      held.clear();
      sync();
    };
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    window.addEventListener('blur', onBlur);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
      window.removeEventListener('blur', onBlur);
    };
  }, []);

  return { inputRef, direction };
}
