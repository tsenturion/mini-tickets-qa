<script setup>
import { computed, onMounted, ref } from 'vue'
import { CommentText, editedList } from './behavior'

const token = ref(sessionStorage.getItem('lab-token') || '')
const user = ref(null)
const error = ref('')
const message = ref('')
const busy = ref(false)
const registering = ref(false)
const email = ref('')
const password = ref('')
const tickets = ref([])
const statusFilter = ref('')
const selected = ref(null)
const comments = ref([])
const title = ref('')
const priority = ref('normal')
const editTitle = ref('')
const editPriority = ref('normal')
const nextStatus = ref('active')
const comment = ref('')
const statusLabels = { new: 'Новая', active: 'В работе', closed: 'Закрыта' }
const priorityLabels = { low: 'Низкий', normal: 'Обычный', high: 'Высокий' }
const canEdit = computed(() => selected.value?.author_id === user.value?.id && selected.value?.status === 'new')

// Длину проверяет API в code points: HTML maxlength считает UTF-16 и обрезает emoji.
async function api(path, method = 'GET', body) {
  const response = await fetch(`/api${path}`, {
    method,
    headers: { ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}), ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (response.status === 204) return null
  const payload = await response.json()
  if (!response.ok) {
    if (response.status === 401 && user.value) clearSession()
    const detail = payload.error?.fields?.map(field => field.message).join('; ')
    throw new Error(`${detail || payload.error?.message || 'Ошибка запроса'} (${response.status})`)
  }
  return payload
}

async function action(callback) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  message.value = ''
  try { await callback() } catch (failure) { error.value = failure.message } finally { busy.value = false }
}

function clearSession() {
  token.value = ''
  user.value = null
  tickets.value = []
  selected.value = null
  sessionStorage.removeItem('lab-token')
}

async function loadTickets() {
  tickets.value = await api(`/tickets${statusFilter.value ? `?status=${statusFilter.value}` : ''}`)
}

async function authenticate() {
  if (registering.value) await api('/auth/register', 'POST', { email: email.value, password: password.value })
  const session = await api('/auth/login', 'POST', { email: email.value, password: password.value })
  token.value = session.access_token
  sessionStorage.setItem('lab-token', token.value)
  password.value = ''
  user.value = await api('/auth/me')
  await loadTickets()
}

async function openTicket(ticket) {
  selected.value = await api(`/tickets/${ticket.id}`)
  editTitle.value = selected.value.title
  editPriority.value = selected.value.priority
  comments.value = await api(`/tickets/${ticket.id}/comments`)
  comment.value = ''
}

async function createTicket() {
  const created = await api('/tickets', 'POST', { title: title.value, priority: priority.value })
  title.value = ''
  priority.value = 'normal'
  await loadTickets()
  await openTicket(created)
  message.value = 'Заявка создана'
}

async function updateTicket() {
  const updated = await api(`/tickets/${selected.value.id}`, 'PATCH', { title: editTitle.value, priority: editPriority.value })
  tickets.value = editedList(tickets.value, updated)
  selected.value = updated
  message.value = 'Изменения сохранены'
}

async function deleteTicket() {
  await api(`/tickets/${selected.value.id}`, 'DELETE')
  selected.value = null
  await loadTickets()
  message.value = 'Заявка удалена'
}

async function updateStatus() {
  const updated = await api(`/tickets/${selected.value.id}/status`, 'PUT', { status: nextStatus.value })
  await loadTickets()
  await openTicket(updated)
  message.value = 'Статус изменён'
}

async function sendComment() {
  await api(`/tickets/${selected.value.id}/comments`, 'POST', { text: comment.value })
  comments.value = await api(`/tickets/${selected.value.id}/comments`)
  comment.value = ''
  message.value = 'Комментарий добавлен'
}

onMounted(() => action(async () => {
  if (!token.value) return
  try { user.value = await api('/auth/me'); await loadTickets() } catch (failure) { clearSession(); throw failure }
}))
</script>

