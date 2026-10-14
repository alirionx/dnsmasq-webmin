import 'vuetify/styles'
import { md3 } from 'vuetify/blueprints'
import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'

const THEME_KEY = 'dnsmasq-webmin.theme'

export function loadThemePreference() {
  try {
    return localStorage.getItem(THEME_KEY)
  } catch {
    return null
  }
}

export function saveThemePreference(name) {
  try {
    localStorage.setItem(THEME_KEY, name)
  } catch {
    // storage unavailable (private mode etc.) - preference is simply not remembered
  }
}

export default createVuetify({
  blueprint: md3,
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } },
  theme: {
    defaultTheme: loadThemePreference() ?? 'system',
    // MD3-style tonal palette around indigo #383b66 with a warm mauve accent
    themes: {
      light: {
        colors: {
          primary: '#383b66',
          secondary: '#5b5f97',
          tertiary: '#8e4a7b',
          background: '#f5f5fb',
          surface: '#ffffff',
          'surface-variant': '#e3e3f1',
          'on-surface-variant': '#45465a',
          'app-bar': '#383b66',
        },
      },
      dark: {
        colors: {
          primary: '#bcc0ff',
          secondary: '#c3c4ec',
          tertiary: '#ffaee4',
          background: '#121319',
          surface: '#1b1c24',
          'surface-variant': '#2e2f3d',
          'on-surface-variant': '#c7c6d9',
          'app-bar': '#262848',
        },
      },
    },
  },
})
