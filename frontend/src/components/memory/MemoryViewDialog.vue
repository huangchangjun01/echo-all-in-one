<template>
  <el-dialog
    v-model="dialogVisible"
    title="查看记忆"
    width="700px"
    :close-on-click-modal="false"
  >
    <div v-loading="loading">
      <template v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="记忆主题">{{ detail.themeName }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType">{{ statusText }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detail.createdAt }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ detail.updatedAt }}</el-descriptions-item>
          <el-descriptions-item label="主观描述" :span="2">
            {{ detail.subjectiveDesc || '无' }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 记忆源文件列表 -->
        <div class="section-title">记忆源文件</div>
        <div class="file-list">
          <div v-for="file in detail.files" :key="file.id" class="file-item">
            <el-icon><Document /></el-icon>
            <span>{{ file.fileName }}</span>
            <el-tag size="small" type="info">{{ file.fileType }}</el-tag>
            <el-button type="primary" size="small" link @click="downloadFile(file)">
              下载
            </el-button>
          </div>
          <el-empty v-if="!detail.files || detail.files.length === 0" description="无源文件" />
        </div>

        <!-- 记忆内容文件 -->
        <div class="section-title">记忆内容文件</div>
        <div class="file-item">
          <el-icon><Document /></el-icon>
          <span>{{ detail.memoryId }}.md</span>
          <el-button type="primary" size="small" link @click="downloadMd">
            下载
          </el-button>
        </div>
      </template>
    </div>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDetail } from '@/api/memory'
import type { MemoryTheme, MemoryFile } from '@/types/memory'

const props = defineProps<{
  visible: boolean
  memoryId: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v),
})

const detail = ref<MemoryTheme | null>(null)
const loading = ref(false)

const statusType = computed(() => {
  if (detail.value?.status === 'completed') return 'success'
  if (detail.value?.status === 'processing') return 'warning'
  return 'info'
})

const statusText = computed(() => {
  const map: Record<string, string> = {
    processing: '解析中',
    completed: '已完成',
    editing: '编辑中',
  }
  return map[detail.value?.status || ''] || detail.value?.status || ''
})

const fetchDetail = async () => {
  if (!props.memoryId) return
  loading.value = true
  try {
    const res = await getDetail(props.memoryId)
    detail.value = res.data
  } catch {
    detail.value = null
  } finally {
    loading.value = false
  }
}

const downloadFile = (file: MemoryFile) => {
  ElMessage.info(`下载文件: ${file.fileName}`)
}

const downloadMd = () => {
  if (detail.value) {
    ElMessage.info(`下载: ${detail.value.memoryId}.md`)
  }
}

watch(() => props.visible, (v) => {
  if (v) fetchDetail()
})
</script>

<style scoped>
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 16px 0 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}
.file-list {
  margin-bottom: 12px;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 6px;
}
</style>