<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ScanLine, ArrowRight, Trash2, Download, Copy, Check, FileText, Link2, X, ChevronRight, AlertTriangle, LoaderCircle, Upload, LogOut, Wallet, ShieldCheck } from 'lucide-vue-next'
import { api, countCharacters, validate, sessionToken, setSession } from './api.js'
import AuthPanel from './AuthPanel.vue'
import AccountPanel from './AccountPanel.vue'
import AdminPanel from './AdminPanel.vue'
import { samples } from './samples.js'

const resume = ref(''), jd = ref(''), external = ref(false), templates = ref([]), selectedTemplate = ref('')
const result = ref(null), trace = ref(''), error = ref(''), fields = ref({}), loading = ref(false), tab = ref('match'), selectedEvidence = ref(''), copied = ref(false)
let controller, generation = 0, analyzedInput = ''
const user = ref(null), restoring = ref(!!sessionToken()), view = ref('workbench'), sampleIndex = ref(0), importing = ref(''), importNotice = ref('')
let uploadController, uploadGeneration=0
const snapshot = () => JSON.stringify([resume.value, jd.value, external.value])
const stale = computed(() => result.value && snapshot() !== analyzedInput)
const evidence = computed(() => result.value?.evidence || [])
const modeLabel = computed(() => ({ rules: '规则提取', degraded: '降级提取', llm: '模型提取' }[result.value?.mode] || ''))
onMounted(async () => {
  window.addEventListener('careerlens-session-expired', logout)
  try { templates.value = (await api('/api/v1/job-templates')).data.items } catch { /* Manual JD remains usable. */ }
  try { if (sessionToken()) user.value = (await api('/api/v1/account')).data.user } catch (cause) { if (cause.status===401) setSession(''); else error.value=cause.message } finally { restoring.value=false }
})
onBeforeUnmount(() => { controller?.abort(); uploadController?.abort(); window.removeEventListener('careerlens-session-expired', logout) })
function login(value) { user.value=value; view.value='workbench'; error.value='' }
function logout() { cancel(); uploadGeneration++; uploadController?.abort(); importing.value=''; setSession(''); user.value=null; resume.value='';jd.value='';result.value=null; error.value=''; view.value='workbench'; importNotice.value='' }
async function refreshUser() { try { user.value=(await api('/api/v1/account')).data.user } catch (cause) { error.value=cause.message } }
async function upload(event,target) {
  const file=event.target.files?.[0]; event.target.value=''; if (!file) return
  if (file.size>2097152 || !/\.(txt|md|pdf|docx)$/i.test(file.name)) { error.value='支持 MD、TXT、PDF、DOCX，文件最多 2 MiB。'; return }
  if ((target==='resume'?resume.value:jd.value) && !window.confirm('导入文件会替换当前文本，是否继续？')) return
  uploadController?.abort(); uploadController=new AbortController(); const current=++uploadGeneration
  importing.value=target; error.value=''; importNotice.value=''
  const form=new FormData(); form.append('target',target); form.append('file',file)
  const timer=setTimeout(()=>uploadController?.abort(),15000)
  try {
    const {data}=await api('/api/v1/documents/text',{body:form,signal:uploadController.signal})
    if (current!==uploadGeneration) return
    if(target==='resume') resume.value=data.text; else jd.value=data.text
    importNotice.value=`已导入 ${data.filename}（${data.charCount} 字符），请核对提取文本。`
  } catch(cause) { if(current===uploadGeneration) error.value=cause.name==='AbortError'?'文件解析超时，请重试或粘贴文本。':cause.message }
  finally {clearTimeout(timer);if(current===uploadGeneration) importing.value=''}
}
function sample() {
  if ((resume.value || jd.value) && !window.confirm('载入虚构示例会替换当前材料，是否继续？')) return
  cancel(); result.value = null; error.value = ''; fields.value = {}
  resume.value = samples[sampleIndex.value].resume
  jd.value = samples[sampleIndex.value].jd
}
function chooseTemplate() {
  const item = templates.value.find(x => x.id === selectedTemplate.value)
  if (item && (!jd.value || window.confirm('替换当前岗位要求？'))) jd.value = item.jdText
  selectedTemplate.value = ''
}
function cancel() { generation++; controller?.abort(); loading.value = false }
function clear() {
  if ((resume.value || jd.value) && !window.confirm('清空当前材料和结果？')) return
  cancel(); resume.value = ''; jd.value = ''; result.value = null; fields.value = {}; error.value = ''; trace.value = ''
}
async function analyze() {
  fields.value = validate(resume.value, jd.value); error.value = ''
  if (Object.keys(fields.value).length) return
  cancel(); const current = ++generation; controller = new AbortController(); loading.value = true
  const input = snapshot(); const timeout = setTimeout(() => controller?.abort('timeout'), 48000)
  try {
    const response = await api('/api/v1/analyses', { body: { resumeText: resume.value, jdText: jd.value, options: { useExternalModel: external.value } }, signal: controller.signal })
    if (current !== generation) return
    result.value = response.data; trace.value = response.traceId; analyzedInput = input; tab.value = 'match'; selectedEvidence.value = ''
  } catch (cause) {
    if (current !== generation) return
    error.value = controller.signal.aborted ? '分析超时，材料已保留。请稍后重试。' : cause.message
    trace.value = cause.traceId || ''; for (const item of cause.fields || []) fields.value[item.field] = item.msg
  } finally { clearTimeout(timeout); if (current === generation) { loading.value = false; await refreshUser() } }
}
function locate(ids) {
  selectedEvidence.value = ids?.[0] || ''
  requestAnimationFrame(() => document.getElementById(`evidence-${selectedEvidence.value}`)?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'nearest' }))
}
function download() {
  const url = URL.createObjectURL(new Blob([JSON.stringify({ ...result.value, traceId: trace.value }, null, 2)], { type: 'application/json' }))
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'careerlens-analysis.json'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}
async function copyTrace() { try { await navigator.clipboard.writeText(trace.value); copied.value = true; setTimeout(() => copied.value = false, 1500) } catch { error.value = `请复制追踪号：${trace.value}` } }
</script>

