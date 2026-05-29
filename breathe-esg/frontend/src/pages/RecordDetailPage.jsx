import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api'

const STATUS_BADGE = {
  pending: 'bg-yellow-50 text-yellow-700',
  flagged: 'bg-red-50 text-red-700',
  approved: 'bg-green-50 text-green-700',
  rejected: 'bg-gray-100 text-gray-500',
}

function Field({ label, value }) {
  if (!value && value !== 0) return null
  return (
    <div>
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="text-sm text-gray-800 mt-0.5">{value}</p>
    </div>
  )
}

export default function RecordDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [note, setNote] = useState('')

  const { data: record, isLoading } = useQuery({
    queryKey: ['record', id],
    queryFn: () => api.get(`/records/${id}/`).then(r => r.data),
  })

  const reviewMutation = useMutation({
    mutationFn: ({ action }) => api.post(`/records/${id}/review/`, { action, note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['record', id] })
      qc.invalidateQueries({ queryKey: ['records'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      setNote('')
    },
  })

  if (isLoading) return <div className="text-gray-400 text-sm p-6">Loading…</div>
  if (!record) return <div className="text-red-500 text-sm p-6">Record not found</div>

  return (
    <div className="max-w-3xl space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-sm text-gray-400 hover:text-gray-700">← Back</button>
        <h1 className="text-xl font-bold text-gray-900">Record #{record.id}</h1>
        {record.locked && <span className="text-sm text-gray-400">🔒 Locked for audit</span>}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 grid grid-cols-2 gap-4">
        <Field label="Description" value={record.description} />
        <Field label="Status" value={
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_BADGE[record.status]}`}>{record.status_display}</span>
        } />
        <Field label="Scope" value={record.scope_display} />
        <Field label="Category" value={record.category_display} />
        <Field label="Quantity (normalized)" value={`${parseFloat(record.quantity).toLocaleString()} ${record.unit_normalized}`} />
        <Field label="Original quantity" value={`${record.original_quantity} ${record.original_unit}`} />
        <Field label="Activity date" value={record.activity_date} />
        <Field label="Billing period" value={record.period_start ? `${record.period_start} → ${record.period_end}` : null} />
        <Field label="Site code" value={record.site_code} />
        <Field label="Site name" value={record.site_name} />
        <Field label="Supplier / Vendor" value={record.supplier_vendor} />
        <Field label="Source" value={record.source_type} />
        <Field label="Tenant" value={record.tenant_name} />
        <Field label="Reviewed by" value={record.reviewed_by_name} />
        {record.review_note && <Field label="Review note" value={record.review_note} />}
      </div>

      {record.flags && record.flags.length > 0 && (
        <div className="bg-white rounded-xl border border-red-200 p-5">
          <h2 className="text-sm font-semibold text-red-700 mb-3">Validation Flags ({record.flags.length})</h2>
          <div className="space-y-2">
            {record.flags.map(f => (
              <div key={f.id} className="flex items-start gap-2 text-sm">
                <span className="text-red-500 mt-0.5">⚠</span>
                <div>
                  <p className="font-medium text-gray-800">{f.flag_type_display} — <span className="font-normal text-gray-600">{f.field_name}</span></p>
                  <p className="text-gray-500 text-xs">{f.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {record.raw_data && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Raw Ingested Data</h2>
          <pre className="text-xs text-gray-600 bg-gray-50 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(record.raw_data, null, 2)}
          </pre>
        </div>
      )}

      {!record.locked && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Review Decision</h2>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Note (optional)</label>
              <textarea
                value={note}
                onChange={e => setNote(e.target.value)}
                rows={2}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="Reason for decision…"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => reviewMutation.mutate({ action: 'approve' })}
                disabled={reviewMutation.isPending || record.status === 'approved'}
                className="bg-green-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-40"
              >
                Approve
              </button>
              <button
                onClick={() => reviewMutation.mutate({ action: 'reject' })}
                disabled={reviewMutation.isPending || record.status === 'rejected'}
                className="bg-gray-100 text-gray-700 text-sm px-4 py-2 rounded-lg hover:bg-gray-200 disabled:opacity-40"
              >
                Reject
              </button>
              <button
                onClick={() => reviewMutation.mutate({ action: 'flag' })}
                disabled={reviewMutation.isPending}
                className="bg-yellow-50 text-yellow-700 border border-yellow-200 text-sm px-4 py-2 rounded-lg hover:bg-yellow-100 disabled:opacity-40"
              >
                Flag for review
              </button>
            </div>
            {reviewMutation.error && (
              <p className="text-sm text-red-600">{reviewMutation.error.response?.data?.error || 'Action failed'}</p>
            )}
          </div>
        </div>
      )}

      {record.audit_events && record.audit_events.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Audit Trail</h2>
          <div className="space-y-2">
            {record.audit_events.map(e => (
              <div key={e.id} className="flex items-start gap-3 text-sm py-2 border-b border-gray-50 last:border-0">
                <span className="text-gray-400 text-xs whitespace-nowrap">{new Date(e.performed_at).toLocaleString()}</span>
                <div>
                  <p className="text-gray-800">
                    <span className="font-medium">{e.performed_by_name}</span> {e.action}
                    {e.previous_status && e.new_status && (
                      <span className="text-gray-400"> · {e.previous_status} → {e.new_status}</span>
                    )}
                  </p>
                  {e.note && <p className="text-gray-500 text-xs">{e.note}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
