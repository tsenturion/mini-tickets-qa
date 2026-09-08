/** Исправленное поведение UI: тесты сравнивают список после PATCH и безопасный вывод текста. */
import { h } from 'vue'

/** Заменить только изменённую заявку; соседние строки и их порядок должны сохраниться. */
export function editedList(list, updated) {
  return list.map(ticket => ticket.id === updated.id ? updated : ticket)
}

/** Вывести комментарий текстовым узлом: строка с HTML не должна создавать элементы DOM. */
export const CommentText = {
  props: ['text'],
  /** Связать реактивный текст с рендером; после нового комментария тест не перезагружает страницу. */
  setup(props) {
    // Третий аргумент h — текст, а не innerHTML: здесь проходит граница защиты от XSS.
    return () => h('p', { class: 'comment-text', 'data-testid': 'comment-text' }, props.text)
  },
}
