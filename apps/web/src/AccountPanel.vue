<script setup>
import { onMounted, ref } from 'vue'
import { RefreshCw, Wallet, Check, LoaderCircle } from 'lucide-vue-next'
import { api } from './api.js'
const emit = defineEmits(['updated'])
const account = ref(null), amount = ref(10), busy = ref(false), error = ref(''), notice = ref('')
let pendingKey = '', pendingAmount = 0
const money = n => (n / 100).toFixed(2)
const time = s => s ? new Date(s).toLocaleString('zh-CN') : '—'
async function load() { const { data } = await api('/api/v1/account'); account.value=data; emit('updated',data.user) }
async function refresh() { error.value=''; try { await load() } catch(e) { error.value=e.message } }
onMounted(refresh)
async function create() {
  error.value=''; notice.value=''; busy.value=true
  try {
    const cents=Number(amount.value)*100
    if (!Number.isInteger(cents) || cents<100 || cents>1000000 || cents%100) throw new Error('请输入 1–10,000 的整数元金额。')
    if (!pendingKey || pendingAmount!==cents) { pendingKey=crypto.randomUUID(); pendingAmount=cents }
    await api('/api/v1/recharges',{body:{amountCents:cents,idempotencyKey:pendingKey}})
    await load(); pendingKey=''; notice.value='模拟订单已创建，请在订单列表确认。'
  } catch(e) { error.value=e.message } finally { busy.value=false }
}
async function confirm(id) {
  busy.value=true; error.value=''; notice.value=''
  try { await api(`/api/v1/recharges/${id}/simulate-confirm`,{body:{}}); await load(); notice.value='模拟充值完成，额度已到账。' }
  catch(e) { error.value=e.message } finally { busy.value=false }
}
</script>
<template>
  <section class="account-view">
    <div class="page-heading"><div><h1>我的账户</h1><p>{{ account?.user.username }}</p></div><button class="icon-button" aria-label="刷新账户" title="刷新账户" @click="refresh"><RefreshCw :size="18" /></button></div>
    <p v-if="error" class="error-banner" role="alert">{{ error }}</p><p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <template v-if="account">
      <div class="balance-band"><Wallet :size="26" /><div><span>可用分析额度</span><strong>{{ account.user.credits }} <small>次</small></strong></div><p>每次成功分析消耗 1 次额度；失败自动退回。</p></div>
      <section class="account-section"><h2>模拟充值</h2><p class="simulation-label">演示环境 · 不会产生真实付款</p><form class="inline-form" @submit.prevent="create"><label for="amount">金额（元）</label><input id="amount" type="number" v-model="amount" min="1" max="10000" step="1" required /><span>1 元 = 10 次</span><button class="primary" :disabled="busy"><LoaderCircle v-if="busy" class="spin" :size="16" /><Wallet v-else :size="16" />创建模拟订单</button></form></section>
      <section class="account-section"><h2>充值记录</h2><p v-if="!account.recharges.length" class="muted">暂无充值记录。</p><div v-else class="table-scroll"><table><thead><tr><th>时间 / 订单号</th><th>金额</th><th>额度</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="order in account.recharges" :key="order.id"><td>{{ time(order.createdAt) }}<small>{{ order.id }}</small></td><td>¥{{ money(order.amountCents) }}</td><td>{{ order.credits }} 次</td><td>{{ order.status==='PENDING'?'待模拟确认':'模拟已到账' }}</td><td><button v-if="order.status==='PENDING'" class="quiet" :disabled="busy" @click="confirm(order.id)"><Check :size="15" />确认模拟充值</button><span v-else>—</span></td></tr></tbody></table></div></section>
      <section class="account-section"><h2>最近分析</h2><p v-if="!account.analyses.length" class="muted">暂无分析记录。</p><ul v-else class="analysis-history"><li v-for="run in account.analyses" :key="run.id"><span>{{ time(run.createdAt) }}</span><span>{{ {SUCCEEDED:'已完成 · 消耗 1 次',FAILED:'失败 · 已退回',RESERVED:'处理中 · 预扣 1 次'}[run.status] }}</span></li></ul></section>
    </template>
  </section>
</template>
