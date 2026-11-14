import { useEffect, useRef } from 'react';
import type { MutableRefObject } from 'react';
import type { Input } from '../game/types';

/** Tracks held movement keys and calls onToggle once per Space press. */
export function useKeyboard(onToggle: () => void): MutableRefObject<Input> {
  const input = useRef<Input>({ up: false, down: false });
  const toggleRef = useRef(onToggle);
  toggleRef.current = onToggle;

  useEffect(() => {
    const set = (e: KeyboardEvent, pressed: boolean) => {
      switch (e.key) {
        case 'w':
        case 'W':
          input.current = { ...input.current, up: pressed };
          break;
        case 's':
        case 'S':
          input.current = { ...input.current, down: pressed };
          break;
        case 'ArrowUp':
          e.preventDefault();
          input.current = { ...input.current, up: pressed };
          break;
        case 'ArrowDown':
          e.preventDefault();
          input.current = { ...input.current, down: pressed };
          break;
      }
    };
    const down = (e: KeyboardEvent) => {
      if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault();
        if (!e.repeat) toggleRef.current();
        return;
      }
      set(e, true);
    };
    const up = (e: KeyboardEvent) => set(e, false);
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    return () => {
      window.removeEventListener('keydown', down);
      window.removeEventListener('keyup', up);
    };
  }, []);

  return input;
}
