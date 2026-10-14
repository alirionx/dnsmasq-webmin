<script setup>
import { mdiApi, mdiFileEyeOutline, mdiThemeLightDark } from '@mdi/js'
import { ref } from 'vue'
import { useTheme } from 'vuetify'
import ServiceControl from '@/components/ServiceControl.vue'
import { KINDS } from '@/kinds'
import { snackbar } from '@/notify'
import { saveThemePreference } from '@/plugins/vuetify'

const theme = useTheme()
const drawer = ref(null) // null: open on desktop, closed on mobile

const nav = [
  ...Object.entries(KINDS).map(([kind, meta]) => ({ title: meta.title, icon: meta.icon, to: `/${kind}` })),
  { title: 'Rendered config', icon: mdiFileEyeOutline, to: '/preview' },
]

function toggleTheme() {
  theme.toggle()
  saveThemePreference(theme.global.name.value)
}
</script>

<template>
  <v-app>
    <v-app-bar flat color="app-bar">
      <v-app-bar-nav-icon @click="drawer = !drawer" />
      <v-app-bar-title class="font-weight-medium">dnsmasq-webmin</v-app-bar-title>
      <template #append>
        <ServiceControl />
        <v-btn :icon="mdiApi" href="/docs" target="_blank" title="API docs" />
        <v-btn :icon="mdiThemeLightDark" title="Toggle theme" @click="toggleTheme" />
      </template>
    </v-app-bar>

    <v-navigation-drawer v-model="drawer">
      <v-list nav color="secondary">
        <v-list-item
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
          rounded="xl"
        />
      </v-list>
    </v-navigation-drawer>

    <v-main>
      <router-view />
    </v-main>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3500" location="bottom right">
      {{ snackbar.text }}
    </v-snackbar>
  </v-app>
</template>
