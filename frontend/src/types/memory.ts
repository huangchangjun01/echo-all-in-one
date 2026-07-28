export interface MemoryFile {
  id?: number
  fileKey: string
  fileType: 'text' | 'audio' | 'video' | 'image'
  fileName: string
  fileSize: number
}

export interface MemoryTheme {
  id?: number
  memoryId: string
  userId: string
  roleId: string
  themeName: string
  subjectiveDesc: string
  status: 'processing' | 'completed' | 'editing'
  files: MemoryFile[]
  fileCount?: number
  createdAt?: string
  updatedAt?: string
}

export interface UploadFileItem {
  uid: string
  name: string
  size: number
  type: string
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number
  fileKey?: string
  fileType?: string
  error?: string
  rawFile?: File
  chunks?: UploadChunk[]
}

export interface UploadChunk {
  index: number
  start: number
  end: number
  uploaded: boolean
  blob: Blob
}

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface PageResult<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}