<template>
  <div class="min-h-screen">
    <header class="topbar">
      <a class="brand" href="/" aria-label="Мини-заявки, главная"><span class="brand-icon">м</span> мини-заявки<span class="edition">учебный стенд</span></a>
      <div v-if="user" class="account"><span>{{ user.email }} <small>{{ user.role === 'operator' ? 'Оператор' : 'Пользователь' }}</small></span><button class="secondary" :disabled="busy" @click="action(async () => { await api('/auth/logout', 'POST'); clearSession() })">Выйти</button></div>
    </header>
    <main>
      <div v-if="error" role="alert" class="notice error">{{ error }}</div>
      <div v-if="message" role="status" class="notice success">{{ message }}</div>
      <section v-if="!user" class="auth-grid">
        <div class="intro"><p class="eyebrow">Практика тестирования</p><h1>Маленькая система.<br>Настоящие проверки.</h1><p>Заявки, статусы и комментарии.<br>Всё необходимое для работы с интерфейсом, API и данными.</p><div class="intro-note"><span>01</span> Войдите в свою учётную запись<br>или создайте новую.</div></div>
        <form class="panel auth-form" @submit.prevent="action(authenticate)">
          <h2>{{ registering ? 'Регистрация' : 'Вход в систему' }}</h2>
          <p class="muted">{{ registering ? 'Новая запись получит роль пользователя.' : 'Продолжите работу с заявками.' }}</p>
          <label>Email<input v-model="email" type="email" autocomplete="username" required placeholder="name@example.test"></label>
          <label>Пароль<input v-model="password" type="password" :autocomplete="registering ? 'new-password' : 'current-password'" required placeholder="От 8 символов"></label>
          <button class="primary full" :disabled="busy">{{ registering ? 'Зарегистрироваться' : 'Войти' }}</button>
          <button class="text-button" type="button" @click="registering = !registering; error = ''">{{ registering ? 'У меня уже есть аккаунт' : 'Создать аккаунт' }}</button>
        </form>
      </section>
      <section v-else>
        <div class="section-title"><div><p class="eyebrow">Рабочее пространство</p><h1>Заявки <span class="count">{{ tickets.length }}</span></h1></div><label class="filter">Статус<select v-model="statusFilter" @change="action(loadTickets)"><option value="">Все статусы</option><option v-for="(label, key) in statusLabels" :key="key" :value="key">{{ label }}</option></select></label></div>
        <form class="panel create-form" aria-label="Новая заявка" @submit.prevent="action(createTicket)"><label class="grow">Заголовок новой заявки<input v-model="title" required placeholder="Например, не открывается учебный портал"></label><label>Приоритет новой заявки<select v-model="priority"><option v-for="(label, key) in priorityLabels" :key="key" :value="key">{{ label }}</option></select></label><button class="primary" :disabled="busy">Создать заявку</button></form>
        <div class="workspace" :class="{ expanded: selected }">
          <div class="panel table-panel"><table aria-label="Список заявок"><thead><tr><th>Заявка</th><th>Статус</th><th>Приоритет</th></tr></thead><tbody><tr v-for="ticket in tickets" :key="ticket.id" :data-testid="`ticket-${ticket.id}`" :class="{ chosen: selected?.id === ticket.id }"><td><button class="ticket-link" :disabled="busy" @click="action(() => openTicket(ticket))">{{ ticket.title }}</button><small>{{ new Date(ticket.created_at).toLocaleString('ru-RU') }}</small></td><td><span class="badge" :class="ticket.status">{{ statusLabels[ticket.status] }}</span></td><td data-testid="ticket-priority">{{ priorityLabels[ticket.priority] }}</td></tr></tbody></table><div v-if="!tickets.length" class="empty">Заявок пока нет. Создайте первую или измените фильтр.</div></div>
          <aside v-if="selected" class="panel detail" aria-label="Карточка заявки"><div class="detail-heading"><h2>Карточка заявки</h2><button class="secondary" @click="selected = null">Закрыть карточку</button></div><small class="identifier">{{ selected.id }}</small>
            <form @submit.prevent="action(updateTicket)"><label>Заголовок заявки<input v-model="editTitle" :disabled="!canEdit" required></label><label>Приоритет заявки<select v-model="editPriority" aria-label="Приоритет заявки" :disabled="!canEdit"><option v-for="(label, key) in priorityLabels" :key="key" :value="key">{{ label }}</option></select></label><div v-if="canEdit" class="actions"><button class="primary" :disabled="busy">Сохранить изменения</button><button class="danger" type="button" :disabled="busy" @click="action(deleteTicket)">Удалить заявку</button></div></form>
            <form v-if="user.role === 'operator'" class="status-form" @submit.prevent="action(updateStatus)"><label>Новый статус<select v-model="nextStatus"><option v-for="(label, key) in statusLabels" :key="key" :value="key">{{ label }}</option></select></label><button class="secondary" :disabled="busy">Изменить статус</button></form>
            <div class="comments"><h3>Комментарии <span class="muted">{{ comments.length }}</span></h3><p v-if="!comments.length" class="muted">Обсуждение ещё не началось.</p><article v-for="item in comments" :key="item.id" class="comment"><small>{{ item.author_id === user.id ? 'Вы' : item.author_id }} · {{ new Date(item.created_at).toLocaleString('ru-RU') }}</small><CommentText :text="item.text" /></article><form v-if="selected.status !== 'closed'" @submit.prevent="action(sendComment)"><label>Комментарий<textarea v-model="comment" required rows="3" placeholder="Добавьте подробности"></textarea></label><button class="primary" :disabled="busy">Добавить комментарий</button></form><p v-else class="muted">Заявка закрыта. Добавление комментариев недоступно.</p></div>
          </aside>
        </div>
      </section>
    </main>
    <footer>Мини-заявки <span>Учебная среда · Только тестовые данные</span></footer>
  </div>
</template>
