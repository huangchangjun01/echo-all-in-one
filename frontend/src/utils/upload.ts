import type { UploadFileItem, UploadChunk } from '../types/memory'

const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB
const MAX_CONCURRENT = 5

const STORAGE_KEY_PREFIX = 'upload_progress_'

function getStorageKey(file: File): string {
  return `${STORAGE_KEY_PREFIX}${file.name}_${file.size}_${file.lastModified}`
}

function saveProgress(file: File, uploadedChunks: number[]) {
  const key = getStorageKey(file)
  localStorage.setItem(key, JSON.stringify(uploadedChunks))
}

function loadProgress(file: File): number[] {
  const key = getStorageKey(file)
  const data = localStorage.getItem(key)
  return data ? JSON.parse(data) : []
}

function clearProgress(file: File) {
  const key = getStorageKey(file)
  localStorage.removeItem(key)
}

function createChunks(file: File, uploadedIndexes: number[]): UploadChunk[] {
  const chunks: UploadChunk[] = []
  let index = 0
  let start = 0
  while (start < file.size) {
    const end = Math.min(start + CHUNK_SIZE, file.size)
    chunks.push({
      index,
      start,
      end,
      uploaded: uploadedIndexes.includes(index),
      blob: file.slice(start, end),
    })
    index++
    start = end
  }
  return chunks
}

async function uploadChunk(
  uploadUrl: string,
  chunk: UploadChunk,
  file: File,
  onProgress: (chunkIndex: number) => void,
): Promise<void> {
  const formData = new FormData()
  formData.append('chunk', chunk.blob, file.name)
  formData.append('chunkIndex', String(chunk.index))
  formData.append('fileName', file.name)
  formData.append('fileSize', String(file.size))
  formData.append('totalChunks', String(Math.ceil(file.size / CHUNK_SIZE)))

  const response = await fetch(uploadUrl, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Chunk ${chunk.index} upload failed`)
  }

  onProgress(chunk.index)
}

export async function uploadFile(
  file: File,
  uploadUrl: string,
  item: UploadFileItem,
  onProgress: (item: UploadFileItem) => void,
): Promise<{ fileKey: string; fileType: string }> {
  const uploadedIndexes = loadProgress(file)
  const chunks = createChunks(file, uploadedIndexes)
  item.chunks = chunks

  const pendingChunks = chunks.filter((c) => !c.uploaded)
  const completedIndexes = new Set(uploadedIndexes)

  const updateProgress = () => {
    const total = chunks.length
    const completed = completedIndexes.size
    item.progress = Math.round((completed / total) * 100)
    onProgress({ ...item })
  }

  updateProgress()

  const queue = [...pendingChunks]
  const running: Promise<void>[] = []

  const runNext = async (): Promise<void> => {
    const chunk = queue.shift()
    if (!chunk) return

    await uploadChunk(uploadUrl, chunk, file, (chunkIndex) => {
      completedIndexes.add(chunkIndex)
      saveProgress(file, Array.from(completedIndexes))
      updateProgress()
    })

    await runNext()
  }

  for (let i = 0; i < Math.min(MAX_CONCURRENT, queue.length); i++) {
    running.push(runNext())
  }

  await Promise.all(running)
  clearProgress(file)

  const result = await fetch(`${uploadUrl}/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fileName: file.name, fileSize: file.size }),
  })

  if (!result.ok) {
    throw new Error('Upload completion failed')
  }

  const data = await result.json()
  return { fileKey: data.fileKey, fileType: data.fileType }
}