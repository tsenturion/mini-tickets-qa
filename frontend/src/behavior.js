import { h } from 'vue'

export function editedList(list, updated) {
  return list.map(ticket => ticket.id === updated.id ? updated : ticket)
}

export const CommentText = {
  props: ['text'],
  setup(props) {
    return () => h('p', { class: 'comment-text', 'data-testid': 'comment-text' }, props.text)
  },
}
