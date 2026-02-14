// Document Upload Component
// Allows users to upload documents to the pipeline

import { useState, useRef, useCallback } from 'react'

interface DocumentUploadProps {
  tenantId?: string
  onUploadComplete?: (documentId: string) => void
}

export function DocumentUpload({ tenantId = 'default', onUploadComplete }: DocumentUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const uploadFile = async (file: File) => {
    setIsUploading(true)
    setError(null)
    setUploadProgress(`Uploading ${file.name}...`)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('tenant_id', tenantId)

      const response = await fetch('/api/v1/intake', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }))
        throw new Error(errorData.detail?.message || errorData.detail || `HTTP ${response.status}`)
      }

      const data = await response.json()
      setUploadProgress(`✓ ${file.name} uploaded successfully`)
      
      if (data.document_id) {
        onUploadComplete?.(data.document_id)
      }

      // Clear success message after 3 seconds
      setTimeout(() => {
        setUploadProgress(null)
        setIsUploading(false)
      }, 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setUploadProgress(null)
      setIsUploading(false)
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      uploadFile(files[0])
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      uploadFile(files[0])
    }
  }, [])

  const handleClick = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-all duration-200
          ${isDragging 
            ? 'border-accent bg-accent/10' 
            : 'border-border bg-surface hover:border-text-secondary hover:bg-interactive'
          }
          ${isUploading ? 'pointer-events-none opacity-70' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileSelect}
          className="hidden"
          accept=".txt,.pdf,.doc,.docx,.md,.json,.csv"
        />
        
        <div className="space-y-2">
          <div className="text-4xl mb-2">
            {isUploading ? '⟳' : isDragging ? '↑' : '+'}
          </div>
          <p className="text-text-secondary font-medium">
            {isUploading ? 'Uploading...' : 'Drop file here or click to upload'}
          </p>
          <p className="text-text-tertiary text-xs">
            Supports: PDF, DOCX, TXT, MD, JSON, CSV
          </p>
        </div>
      </div>

      {/* Progress / Status */}
      {uploadProgress && (
        <div className="flex items-center gap-2 text-sm">
          <span className={uploadProgress.startsWith('✓') ? 'text-accent' : 'text-blue-400 animate-pulse'}>
            {uploadProgress.startsWith('✓') ? '✓' : '⟳'}
          </span>
          <span className={uploadProgress.startsWith('✓') ? 'text-accent' : 'text-text-secondary'}>
            {uploadProgress}
          </span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-red-400">
          <span>✗</span>
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}
