// Light/dark theme, dark by default, remembered in local storage.
// index.html applies the stored theme before the first render to avoid a flash.
import { computed } from 'vue'
import { useTheme } from 'vuetify'

export const THEME_STORAGE_KEY = 'dnsmasq-webmin.theme'

/** The stored theme; dark if nothing (or something invalid) is stored. */
export function storedTheme() {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) === 'light' ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

export function useThemeSwitch() {
  const theme = useTheme()
  const dark = computed(() => theme.global.current.value.dark)

  function setTheme(name) {
    theme.change(name)
    document.documentElement.dataset.theme = name
    try {
      localStorage.setItem(THEME_STORAGE_KEY, name)
    } catch {
      // storage unavailable (private mode): the choice lasts for this page only
    }
  }

  const toggle = () => setTheme(dark.value ? 'light' : 'dark')

  return { dark, toggle }
}
