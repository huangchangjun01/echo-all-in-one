<template>
  <el-dialog
    v-model="dialogVisible"
    title="编辑记忆"
    width="750px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div v-loading="loading">
      <template v-if="detail">
        <!-- 记忆主题（只读） -->
        <el-form label-width="100px">
          <el-form-item label="记忆主题">
            <el-input :model-value="detail.themeName" disabled />
          </el-form-item>

          <!-- 主观描述 -->
          <el-form-item label="主观描述">
            <el-input
              v-model="editForm.subjectiveDesc"
              type="textarea"
              :rows="3"
              maxlength="1000"
              show-word-limit
            />
          </el-form-item>

          <!-- 现有源文件 -->
          <el-form-item label="现有源文件">
            <div class="file-list">
              <div v-for="file in existingFiles" :key="file.id" class="file-item">
                <el-icon><Document /></el-icon>
                <span>{{ file.fileName }}</span>
                <el-tag size="small" type="info">{{ file.fileType }}</el-tag>
                <el-button type="primary" size="small" link @click="downloadFile(file)">下载</el-button>
                <el-button type="danger" size="small" link @click="removeExistingFile(file)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </el-form-item>

          <!-- 新增文件 -->
          <el-form-item label="新增文件">
            <FileUploader
              v-model:files="newFiles"
              :memory-id="detail.memoryId"
              :user-id="detail.userId"
              :role-id="detail.roleId"
            />
          </el-form-item>

          <!-- 记忆内容编辑 -->
          <el-form-item label="记忆内容">
            <div v-if="aiEditing" class="ai-editing-tip">
              <el-alert type="warning" :closable="false" show-icon>
                AI 正在处理该记忆，请稍后再试
              </el-alert>
            </div>
            <MarkdownEditor
              v-else
              v-model="editForm.mdContent"
              :disabled="aiEditing"
            />
          </el-form-item>
        </el-form>
      </template>
    </div>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="aiEditing" @click="handleSave">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Document, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDetail, getStatus, saveMemory, deleteFile } from '@/api/memory'
import FileUploader from './FileUploader.vue'
import MarkdownEditor from './MarkdownEditor.vue'
import type { MemoryTheme, UploadFileItem, MemoryFile } from '@/types/memory'

const props = defineProps<{
  visible: boolean
  memoryId: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'success'): void
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v),
})

const detail = ref<MemoryTheme | null>(null)
const loading = ref(false)
const saving = ref(false)
const aiEditing = ref(false)
const existingFiles = ref<MemoryFile[]>([])
const newFiles = ref<UploadFileItem[]>([])
const deletedFileIds = ref<number[]>([])

const editForm = ref({
  subjectiveDesc: '',
  mdContent: '',
})

const fetchDetail = async () => {
  if (!props.memoryId) return
  loading.value = true
  try {
    const [detailRes, statusRes] = await Promise.all([
      getDetail(props.memoryId),
      getStatus(props.memoryId),
    ])
    detail.value = detailRes.data
    editForm.value.subjectiveDesc = detailRes.data?.subjectiveDesc || ''
    editForm.value.mdContent = '' // 从对象存储获取
    existingFiles.value = detailRes.data?.files || []
    aiEditing.value = statusRes.data?.status === 'editing'
  } catch {
    detail.value = null
  } finally {
    loading.value = false
  }
}

const removeExistingFile = async (file: MemoryFile) => {
  try {
    await ElMessageBox.confirm(`确定删除文件"${file.fileName}"吗？`, '删除确认', {
      type: 'warning',
    })
    if (file.id !== undefined) {
      await deleteFile(props.memoryId, file.id)
      deletedFileIds.value.push(file.id)
    }
    existingFiles.value = existingFiles.value.filter(f => f.id !== file.id)
    ElMessage.success('文件已删除')
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '删除失败')
    }
  }
}

const downloadFile = (file: MemoryFile) => {
  ElMessage.info(`下载文件: ${file.fileName}`)
}

const handleSave = async () => {
  // 检查新增文件是否全部上传成功
  const failed = newFiles.value.filter(f => f.status !== 'success')
  if (failed.length > 0) {
    ElMessage.warning('还有文件未上传成功')
    return
  }

  // 如果编辑了 md 内容，二次确认
  if (editForm.value.mdContent) {
    try {
      await ElMessageBox.confirm('确定要保存对记忆内容的修改吗？修改后将覆盖原有内容。', '保存确认', {
        type: 'warning',
      })
    } catch {
      return
    }
  }

  saving.value = true
  try {
    // 判断是否有实质性变更
    const hasChanges = deletedFileIds.value.length > 0
      || newFiles.value.length > 0
      || editForm.value.subjectiveDesc !== detail.value?.subjectiveDesc

    if (hasChanges && detail.value) {
      // 如果有变更，调用保存接口触发重新解析
      const newMemoryFiles: MemoryFile[] = newFiles.value.map(f => ({
        fileKey: f.fileKey || '',
        fileType: (f.fileType || 'text') as MemoryFile['fileType'],
        fileName: f.name,
        fileSize: f.size,
      }))

      await saveMemory({
        userId: detail.value.userId,
        roleId: detail.value.roleId,
        memoryId: props.memoryId,
        themeName: detail.value.themeName,
        subjectiveDesc: editForm.value.subjectiveDesc,
        status: 'processing',
        files: [...existingFiles.value, ...newMemoryFiles],
      })
    }

    ElMessage.success('保存成功')
    emit('success')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleClose = () => {
  detail.value = null
  existingFiles.value = []
  newFiles.value = []
  deletedFileIds.value = []
  editForm.value = { subjectiveDesc: '', mdContent: '' }
}

watch(() => props.visible, (v) => {
  if (v) fetchDetail()
})
</script>

<style scoped>
.file-list {
  margin-bottom: 8px;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 6px;
}
.ai-editing-tip {
  width: 100%;
}
</style>