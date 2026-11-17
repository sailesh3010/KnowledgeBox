import { useState } from 'react';
import { QueryResponse } from '../types';

export function useQuery() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<string[]>([]);

  const ask = async (query: string, topK: number = 4) => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), top_k: topK }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || `HTTP ${res.status}`);
      }

      setResult(data);
      setHistory(prev => [query, ...prev.filter(q => q !== query)].slice(0, 5));
    } catch (e: any) {
      setError(e.message || 'Query failed');
    } finally {
      setLoading(false);
    }
  };

  return {
    loading,
    result,
    error,
    history,
    ask,
    setResult,
  };
}
