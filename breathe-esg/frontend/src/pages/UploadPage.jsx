import { useState, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../api'

const SOURCE_OPTIONS = [
  { value: 'sap', label: 'SAP Fuel & Procurement', desc: 'MB51/ME2M flat file export (CSV with German headers)' },
  { value: 'utility', label: 'Utility Electricity', desc: 'Green Button portal CSV export' },
  { value: 'travel', label: 'Corporate Travel', desc: 'Navan/Concur trip report CSV export' },
]

const STATUS_COLORS = {
  done: 'bg-green-50 text-green-700 border-green-200',
  processing: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  failed: 'bg-red-50 text-red-700 border-red-200',
  pending: 'bg-gray-50 text-gray-600 border-gray-200',
}

export default function UploadPage() {
  const qc = useQueryClient()
  const fileRef = useRef()
  const [sourceType, setSourceType] = useState('sap')
  const [tenantSlug, setTenantSlug] = useState('acme-corp')
  const [result, setResult] = useState(null)

  const { data: batches } = useQuery({
    queryKey: ['batches'],
    queryFn: () => api.get('/batches/').then(r => r.data),
  })

  const upload = useMutation({
    mutationFn: (formData) => api.post('/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    onSuccess: (res) => {
      setResult(res.data)
      qc.invalidateQueries({ queryKey: ['batches'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      if (fileRef.current) fileRef.current.value = ''
    },
  })

  function handleSubmit(e) {
    e.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    fd.append('source_type', sourceType)
    fd.append('tenant_slug', tenantSlug)
    setResult(null)
    upload.mutate(fd)
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Data</h1>
        <p className="text-sm text-gray-500 mt-1">Upload a CSV file from one of the three supported sources</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Source Type</label>
            <div className="space-y-2">
              {SOURCE_OPTIONS.map(opt => (
                <label key={opt.value} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${sourceType === opt.value ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:border-gray-300'}`}>
                  <input
                    type="radio"
                    name="source"
                    value={opt.value}
                    checked={sourceType === opt.value}
                    onChange={() => setSourceType(opt.value)}
                    className="mt-0.5"
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-800">{opt.label}</p>
                    <p className="text-xs text-gray-500">{opt.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Client / Tenant</label>
            <input
              type="text"
              value={tenantSlug}
              onChange={e => setTenantSlug(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="acme-corp"
            />
            <p className="text-xs text-gray-400 mt-1">Slug identifier for the client company</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CSV File</label>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:bg-green-50 file:text-green-700"
            />
            <p className="text-xs text-gray-400 mt-1">
              Use the sample files in <code className="bg-gray-100 px-1 rounded text-xs">sample_data/</code> to try it out
            </p>
          </div>

          {upload.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              Upload failed: {upload.error.response?.data?.detail || upload.error.message}
            </div>
          )}

          {result && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm">
              <p className="font-medium text-green-800">Upload complete</p>
              <p className="text-green-700 mt-1">
                {result.parsed_rows} rows processed · {result.failed_rows} failed · Status: {result.status_display}
              </p>
              {result.error_message && <p className="text-red-600 mt-1">{result.error_message}</p>}
            </div>
          )}

          <button
            type="submit"
            disabled={upload.isPending}
            className="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-5 rounded-lg text-sm disabled:opacity-50 transition-colors"
          >
            {upload.isPending ? 'Processing…' : 'Upload & Ingest'}
          </button>
        </form>
      </div>

      {batches && batches.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">All Upload Batches</h2>
          <div className="space-y-2">
            {batches.map(b => (
              <div key={b.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-800">{b.source_type_display}</p>
                  <p className="text-xs text-gray-400 font-mono truncate max-w-xs">{b.filename}</p>
                </div>
                <div className="text-right ml-4">
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_COLORS[b.status]}`}>{b.status_display}</span>
                  <p className="text-xs text-gray-400 mt-1">{b.parsed_rows}/{b.total_rows} rows</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
