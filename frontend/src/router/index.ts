import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'MemoryManagement',
      component: () => import('../views/MemoryManagement.vue'),
    },
  ],
})

export default router