<template>
  <div class="app-shell">
    <header class="topbar"><a href="/" class="brand"><ScanLine :size="26" /><strong>CareerLens</strong><span>简历岗位分析</span></a><nav v-if="user" class="app-nav" aria-label="主导航"><button :class="{active:view==='workbench'}" @click="view='workbench'"><ScanLine :size="16" /><span>工作台</span></button><button :class="{active:view==='account'}" @click="view='account'"><Wallet :size="16" /><span>账户 · {{ user.credits }} 次</span></button><button v-if="user.role==='ADMIN'" :class="{active:view==='admin'}" @click="view='admin'"><ShieldCheck :size="16" /><span>管理后台</span></button><button class="icon-button" title="退出登录" aria-label="退出登录" @click="logout"><LogOut :size="17" /></button></nav><span v-else class="version">v0.2</span></header>
    <main>
      <p v-if="restoring" class="empty-state" role="status">正在恢复会话…</p>
      <AuthPanel v-else-if="!user" @authenticated="login" />
      <AccountPanel v-else-if="view==='account'" @updated="user=$event" />
      <AdminPanel v-else-if="view==='admin' && user.role==='ADMIN'" />
      <template v-else>
      <section class="page-heading"><div><h1>让每一项匹配，都有依据。</h1><p>对照岗位要求，查看简历中的已有证据与待补充项。</p></div><div class="sample-controls"><select v-model="sampleIndex" aria-label="选择虚构简历示例"><option v-for="(s,i) in samples" :key="s.title" :value="i">{{ s.title }}</option></select><button class="quiet" @click="sample"><FileText :size="16" />载入虚构示例</button></div></section>
      <p v-if="importNotice" class="notice" role="status">{{ importNotice }}</p>
      <form @submit.prevent="analyze" novalidate>
        <div class="input-grid">
          <section class="input-section"><div class="field-heading"><label for="resume">简历文本</label><div class="field-tools"><label class="upload-button" :class="{disabled:!!importing}" title="上传 MD、TXT、PDF 或 DOCX"><LoaderCircle v-if="importing==='resume'" class="spin" :size="16" /><Upload v-else :size="16" />上传简历<input type="file" aria-label="上传简历文件" accept=".md,.txt,.pdf,.docx" :disabled="!!importing" @change="upload($event,'resume')" /></label><button type="button" class="icon-button" title="清空所有材料" aria-label="清空所有材料" @click="clear"><Trash2 :size="17" /></button></div></div><textarea id="resume" v-model="resume" placeholder="粘贴教育背景、项目经历和技能…" :aria-invalid="!!fields.resumeText" aria-describedby="resume-help" /><div id="resume-help" class="field-footer"><span class="field-error">{{ fields.resumeText || '材料仅在本次分析中使用' }}</span><span>{{ countCharacters(resume) }} / 20,000</span></div></section>
          <section class="input-section"><div class="field-heading"><label for="jd">岗位 JD</label><div class="field-tools"><select v-model="selectedTemplate" @change="chooseTemplate" aria-label="选择示例岗位"><option value="">示例岗位</option><option v-for="item in templates" :key="item.id" :value="item.id">{{ item.title }}</option></select><label class="upload-button" :class="{disabled:!!importing}" title="上传 MD、TXT、PDF 或 DOCX"><LoaderCircle v-if="importing==='jd'" class="spin" :size="16" /><Upload v-else :size="16" />上传 JD<input type="file" aria-label="上传岗位文件" accept=".md,.txt,.pdf,.docx" :disabled="!!importing" @change="upload($event,'jd')" /></label></div></div><textarea id="jd" v-model="jd" placeholder="粘贴岗位职责、必需技能和加分项…" :aria-invalid="!!fields.jdText" aria-describedby="jd-help" /><div id="jd-help" class="field-footer"><span class="field-error">{{ fields.jdText || '保留具体技能与优先级描述' }}</span><span>{{ countCharacters(jd) }} / 12,000</span></div></section>
        </div>
        <div class="action-bar"><div class="privacy-option"><label><input type="checkbox" v-model="external" />使用外部模型</label><small v-if="external">将向配置的模型发送尽力脱敏后的材料，脱敏可能不完整。</small><small v-else>当前使用本地规则提取，不向外部模型发送材料。</small></div><div class="commands"><button v-if="loading" type="button" class="quiet" @click="cancel"><X :size="16" />取消</button><button class="primary" type="submit" :disabled="loading"><LoaderCircle v-if="loading" :size="18" class="spin" /><ScanLine v-else :size="18" />{{ loading ? '分析中' : '分析匹配' }}<ArrowRight v-if="!loading" :size="17" /></button></div></div>
      </form>
      <div v-if="error" class="error-banner" role="alert"><AlertTriangle :size="19" /><div>{{ error }}<small v-if="trace">追踪号：{{ trace }}</small></div></div>
      <section v-if="!result" class="empty-state"><div class="empty-mark"><FileText :size="28" /><ChevronRight :size="18" /><ScanLine :size="28" /></div><h2>从两份材料开始</h2><p>填写简历和岗位要求，查看技能覆盖与原文依据。</p><span>命中证据 <span class="dot">/</span> 待补充项 <span class="dot">/</span> 结构化简历</span></section>
      <section v-else class="results" aria-live="polite">
        <div v-if="stale" class="stale-banner">材料已修改，以下是上一次分析结果。请重新分析。</div>
        <div class="result-heading"><div><h2>匹配分析</h2><span class="mode">{{ modeLabel }}</span></div><button class="quiet" @click="download"><Download :size="16" />导出 JSON</button></div>
        <div class="score-band"><div class="score-number"><strong>{{ result.score.value ?? '—' }}</strong><span>{{ result.score.value === null ? '暂不评分' : '/ 100' }}</span></div><div class="score-detail"><h3>技能覆盖分</h3><p v-if="result.score.totalWeight">已匹配权重 {{ result.score.matchedWeight }} / {{ result.score.totalWeight }}，必需项 ×3，普通项 ×2，加分项 ×1。</p><p v-else>未识别到可评分的技能要求，请补充具体技术要求。</p><meter min="0" max="100" :value="result.score.value || 0" aria-label="技能覆盖分" /><small>仅衡量材料中的技能证据，不代表录用概率。</small></div><div class="totals"><span><strong>{{ result.matches.length }}</strong> 命中</span><span><strong>{{ result.gaps.length }}</strong> 待补充</span></div></div>
        <div v-for="warning in result.warnings" :key="warning.code" class="warning"><AlertTriangle :size="15" />{{ warning.msg }}</div>
        <div class="view-tabs" role="tablist" aria-label="分析视图"><button v-for="item in [['match','岗位对照'],['resume','结构化简历'],['evidence','全部证据']]" :key="item[0]" role="tab" :aria-selected="tab === item[0]" :class="{active:tab === item[0]}" @click="tab=item[0]">{{ item[1] }}</button></div>
        <div v-if="tab === 'match'" class="comparison-grid">
          <div><h3 class="section-label">岗位要求与覆盖情况</h3><p v-if="!result.requirements.length" class="muted">未识别到词典内的技能要求。</p><article v-for="item in result.requirements" :key="item.skillId" class="requirement"><div class="requirement-title"><strong>{{ item.displayName }}</strong><span class="priority">{{ {required:'必需',preferred:'加分',unspecified:'普通'}[item.priority] }}</span></div><template v-if="result.matches.find(x=>x.skillId===item.skillId)"><span class="matched"><Check :size="15" />简历中已发现证据</span><button class="evidence-link" @click="locate(result.matches.find(x=>x.skillId===item.skillId).resumeEvidenceIds)"><Link2 :size="14" />查看原文</button></template><template v-else><span class="gap">简历中未发现证据</span><p class="suggestion">{{ result.gaps.find(x=>x.skillId===item.skillId)?.suggestion }}</p></template></article></div>
          <aside class="evidence-panel"><h3 class="section-label">简历原文依据</h3><ol><li v-for="line in evidence.filter(x=>x.source==='resume')" :id="`evidence-${line.id}`" :key="line.id" :class="{highlight:selectedEvidence===line.id}"><span>{{ line.id }}</span><p>{{ line.text }}</p></li></ol></aside>
        </div>
        <div v-else-if="tab === 'resume'" class="structured"><section v-for="[key,label] in [['education','教育背景'],['experience','工作经历'],['projects','项目经历']]" :key="key"><h3>{{ label }}</h3><p v-if="!result.structuredResume[key].length" class="muted">材料中未识别到相关信息。</p><article v-for="(entry,index) in result.structuredResume[key]" :key="index"><h4>{{ entry.title || '未命名条目' }}</h4><p>{{ entry.summary }}</p><button class="evidence-link" @click="tab='evidence';selectedEvidence=entry.evidenceIds?.[0]"><Link2 :size="14" />查看证据</button></article></section><section><h3>归一化技能</h3><div class="skills"><span v-for="skill in result.structuredResume.skills" :key="skill.skillId">{{ skill.displayName }}</span></div><p v-for="issue in result.structuredResume.issues" :key="issue.code" class="muted">{{ issue.msg }}</p></section></div>
        <div v-else class="all-evidence"><article v-for="line in evidence" :key="line.id" :class="{highlight:selectedEvidence===line.id}"><span>{{ line.id }} · {{ line.source==='resume'?'简历':'岗位' }}</span><p>{{ line.text }}</p></article></div>
        <footer class="result-footer"><span>{{ result.ruleVersion }} · {{ result.skillDictionaryVersion }}</span><button v-if="trace" class="trace-button" @click="copyTrace" :title="trace"><Check v-if="copied" :size="13" /><Copy v-else :size="13" />{{ copied?'已复制':'复制追踪号' }}</button></footer>
      </section>
      </template>
    </main><footer class="page-footer">CareerLens <span>让经历可见，让差距可行动。</span></footer>
  </div>
</template>
