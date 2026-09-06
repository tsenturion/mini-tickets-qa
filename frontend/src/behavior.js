import { h } from 'vue'

const selected = (import.meta.env.VITE_DEFECTS || 'all').split(',')
const enabled = code => selected.includes('all') || selected.includes(code)

export function editedList(list, updated) {
  if (enabled('D07')) return list
  return list.map(ticket => ticket.id === updated.id ? updated : ticket)
}

export const CommentText = {
  props: ['text'],
  setup(props) {
    return () => enabled('D08')
      ? h('p', { class: 'comment-text', 'data-testid': 'comment-text', innerHTML: props.text })
      : h('p', { class: 'comment-text', 'data-testid': 'comment-text' }, props.text)
  },
}
