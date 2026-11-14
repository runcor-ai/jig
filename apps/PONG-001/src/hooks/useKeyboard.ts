import { useEffect, useRef } from 'react';
import type { Input } from '../game/config';

export type KeyAction = 'up' | 'down' | 'toggle' | null;

/** Whitelist mapping; unknown keys return null. */
export function keyToAction(key: string): KeyAction {
  switch (key) {
    case 'ArrowUp': case 'w': case 'W': return 'up';
    case 'ArrowDown': case 's': case 'S': return 'down';
    case ' ': case 'Spacebar': return 'toggle';
    default: return null;
  }
}

export function useKeyboard(onToggle: () => void) {
  const input = useRef<Input>({ up: false, down: false });
  const toggleRef = useRef(onToggle);
  toggleRef.current = onToggle;

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      const a = keyToAction(e.key);
      if (!a) return;
      e.preventDefault();
      if (a === 'up') input.current.up = true;
      else if (a === 'down') input.current.down = true;
      else if (!e.repeat) toggleRef.current();
    };
    const up = (e: KeyboardEvent) => {
      const a = keyToAction(e.key);
      if (!a) return;
      e.preventDefault();
      if (a === 'up') input.current.up = false;
      else if (a === 'down') input.current.down = false;
    };
    const blur = () => { input.current.up = false; input.current.down = false; };
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    window.addEventListener('blur', blur);
    return () => {
      window.removeEventListener('keydown', down);
      window.removeEventListener('keyup', up);
      window.removeEventListener('blur', blur);
    };
  }, []);

  return input;
}
