import { get, post, del } from './index'
import type { ApiResponse, MemoryTheme, PageResult } from '../types/memory'

export function checkTheme(userId: string, roleId: string, themeName: string) {
  return get<ApiResponse<MemoryTheme | null>>('/api/memory/check-theme', { userId, roleId, themeName })
}

export function applyMemoryId() {
  return post<ApiResponse<string>>('/api/memory/apply-id')
}

export function saveMemory(data: MemoryTheme) {
  return post<ApiResponse<MemoryTheme>>('/api/memory/save', data)
}

export function deleteFile(memoryId: string, fileId: number) {
  return del<ApiResponse<void>>(`/api/memory/${memoryId}/file/${fileId}`)
}

export function deleteTheme(memoryId: string) {
  return del<ApiResponse<void>>(`/api/memory/${memoryId}`)
}

export function getList(params: { page?: number; pageSize?: number; userId?: string; status?: string }) {
  return get<ApiResponse<PageResult<MemoryTheme>>>('/api/memory/list', params)
}

export function getDetail(memoryId: string) {
  return get<ApiResponse<MemoryTheme>>(`/api/memory/${memoryId}`)
}

export function getStatus(memoryId: string) {
  return get<ApiResponse<Pick<MemoryTheme, 'status'>>>('/api/memory/status', { memoryId })
}