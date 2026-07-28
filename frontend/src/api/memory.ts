import { get, post, del } from './index'
import type { ApiResponse, MemoryTheme, PageResult } from '../types/memory'

export function checkMemoryTheme(params: { user_id: string; role_id: string; theme_name: string }) {
  return get<ApiResponse<{ exists: boolean }>>('/api/memory/check-theme', params)
}

export function applyMemoryId() {
  return post<ApiResponse<{ memory_id: string }>>('/api/memory/apply-id')
}

export function saveMemory(data: {
  user_id: string
  role_id: string
  memory_id: string
  theme_name: string
  subjective_desc?: string
  files: { file_key: string; file_type: string; file_name: string }[]
}) {
  return post<ApiResponse<{ memory_id: string }>>('/api/memory/save', data)
}

export function deleteMemoryFile(memoryId: string, fileId: number) {
  return del<ApiResponse<null>>('/api/memory/file', { params: { memory_id: memoryId, file_id: fileId } })
}

export function deleteMemoryTheme(memoryId: string) {
  return del<ApiResponse<null>>('/api/memory/theme', { params: { memory_id: memoryId } })
}

export function getMemoryList(params: {
  user_id: string
  role_id: string
  page?: number
  page_size?: number
}) {
  return get<ApiResponse<PageResult<MemoryTheme>>>('/api/memory/list', params)
}

export function getMemoryDetail(memoryId: string) {
  return get<ApiResponse<MemoryTheme>>('/api/memory/detail', { memory_id: memoryId })
}

export function getMemoryStatus(memoryId: string) {
  return get<ApiResponse<{ status: string }>>('/api/memory/status', { memory_id: memoryId })
}