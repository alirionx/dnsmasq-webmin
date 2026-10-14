import { createRouter, createWebHistory } from 'vue-router'

// views are loaded on demand to keep the initial bundle small
const ConfigFilesView = () => import('@/views/ConfigFilesView.vue')
const RenderView = () => import('@/views/RenderView.vue')

const filesRoute = (kind) => ({
  path: `/${kind}/:name?`,
  name: kind,
  component: ConfigFilesView,
  props: (route) => ({ kind, name: route.params.name }),
})

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dns' },
    filesRoute('dns'),
    filesRoute('dhcp'),
    { path: '/preview', name: 'preview', component: RenderView },
    { path: '/:pathMatch(.*)*', redirect: '/dns' },
  ],
})
