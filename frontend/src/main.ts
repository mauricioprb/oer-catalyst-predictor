import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import { definePreset } from '@primeuix/themes'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'

import App from './App.vue'
import router from './router/index'
import './assets/main.css'

const Nanoxus = definePreset(Aura, {
  semantic: {
    primary: {
      50:  '#f0fdf2',
      100: '#ddfbe2',
      200: '#bdf5c7',
      300: '#8beb9f',
      400: '#52d96e',
      500: '#38c649',
      600: '#24a235',
      700: '#1f7f2c',
      800: '#1e6428',
      900: '#1a5323',
      950: '#092e10',
    },
    colorScheme: {
      dark: {
        surface: {
          0:   '#ffffff',
          50:  '#f3f4f6',
          100: '#e5e7eb',
          200: '#d1d5db',
          300: '#9ca3af',
          400: '#6b7280',
          500: '#454c59',
          600: '#363b46',
          700: '#282c34',
          800: '#21242b',
          900: '#1a1d22',
          950: '#363b46',
        },
      },
    },
  },
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Nanoxus,
    options: {
      prefix: 'p',
      darkModeSelector: '.dark',
    },
  },
})
app.use(ToastService)
app.use(ConfirmationService)
app.directive('tooltip', Tooltip)

app.mount('#app')
