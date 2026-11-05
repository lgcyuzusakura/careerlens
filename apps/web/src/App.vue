<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ScanLine, ArrowRight, Trash2, Download, Copy, Check, FileText, Link2, X, ChevronRight, AlertTriangle, LoaderCircle } from 'lucide-vue-next'
import { api, countCharacters, validate } from './api.js'

const resume = ref(''), jd = ref(''), external = ref(false), templates = ref([]), selectedTemplate = ref('')
const result = ref(null), trace = ref(''), error = ref(''), fields = ref({}), loading = ref(false), tab = ref('match'), selectedEvidence = ref(''), copied = ref(false)
let controller, generation = 0, analyzedInput = ''
const snapshot = () => JSON.stringify([resume.value, jd.value, external.value])
const stale = computed(() => result.value && snapshot() !== analyzedInput)
const evidence = computed(() => result.value?.evidence || [])
const modeLabel = computed(() => ({ rules: '规则提取', degraded: '降级提取', llm: '模型提取' }[result.value?.mode] || ''))
onMounted(async () => { try { templates.value = (await api('/api/v1/job-templates')).data.items } catch { /* Manual JD remains usable. */ } })
onBeforeUnmount(() => controller?.abort())
function sample() {
  if ((resume.value || jd.value) && !window.confirm('载入虚构示例会替换当前材料，是否继续？')) return
  cancel(); result.value = null; error.value = ''; fields.value = {}
  resume.value = '教育背景\n某示例大学 计算机科学 本科\n项目经历\n课程管理平台：使用 Java、Spring Boot 和 MySQL 实现 REST API，使用 JUnit 编写单元测试。\n技能\n熟悉 Java、SQL、Git 和 Vue 3，使用 Docker 部署课程项目。'
  jd.value = 'Java 校招开发（虚构示例）\n必须熟悉 Java、Spring Boot 和 SQL。\n掌握 Redis，了解 Git；Docker 和 Kubernetes 经验优先。'
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
  const input = snapshot(); const timeout = setTimeout(() => controller?.abort('timeout'), 25000)
  try {
    const response = await api('/api/v1/analyses', { body: { resumeText: resume.value, jdText: jd.value, options: { useExternalModel: external.value } }, signal: controller.signal })
    if (current !== generation) return
    result.value = response.data; trace.value = response.traceId; analyzedInput = input; tab.value = 'match'; selectedEvidence.value = ''
  } catch (cause) {
    if (current !== generation) return
    error.value = controller.signal.aborted ? '分析超时，材料已保留。请稍后重试。' : cause.message
    trace.value = cause.traceId || ''; for (const item of cause.fields || []) fields.value[item.field] = item.msg
  } finally { clearTimeout(timeout); if (current === generation) loading.value = false }
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
    <header class="topbar"><a href="/" class="brand"><ScanLine :size="26" /><strong>CareerLens</strong><span>简历岗位分析</span></a><span class="version">v0.1</span></header>
    <main>
      <section class="page-heading"><div><h1>让每一项匹配，都有依据。</h1><p>对照岗位要求，查看简历中的已有证据与待补充项。</p></div><button class="quiet" @click="sample"><FileText :size="16" />载入虚构示例</button></section>
      <form @submit.prevent="analyze" novalidate>
        <div class="input-grid">
          <section class="input-section"><div class="field-heading"><label for="resume">简历文本</label><button type="button" class="icon-button" title="清空所有材料" aria-label="清空所有材料" @click="clear"><Trash2 :size="17" /></button></div><textarea id="resume" v-model="resume" placeholder="粘贴教育背景、项目经历和技能…" :aria-invalid="!!fields.resumeText" aria-describedby="resume-help" /><div id="resume-help" class="field-footer"><span class="field-error">{{ fields.resumeText || '材料仅在本次分析中使用' }}</span><span>{{ countCharacters(resume) }} / 20,000</span></div></section>
          <section class="input-section"><div class="field-heading"><label for="jd">岗位 JD</label><select v-model="selectedTemplate" @change="chooseTemplate" aria-label="选择示例岗位"><option value="">选择示例岗位</option><option v-for="item in templates" :key="item.id" :value="item.id">{{ item.title }}</option></select></div><textarea id="jd" v-model="jd" placeholder="粘贴岗位职责、必需技能和加分项…" :aria-invalid="!!fields.jdText" aria-describedby="jd-help" /><div id="jd-help" class="field-footer"><span class="field-error">{{ fields.jdText || '保留具体技能与优先级描述' }}</span><span>{{ countCharacters(jd) }} / 12,000</span></div></section>
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
    </main><footer class="page-footer">CareerLens <span>让经历可见，让差距可行动。</span></footer>
  </div>
</template>
