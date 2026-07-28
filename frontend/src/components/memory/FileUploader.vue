<template>
  <div class="file-uploader">
    <!-- 上传区域 -->
    <el-upload
      ref="uploadRef"
      v-model:file-list="fileList"
      :auto-upload="false"
      :accept="acceptTypes"
      :limit="20"
      multiple
      drag
      :on-change="handleFileChange"
      :on-remove="handleFileRemove"
      :before-upload="() => false"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">
        拖拽文件到此处或 <em>点击上传</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">
          支持文本(.txt/.md/.pdf/.doc/.docx)、音频(.mp3/.wav/.m4a/.aac)、
          视频(.mp4/.mov/.avi/.mkv)、图片(.jpg/.png/.gif/.webp)
        </div>
      </template>
    </el-upload>

    <!-- 文件列表（自定义） -->
    <div class="upload-list" v-if="uploadItems.length > 0">
      <div v-for="item in uploadItems" :key="item.uid" class="upload-item">
        <div class="file-info">
          <el-icon><Document /></el-icon>
          <span class="file-name">{{ item.name }}</span>
          <span class="file-size">{{ formatSize(item.size) }}</span>
        </div>

        <!-- 进度条 -->
        <el-progress
          v-if="item.status === 'uploading'"
          :percentage="item.progress"
          :stroke-width="6"
          style="flex: 1; margin: 0 12px"
        />

        <!-- 状态标签 -->
        <el-tag v-if="item.status === 'success'" type="success" size="small">上传成功</el-tag>
        <el-tag v-else-if="item.status === 'error'" type="danger" size="small">上传失败</el-tag>
        <el-tag v-else-if="item.status === 'pending'" type="info" size="small">等待上传</el-tag>

        <!-- 操作按钮 -->
        <el-button
          v-if="item.status === 'error'"
          type="primary"
          size="small"
          link
          @click="retryUpload(item)"
        >
          重试
        </el-button>
        <el-button
          type="danger"
          size="small"
          link
          @click="removeFile(item)"
        >
          删除
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { UploadFilled, Document } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import type { UploadFileItem } from '@/types/memory'

const props = defineProps<{
  files: UploadFileItem[]
  memoryId: string
  userId: string
  roleId: string
}>()

const emit = defineEmits<{
  (e: 'update:files', v: UploadFileItem[]): void
}>()

const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB
const MAX_CONCURRENT = 5
const LARGE_FILE_THRESHOLD = 500 * 1024 * 1024 // 500MB

const acceptTypes = '.txt,.md,.pdf,.doc,.docx,.mp3,.wav,.m4a,.aac,.mp4,.mov,.avi,.mkv,.jpg,.jpeg,.png,.gif,.webp'
const uploadItems = ref<UploadFileItem[]>([])
const fileList = ref<any[]>([])
const uploadQueue: UploadFileItem[] = []
let activeUploads = 0

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}

const getFileType = (fileName: string): string => {
  const ext = fileName.split('.').pop()?.toLowerCase() || ''
  if (['txt', 'md', 'pdf', 'doc', 'docx'].includes(ext)) return 'text'
  if (['mp3', 'wav', 'm4a', 'aac', 'flac'].includes(ext)) return 'audio'
  if (['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv'].includes(ext)) return 'video'
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'].includes(ext)) return 'image'
  return 'text'
}

const handleFileChange = async (file: any, fileListNew: any[]) => {
  fileList.value = fileListNew

  // 大文件确认
  if (file.size > LARGE_FILE_THRESHOLD) {
    try {
      await ElMessageBox.confirm(
        `文件"${file.name}"大小为 ${formatSize(file.size)}，超过 500MB。上传可能需要较长时间，是否继续？`,
        '大文件提示',
        { confirmButtonText: '继续上传', cancelButtonText: '取消', type: 'warning' }
      )
    } catch {
      fileList.value = fileList.value.filter((f: any) => f.uid !== file.uid)
      return
    }
  }

  const fileType = getFileType(file.name)
  const item: UploadFileItem = {
    uid: file.uid,
    name: file.name,
    size: file.size || 0,
    type: fileType,
    status: 'pending',
    progress: 0,
    fileType,
    rawFile: file.raw,
  }

  uploadItems.value.push(item)
  emit('update:files', [...uploadItems.value])

  // 开始上传
  startUpload(item)
}

const handleFileRemove = (file: any) => {
  const idx = uploadItems.value.findIndex(f => f.uid === file.uid)
  if (idx >= 0) {
    uploadItems.value.splice(idx, 1)
    emit('update:files', [...uploadItems.value])
  }
}

const removeFile = (item: UploadFileItem) => {
  const idx = uploadItems.value.findIndex(f => f.uid === item.uid)
  if (idx >= 0) {
    uploadItems.value.splice(idx, 1)
    fileList.value = fileList.value.filter((f: any) => f.uid !== item.uid)
    emit('update:files', [...uploadItems.value])
  }
}

const startUpload = async (item: UploadFileItem) => {
  if (activeUploads >= MAX_CONCURRENT) {
    uploadQueue.push(item)
    return
  }

  activeUploads++
  item.status = 'uploading'

  try {
    // 模拟分片上传（实际项目中替换为真实的对象存储上传）
    await simulateChunkedUpload(item)
    item.status = 'success'
    item.progress = 100
    item.fileKey = `memory/${props.userId}/${props.roleId}/${props.memoryId}/${item.name}`
  } catch (e: any) {
    item.status = 'error'
    item.error = e.message || '上传失败'
    console.error('上传失败:', item.name, e)
  } finally {
    activeUploads--
    emit('update:files', [...uploadItems.value])
    // 处理队列中的下一个
    processQueue()
  }
}

const simulateChunkedUpload = async (item: UploadFileItem): Promise<void> => {
  const totalChunks = Math.ceil(item.size / CHUNK_SIZE)

  // 检查断点续传
  const saved = localStorage.getItem(`upload_${item.uid}`)
  let startChunk = 0
  if (saved) {
    startChunk = parseInt(saved, 10)
  }

  for (let i = startChunk; i < totalChunks; i++) {
    // 模拟上传延迟
    await new Promise((resolve) => setTimeout(resolve, 200))

    item.progress = Math.round(((i + 1) / totalChunks) * 100)
    emit('update:files', [...uploadItems.value])

    // 保存断点
    localStorage.setItem(`upload_${item.uid}`, String(i + 1))
  }

  // 上传完成，清除断点
  localStorage.removeItem(`upload_${item.uid}`)
}

const retryUpload = async (item: UploadFileItem) => {
  item.status = 'pending'
  item.progress = 0
  startUpload(item)
}

const processQueue = () => {
  if (uploadQueue.length > 0 && activeUploads < MAX_CONCURRENT) {
    const next = uploadQueue.shift()
    if (next) startUpload(next)
  }
}
</script>

<style scoped>
.file-uploader {
  width: 100%;
}
.upload-list {
  margin-top: 12px;
}
.upload-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 8px;
  gap: 8px;
}
.file-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 200px;
}
.file-name {
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 150px;
}
.file-size {
  font-size: 12px;
  color: #909399;
}
</style>