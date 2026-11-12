<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getJSON } from '../api'
const route = useRoute()
const orchId = ref(null)
const orchList = ref([])
const rows = ref([])
const err = ref('')
async function load() {
  err.value = ''
  try {
    const q = orchId.value != null ? `?orchestration_id=${orchId.value}` : ''
    rows.value = await getJSON(`/api/attempts${q}`)
  } catch (e) { err.value = String(e.message || e) }
}
function exportUrl() {
  const q = orchId.value != null ? `?orchestration_id=${orchId.value}` : ''
  return `/api/attempts/export${q}`
}
onMounted(async () => {
  try {
    orchList.value = await getJSON('/api/orchestrations')
    const q = Number(route.query.orchestration_id)
    if (q) orchId.value = q
    await load()
  } catch (e) { err.value = String(e.message || e) }
})
watch(orchId, load)
</script>
<template>
  <div class="page">
    <h1>尝试记录</h1>
    <p class="muted">每次作业尝试的状态：success / failed / skipped_dep。详情在写入时已按<router-link to="/redaction">脱敏规则</router-link>处理，页面与导出均无明文敏感值。</p>
    <p v-if="err" class="tag danger">{{ err }}</p>
    <div class="panel">
      <label>
        编排
        <select v-model.number="orchId">
          <option :value="null">全部</option>
          <option v-for="o in orchList" :key="o.id" :value="o.id">#{{ o.id }} · {{ o.status }}</option>
        </select>
      </label>
      <span class="muted" style="margin-left:0.75rem">共 {{ rows.length }} 条</span>
      <a :href="exportUrl()" style="margin-left:0.75rem"><button type="button">导出（含清单）</button></a>
    </div>
    <div class="panel">
      <table>
        <thead><tr><th>ID</th><th>编排</th><th>作业</th><th>次</th><th>状态</th><th>详情</th></tr></thead>
        <tbody>
          <tr v-for="a in rows" :key="a.id">
            <td>{{ a.id }}</td>
            <td>{{ a.orchestration_id }}</td>
            <td class="mono">{{ a.job_name }}</td>
            <td>{{ a.attempt_no }}</td>
            <td><span class="tag" :class="a.status==='success'?'ok':(a.status==='failed'?'danger':'warn')">{{ a.status }}</span></td>
            <td class="mono">{{ JSON.stringify(a.detail) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
