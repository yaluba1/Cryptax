import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { 
        path: '', 
        name: 'main',
        component: () => import('pages/MainPage.vue'),
        meta: { requiresAuth: true }
      },
      { 
        path: 'new', 
        name: 'new-job',
        component: () => import('pages/NewJobPage.vue'),
        meta: { requiresAuth: true }
      },
      { 
        path: 'login', 
        name: 'login',
        component: () => import('pages/AuthPage.vue') 
      },
    ],
  },

  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
];

export default routes;
