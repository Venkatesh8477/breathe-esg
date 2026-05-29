import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'

function StatCard({ label, value, color }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${color}`}>{value ?? '—'}</p>
    </div>
  )
}

const SOURCE_LABELS = { sap: 'SAP Fuel & Procurement', utility: 'Utility Electricity', travel: 'Corporate Travel' }
const SCOPE_LABELS = { scope1: 'Scope 1', scope2: 'Scope 2', scope3: 'Scope 3' }
const STATUS_COLORS = { done: 'text-green-600', processing: 'text-yellow-600', failed: 'text-red-600', pending: 'text-gray-500' }

export default function DashboardPage() {
  const queryClient = useQueryClient()
  const [deletingId, setDeletingId] = useState(null)

  const deleteBatch = useMutation({
    mutationFn: (id) => api.delete(`/batches/${id}/`),
    onSettled: () => {
      setDeletingId(null)
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard/').then(r => r.data),
    refetchInterval: 15000,
  })

  if (isLoading) return <div className="text-gray-400 text-sm">Loading…</div>
  if (error) return <div className="text-red-500 text-sm">Failed to load dashboard</div>

  const { summary, by_scope, by_source, recent_batches } = data

  const handleDelete = (batchId) => {
    if (!window.confirm('Delete this upload batch and all its records? This cannot be undone.')) {
      return
    }
    setDeletingId(batchId)
    deleteBatch.mutate(batchId)
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Overview of ingested emission records</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Records" value={summary.total} color="text-gray-900" />
        <StatCard label="Pending Review" value={summary.pending} color="text-yellow-600" />
        <StatCard label="Flagged" value={summary.flagged} color="text-red-600" />
        <StatCard label="Approved" value={summary.approved} color="text-green-600" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Records by Scope</h2>
          <div className="space-y-2">
            {by_scope.map(s => (
              <div key={s.scope} className="flex justify-between items-center">
                <span className="text-sm text-gray-600">{SCOPE_LABELS[s.scope] || s.scope}</span>
                <span className="text-sm font-medium text-gray-900">{s.count}</span>
              </div>
            ))}
            {by_scope.length === 0 && <p className="text-sm text-gray-400">No data yet</p>}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Records by Source</h2>
          <div className="space-y-2">
            {by_source.map(s => (
              <div key={s.batch__source_type} className="flex justify-between items-center">
                <span className="text-sm text-gray-600">{SOURCE_LABELS[s.batch__source_type] || s.batch__source_type}</span>
                <span className="text-sm font-medium text-gray-900">{s.count}</span>
              </div>
            ))}
            {by_source.length === 0 && <p className="text-sm text-gray-400">No data yet</p>}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-700">Recent Upload Batches</h2>
          <Link to="/upload" className="text-xs text-green-600 hover:underline">Upload new →</Link>
        </div>
        {recent_batches.length === 0 ? (
          <p className="text-sm text-gray-400">No uploads yet. <Link to="/upload" className="text-green-600 hover:underline">Upload a file</Link> to get started.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-400 uppercase border-b border-gray-100">
                  <th className="text-left pb-2 font-medium">Source</th>
                  <th className="text-left pb-2 font-medium">File</th>
                  <th className="text-left pb-2 font-medium">Rows</th>
                  <th className="text-left pb-2 font-medium">Status</th>
                  <th className="text-left pb-2 font-medium">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {recent_batches.map(b => (
                  <tr key={b.id} className="border-b border-gray-50 last:border-0">
                    <td className="py-2 text-gray-700">{SOURCE_LABELS[b.source_type] || b.source_type}</td>
                    <td className="py-2 text-gray-500 font-mono text-xs max-w-xs truncate">{b.filename}</td>
                    <td className="py-2 text-gray-700">{b.parsed_rows}/{b.total_rows}</td>
                    <td className={`py-2 font-medium ${STATUS_COLORS[b.status]}`}>{b.status_display}</td>
                    <td className="py-2 text-right">
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        <span className="text-gray-400 text-xs">{new Date(b.uploaded_at).toLocaleString()}</span>
                        {b.is_mine && (
                          <button
                            type="button"
                            onClick={() => handleDelete(b.id)}
                            disabled={deletingId === b.id || deleteBatch.isLoading}
                            className="text-xs text-red-600 hover:text-red-800 disabled:opacity-50"
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
