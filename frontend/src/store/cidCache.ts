import { defineStore } from 'pinia'
import { reactive } from 'vue'

export const useCidCacheStore = defineStore('cidCache', () => {
  const names = reactive<Record<string, string>>({})

  function set(cid: string, name: string) {
    names[cid] = name
  }

  function get(cid: string): string | undefined {
    return names[cid]
  }

  return { names, set, get }
})
