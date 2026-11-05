<script setup>
import { onMounted, ref } from 'vue'
import { RefreshCw, Save, SlidersHorizontal, X } from 'lucide-vue-next'
import { api } from './api.js'
const overview=ref(null), users=ref([]), orders=ref([]), percentage=ref(10), error=ref(''), notice=ref(''), busy=ref(false), selected=ref(null), delta=ref(10), reason=ref('')
const money=n=>(n/100).toFixed(2)
async function load() {
  const [a,b,c,d]=await Promise.all([api('/api/v1/admin/overview'),api('/api/v1/admin/users'),api('/api/v1/admin/recharges'),api('/api/v1/admin/settings')])
  overview.value=a.data; users.value=b.data.items; orders.value=c.data.items; percentage.value=d.data.commissionBps/100
}
async function refresh() { error.value=''; try { await load() } catch(e) { error.value=e.message } }
onMounted(refresh)
async function save() {
  busy.value=true; error.value=''; notice.value=''
  try {
    const bps=Math.round(Number(percentage.value)*100)
    if (!Number.isFinite(bps)||bps<0||bps>10000) throw new Error('比例必须为 0–100%。')
    await api('/api/v1/admin/settings',{method:'PUT',body:{commissionBps:bps}}); await load(); notice.value='分成比例已保存，仅影响新订单。'
  } catch(e) { error.value=e.message } finally { busy.value=false }
}
async function adjust() {
  busy.value=true; error.value=''; notice.value=''
  try { await api(`/api/v1/admin/users/${selected.value.id}/quota`,{body:{delta:Number(delta.value),reason:reason.value.trim()}}); await load(); selected.value=null; notice.value='额度已调整，操作原因已记录。' }
  catch(e) { error.value=e.message } finally { busy.value=false }
}
</script>
<template>
  <section class="admin-view"><div class="page-heading"><div><h1>管理后台</h1><p>用户、额度与模拟充值账目</p></div><button class="icon-button" title="刷新后台" aria-label="刷新后台" @click="refresh"><RefreshCw :size="18" /></button></div>
    <p v-if="error" class="error-banner" role="alert">{{ error }}</p><p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <template v-if="overview"><div class="admin-stats"><div><span>用户总数</span><strong>{{ overview.users }}</strong></div><div><span>剩余额度</span><strong>{{ overview.availableCredits }}</strong></div><div><span>成功分析</span><strong>{{ overview.successfulAnalyses }}</strong></div><div><span>模拟充值额</span><strong>¥{{ money(overview.simulatedRevenueCents) }}</strong></div><div><span>模拟平台分成</span><strong>¥{{ money(overview.simulatedFeeCents) }}</strong></div></div>
    <section class="account-section"><h2>平台分成</h2><p class="muted">按订单创建时的比例记录平台分成，不影响用户购买的额度；无真实收款或结算。</p><form class="inline-form" @submit.prevent="save"><label for="commission">分成比例（%）</label><input id="commission" v-model="percentage" type="number" min="0" max="100" step="0.01" required /><button class="quiet" :disabled="busy"><Save :size="16" />保存比例</button></form></section>
    <section class="account-section"><h2>用户与额度 <small>最近 200 个用户</small></h2><div class="table-scroll"><table><thead><tr><th>用户名</th><th>角色</th><th>可用额度</th><th>操作</th></tr></thead><tbody><tr v-for="u in users" :key="u.id"><td>{{ u.username }}</td><td>{{ u.role==='ADMIN'?'管理员':'用户' }}</td><td>{{ u.credits }} 次</td><td><button class="quiet" @click="selected=u;delta=10;reason=''"><SlidersHorizontal :size="15" />调整额度</button></td></tr></tbody></table></div></section>
    <section class="account-section"><h2>模拟充值 <small>最近 200 笔</small></h2><p v-if="!orders.length" class="muted">暂无模拟充值。</p><div v-else class="table-scroll"><table><thead><tr><th>用户 / 订单</th><th>金额</th><th>额度</th><th>分成比例</th><th>平台分成</th><th>状态</th></tr></thead><tbody><tr v-for="o in orders" :key="o.id"><td>{{ o.username }}<small>{{ o.id }}</small></td><td>¥{{ money(o.amountCents) }}</td><td>{{ o.credits }}</td><td>{{ o.commissionBps/100 }}%</td><td>¥{{ money(o.feeCents) }}</td><td>{{ o.status==='PENDING'?'待模拟确认':'模拟已到账' }}</td></tr></tbody></table></div></section></template>
    <div v-if="selected" class="modal-backdrop" @click.self="selected=null"><form class="quota-dialog" role="dialog" aria-modal="true" aria-labelledby="quota-title" @submit.prevent="adjust"><div class="field-heading"><h2 id="quota-title">调整 {{ selected.username }} 的额度</h2><button type="button" class="icon-button" aria-label="关闭额度调整" title="关闭" @click="selected=null"><X :size="18" /></button></div><label for="delta">变动次数（正数增加，负数扣减）</label><input id="delta" v-model="delta" type="number" min="-1000000" max="1000000" step="1" required /><label for="reason">调整原因</label><input id="reason" v-model="reason" maxlength="200" required /><p v-if="error" role="alert" class="auth-error">{{ error }}</p><button class="primary" :disabled="busy"><Save :size="16" />确认调整</button></form></div>
  </section>
</template>
