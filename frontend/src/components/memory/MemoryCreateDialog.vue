<template>
  <el-dialog
    v-model="dialogVisible"
    title="新增记忆"
    width="700px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
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

      <el-form-item label="记忆源文件" required>
        <FileUploader
          v-model:files="uploadFiles"
          :memory-id="memoryId"
          :user-id="userId"
          :role-id="roleId"
        />
      </el-form-item>

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
      <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { applyMemoryId, checkMemoryTheme, saveMemory } from '@/api/memory'
import FileUploader from './FileUploader.vue'
import type { UploadFileItem } from '@/types/memory'

const props = defineProps<{ visible: boolean }>()

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
const form = ref({ themeName: '', subjectiveDesc: '' })
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

const checkThemeUnique = async () => {
  if (!form.value.themeName.trim()) { themeExists.value = false; return }
  try {
    const res = await checkMemoryTheme({
      user_id: userId,
      role_id: roleId,
      theme_name: form.value.themeName.trim(),
    })
    themeExists.value = res.data?.exists || false
  } catch { themeExists.value = false }
}

const fetchMemoryId = async () => {
  try {
    const res = await applyMemoryId()
    memoryId.value = res.data?.memory_id || ''
  } catch (e: any) {
    ElMessage.error('获取记忆ID失败: ' + (e.message || '未知错误'))
  }
}

const handleSubmit = async () => {
  if (themeExists.value) { ElMessage.warning('记忆主题已存在，请更换名称'); return }
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  if (uploadFiles.value.length === 0) { ElMessage.warning('请至少上传一个记忆源文件'); return }

  const failed = uploadFiles.value.filter(f => f.status !== 'success')
  if (failed.length > 0) {
    ElMessage.warning(`还有 ${failed.length} 个文件未上传成功`)
    return
  }

  submitting.value = true
  try {
    await saveMemory({
      user_id: userId,
      role_id: roleId,
      memory_id: memoryId.value,
      theme_name: form.value.themeName.trim(),
      subjective_desc: form.value.subjectiveDesc.trim(),
      files: uploadFiles.value.map(f => ({
        file_key: f.fileKey || '',
        file_type: f.fileType || 'text',
        file_name: f.name,
      })),
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

watch(() => props.visible, (v) => { if (v) fetchMemoryId() })
</script>

<style scoped>
.error-tip { color: #f56c6c; font-size: 12px; margin-top: 4px; }
</style>