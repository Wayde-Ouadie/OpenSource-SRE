import { useState, useEffect, useCallback } from 'react';

type ApiState<T> =
    | { status: 'loading'; data: null; error: null }
    | { status: 'error'; data: null; error: string }
    | { status: 'empty'; data: null; error: null }
    | { status: 'success'; data: T; error: null };

export function useApi<T>(fetchFn: () => Promise<T>, deps: unknown[] = []) {
    const [state, setState] = useState<ApiState<T>>({
        status: 'loading',
        data: null,
        error: null,
    });

    const execute = useCallback(async () => {
        setState({ status: 'loading', data: null, error: null });
        try {
            const result = await fetchFn();
            const isEmpty = Array.isArray(result) ? result.length === 0 : !result;
            if (isEmpty) {
                setState({ status: 'empty', data: null, error: null });
            } else {
                setState({ status: 'success', data: result, error: null });
            }
        } catch (err) {
            setState({
                status: 'error',
                data: null,
                error: err instanceof Error ? err.message : 'An unexpected error occurred',
            });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps);

    useEffect(() => {
        execute();
    }, [execute]);

    return { ...state, refetch: execute };
}
