import { useEffect } from 'react';
import type { Action } from '../game/game';

export function actionForKey(e: { key: string; code?: string }): Action | null {
  switch (e.key) {
    case 'ArrowLeft':
      return 'left';
    case 'ArrowRight':
      return 'right';
    case 'ArrowUp':
      return 'rotate';
    case 'ArrowDown':
      return 'softDrop';
    case ' ':
    case 'Spacebar':
      return 'hardDrop';
    case 'p':
    case 'P':
      return 'togglePause';
    default:
      return e.code === 'Space' ? 'hardDrop' : null;
  }
}

export function useKeyboard(dispatch: (a: Action) => void): void {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const action = actionForKey(e);
      if (!action) return;
      e.preventDefault();
      dispatch(action);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [dispatch]);
}
