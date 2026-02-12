import VerificationControlRoom from '../features/verification/VerificationControlRoom'

export default function Verify() {
  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary">
        VERIFICATION
      </h2>
      <VerificationControlRoom />
    </div>
  )
}
