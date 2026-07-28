<template>
  <div class="memory-management">
    <div class="page-header">
      <h2>记忆管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>新增记忆
      </el-button>
    </div>

    <MemoryList
      :data="memoryList"
      :loading="loading"
      :total="total"
      :page="page"
      :page-size="pageSize"
      @page-change="handlePageChange"
      @view="handleView"
      @edit="handleEdit"
      @delete="handleDelete"
    />

    <!-- 新增弹窗 -->
    <MemoryCreateDialog
      v-model:visible="showCreateDialog"
      @success="handleCreateSuccess"
    />

    <!-- 查看弹窗 -->
    <MemoryViewDialog
      v-model:visible="showViewDialog"
      :memory-id="viewMemoryId"
    />

    <!-- 编辑弹窗 -->
    <MemoryEditDialog
      v-model:visible="showEditDialog"
      :memory-id="editMemoryId"
      @success="handleEditSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMemoryList, deleteMemoryTheme } from '@/api/memory'
import MemoryList from '@/components/memory/MemoryList.vue'
import MemoryCreateDialog from '@/components/memory/MemoryCreateDialog.vue'
import MemoryViewDialog from '@/components/memory/MemoryViewDialog.vue'
import MemoryEditDialog from '@/components/memory/MemoryEditDialog.vue'
import type { MemoryTheme } from '@/types/memory'

const USER_ID = 'user_001'
const ROLE_ID = 'role_001'

const memoryList = ref<MemoryTheme[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

const showCreateDialog = ref(false)
const showViewDialog = ref(false)
const showEditDialog = ref(false)
const viewMemoryId = ref('')
const editMemoryId = ref('')

const fetchList = async () => {
  loading.value = true
  try {
    const res = await getMemoryList({
      user_id: USER_ID,
      role_id: ROLE_ID,
      page: page.value,
      page_size: pageSize.value,
    })
    memoryList.value = res.data.list || []
    total.value = res.data.total || 0
  } catch (e: any) {
    ElMessage.error(e.message || '获取列表失败')
  } finally {
    loading.value = false
  }
}

const handlePageChange = (p: number, ps: number) => {
  page.value = p
  pageSize.value = ps
  fetchList()
}

const handleView = (row: MemoryTheme) => {
  viewMemoryId.value = row.memory_id
  showViewDialog.value = true
}

const handleEdit = (row: MemoryTheme) => {
  editMemoryId.value = row.memory_id
  showEditDialog.value = true
}

const handleDelete = async (row: MemoryTheme) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除记忆主题"${row.theme_name}"吗？此操作将删除所有关联文件和记忆内容，且不可恢复。`,
      '删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteMemoryTheme(row.memory_id)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '删除失败')
    }
  }
}

const handleCreateSuccess = () => {
  showCreateDialog.value = false
  fetchList()
}

const handleEditSuccess = () => {
  showEditDialog.value = false
  fetchList()
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.memory-management {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}
</style>