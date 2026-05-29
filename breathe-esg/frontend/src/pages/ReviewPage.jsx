import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../api'

const STATUS_BADGE = {
  pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  flagged: 'bg-red-50 text-red-700 border-red-200',
  approved: 'bg-green-50 text-green-700 border-green-200',
  rejected: 'bg-gray-100 text-gray-500 border-gray-200',
}

const SCOPE_SHORT = { scope1: 'S1', scope2: 'S2', scope3: 'S3' }

function FlagPill({ flag }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 bg-red-50 text-red-600 border border-red-200 rounded-full" title={flag.detail}>
      ⚠ {flag.flag_type_display}
    </span>
  )
}

export default function ReviewPage() {
  const qc = useQueryClient()
  const [filters, setFilters] = useState({ status: '', scope: '', source: '' })
  const [selected, setSelected] = useState(new Set())
  const [bulkNote, setBulkNote] = useState('')
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 25

  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
  const { data: records, isLoading } = useQuery({
    queryKey: ['records', params],
    queryFn: () => api.get('/records/', { params }).then(r => r.data),
  })

  const reviewMutation = useMutation({
    mutationFn: ({ id, action, note }) => api.post(`/records/${id}/review/`, { action, note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['records'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const bulkMutation = useMutation({
    mutationFn: ({ ids, action, note }) => api.post('/records/bulk-review/', { ids, action, note }),
    onSuccess: () => {
      setSelected(new Set())
      setBulkNote('')
      qc.invalidateQueries({ queryKey: ['records'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const allIds = records?.map(r => r.id) ?? []
  const unlocked = records?.filter(r => !r.locked).map(r => r.id) ?? []
  const allSelected = unlocked.length > 0 && unlocked.every(id => selected.has(id))

  function toggleAll() {
    if (allSelected) {
      setSelected(new Set())
    } else {
      setSelected(new Set(unlocked))
    }
  }

  function toggleOne(id) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const paged = records?.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE) ?? []
  const totalPages = records ? Math.ceil(records.length / PAGE_SIZE) : 0

  return (
    <div className="space-y-4 max-w-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
          <p className="text-sm text-gray-500 mt-0.5">{records?.length ?? '…'} records</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 bg-white rounded-xl border border-gray-200 p-4">
        {[
          { key: 'status', label: 'Status', options: [['', 'All'], ['pending', 'Pending'], ['flagged', 'Flagged'], ['approved', 'Approved'], ['rejected', 'Rejected']] },
          { key: 'scope', label: 'Scope', options: [['', 'All'], ['scope1', 'Scope 1'], ['scope2', 'Scope 2'], ['scope3', 'Scope 3']] },
          { key: 'source', label: 'Source', options: [['', 'All'], ['sap', 'SAP'], ['utility', 'Utility'], ['travel', 'Travel']] },
        ].map(f => (
          <div key={f.key}>
            <label className="block text-xs text-gray-500 mb-1">{f.label}</label>
            <select
              value={filters[f.key]}
              onChange={e => { setFilters(prev => ({ ...prev, [f.key]: e.target.value })); setPage(1) }}
              className="border border-gray-200 rounded-lg text-sm px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              {f.options.map(([val, lbl]) => <option key={val} value={val}>{lbl}</option>)}
            </select>
          </div>
        ))}
      </div>

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-xl p-3">
          <span className="text-sm font-medium text-blue-700">{selected.size} selected</span>
          <input
            type="text"
            value={bulkNote}
            onChange={e => setBulkNote(e.target.value)}
            placeholder="Note (optional)"
            className="border border-blue-200 rounded-lg text-sm px-2 py-1 flex-1 max-w-xs focus:outline-none"
          />
          <button
            onClick={() => bulkMutation.mutate({ ids: [...selected], action: 'approve', note: bulkNote })}
            disabled={bulkMutation.isPending}
            className="text-sm bg-green-600 text-white px-3 py-1 rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            Approve all
          </button>
          <button
            onClick={() => bulkMutation.mutate({ ids: [...selected], action: 'reject', note: bulkNote })}
            disabled={bulkMutation.isPending}
            className="text-sm bg-gray-200 text-gray-700 px-3 py-1 rounded-lg hover:bg-gray-300 disabled:opacity-50"
          >
            Reject all
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Loading…</div>
        ) : paged.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">No records match the current filters.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100">
              <tr className="text-xs text-gray-400 uppercase">
                <th className="pl-4 py-3 text-left w-8">
                  <input type="checkbox" checked={allSelected} onChange={toggleAll} className="rounded" />
                </th>
                <th className="py-3 text-left font-medium px-2">Scope</th>
                <th className="py-3 text-left font-medium px-2">Category</th>
                <th className="py-3 text-left font-medium px-2">Description</th>
                <th className="py-3 text-left font-medium px-2">Quantity</th>
                <th className="py-3 text-left font-medium px-2">Date</th>
                <th className="py-3 text-left font-medium px-2">Site</th>
                <th className="py-3 text-left font-medium px-2">Flags</th>
                <th className="py-3 text-left font-medium px-2">Status</th>
                <th className="py-3 text-left font-medium px-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {paged.map(r => (
                <tr key={r.id} className={`border-b border-gray-50 last:border-0 hover:bg-gray-50 ${r.locked ? 'opacity-60' : ''}`}>
                  <td className="pl-4 py-2.5">
                    {!r.locked && (
                      <input
                        type="checkbox"
                        checked={selected.has(r.id)}
                        onChange={() => toggleOne(r.id)}
                        className="rounded"
                      />
                    )}
                    {r.locked && <span title="Locked for audit">🔒</span>}
                  </td>
                  <td className="py-2.5 px-2">
                    <span className="font-mono text-xs text-gray-500">{SCOPE_SHORT[r.scope] || r.scope}</span>
                  </td>
                  <td className="py-2.5 px-2 text-gray-700 capitalize">{r.category_display}</td>
                  <td className="py-2.5 px-2 max-w-xs">
                    <Link to={`/records/${r.id}`} className="text-green-700 hover:underline truncate block max-w-xs">
                      {r.description || '—'}
                    </Link>
                  </td>
                  <td className="py-2.5 px-2 text-gray-700 font-mono text-xs">
                    {parseFloat(r.quantity).toFixed(1)} {r.unit_normalized}
                  </td>
                  <td className="py-2.5 px-2 text-gray-500 text-xs">{r.activity_date || '—'}</td>
                  <td className="py-2.5 px-2 text-gray-500 text-xs truncate max-w-[120px]">{r.site_name || r.site_code || '—'}</td>
                  <td className="py-2.5 px-2">
                    <div className="flex flex-wrap gap-1">
                      {r.flags.slice(0, 2).map((f, i) => <FlagPill key={i} flag={f} />)}
                      {r.flags.length > 2 && <span className="text-xs text-gray-400">+{r.flags.length - 2}</span>}
                    </div>
                  </td>
                  <td className="py-2.5 px-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_BADGE[r.status]}`}>
                      {r.status_display}
                    </span>
                  </td>
                  <td className="py-2.5 px-2">
                    {!r.locked && (
                      <div className="flex gap-1">
                        <button
                          onClick={() => reviewMutation.mutate({ id: r.id, action: 'approve', note: '' })}
                          disabled={reviewMutation.isPending || r.status === 'approved'}
                          className="text-xs bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded hover:bg-green-100 disabled:opacity-40"
                        >✓</button>
                        <button
                          onClick={() => reviewMutation.mutate({ id: r.id, action: 'reject', note: '' })}
                          disabled={reviewMutation.isPending || r.status === 'rejected'}
                          className="text-xs bg-gray-50 text-gray-600 border border-gray-200 px-2 py-0.5 rounded hover:bg-gray-100 disabled:opacity-40"
                        >✕</button>
                        <button
                          onClick={() => reviewMutation.mutate({ id: r.id, action: 'flag', note: '' })}
                          disabled={reviewMutation.isPending}
                          className="text-xs bg-yellow-50 text-yellow-700 border border-yellow-200 px-2 py-0.5 rounded hover:bg-yellow-100 disabled:opacity-40"
                        >⚑</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-2 justify-end">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="text-sm px-3 py-1.5 border border-gray-200 rounded-lg disabled:opacity-40">Prev</button>
          <span className="text-sm text-gray-500">{page} / {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="text-sm px-3 py-1.5 border border-gray-200 rounded-lg disabled:opacity-40">Next</button>
        </div>
      )}
    </div>
  )
}
