let container: HTMLDivElement | null = null
let toastId = 0

function getContainer(): HTMLDivElement {
  if (!container) {
    container = document.createElement('div')
    container.className = 'toast-container'
    document.body.appendChild(container)
  }
  return container
}

export function showToast(message: string, type: 'success' | 'error' | 'info' = 'info', duration = 2500) {
  const id = ++toastId
  const el = document.createElement('div')
  el.className = `toast-item toast-${type}`
  el.id = `toast-${id}`

  const iconMap = { success: '✅', error: '❌', info: 'ℹ️' }
  el.innerHTML = `<span class="toast-icon">${iconMap[type]}</span><span class="toast-text">${message}</span>`

  const c = getContainer()
  c.appendChild(el)

  requestAnimationFrame(() => el.classList.add('toast-enter'))

  setTimeout(() => {
    el.classList.remove('toast-enter')
    el.classList.add('toast-leave')
    setTimeout(() => {
      if (el.parentNode) el.parentNode.removeChild(el)
    }, 300)
  }, duration)
}
