<template>
  <div class="about-page">
    <!-- 品牌区 -->
    <section class="card hero">
      <img src="/images/logo_128.png" alt="小小账单" class="hero-logo" />
      <h1>关于小小账单</h1>
      <p class="tagline">隐私优先的个人账单分析工具 · 数据完全本地处理，不上传任何服务器</p>
    </section>

    <!-- 项目介绍 -->
    <section class="card">
      <h2 class="section-title">这是什么</h2>
      <p>
        小小账单把支付宝、WeChat、银行的账单文件导入<strong>本地</strong>，自动解析、跨源去重，
        生成年度 / 月度 / 分类 / 时间 / 渠道等多维度可视化分析，并内置可选的 AI 账单助手（小小）。
        支持多用户与家庭成员维度、邮箱自动导入、净资产与对账中心。
      </p>
      <p>
        所有数据处理都在你自己的设备上完成；AI 功能完全可选，仅在你主动配置并使用时，
        相关查询结果才会发送到你自己指定的模型端点。
      </p>
    </section>

    <!-- 开源与致谢 -->
    <section class="card">
      <h2 class="section-title">开源与致谢</h2>
      <p>小小账单是一个 MIT 协议的开源项目，站在两位开源作者的肩膀上：</p>
      <ol class="lineage">
        <li>
          <strong>Hessel2333</strong> ——
          <a href="https://github.com/Hessel2333/alipay_record_analysis" target="_blank" rel="noopener noreferrer">alipay_record_analysis</a>，
          最初的灵感与基础代码。
        </li>
        <li>
          <strong>dtsola</strong> ——
          <a href="https://github.com/dtsola/xiaoyaoprivatebill" target="_blank" rel="noopener noreferrer">xiaoyaoprivatebill（小遥账单助手）</a>，
          本项目的直接上游：完成了 Vue 3 + Flask 的现代化重构、模块化蓝图架构与 Docker 部署能力。
        </li>
        <li>
          <strong>小小账单</strong> —— 在上游基础上演进：银行账单接入与跨源去重、转账口径、渠道分析、
          多用户与数据隔离、AI 助手、邮箱自动导入、净资产与对账等。
        </li>
      </ol>
      <p class="license-note">
        许可证：<a href="https://github.com/JokerFuFu/xiaoyaoprivatebill/blob/main/LICENSE" target="_blank" rel="noopener noreferrer">MIT</a>，
        版权声明采用叠加方式——原作品 © dtsola，本项目新增与修改部分 © JokerFuFu。
      </p>
    </section>
  </div>
</template>

<script setup>
// 纯静态展示页,无逻辑
</script>

<style scoped>
.about-page {
  max-width: 760px;
  margin: 0 auto;
  padding: var(--space-6, 24px) var(--space-4, 16px);
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 16px);
}
.card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg, 14px);
  padding: var(--space-6, 24px);
}
.hero { text-align: center; }
.hero-logo { width: 88px; height: 88px; object-fit: contain; margin-bottom: 12px; }
.hero h1 { font-size: 26px; color: var(--text-color); margin: 0 0 8px; }
.tagline { color: var(--secondary-text); margin: 0; }
.section-title { font-size: 18px; color: var(--text-color); margin: 0 0 12px; }
.card p { color: var(--text-color); line-height: 1.75; margin: 0 0 10px; }
.lineage { padding-left: 20px; margin: 0 0 10px; }
.lineage li { color: var(--text-color); line-height: 1.9; }
.lineage a, .license-note a { color: var(--primary-color); text-decoration: none; }
.lineage a:hover, .license-note a:hover { text-decoration: underline; }
.license-note { color: var(--secondary-text); font-size: 13px; }
</style>
