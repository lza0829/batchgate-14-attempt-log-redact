<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, putJSON } from '../api'

const rules = ref([])
const err = ref('')
const msg = ref('')
const busy = ref(false)

async function load() {
  err.value = ''
  try {
    const data = await getJSON('/api/redaction-rules')
    rules.value = data.rules.map((r) => ({
      fieldsText: (r.fields || []).join(', '),
      action: r.action,
      enabled: !!r.enabled,
    }))
  } catch (e) { err.value = String(e.message || e) }
}

function addRule() {
  rules.value.push({ fieldsText: '', action: 'mask', enabled: true })
}

function removeRule(i) {
  rules.value.splice(i, 1)
}

async function save() {
  err.value = ''; msg.value = ''; busy.value = true
  try {
    const payload = {
      rules: rules.value.map((r) => ({
        fields: r.fieldsText.split(',').map((s) => s.trim()).filter(Boolean),
        action: r.action,
        enabled: r.enabled,
      })),
    }
    const data = await putJSON('/api/redaction-rules', payload)
    msg.value = `已保存 ${data.rules.length} 条规则；之后执行的编排将按新规则脱敏`
    await load()
  } catch (e) { err.value = String(e.message || e) }
  finally { busy.value = false }
}

onMounted(load)
</script>
<template>
  <div class="page">
    <h1>脱敏规则</h1>
    <p class="muted">
      按 JSON 字段名匹配（任意嵌套层级，也支持 a.b 路径）；动作：掩码（替换为 ***）或丢弃（移除字段）。
      规则在编排写入尝试详情时生效，页面与导出均只见脱敏结果。
    </p>
    <p v-if="err" class="tag danger">{{ err }}</p>
    <p v-if="msg" class="tag ok">{{ msg }}</p>
    <div class="panel">
      <table>
        <thead>
          <tr><th>启用</th><th>字段名（逗号分隔）</th><th>动作</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in rules" :key="i">
            <td><input type="checkbox" v-model="r.enabled" /></td>
            <td><input class="mono" style="width:100%" v-model="r.fieldsText" placeholder="customer_id, phone" /></td>
            <td>
              <select v-model="r.action">
                <option value="mask">掩码</option>
                <option value="drop">丢弃</option>
              </select>
            </td>
            <td><button class="secondary" @click="removeRule(i)">删除</button></td>
          </tr>
        </tbody>
      </table>
      <p>
        <button class="secondary" @click="addRule">新增规则</button>
        <button style="margin-left:0.5rem" :disabled="busy" @click="save">{{ busy ? '保存中…' : '保存规则' }}</button>
      </p>
    </div>
    <div class="panel">
      <p class="muted">
        修改规则后请到<router-link to="/orchestrate">编排台</router-link>再执行一次编排，
        然后到<router-link to="/attempts">尝试记录</router-link>核对脱敏结果或导出清单。
      </p>
    </div>
  </div>
</template>
