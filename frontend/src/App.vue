<script setup>
// Layout: navigation sidebar (permanent on desktop, toggleable on mobile) and the routed view.
import { BookOpen, FileCode2, Menu, Moon, Sun } from '@lucide/vue'
import { ref } from 'vue'
import { useDisplay } from 'vuetify'
import AppLogo from '@/components/AppLogo.vue'
import ServiceControl from '@/components/ServiceControl.vue'
import { KINDS } from '@/kinds'
import { snackbar } from '@/notify'
import { useThemeSwitch } from '@/theme'

const { dark, toggle } = useThemeSwitch()
const { mdAndUp } = useDisplay()
const drawer = ref(false) // only used on mobile; on desktop the sidebar is permanent

const configNav = Object.entries(KINDS).map(([kind, meta]) => ({ title: meta.title, icon: meta.icon, to: `/${kind}` }))
</script>

<template>
  <v-app>
    <v-app-bar v-if="!mdAndUp" flat border="b" density="comfortable" color="background">
      <v-app-bar-nav-icon :icon="Menu" aria-label="Open navigation" @click="drawer = !drawer" />
      <router-link to="/" class="brand d-flex align-center ga-2" aria-label="Home">
        <AppLogo :size="28" />
        <span class="brand-title">dnsmasq</span>
      </router-link>
    </v-app-bar>

    <v-navigation-drawer
      :model-value="mdAndUp || drawer"
      :permanent="mdAndUp"
      :temporary="!mdAndUp"
      width="248"
      border="0"
      class="sidebar"
      aria-label="Main navigation"
      @update:model-value="(open) => (drawer = open)"
    >
      <router-link to="/" class="brand d-flex align-center ga-3 px-5 pt-6 pb-8" aria-label="Home">
        <AppLogo :size="38" />
        <div>
          <div class="brand-title">dnsmasq</div>
          <div class="brand-subtitle">webmin · DNS &amp; DHCP</div>
        </div>
      </router-link>

      <v-list nav density="comfortable" class="px-3">
        <v-list-subheader class="nav-heading">Configuration</v-list-subheader>
        <v-list-item
          v-for="item in configNav"
          :key="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
          :to="item.to"
          rounded="lg"
        />
        <v-list-item :prepend-icon="FileCode2" title="Rendered config" to="/preview" rounded="lg" />

        <v-list-subheader class="nav-heading mt-4">Developer</v-list-subheader>
        <v-list-item :prepend-icon="BookOpen" title="API docs" href="/docs" target="_blank" rel="noopener" rounded="lg" />
      </v-list>

      <template #append>
        <ServiceControl />
        <v-list nav density="comfortable" class="px-3 pb-4">
          <v-list-item
            :prepend-icon="dark ? Sun : Moon"
            :title="dark ? 'Light mode' : 'Dark mode'"
            :aria-label="dark ? 'Switch to light theme' : 'Switch to dark theme'"
            role="button"
            rounded="lg"
            @click="toggle"
          />
        </v-list>
      </template>
    </v-navigation-drawer>

    <v-main>
      <router-view />
    </v-main>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3500" location="bottom right">
      {{ snackbar.text }}
    </v-snackbar>
  </v-app>
</template>

<style scoped>
.sidebar {
  background: rgb(var(--v-theme-background)) !important;
}
.brand {
  text-decoration: none;
  color: inherit;
}
.brand-title {
  font-weight: 800;
  font-size: 1.15rem;
  line-height: 1.1;
}
.brand-subtitle {
  font-size: 0.75rem;
  opacity: 0.75;
}
.sidebar :deep(.v-list-item--active) {
  background: rgb(var(--v-theme-surface-variant));
  color: rgb(var(--v-theme-on-surface));
}
.sidebar :deep(.v-list-item--active .v-list-item__overlay) {
  opacity: 0;
}
.sidebar :deep(.v-list-item--active .v-icon) {
  color: rgb(var(--v-theme-primary));
}
</style>
