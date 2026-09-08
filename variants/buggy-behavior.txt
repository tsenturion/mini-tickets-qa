/** Шаблон учебных UI-дефектов; копируется только в buggy, в fixed не исполняется. */
import { h } from 'vue'

const selected = (import.meta.env.VITE_DEFECTS || 'all').split(',')
/** Выбрать один дефект на этапе сборки, чтобы причинность падения теста была однозначной. */
const enabled = code => selected.includes('all') || selected.includes(code)

/** D07 оставляет устаревшую строку; перезагрузка страницы скрыла бы ошибку от UI-теста. */
export function editedList(list, updated) {
  if (enabled('D07')) return list
  return list.map(ticket => ticket.id === updated.id ? updated : ticket)
}

/** D08 намеренно демонстрирует различие текстового вывода и интерпретации недоверенного HTML. */
export const CommentText = {
  props: ['text'],
  /** Вернуть рендер выбранного варианта; проверка должна искать DOM-элемент, а не только HTTP-ответ. */
  setup(props) {
    return () => enabled('D08')
      ? h('p', { class: 'comment-text', 'data-testid': 'comment-text', innerHTML: props.text })
      : h('p', { class: 'comment-text', 'data-testid': 'comment-text' }, props.text)
  },
}
