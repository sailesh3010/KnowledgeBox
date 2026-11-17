import React, { useState, useEffect } from 'react';
import { useInbox } from './hooks/useInbox';
import { useQuery } from './hooks/useQuery';
import { HealthResponse } from './types';

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const { items, total, loading: loadingItems, fetchItems, deleteItem, fetchDetail, selectedItem, setSelectedItem } = useInbox();
  const { loading: querying, result: queryResult, error: queryError, history, ask } = useQuery();

  // Ingest form state
  const [ingestTab, setIngestTab] = useState<'note' | 'url'>('note');
  const [noteTitle, setNoteTitle] = useState('');
  const [noteContent, setNoteContent] = useState('');
  const [urlInput, setUrlInput] = useState('');
  const [urlTitle, setUrlTitle] = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [ingestMsg, setIngestMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Query state
  const [queryInput, setQueryInput] = useState('');
  const [topK, setTopK] = useState(4);
  const [searchFilter, setSearchFilter] = useState('');

  useEffect(() => {
    fetch('/health')
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(() => {});
  }, [items]);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setIngesting(true);
    setIngestMsg(null);

    try {
      const payload = ingestTab === 'note'
        ? { type: 'note', title: noteTitle || undefined, content: noteContent }
        : { type: 'url', title: urlTitle || undefined, content: urlInput };

      const res = await fetch('/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.error?.message || 'Ingestion failed');

      setIngestMsg({
        type: 'success',
        text: `Saved "${data.title}" with ${data.chunk_count} semantic chunks.`,
      });

      if (ingestTab === 'note') {
        setNoteTitle('');
        setNoteContent('');
      } else {
        setUrlInput('');
        setUrlTitle('');
      }
      await fetchItems();
    } catch (err: any) {
      setIngestMsg({ type: 'error', text: err.message });
    } finally {
      setIngesting(false);
    }
  };

  const filteredItems = items.filter(item => {
    if (!searchFilter) return true;
    const term = searchFilter.toLowerCase();
    return item.title.toLowerCase().includes(term) || item.content_preview.toLowerCase().includes(term);
  });

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 py-3.5 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-base shadow-sm">
              T
            </div>
            <div>
              <h1 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
                Turium AI Knowledge Inbox
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">v1.0</span>
              </h1>
              <p className="text-[11px] text-slate-500">Minimalist Semantic Ingestion & RAG Question Answering</p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs">
            {health && (
              <>
                <span className="px-2.5 py-1 bg-emerald-50 border border-emerald-200 rounded text-emerald-700 font-medium">
                  ● Online
                </span>
                <span className="px-2.5 py-1 bg-slate-100 border border-slate-200 rounded text-slate-700">
                  Provider: <strong className="uppercase text-indigo-600">{health.provider}</strong>
                </span>
                <span className="px-2.5 py-1 bg-slate-100 border border-slate-200 rounded text-slate-600">
                  {total} Items ({health.chunks_count} Chunks)
                </span>
              </>
            )}
            <a href="/docs" target="_blank" className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded font-medium transition">
              Docs &rarr;
            </a>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <main className="max-w-7xl mx-auto px-4 py-6 flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Ingest & Saved Items */}
        <div className="lg:col-span-5 space-y-6">
          {/* Ingest Card */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">Add to Knowledge Inbox</h2>
            <div className="flex p-1 bg-slate-100 rounded-lg mb-4 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setIngestTab('note')}
                className={`flex-1 py-1.5 rounded-md transition ${ingestTab === 'note' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-600'}`}
              >
                Text Note
              </button>
              <button
                type="button"
                onClick={() => setIngestTab('url')}
                className={`flex-1 py-1.5 rounded-md transition ${ingestTab === 'url' ? 'bg-white text-indigo-600 shadow-xs' : 'text-slate-600'}`}
              >
                Web URL
              </button>
            </div>

            <form onSubmit={handleIngest} className="space-y-3">
              {ingestTab === 'note' ? (
                <>
                  <input
                    type="text"
                    placeholder="Title (Optional)"
                    value={noteTitle}
                    onChange={e => setNoteTitle(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                  <textarea
                    rows={4}
                    placeholder="Note text..."
                    required
                    value={noteContent}
                    onChange={e => setNoteContent(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-indigo-500 leading-relaxed"
                  />
                </>
              ) : (
                <>
                  <input
                    type="url"
                    placeholder="https://example.com/article"
                    required
                    value={urlInput}
                    onChange={e => setUrlInput(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                  <input
                    type="text"
                    placeholder="Custom Title (Optional)"
                    value={urlTitle}
                    onChange={e => setUrlTitle(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </>
              )}

              {ingestMsg && (
                <div className={`p-2.5 rounded text-xs ${ingestMsg.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'}`}>
                  {ingestMsg.text}
                </div>
              )}

              <button
                type="submit"
                disabled={ingesting}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg transition disabled:opacity-50"
              >
                {ingesting ? 'Processing & Vectorizing...' : 'Ingest Content'}
              </button>
            </form>
          </div>

          {/* Saved Items */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Saved Items ({total})</h2>
              <button onClick={() => fetchItems()} className="text-xs text-slate-400 hover:text-slate-700">Refresh</button>
            </div>
            <input
              type="text"
              placeholder="Filter items..."
              value={searchFilter}
              onChange={e => setSearchFilter(e.target.value)}
              className="w-full text-xs px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg mb-3 outline-none"
            />
            {loadingItems ? (
              <p className="text-xs text-slate-400 text-center py-6">Loading...</p>
            ) : filteredItems.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-6">No saved items found.</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {filteredItems.map(item => (
                  <div key={item.id} className="p-3 border border-slate-200 rounded-lg hover:bg-slate-50 transition group">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 mb-1">
                          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${item.source_type === 'url' ? 'bg-emerald-100 text-emerald-800' : 'bg-indigo-100 text-indigo-800'}`}>
                            {item.source_type}
                          </span>
                          <span className="text-xs font-semibold text-slate-900 truncate">{item.title}</span>
                        </div>
                        <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">{item.content_preview}</p>
                        <div className="text-[10px] text-slate-400 mt-1 flex gap-2">
                          <span>{item.chunk_count} chunks</span>
                          <span>•</span>
                          <span>{item.word_count} words</span>
                        </div>
                      </div>
                      <div className="flex flex-col gap-1">
                        <button
                          onClick={() => fetchDetail(item.id)}
                          className="text-[10px] px-2 py-0.5 bg-slate-100 hover:bg-slate-200 rounded text-slate-700"
                        >
                          Chunks
                        </button>
                        <button
                          onClick={() => deleteItem(item.id)}
                          className="text-[10px] px-2 py-0.5 bg-rose-50 hover:bg-rose-100 rounded text-rose-600"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Q&A */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Ask Knowledge Inbox</h2>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-500">Top-k:</span>
                <select
                  value={topK}
                  onChange={e => setTopK(Number(e.target.value))}
                  className="bg-slate-50 border border-slate-200 rounded px-2 py-0.5 text-xs outline-none"
                >
                  <option value={2}>2</option>
                  <option value={4}>4</option>
                  <option value={6}>6</option>
                </select>
              </div>
            </div>

            <textarea
              rows={3}
              value={queryInput}
              onChange={e => setQueryInput(e.target.value)}
              placeholder="Ask anything about your saved content..."
              className="w-full text-xs px-3.5 py-2.5 border border-slate-300 rounded-lg outline-none focus:ring-1 focus:ring-indigo-500 leading-relaxed"
            />

            {queryError && (
              <div className="p-2.5 bg-rose-50 text-rose-800 border border-rose-200 rounded text-xs">
                {queryError}
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => ask(queryInput, topK)}
                disabled={querying || !queryInput.trim()}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg transition disabled:opacity-50"
              >
                {querying ? 'Searching & Generating...' : 'Ask Question &rarr;'}
              </button>
            </div>
          </div>

          {/* Answer Card */}
          {queryResult && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 text-xs">
                <span className="font-bold text-slate-900">Answer</span>
                <div className="flex gap-2 text-[11px] text-slate-500">
                  <span className="font-mono">{queryResult.latency_ms}ms</span>
                  <span>Model: {queryResult.model}</span>
                </div>
              </div>
              <div className="text-xs text-slate-800 leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-200 whitespace-pre-wrap">
                {queryResult.answer}
              </div>

              {queryResult.sources.length > 0 && (
                <div className="space-y-2 pt-2">
                  <h3 className="text-xs font-bold text-slate-900">Retrieved Sources ({queryResult.sources.length})</h3>
                  {queryResult.sources.map((src, i) => (
                    <div key={i} className="p-3 bg-white border border-slate-200 rounded-lg text-xs">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-bold text-indigo-700">Source {i + 1}: {src.source_title}</span>
                        <span className="text-[10px] text-slate-500">Similarity: {(src.similarity_score * 100).toFixed(1)}%</span>
                      </div>
                      <p className="text-[11px] text-slate-600 font-mono bg-slate-50 p-2 rounded">
                        "{src.snippet}"
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Query History */}
          {history.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4">
              <h3 className="text-xs font-bold text-slate-600 mb-2 uppercase tracking-wider">Recent Questions</h3>
              <div className="flex flex-wrap gap-2">
                {history.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => { setQueryInput(q); ask(q, topK); }}
                    className="text-xs bg-slate-50 hover:bg-slate-100 border border-slate-200 px-2.5 py-1 rounded text-slate-700"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Chunks Inspector Modal */}
      {selectedItem && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[80vh] flex flex-col shadow-xl">
            <div className="p-4 border-b border-slate-200 flex justify-between items-center">
              <h3 className="text-sm font-bold text-slate-900">{selectedItem.title} - Chunks Detail</h3>
              <button onClick={() => setSelectedItem(null)} className="text-slate-400 hover:text-slate-700 font-bold">✕</button>
            </div>
            <div className="p-4 overflow-y-auto space-y-3 text-xs flex-1">
              {selectedItem.chunks.map(c => (
                <div key={c.id} className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                  <div className="flex justify-between text-[10px] text-slate-500 font-mono mb-1">
                    <span>Chunk #{c.chunk_index}</span>
                    <span>Offsets [{c.char_start}..{c.char_end}]</span>
                  </div>
                  <p className="font-mono text-slate-800 leading-relaxed whitespace-pre-wrap">{c.content}</p>
                </div>
              ))}
            </div>
            <div className="p-3 border-t border-slate-200 flex justify-end">
              <button onClick={() => setSelectedItem(null)} className="px-4 py-1.5 bg-slate-800 text-white rounded text-xs font-semibold">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
