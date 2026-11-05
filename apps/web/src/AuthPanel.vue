<script setup>
import { ref } from 'vue'
import { LogIn, UserPlus, LoaderCircle } from 'lucide-vue-next'
import { api, setSession } from './api.js'
const emit = defineEmits(['authenticated'])
const register = ref(false), username = ref(''), password = ref(''), error = ref(''), busy = ref(false)
async function submit() {
  error.value = ''; busy.value = true
  try {
    if (!/^[A-Za-z0-9_]{3,32}$/.test(username.value) || password.value.length < 10 || new TextEncoder().encode(password.value).length > 72) throw new Error('用户名为 3–32 位字母、数字或下划线；密码至少 10 字符，最多 72 字节。')
    const { data } = await api(`/api/v1/auth/${register.value ? 'register' : 'login'}`, { body: { username: username.value, password: password.value } })
    setSession(data.token); password.value = ''; emit('authenticated', data.user)
  } catch (cause) { error.value = cause.message } finally { busy.value = false }
}
</script>
<template>
  <section class="auth-layout">
    <div class="auth-intro"><h1>CareerLens</h1><p>简历与岗位，逐项对照。</p><div class="auth-preview"><span>简历证据</span><strong>Java · Spring Boot · SQL</strong><span>岗位要求</span><strong>必需技能 / 加分项</strong></div></div>
    <form class="auth-form" @submit.prevent="submit">
      <div class="view-tabs" role="tablist" aria-label="账号入口"><button type="button" role="tab" :aria-selected="!register" :class="{active:!register}" @click="register=false;error=''">登录</button><button type="button" role="tab" :aria-selected="register" :class="{active:register}" @click="register=true;error=''">注册</button></div>
      <h2>{{ register ? '创建账户' : '登录账户' }}</h2>
      <label for="username">用户名</label><input id="username" v-model="username" autocomplete="username" maxlength="32" required />
      <label for="password">密码</label><input id="password" v-model="password" type="password" :autocomplete="register?'new-password':'current-password'" minlength="10" maxlength="72" required />
      <p v-if="register" class="muted">注册赠送 10 次分析额度。</p><p v-if="error" role="alert" class="field-error auth-error">{{ error }}</p>
      <button class="primary" :disabled="busy"><LoaderCircle v-if="busy" class="spin" :size="18" /><UserPlus v-else-if="register" :size="18" /><LogIn v-else :size="18" />{{ register?'注册并登录':'登录' }}</button>
    </form>
  </section>
</template>
