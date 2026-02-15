import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DocumentQueue from '../features/documents/DocumentQueue'
import { DocumentUpload } from '../components/DocumentUpload'
import Panel from '../components/Panel'

export default function DocumentList() {
  const [docId, setDocId] = useState('')
  const navigate = useNavigate()

  const handleUploadComplete = (_documentId: string) => {
    // Optionally navigate to the new document
    // navigate(`/documents/${documentId}`)
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary">
        DOCUMENTS
      </h2>

      {/* Upload Section */}
      <Panel title="UPLOAD DOCUMENT">
        <DocumentUpload 
          tenantId="default"
          onUploadComplete={handleUploadComplete}
        />
      </Panel>

      <Panel title="LOOKUP BY ID">
        <p className="text-text-secondary mb-4">
          Documents are ingested via POST /api/v1/intake.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="DOCUMENT ID (UUID)"
            value={docId}
            onChange={(e) => setDocId(e.target.value)}
            className="bg-base border border-border px-3 py-2 flex-1 text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-0"
          />
          <button
            onClick={() => docId && navigate(`/documents/${docId}`)}
            disabled={!docId.trim()}
            className="px-4 py-2 border border-border bg-interactive text-text-primary font-medium uppercase text-xs tracking-wider disabled:opacity-50 disabled:cursor-not-allowed hover:bg-surface active:translate-y-px"
          >
            [VIEW]
          </button>
        </div>
      </Panel>
      <DocumentQueue />
    </div>
  )
}
