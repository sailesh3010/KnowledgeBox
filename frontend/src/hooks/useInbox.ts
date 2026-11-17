import { useState, useEffect, useCallback } from 'react';
import { ItemSummary, ItemDetail } from '../types';

export function useInbox() {
  const [items, setItems] = useState<ItemSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<ItemDetail | null>(null);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/items?limit=100');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch items');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const deleteItem = async (id: string) => {
    try {
      const res = await fetch(`/items/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchItems();
      if (selectedItem?.id === id) {
        setSelectedItem(null);
      }
    } catch (e: any) {
      setError(e.message || 'Failed to delete item');
    }
  };

  const fetchDetail = async (id: string) => {
    try {
      const res = await fetch(`/items/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const detail = await res.json();
      setSelectedItem(detail);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch item details');
    }
  };

  return {
    items,
    total,
    loading,
    error,
    selectedItem,
    setSelectedItem,
    fetchItems,
    deleteItem,
    fetchDetail,
  };
}
