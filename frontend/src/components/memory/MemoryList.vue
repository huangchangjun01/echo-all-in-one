<template>
  <div class="memory-list">
    <el-table :data="data" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="themeName" label="记忆主题" min-width="200" />
      <el-table-column prop="fileCount" label="文件数量" width="100" align="center" />
      <el-table-column prop="status" label="状态" width="120" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'processing'" type="warning">解析中</el-tag>
          <el-tag v-else-if="row.status === 'completed'" type="success">已完成</el-tag>
          <el-tag v-else-if="row.status === 'editing'" type="info">编辑中</el-tag>
          <el-tag v-else>{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="创建时间" width="180" />
      <el-table-column label="操作" width="240" align="center" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" link @click="$emit('view', row)">查看</el-button>
          <el-button type="warning" size="small" link @click="$emit('edit', row)">编辑</el-button>
          <el-button type="danger" size="small" link @click="$emit('delete', row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="currentPageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="handlePageChange"
        @size-change="handlePageChange"
      />
    </div>

    <el-empty v-if="!loading && data.length === 0" description="暂无记忆数据" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { MemoryTheme } from '@/types/memory'

const props = defineProps<{
  data: MemoryTheme[]
  loading: boolean
  total: number
  page: number
  pageSize: number
}>()

const emit = defineEmits<{
  (e: 'page-change', page: number, pageSize: number): void
  (e: 'view', row: MemoryTheme): void
  (e: 'edit', row: MemoryTheme): void
  (e: 'delete', row: MemoryTheme): void
}>()

const currentPage = ref(props.page)
const currentPageSize = ref(props.pageSize)

watch(() => props.page, (v) => { currentPage.value = v })
watch(() => props.pageSize, (v) => { currentPageSize.value = v })

const handlePageChange = () => {
  emit('page-change', currentPage.value, currentPageSize.value)
}
</script>

<style scoped>
.memory-list {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
}
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>