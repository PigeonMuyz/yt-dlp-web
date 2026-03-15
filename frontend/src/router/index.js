import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/setup',
    name: 'Setup',
    component: () => import('../views/Setup.vue'),
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
  },
  {
    path: '/download',
    name: 'Download',
    component: () => import('../views/Download.vue'),
  },
  {
    path: '/subscriptions',
    name: 'Subscriptions',
    component: () => import('../views/Subscriptions.vue'),
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('../views/Tasks.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
