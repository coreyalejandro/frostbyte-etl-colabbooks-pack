import AuditGallery from '../features/audit/AuditGallery'

export default function Audit() {
  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary">
        AUDIT
      </h2>
      <AuditGallery />
    </div>
  )
}
