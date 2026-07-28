<template>
  <div class="markdown-editor">
    <v-md-editor
      v-model="content"
      :disabled="disabled"
      height="400px"
      @change="handleChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import VMdEditor from '@kangc/v-md-editor'
import '@kangc/v-md-editor/lib/style/base-editor.css'
import '@kangc/v-md-editor/lib/theme/style/vuepress.css'

const props = defineProps<{
  modelValue: string
  disabled: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
}>()

const content = ref(props.modelValue)

watch(() => props.modelValue, (v) => {
  content.value = v
})

const handleChange = (text: string) => {
  emit('update:modelValue', text)
}
</script>

<style scoped>
.markdown-editor {
  width: 100%;
}
</style>