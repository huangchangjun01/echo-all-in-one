<template>
  <el-dialog
    v-model="dialogVisible"
    title="新增记忆"
    width="700px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <!-- 记忆主题 -->
      <el-form-item label="记忆主题" prop="themeName">
        <el-input
          v-model="form.themeName"
          placeholder="请填写完整的时间+地点+人物+事件，例如：2024年3月15日在京都与Agent一起赏樱花"
          maxlength="100"
          show-word-limit
          @blur="checkThemeUnique"
        />
        <div v-if="themeExists" class="error-tip">该记忆主题已存在，请更换名称</div>
      </el-form-item>

      <!-- 记忆源文件 -->
      <el-form-item label="记忆源文件" prop="files" required>
        <FileUploader
          v-model:files="uploadFiles"
          :memory-id="memoryId"
          :user-id="userId"
          :role-id="roleId"
        />
      </el-form-item>

      <!-- 主观描述 -->
      <el-form-item label="主观描述">
        <el-input
          v-model="form.subjectiveDesc"
          type="textarea"
          :rows="4"
          placeholder="请输入对这段记忆的主观描述（选填）"
          maxlength="1000"
          show-word-limit
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { applyMemoryId, checkTheme, saveMemory } from '@/api/memory'
import FileUploader from './FileUploader.vue'
import type { UploadFileItem, MemoryFile } from '@/types/memory'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'success'): void
}>()

const userId = 'user_001'
const roleId = 'role_001'

const dialogVisible = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v),
})

const formRef = ref()
const form = ref({
  themeName: '',
  subjectiveDesc: '',
})
const uploadFiles = ref<UploadFileItem[]>([])
const memoryId = ref('')
const themeExists = ref(false)
const submitting = ref(false)

const rules = {
  themeName: [
    { required: true, message: '请输入记忆主题', trigger: 'blur' },
    { min: 4, message: '主题名称至少4个字符', trigger: 'blur' },
  ],
}

// 校验主题唯一性
const checkThemeUnique = async () => {
  if (!form.value.themeName.trim()) {
    themeExists.value = false
    return
  }
  try {
    const res = await checkTheme(userId, roleId, form.value.themeName.trim())
    themeExists.value = res.data !== null
  } catch {
    themeExists.value = false
  }
}

// 获取 memoryId
const fetchMemoryId = async () => {
  try {
    const res = await applyMemoryId()
    memoryId.value = res.data || ''
  } catch (e: any) {
    ElMessage.error('获取记忆ID失败: ' + (e.message || '未知错误'))
  }
}

// 提交
const handleSubmit = async () => {
  if (themeExists.value) {
    ElMessage.warning('记忆主题已存在，请更换名称')
    return
  }

  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  // 检查是否有文件
  if (uploadFiles.value.length === 0) {
    ElMessage.warning('请至少上传一个记忆源文件')
    return
  }

  // 检查所有文件是否上传成功
  const failedFiles = uploadFiles.value.filter(f => f.status !== 'success')
  if (failedFiles.length > 0) {
    ElMessage.warning(`还有 ${failedFiles.length} 个文件未上传成功，请等待上传完成或重试`)
    return
  }

  submitting.value = true
  try {
    const files: MemoryFile[] = uploadFiles.value.map(f => ({
      fileKey: f.fileKey || '',
      fileType: (f.fileType || 'text') as MemoryFile['fileType'],
      fileName: f.name,
      fileSize: f.size,
    }))

    await saveMemory({
      userId: userId,
      roleId: roleId,
      memoryId: memoryId.value,
      themeName: form.value.themeName.trim(),
      subjectiveDesc: form.value.subjectiveDesc.trim(),
      status: 'processing',
      files: files,
    })
    ElMessage.success('记忆创建成功')
    emit('success')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

const handleClose = () => {
  form.value = { themeName: '', subjectiveDesc: '' }
  uploadFiles.value = []
  themeExists.value = false
}

// 弹窗打开时获取 memoryId
watch(() => props.visible, (v) => {
  if (v) {
    fetchMemoryId()
  }
})
</script>

<style scoped>
.error-tip {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 4px;
}
</style>