<template>
  <table class="data-table">
    <thead v-if="columns.length">
      <tr>
        <th v-for="col in columns" :key="col.key" :style="col.width ? { width: col.width } : null">
          {{ col.label }}
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(row, i) in rows" :key="rowKey ? row[rowKey] : i">
        <td v-for="col in columns" :key="col.key" :class="col.align ? 'align-' + col.align : null">
          <!-- 每列可用 #cell-<key> 插槽自定义;默认走 formatter 或原值 -->
          <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
            {{ formatCell(row, col) }}
          </slot>
        </td>
      </tr>
      <tr v-if="!rows.length">
        <td :colspan="columns.length || 1" class="data-table-empty">{{ emptyText }}</td>
      </tr>
    </tbody>
  </table>
</template>

<script setup>
/**
 * 通用数据表格:列配置(可带 formatter/对齐/宽度)+ 具名单元格插槽 + 空态。
 * 收敛 Transactions/Category 等页面重复的 thead/tbody/v-for 表格样板。
 */
const props = defineProps({
  // [{ key, label, width?, align?: 'left'|'center'|'right', formatter?: (value, row) => string }]
  columns: { type: Array, default: () => [] },
  rows: { type: Array, default: () => [] },
  // 行唯一键字段名(缺省用索引)
  rowKey: { type: String, default: '' },
  emptyText: { type: String, default: '暂无数据' },
})

function formatCell(row, col) {
  const value = row[col.key]
  return col.formatter ? col.formatter(value, row) : value
}
</script>

<style scoped>
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color, #eee);
  text-align: left;
}

.data-table th {
  font-weight: 600;
  color: var(--text-color, #333);
  background: var(--table-head-bg, transparent);
}

.data-table .align-right {
  text-align: right;
}

.data-table .align-center {
  text-align: center;
}

.data-table-empty {
  text-align: center;
  color: var(--text-muted, #999);
  padding: 24px 12px;
}
</style>
