import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: doc, isLoading, error } = useQuery({
    queryKey: ['document', id],
    queryFn: () => api.getDocument(id!),
    enabled: !!id,
  })

  return (
    <div>
      <div className="mb-4">
        <Link
          to="/documents"
          className="text-text-secondary hover:text-text-primary text-xs font-medium uppercase tracking-wider"
        >
          [← BACK]
        </Link>
      </div>
      <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary mb-4">
        DOCUMENT: {id}
      </h2>
      <div
        className="bg-surface border border-border p-4"
        style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
      >
        {isLoading && <p className="text-text-tertiary">LOADING…</p>}
        {error && <p className="text-accent">FAILED: Document not found.</p>}
        {doc && (
          <dl className="grid grid-cols-2 gap-2">
            <dt className="text-xs text-text-secondary uppercase tracking-wider">ID</dt>
            <dd className="text-text-primary">{doc.id}</dd>
            <dt className="text-xs text-text-secondary uppercase tracking-wider">STATUS</dt>
            <dd className={doc.status === 'failed' ? 'text-accent' : 'text-text-primary'}>
              {doc.status ?? '—'}
            </dd>
            <dt className="text-xs text-text-secondary uppercase tracking-wider">TENANT</dt>
            <dd>{doc.tenant_id ?? '—'}</dd>
            <dt className="text-xs text-text-secondary uppercase tracking-wider">FILENAME</dt>
            <dd>{doc.filename ?? '—'}</dd>
            <dt className="text-xs text-text-secondary uppercase tracking-wider">MODALITY</dt>
            <dd>{doc.modality ?? 'text'}</dd>
            <dt className="text-xs text-text-secondary uppercase tracking-wider">CREATED</dt>
            <dd>{doc.created_at ?? '—'}</dd>
          </dl>
        )}
      </div>
    </div>
  )
}
