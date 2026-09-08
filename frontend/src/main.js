/** Единая точка входа SPA; все архитектуры используют одинаковый интерфейс и локаторы. */
import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
createApp(App).mount('#app')
