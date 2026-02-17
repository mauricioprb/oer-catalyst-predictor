import { ref, watchEffect } from 'vue'

const temaEscuro = ref(
  typeof localStorage !== 'undefined'
    ? localStorage.getItem('tema') === 'dark' ||
      (!localStorage.getItem('tema') &&
        window.matchMedia('(prefers-color-scheme: dark)').matches)
    : false,
)

if (temaEscuro.value) {
  document.documentElement.classList.add('dark')
}

export function useTheme() {
  watchEffect(() => {
    document.documentElement.classList.toggle('dark', temaEscuro.value)
    localStorage.setItem('tema', temaEscuro.value ? 'dark' : 'light')
  })

  function alternarTema() {
    temaEscuro.value = !temaEscuro.value
  }

  return { temaEscuro, alternarTema }
}
