import { useEffect, useState } from 'react';

type QueryState<T> =
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

export function useRepositoryQuery<T>(query: () => Promise<T>): QueryState<T> {
  const [state, setState] = useState<QueryState<T>>({ status: 'loading' });

  useEffect(() => {
    let active = true;

    query()
      .then((data) => {
        if (active) {
          setState({ status: 'success', data });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            status: 'error',
            error: error instanceof Error ? error : new Error('Error desconocido'),
          });
        }
      });

    return () => {
      active = false;
    };
  }, [query]);

  return state;
}
