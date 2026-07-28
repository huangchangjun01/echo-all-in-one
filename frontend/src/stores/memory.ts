import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { getList, getDetail, deleteTheme, saveMemory } from '../api/memory'
import type { MemoryTheme, PageResult } from '../types/memory'

export const useMemoryStore = defineStore('memory', () => {
  const list = ref<MemoryTheme[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentDetail = ref<MemoryTheme | null>(null)
  const pagination = reactive({ page: 1, pageSize: 10 })

  async function fetchList(params?: { userId?: string; status?: string }) {
    loading.value = true
    try {
      const res = await getList({
        page: pagination.page,
        pageSize: pagination.pageSize,
        ...params,
      })
      const data = res as unknown as { data: PageResult<MemoryTheme> }
      list.value = data.data.list
      total.value = data.data.total
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(memoryId: string) {
    const res = await getDetail(memoryId)
    const data = res as unknown as { data: MemoryTheme }
    currentDetail.value = data.data
    return currentDetail.value
  }

  async function remove(memoryId: string) {
    await deleteTheme(memoryId)
    list.value = list.value.filter((item) => item.memoryId !== memoryId)
    total.value--
  }

  async function create(data: MemoryTheme) {
    const res = await saveMemory(data)
    const result = res as unknown as { data: MemoryTheme }
    return result.data
  }

  function setPage(page: number) {
    pagination.page = page
  }

  return {
    list,
    total,
    loading,
    currentDetail,
    pagination,
    fetchList,
    fetchDetail,
    remove,
    create,
    setPage,
  }
})