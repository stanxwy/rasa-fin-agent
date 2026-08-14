<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import 'element-plus/es/components/message-box/style/css'
import xiaoerAvatar from './assets/xiaoer.png'
import userProfileAvatar from './assets/userProfileAvatar.svg'
// ═══════════════════════════════════════════════════════════
// 所有业务字词集中在 domainConfig.js 管理，
// 要切换到别的行业（电商/教育/医疗）只需改这一个配置文件
// ═══════════════════════════════════════════════════════════
import {
  APP, WELCOME, BUSINESS_PANEL, SESSION_LIST, UI,
  LOAN_PRODUCT_NAMES, WEALTH_PRODUCT_NAMES, ACCOUNT_PRODUCT_NAMES,
  CATEGORY_NAMES, CURRENCY_NAMES, RISK_NAMES, CUSTOMER_TYPE_NAMES,
  OPEN_STATUS_NAMES, REPAYMENT_METHOD_NAMES, WEALTH_OPERATION_NAMES,
  WEALTH_TYPE_NAMES, NOTIFICATION_TYPE_NAMES, SEND_STATUS_NAMES,
  COLLECTION_STATUS_NAMES, BILL_STATUS_NAMES, OVERDUE_STATUS_NAMES,
} from './config/domainConfig.js'

// sender_id 通过 URL 参数传入（?sender_id=xxx），未指定时默认 CUS00000001
function resolveSenderId() {
  const param = new URLSearchParams(window.location.search).get('sender_id')
  return param && param.trim() ? param.trim() : 'CUS00000001'
}
const senderId = ref(resolveSenderId())
const draftMessage = ref('')
const isSending = ref(false)
const errorMessage = ref('')
const messages = ref([])
const messagesContainer = ref(null)

// 金融业务对象数据
const customerInfo = ref(null)
const accounts = ref([])
const transactions = ref([])
const wealthProducts = ref([])
const wealthPositions = ref([])
const loanProducts = ref([])
const creditLimits = ref([])
const repaymentBills = ref([])
const overdues = ref([])
const notifications = ref([])

const isLoadingSidebar = ref(false)
const sidebarError = ref('')
// 默认激活 tab（从业务配置中取第一个 tab key）
const activeTab = ref(BUSINESS_PANEL.TABS[0]?.key || 'customer')

// ── 构建金融 API 请求头 ──────
function buildFinHeaders(extra = {}) {
  return {
    'X-Channel-Code': 'MOBILE_BANK',
    'Authorization': `Bearer ${senderId.value.trim()}`,
    ...extra,
  }
}

// 理财产品其它前缀按格式自动生成中文名称
function buildWealthName(code) {
  if (WEALTH_PRODUCT_NAMES[code]) return WEALTH_PRODUCT_NAMES[code]
  const m = code.match(/^WM_(FIXED90|FIXED180|MIXED|EQUITY|STRUCT)_(\d+)$/)
  if (m) {
    const [, prefix, num] = m
    const n = Number(num)
    const typeMap = {
      FIXED90: '90天固定收益', FIXED180: '180天固定收益',
      MIXED: '平衡配置混合策略', EQUITY: '权益成长优选', STRUCT: '指数挂钩结构性存款',
    }
    return `中州${typeMap[prefix] || prefix}${n}${n < 10 ? '' : ''}号`
  }
  return code
}

// ── 映射工具函数 ───────────────────────────────────────────────
function mapCode(value, dict, fallback) {
  if (!value) return fallback || '-'
  return dict[value] || fallback || value
}
function loanName(code) { return mapCode(code, LOAN_PRODUCT_NAMES) }
function wealthName(code) { return buildWealthName(code) }
function accountProductName(code) { return mapCode(code, ACCOUNT_PRODUCT_NAMES) }
function categoryName(code) { return mapCode(code, CATEGORY_NAMES) }
function currencyName(code) { return mapCode(code, CURRENCY_NAMES) }
function riskName(code) { return mapCode(code, RISK_NAMES) }
function customerTypeName(code) { return mapCode(code, CUSTOMER_TYPE_NAMES) }
function openStatusName(code) { return mapCode(code, OPEN_STATUS_NAMES) }
function repaymentMethodName(code) { return mapCode(code, REPAYMENT_METHOD_NAMES) }
function wealthOperationName(code) { return mapCode(code, WEALTH_OPERATION_NAMES) }
function wealthTypeName(code) { return mapCode(code, WEALTH_TYPE_NAMES) }
function notificationTypeName(code) { return mapCode(code, NOTIFICATION_TYPE_NAMES) }
function sendStatusName(code) { return mapCode(code, SEND_STATUS_NAMES) }
function collectionStatusName(code) { return mapCode(code, COLLECTION_STATUS_NAMES) }
function billStatusName(code) { return mapCode(code, BILL_STATUS_NAMES) }
function overdueStatusName(code) { return mapCode(code, OVERDUE_STATUS_NAMES) }

// 金额格式化（保留两位小数，带符号）
function fmtAmt(val) {
  const n = Number(val || 0)
  if (!isFinite(n)) return '0.00'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ── 多会话（会话列表）─────────────────────────────────────
const sessions = ref([])
const activeSessionId = ref(null)
const showSessionList = ref(false)
const showSidebar = ref(false)
// 当前进行中的会话 ID（后端标记 is_current）
const currentSessionId = computed(
  () => sessions.value.find((s) => s.is_current)?.session_id ?? null
)

// TTS state
const ttsState = ref({})
let currentAudio = null

// Copy state
const copyState = ref({})

// ── Canvas 粒子背景系统 ──────────────────────────────────────────────
const bgCanvas = ref(null)
let animFrameId = null
let bgParticles = []
const BG_PARTICLE_COUNT = 80
const BG_CONNECT_DIST = 150
const BG_MOUSE_RADIUS = 180
const bgMouse = { x: null, y: null }

function createBgParticles(w, h) {
  const palette = [
    [13, 148, 136], [20, 184, 166], [245, 158, 11],
    [217, 119, 6], [2, 132, 199], [56, 189, 248],
  ]
  bgParticles = Array.from({ length: BG_PARTICLE_COUNT }, () => {
    const color = palette[Math.floor(Math.random() * palette.length)]
    return {
      x: Math.random() * w, y: Math.random() * h,
      size: Math.random() * 2.5 + 1,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      color, opacity: Math.random() * 0.45 + 0.12,
      phase: Math.random() * Math.PI * 2,
      pulse: Math.random() * 0.015 + 0.005,
    }
  })
}

function animateBg(ctx, w, h, time) {
  ctx.clearRect(0, 0, w, h)

  for (const p of bgParticles) {
    p.x += p.vx + Math.sin(time * 0.001 + p.phase) * 0.25
    p.y += p.vy + Math.cos(time * 0.001 + p.phase + 1) * 0.25

    if (bgMouse.x !== null) {
      const dx = p.x - bgMouse.x, dy = p.y - bgMouse.y
      const dist = Math.hypot(dx, dy)
      if (dist < BG_MOUSE_RADIUS) {
        const force = (BG_MOUSE_RADIUS - dist) / BG_MOUSE_RADIUS
        p.x += (dx / dist) * force * 0.7
        p.y += (dy / dist) * force * 0.7
      }
    }

    if (p.x < -20) p.x = w + 20; if (p.x > w + 20) p.x = -20
    if (p.y < -20) p.y = h + 20; if (p.y > h + 20) p.y = -20
  }

  // 连线
  ctx.lineWidth = 0.5
  for (let i = 0; i < bgParticles.length; i++) {
    for (let j = i + 1; j < bgParticles.length; j++) {
      const dx = bgParticles[i].x - bgParticles[j].x
      const dy = bgParticles[i].y - bgParticles[j].y
      const dist = Math.hypot(dx, dy)
      if (dist < BG_CONNECT_DIST) {
        const alpha = (1 - dist / BG_CONNECT_DIST) * 0.1
        ctx.strokeStyle = `rgba(13,148,136,${alpha})`
        ctx.beginPath()
        ctx.moveTo(bgParticles[i].x, bgParticles[i].y)
        ctx.lineTo(bgParticles[j].x, bgParticles[j].y)
        ctx.stroke()
      }
    }
  }

  // 粒子光晕
  for (const p of bgParticles) {
    const pulse = 1 + Math.sin(time * p.pulse + p.phase) * 0.25
    const r = p.size * pulse
    const [cr, cg, cb] = p.color

    ctx.beginPath()
    ctx.arc(p.x, p.y, r * 2.5, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${cr},${cg},${cb},${p.opacity * 0.08})`
    ctx.fill()

    ctx.beginPath()
    ctx.arc(p.x, p.y, r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${cr},${cg},${cb},${p.opacity * 0.7})`
    ctx.fill()
  }
}

function initBg() {
  const canvas = bgCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')

  const resize = () => {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
    createBgParticles(canvas.width, canvas.height)
  }
  resize()
  window.addEventListener('resize', resize)

  const onMouseMove = (e) => { bgMouse.x = e.clientX; bgMouse.y = e.clientY }
  const onMouseLeave = () => { bgMouse.x = null; bgMouse.y = null }
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseleave', onMouseLeave)

  const loop = (time) => {
    animateBg(ctx, canvas.width, canvas.height, time)
    animFrameId = requestAnimationFrame(loop)
  }
  animFrameId = requestAnimationFrame(loop)

  canvas._cleanup = () => {
    cancelAnimationFrame(animFrameId)
    window.removeEventListener('resize', resize)
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseleave', onMouseLeave)
  }
}
// ── 粒子背景系统结束 ──────────────────────────────────────────────────

// 客服数字人配置（从业务配置读取，便于换领域）
const customerService = {
  name: APP.AGENT.name,
  title: APP.AGENT.title,
  avatar: xiaoerAvatar,
  status: APP.AGENT.status,
}

// 用户配置
const userProfile = {
  name: '你',
  avatar: userProfileAvatar
}

// 将消息分组为 Turn 结构
const turns = computed(() => {
  const result = []
  let currentTurn = null
  let turnIndex = 0

  for (const message of messages.value) {
    if (message.type === 'divider') {
      if (currentTurn) {
        result.push(currentTurn)
        currentTurn = null
      }
      result.push({
        type: 'divider',
        text: message.text
      })
      continue
    }

    if (message.role === 'user') {
      // 如果有待处理的当前 turn，先保存
      if (currentTurn) {
        result.push(currentTurn)
      }
      // 创建新的 turn
      turnIndex++
      currentTurn = {
        type: 'turn',
        id: `turn-${turnIndex}`,
        index: turnIndex,
        userMessage: message,
        botMessages: []
      }
    } else if (message.role === 'bot') {
      if (!currentTurn) {
        // 如果没有当前 turn，创建一个（可能是因为历史消息）
        turnIndex++
        currentTurn = {
          type: 'turn',
          id: `turn-${turnIndex}`,
          index: turnIndex,
          userMessage: null,
          botMessages: []
        }
      }
      currentTurn.botMessages.push(message)
    }
  }

  if (currentTurn) {
    result.push(currentTurn)
  }

  return result
})

const chatEndpoint = computed(() => '/api/chat')
const chatHistoryEndpoint = computed(() => {
  const base = `/api/chat/history?sender_id=${encodeURIComponent(senderId.value.trim())}`
  return activeSessionId.value
    ? `${base}&session_id=${encodeURIComponent(activeSessionId.value)}`
    : base
})

// 金融后端 API 端点（/api/v1/*）
// 响应格式：{code:0, message:"ok", data:{...}}
// 列表端点：data.list / data.total_count
const finApiCustomerDetail = computed(
  () => `/api/v1/customers/${encodeURIComponent(senderId.value.trim())}`
)
const finApiCustomerAccounts = computed(
  () => `/api/v1/customers/${encodeURIComponent(senderId.value.trim())}/accounts`
)
function finApiAccountTransactions(accountNo) {
  return `/api/v1/accounts/${encodeURIComponent(accountNo)}/transactions?page_size=100`
}
const finApiWealthProducts = '/api/v1/wealth/products'
const finApiWealthPositions = computed(
  () => `/api/v1/customers/${encodeURIComponent(senderId.value.trim())}/wealth/positions`
)
const finApiLoanProducts = '/api/v1/loan/products'
const finApiCreditLimits = computed(
  () => `/api/v1/customers/${encodeURIComponent(senderId.value.trim())}/credit-limits`
)
const finApiRepaymentBills = computed(
  () => `/api/v1/repayment/bills?customer_no=${encodeURIComponent(senderId.value.trim())}&page_size=100`
)
const finApiOverdues = computed(
  () => `/api/v1/overdues?customer_no=${encodeURIComponent(senderId.value.trim())}&page_size=100`
)
const finApiNotifications = computed(
  () => `/api/v1/customers/${encodeURIComponent(senderId.value.trim())}/notifications?page_size=100`
)

function createBaseMessage(role) {
  return {
    id: crypto.randomUUID(),
    role,
    buttons: [],
    timestamp: null,
  }
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ''
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

function appendUserText(text) {
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'text',
    text,
    timestamp: new Date().toISOString(),
  })
}

function appendUserObject(objectType, payload) {
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'object',
    objectType,
    payload,
    timestamp: new Date().toISOString(),
  })
}

function appendBotMessages(botMessages) {
  for (const message of botMessages) {
    appendMessage('bot', message)
  }
}

function appendMessage(role, message) {
  if (role === 'divider') {
    messages.value.push({
      ...createBaseMessage('divider'),
      type: 'divider',
      text: message.text ?? '以上为历史消息',
    })
    return
  }

  if (message.object) {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'object',
      objectType: message.object.type,
      payload: message.object,
      timestamp: message.timestamp ?? null,
    })
  } else {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'text',
      text: message.text ?? '',
      suggestions: message.suggestions ?? null,
      timestamp: message.timestamp ?? null,
    })
  }
}

function setHistoryMessages(historyMessages) {
  messages.value = []
  for (const message of historyMessages) {
    const role = ['user', 'bot', 'divider'].includes(message.role) ? message.role : 'bot'
    appendMessage(role, message)
  }
}

async function scrollToBottom() {
  await nextTick()
  const container = messagesContainer.value
  if (!container) {
    return
  }
  container.scrollTop = container.scrollHeight
  // 图片/字体加载后高度会变，再校正一次，确保停在底部
  requestAnimationFrame(() => {
    if (container) container.scrollTop = container.scrollHeight
  })
}

watch(
  () => messages.value.length,
  async () => {
    await scrollToBottom()
  }
)

function resetConversation() {
  messages.value = []
  errorMessage.value = ''
}

function formatAmount(amount) {
  const numericAmount = Number(amount)
  if (Number.isNaN(numericAmount)) {
    return '￥0.00'
  }
  return `￥${numericAmount.toFixed(2)}`
}

function formatOrderSummary(order) {
  return order.status ? `订单状态：${order.status}` : '订单'
}

const ORDER_STATUS_CLASS = {
  '待发货': 'status-warning',
  '待揽收': 'status-warning',
  '运输中': 'status-info',
  '派送中': 'status-info',
  '已完成': 'status-success',
  '已签收': 'status-success',
  '已取消': 'status-muted',
  '退款中': 'status-danger',
  '已退款': 'status-muted',
}

function getStatusClass(status) {
  return ORDER_STATUS_CLASS[status] || 'status-muted'
}

function formatProductSummary(product) {
  if (product.description) {
    return product.description
  }
  if (product.attributes?.price) {
    return `商品价格：${formatAmount(product.attributes.price)}`
  }
  return '商品信息'
}

function getObjectTitle(message) {
  const payload = message.payload ?? {}
  if (payload.title) {
    return payload.title
  }
  return message.objectType === 'order' ? UI.objectBadge.order : UI.objectBadge.product
}

function getObjectIdentifier(message) {
  const payload = message.payload ?? {}
  const id = payload.order_id ?? payload.product_id ?? payload.id
  const label = message.objectType === 'order' ? UI.objectLabel.orderId : UI.objectLabel.productId
  return id ? `${label}：${id}` : label
}

function getObjectSummary(message) {
  const payload = message.payload ?? {}
  if (message.objectType === 'order') {
    const status = payload.status ?? payload.attributes?.status
    return status ? `订单状态：${status}` : '订单'
  }
  return formatProductSummary(payload)
}

function getObjectAmount(message) {
  const payload = message.payload ?? {}
  const amount = message.objectType === 'order'
    ? payload.amount ?? payload.attributes?.amount
    : payload.price ?? payload.attributes?.price
  return formatAmount(amount)
}

// 通用金融 API GET 请求封装
// 响应格式：{code:0, message:"ok", data:{...}}
async function fetchFin(endpoint) {
  const res = await fetch(endpoint, { headers: buildFinHeaders() })
  const payload = await res.json()
  if (!res.ok || payload.code !== 0) {
    throw new Error(payload?.message || payload?.detail || `请求失败 (${res.status})`)
  }
  return payload.data
}

// 刷新右侧「业务对象」列表。
// which: 'all' | 'customer' | 'accounts' | 'transactions' | 'wealth' | 'loans' | 'repayments' | 'overdues' | 'notifications'
async function refreshObjects(which = 'all') {
  const sid = senderId.value.trim()
  if (!sid) return

  isLoadingSidebar.value = true
  sidebarError.value = ''
  try {
    const tasks = []
    const need = (key) => which === 'all' || which === key

    // ── 客户信息 ──────────────────────────────────────────────
    if (need('customer')) {
      tasks.push((async () => {
        try { customerInfo.value = await fetchFin(finApiCustomerDetail.value) }
        catch { customerInfo.value = null }
      })())
    }

    // ── 银行账户 ──────────────────────────────────────────────
    if (need('accounts')) {
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiCustomerAccounts.value)
          accounts.value = data?.list ?? []
        } catch { accounts.value = [] }
      })())
    }

    // ── 交易流水（取第一个账户的流水） ─────────────────────────
    if (need('transactions')) {
      tasks.push((async () => {
        try {
          let accts = accounts.value
          if (!accts.length) {
            const data = await fetchFin(finApiCustomerAccounts.value)
            accts = data?.list ?? []
          }
          if (accts.length) {
            const data = await fetchFin(finApiAccountTransactions(accts[0].account_no))
            transactions.value = data?.list ?? []
          } else { transactions.value = [] }
        } catch { transactions.value = [] }
      })())
    }

    // ── 理财产品 + 持仓 ──────────────────────────────────────
    if (need('wealth')) {
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiWealthProducts)
          wealthProducts.value = data?.list ?? []
        } catch { wealthProducts.value = [] }
      })())
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiWealthPositions.value)
          wealthPositions.value = data?.list ?? []
        } catch { wealthPositions.value = [] }
      })())
    }

    // ── 贷款产品 + 授信额度 ───────────────────────────────────
    if (need('loans')) {
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiLoanProducts)
          loanProducts.value = data?.list ?? []
        } catch { loanProducts.value = [] }
      })())
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiCreditLimits.value)
          creditLimits.value = data?.list ?? []
        } catch { creditLimits.value = [] }
      })())
    }

    // ── 还款账单 ──────────────────────────────────────────────
    if (need('repayments')) {
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiRepaymentBills.value)
          repaymentBills.value = data?.list ?? []
        } catch { repaymentBills.value = [] }
      })())
    }

    // ── 逾期记录 ──────────────────────────────────────────────
    if (need('overdues')) {
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiOverdues.value)
          overdues.value = data?.list ?? []
        } catch { overdues.value = [] }
      })())
    }

    // ── 通知消息 ──────────────────────────────────────────────
    if (need('notifications')) {
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiNotifications.value)
          notifications.value = data?.list ?? []
        } catch { notifications.value = [] }
      })())
    }

    await Promise.all(tasks)
  } catch (error) {
    sidebarError.value = error instanceof Error ? error.message : UI.sidebarErrorDefault
  } finally {
    isLoadingSidebar.value = false
  }
}

async function fetchChatHistory() {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    messages.value = []
    return
  }

  try {
    const response = await fetch(chatHistoryEndpoint.value)
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || UI.chatHistoryFailDefault)
    }
    if (currentSenderId === senderId.value.trim()) {
      setHistoryMessages(Array.isArray(data?.messages) ? data.messages : [])
      await scrollToBottom()
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : UI.chatHistoryFailDefault
  }
}

async function fetchSessions() {
  const sid = senderId.value.trim()
  if (!sid) {
    sessions.value = []
    return
  }
  try {
    const response = await fetch(`/api/chat/sessions?sender_id=${encodeURIComponent(sid)}`)
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || UI.sessionListFail)
    }
    sessions.value = Array.isArray(data?.sessions) ? data.sessions : []
  } catch (error) {
    console.error(`${UI.sessionListFail}：`, error)
  }
}

async function selectSession(id) {
  if (id === activeSessionId.value) {
    showSessionList.value = false
    return
  }
  activeSessionId.value = id
  showSessionList.value = false
  showSidebar.value = false
  await fetchChatHistory()
  await scrollToBottom()
}

async function startNewSession() {
  const sid = senderId.value.trim()
  showSessionList.value = false
  showSidebar.value = false
  if (!sid) return
  try {
    await fetch('/api/chat/session/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sender_id: sid }),
    })
  } catch (error) {
    console.error(`${UI.resetSessionFail}：`, error)
  }
  await fetchSessions()
  activeSessionId.value = currentSessionId.value
  messages.value = []
  draftMessage.value = ''
  errorMessage.value = ''
}

async function deleteSession(id) {
  try {
    await ElMessageBox.confirm(
      SESSION_LIST.deleteConfirm.message,
      SESSION_LIST.deleteConfirm.title,
      {
        confirmButtonText: SESSION_LIST.deleteConfirm.confirm,
        cancelButtonText:  SESSION_LIST.deleteConfirm.cancel,
        type: 'warning',
      }
    )
  } catch {
    return // 用户点击取消或关闭弹窗
  }
  try {
    const response = await fetch('/api/chat/session/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sender_id: senderId.value.trim(), session_id: id }),
    })
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || UI.deleteSessionFail)
    }
    if (id === activeSessionId.value) {
      activeSessionId.value = null
      messages.value = []
    }
    await fetchSessions()
  } catch (error) {
    console.error(`${UI.deleteSessionFail}：`, error)
  }
}

// 发送前确保视图停留在「当前会话」：若当前正在看别的会话，先切换回来并加载其历史
async function ensureCurrentSessionView() {
  const cur = currentSessionId.value
  if (activeSessionId.value !== cur) {
    activeSessionId.value = cur
    if (cur) {
      await fetchChatHistory()
    } else {
      messages.value = []
    }
  }
}

// 发送后把活动会话同步为当前会话（不重载，避免重复本地消息）
function syncActiveToCurrent() {
  const cur = currentSessionId.value
  if (cur && activeSessionId.value !== cur) {
    activeSessionId.value = cur
  }
}

function formatSessionTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  if (sameDay) return `${hh}:${mm}`
  const mo = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${mo}-${dd} ${hh}:${mm}`
}

async function sendPayload(payload, onAppend) {
  if (isSending.value) {
    return
  }

  errorMessage.value = ''
  await ensureCurrentSessionView()
  if (onAppend) onAppend()
  isSending.value = true

  try {
    const response = await fetch(chatEndpoint.value, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sender_id: senderId.value.trim(),
        ...payload,
      }),
    })

    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || UI.requestFail)
    }

    appendBotMessages(data.messages ?? [])
    await fetchSessions()
    syncActiveToCurrent()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : UI.requestFail
  } finally {
    isSending.value = false
  }
}

async function sendSuggestion(text) {
  await sendPayload({ text }, () => appendUserText(text))
}

async function sendQuickText(text) {
  draftMessage.value = text
  await sendTextMessage()
}
async function sendTextMessage() {
  const text = draftMessage.value.trim()
  const currentSenderId = senderId.value.trim()

  if (!currentSenderId) {
    errorMessage.value = UI.senderIdRequired
    return
  }
  if (!text) {
    return
  }

  draftMessage.value = ''
  await sendPayload({ text }, () => appendUserText(text))
}

async function sendOrder(order) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = UI.senderIdRequired
    return
  }

  await sendPayload({
    object: {
      type: 'order',
      id: order.order_id,
      title: order.title,
      attributes: {
        status: order.status,
        amount: order.amount,
        created_at: order.created_at,
        cover_url: order.cover_url,
      },
    },
  }, () => appendUserObject('order', { ...order }))
}

async function sendProduct(product) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = UI.senderIdRequired
    return
  }

  await sendPayload({
    object: {
      type: 'product',
      id: product.product_id,
      title: product.title,
      attributes: {
        price: product.price,
        cover_url: product.cover_url,
        description: product.description,
      },
    },
  }, () => appendUserObject('product', { ...product }))
}

watch(
  () => senderId.value.trim(),
  async (value, previousValue) => {
    if (value === previousValue) return

    resetConversation()
    if (!value) {
      customerInfo.value = null
      accounts.value = []
      transactions.value = []
      wealthProducts.value = []
      wealthPositions.value = []
      loanProducts.value = []
      creditLimits.value = []
      repaymentBills.value = []
      overdues.value = []
      notifications.value = []
      sessions.value = []
      activeSessionId.value = null
      return
    }
    await refreshObjects('all')
    await fetchSessions()
    activeSessionId.value = currentSessionId.value
    await fetchChatHistory()
  }
)

onMounted(async () => {
  await refreshObjects('all')
  await fetchSessions()
  activeSessionId.value = currentSessionId.value
  await fetchChatHistory()
})

onUnmounted(() => {})

async function playTts(botMsg) {
  const msgId = botMsg.id
  if (!botMsg.text || ttsState.value[msgId] === 'loading') return

  if (currentAudio) { currentAudio.pause(); currentAudio = null }
  for (const key of Object.keys(ttsState.value)) {
    if (ttsState.value[key] === 'playing') ttsState.value[key] = 'idle'
  }

  ttsState.value[msgId] = 'loading'
  try {
    const response = await fetch('/api/chat/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: botMsg.text }),
    })
    if (!response.ok) throw new Error('TTS 请求失败')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    currentAudio = new Audio(url)
    ttsState.value[msgId] = 'playing'
    currentAudio.onended = () => { ttsState.value[msgId] = 'idle'; URL.revokeObjectURL(url); currentAudio = null }
    currentAudio.onerror = () => { ttsState.value[msgId] = 'idle'; URL.revokeObjectURL(url); currentAudio = null }
    await currentAudio.play()
  } catch (error) {
    ttsState.value[msgId] = 'idle'
    console.error('TTS error:', error)
  }
}

async function copyBotText(botMsg) {
  const msgId = botMsg.id
  try {
    await navigator.clipboard.writeText(botMsg.text)
    copyState.value[msgId] = true
    setTimeout(() => { copyState.value[msgId] = false }, 1800)
  } catch (error) {
    console.error('Copy failed:', error)
  }
}
</script>

<template>
  <div class="app-shell">
    <div class="workspace">
      <!-- 会话列表：桌面端常驻左侧；移动端为抽屉（由 showSessionList 控制） -->
      <aside class="conversation-list" :class="{ open: showSessionList }">
        <div class="conversation-header">
          <h2>{{ SESSION_LIST.title }}</h2>
          <button type="button" class="new-session-button" @click="startNewSession">
            <span>＋</span>
            <span>{{ SESSION_LIST.newChat }}</span>
          </button>
        </div>
        <div class="conversation-items">
          <div v-if="!sessions.length" class="conversation-empty">{{ SESSION_LIST.empty }}</div>
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="conversation-item"
            :class="{ active: s.session_id === activeSessionId }"
          >
            <div class="conversation-main" @click="selectSession(s.session_id)">
              <span class="conversation-preview">{{ s.preview || SESSION_LIST.defaultPreview }}</span>
              <span class="conversation-time">{{ formatSessionTime(s.last_activity_at) }}</span>
            </div>
            <button
              type="button"
              class="conversation-delete"
              :title="SESSION_LIST.deleteConfirm.title"
              @click.stop="deleteSession(s.session_id)"
            >🗑</button>
          </div>
        </div>
      </aside>

      <div class="chat-card">
        <header class="chat-header">
          <div class="header-content">
            <!-- 左侧会话按钮：气泡图标（bubble） -->
            <button type="button" class="icon-button mobile-only" :title="SESSION_LIST.title" @click="showSessionList = true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
            </button>
            <div class="header-info">
              <h1>{{ APP.SYSTEM_NAME }}</h1>
              <div class="service-info">
                <div class="service-avatar-wrapper">
                  <img :src="customerService.avatar" class="service-avatar" />
                  <span class="status-indicator"></span>
                </div>
                <div class="service-details">
                  <span class="service-name">{{ customerService.name }}</span>
                  <span class="service-status">{{ customerService.status }}</span>
                </div>
              </div>
            </div>
            <div class="header-actions">
              <!-- 右侧业务对象按钮：三条横线图标 -->
              <button type="button" class="icon-button mobile-only" :title="BUSINESS_PANEL.title" @click="showSidebar = true">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <line x1="3" y1="6" x2="21" y2="6"></line>
                  <line x1="3" y1="12" x2="21" y2="12"></line>
                  <line x1="3" y1="18" x2="21" y2="18"></line>
                </svg>
              </button>
            </div>
          </div>
        </header>

        <section ref="messagesContainer" class="messages">
          <div v-if="turns.length === 0" class="welcome">
            <div class="welcome-card">
              <div class="welcome-glow"></div>
              <div class="welcome-avatar-wrapper">
                <img :src="customerService.avatar" class="welcome-avatar" :alt="customerService.name" />
                <span class="welcome-status-pulse"></span>
              </div>
              <h2 class="welcome-greeting">Hi，我是 {{ customerService.name }}</h2>
              <p class="welcome-subtitle">{{ WELCOME.greeting }}</p>
              <div class="welcome-chips">
                <button
                  v-for="chip in WELCOME.quickQuestions"
                  :key="chip"
                  type="button"
                  class="welcome-chip"
                  :disabled="isSending"
                  @click="sendQuickText(chip)"
                >{{ chip }}</button>
              </div>
              <p class="welcome-features">
                <span v-for="(feat, idx) in WELCOME.features" :key="idx">{{ feat.icon }} {{ feat.text }}</span>
              </p>
            </div>
          </div>

          <!-- Turn 结构展示 -->
          <template v-for="(item, index) in turns" :key="item.id || index">
            <!-- 分隔线 -->
            <div v-if="item.type === 'divider'" class="history-divider">
              <span>{{ item.text }}</span>
            </div>

            <!-- Turn 卡片 -->
            <div v-else class="turn-card" :class="{ 'has-user-message': item.userMessage }">

              <!-- 用户消息区域（京东金融风格：蓝色气泡，靠右，无头像） -->
              <div v-if="item.userMessage" class="turn-section user-section">
                <div class="section-meta user-meta">
                  <span class="meta-name">{{ userProfile.name }}</span>
                  <span class="meta-time">{{ formatTime(item.userMessage.timestamp) }}</span>
                </div>
                <div class="turn-bubble user-bubble">
                  <template v-if="item.userMessage.type === 'object'">
                    <div class="object-card" :class="`object-card-${item.userMessage.objectType}`">
                      <div class="object-card-badge">
                        {{ item.userMessage.objectType === 'order' ? UI.objectBadge.order : UI.objectBadge.product }}
                      </div>
                      <img
                        v-if="item.userMessage.type === 'object' && item.userMessage.payload.cover_url"
                        :src="item.userMessage.payload.cover_url"
                        :alt="getObjectTitle(item.userMessage)"
                        class="object-card-image"
                        @error="$event.target.style.display='none'"
                      />
                      <div class="object-card-title">{{ getObjectTitle(item.userMessage) }}</div>
                      <div class="object-card-meta">{{ getObjectIdentifier(item.userMessage) }}</div>
                      <div class="object-card-meta">
                        <span v-if="item.userMessage.objectType === 'order' && item.userMessage.payload.status" class="status-badge" :class="getStatusClass(item.userMessage.payload.status)">{{ item.userMessage.payload.status }}</span>
                        <span v-else>{{ getObjectSummary(item.userMessage) }}</span>
                      </div>
                      <div class="object-card-price">{{ getObjectAmount(item.userMessage) }}</div>
                    </div>
                  </template>
                  <template v-else>
                    <p>{{ item.userMessage.text }}</p>
                  </template>
                </div>
              </div>

              <!-- 客服回复区域（京东金融风格：白色气泡靠左，无头像，顶部只显示名称） -->
              <div v-if="item.botMessages.length > 0" class="turn-section bot-section">
                <div class="section-meta bot-meta">
                  <span class="meta-name">{{ customerService.name }}</span>
                </div>
                <div class="bot-messages">
                  <div
                    v-for="(botMsg, msgIndex) in item.botMessages"
                    :key="msgIndex"
                    class="turn-bubble bot-bubble"
                  >
                    <template v-if="botMsg.type === 'object'">
                      <div class="object-card" :class="`object-card-${botMsg.objectType}`">
                        <div class="object-card-badge">
                          {{ botMsg.objectType === 'order' ? UI.objectBadge.order : UI.objectBadge.product }}
                        </div>
                        <img
                          v-if="botMsg.type === 'object' && botMsg.payload.cover_url"
                          :src="botMsg.payload.cover_url"
                          :alt="getObjectTitle(botMsg)"
                          class="object-card-image"
                          @error="$event.target.style.display='none'"
                        />
                        <div class="object-card-title">{{ getObjectTitle(botMsg) }}</div>
                        <div class="object-card-meta">{{ getObjectIdentifier(botMsg) }}</div>
                        <div class="object-card-meta">
                          <span v-if="botMsg.objectType === 'order' && botMsg.payload.status" class="status-badge" :class="getStatusClass(botMsg.payload.status)">{{ botMsg.payload.status }}</span>
                          <span v-else>{{ getObjectSummary(botMsg) }}</span>
                        </div>
                        <div class="object-card-price">{{ getObjectAmount(botMsg) }}</div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="bot-text-row">
                        <p>{{ botMsg.text }}</p>
                        <div class="bot-actions">
                          <button type="button" class="tts-button"
                            :class="{ 'tts-loading': ttsState[botMsg.id] === 'loading', 'tts-playing': ttsState[botMsg.id] === 'playing' }"
                            :disabled="ttsState[botMsg.id] === 'loading'"
                            :title="ttsState[botMsg.id] === 'playing' ? UI.tts.playing : UI.tts.default"
                            @click.stop="playTts(botMsg)">
                            <span v-if="ttsState[botMsg.id] === 'loading'" class="tts-spinner"></span>
                            <span v-else-if="ttsState[botMsg.id] === 'playing'" class="tts-bars">
                              <span></span><span></span><span></span>
                            </span>
                            <span v-else>🔈</span>
                          </button>
                          <button type="button" class="copy-button"
                            :class="{ 'copy-done': copyState[botMsg.id] }"
                            :title="copyState[botMsg.id] ? UI.copy.done : UI.copy.title"
                            @click.stop="copyBotText(botMsg)">
                            <span v-if="copyState[botMsg.id]">✓</span>
                            <span v-else>📋</span>
                          </button>
                        </div>
                      </div>
                    </template>
                    <div v-if="botMsg.suggestions && botMsg.suggestions.length > 0" class="suggestion-chips">
                      <button
                        v-for="sug in botMsg.suggestions"
                        :key="sug"
                        type="button"
                        class="suggestion-chip"
                        :disabled="isSending"
                        @click.stop="sendSuggestion(sug)"
                      >{{ sug }}</button>
                    </div>
                    <div class="msg-time">{{ formatTime(botMsg.timestamp) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </section>

        <div v-if="isSending" class="typing-indicator">
          <div class="typing-avatar">
            <img :src="customerService.avatar" class="avatar-small" :alt="customerService.name" />
          </div>
          <div class="typing-bubble">
            <span class="typing-dots">
              <span></span><span></span><span></span>
            </span>
            <span class="typing-label">{{ UI.typingLabel(customerService.name) }}</span>
          </div>
        </div>

        <p v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </p>

        <form class="composer" @submit.prevent="sendTextMessage">
          <input
            v-model="draftMessage"
            type="text"
            :placeholder="UI.sendPlaceholder"
            :disabled="isSending"
          />
          <button type="submit" :disabled="isSending || !draftMessage.trim()">
            {{ isSending ? UI.sending : UI.send }}
          </button>
        </form>
      </div>

      <aside class="sidebar" :class="{ open: showSidebar }">
        <div class="sidebar-header">
          <h2>{{ BUSINESS_PANEL.title }}</h2>
        </div>

        <!-- 金融业务 Tabs（从配置动态生成，换领域时只要改 BUSINESS_PANEL.TABS） -->
        <div class="tabs tabs-wrap">
          <button
            v-for="tab in BUSINESS_PANEL.TABS"
            :key="tab.key"
            type="button"
            class="tab-button"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key; refreshObjects(tab.refreshKey || tab.key)"
          >{{ tab.label }}</button>
        </div>

        <p v-if="sidebarError" class="sidebar-error">{{ sidebarError }}</p>

        <!-- ── Tab: 客户信息 ────────────────────────────────────────── -->
        <div v-if="activeTab === 'customer'" class="sidebar-list">
          <div v-if="!customerInfo && !isLoadingSidebar" class="sidebar-empty">{{ BUSINESS_PANEL.EMPTY.customer }}</div>
          <article v-if="customerInfo" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ customerInfo?.customer_profile?.customer_name || BUSINESS_PANEL.CARD_DEFAULTS.customerTitle }}</div>
              <span class="status-badge status-success">{{ customerInfo?.customer_status || UI.customerStatusDefault }}</span>
            </div>
            <div class="card-meta">客户号：{{ customerInfo?.customer_profile?.customer_no || '-' }}</div>
            <div class="card-meta">客户类型：{{ customerTypeName(customerInfo?.customer_profile?.customer_type) }}</div>
            <div class="card-meta">风险等级：{{ customerInfo?.risk_level?.risk_level_name || riskName(customerInfo?.risk_level?.risk_level_code) }}</div>
            <div class="card-meta">KYC状态：{{ customerInfo?.kyc_status || '-' }}</div>
            <div class="card-meta">开户时间：{{ customerInfo?.customer_profile?.opened_at || '-' }}</div>
          </article>
        </div>

        <!-- ── Tab: 银行账户 ────────────────────────────────────────── -->
        <div v-else-if="activeTab === 'accounts'" class="sidebar-list">
          <div v-if="!accounts.length && !isLoadingSidebar" class="sidebar-empty">{{ BUSINESS_PANEL.EMPTY.accounts }}</div>
          <article v-for="acc in accounts" :key="acc.account_no" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ acc.account_product?.product_name || accountProductName(acc.account_product?.product_code) || BUSINESS_PANEL.CARD_DEFAULTS.accountTitle }}</div>
              <div class="card-amount">{{ currencyName(acc.currency_code) }} {{ fmtAmt(acc.balance_amount) }}</div>
            </div>
            <div class="card-meta">账号：{{ acc.account_no }}</div>
            <div class="card-meta">币种：{{ currencyName(acc.currency_code) }}（{{ acc.currency_code || 'CNY' }}）</div>
            <div class="card-meta">产品代码：{{ acc.account_product?.product_code || '-' }}</div>
          </article>
        </div>

        <!-- ── Tab: 交易流水 ────────────────────────────────────────── -->
        <div v-else-if="activeTab === 'transactions'" class="sidebar-list">
          <div v-if="!transactions.length && !isLoadingSidebar" class="sidebar-empty">{{ BUSINESS_PANEL.EMPTY.transactions }}</div>
          <article v-for="txn in transactions" :key="txn.transaction_no || txn.id" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ txn.transaction_type || BUSINESS_PANEL.CARD_DEFAULTS.transactionTitle }}</div>
              <div class="card-amount" :style="{ color: Number(txn.transaction_amount) >= 0 ? '#00b42a' : '#f53f3f' }">
                {{ Number(txn.transaction_amount) >= 0 ? '+' : '' }}{{ fmtAmt(txn.transaction_amount) }}
              </div>
            </div>
            <div class="card-meta">流水号：{{ txn.transaction_no || '-' }}</div>
            <div class="card-meta">时间：{{ txn.transaction_at || '-' }}</div>
            <div class="card-meta" v-if="txn.counterparty_name">交易对手：{{ txn.counterparty_name }}</div>
            <div class="card-meta">
              <span class="status-badge" :class="txn.transaction_status === 'success' ? 'status-success' : txn.transaction_status === 'failed' ? 'status-danger' : 'status-info'">
                {{ txn.transaction_status || '处理中' }}
              </span>
            </div>
          </article>
        </div>

        <!-- ── Tab: 理财（持仓 + 产品） ─────────────────────────────── -->
        <div v-else-if="activeTab === 'wealth'" class="sidebar-list">
          <div v-if="!wealthPositions.length && !wealthProducts.length && !isLoadingSidebar" class="sidebar-empty">{{ BUSINESS_PANEL.EMPTY.wealth }}</div>

          <template v-if="wealthPositions.length">
            <div class="section-label">{{ BUSINESS_PANEL.SECTIONS.wealth.positions }}</div>
            <article v-for="pos in wealthPositions" :key="pos.id || pos.position_no" class="sidebar-card">
              <div class="card-top">
                <div class="card-title">{{ pos.product_name || wealthName(pos.product_code) || BUSINESS_PANEL.CARD_DEFAULTS.wealthPosition }}</div>
                <div class="card-amount">{{ fmtAmt(pos.holding_amount || pos.market_value) }}</div>
              </div>
              <div class="card-meta">产品代码：{{ pos.product_code || '-' }}</div>
              <div class="card-meta">持有份额：{{ pos.holding_shares || pos.shares || '-' }}</div>
              <div class="card-meta" :style="{ color: Number(pos.income) >= 0 ? '#00b42a' : '#f53f3f' }">
                累计收益：{{ Number(pos.income) >= 0 ? '+' : '' }}{{ fmtAmt(pos.income) }}
              </div>
              <div class="card-meta">持仓状态：{{ pos.position_status || '-' }}</div>
            </article>
          </template>

          <template v-if="wealthProducts.length">
            <div class="section-label">{{ BUSINESS_PANEL.SECTIONS.wealth.products }}</div>
            <article v-for="prod in wealthProducts" :key="prod.product_code" class="sidebar-card">
              <div class="card-top">
                <div class="card-title">{{ prod.product_name || wealthName(prod.product_code) || BUSINESS_PANEL.CARD_DEFAULTS.wealthProduct }}</div>
                <div class="card-amount" style="color: #d97706;">
                  {{ prod.expected_yield_rate ? `${(Number(prod.expected_yield_rate) * 100).toFixed(2)}%` : '-' }}
                </div>
              </div>
              <div class="card-meta">产品代码：{{ prod.product_code }}</div>
              <div class="card-meta">产品类型：{{ wealthTypeName(prod.product_type) }} · 运作：{{ wealthOperationName(prod.operation_mode) }}</div>
              <div class="card-meta">风险等级：{{ riskName(prod.risk_level?.risk_level_code) || prod.risk_level || '-' }}</div>
              <div class="card-meta">状态：{{ openStatusName(prod.open_status) }}</div>
            </article>
          </template>
        </div>

        <!-- ── Tab: 信贷（授信额度 + 贷款产品） ─────────────────────── -->
        <div v-else-if="activeTab === 'loans'" class="sidebar-list">
          <div v-if="!creditLimits.length && !loanProducts.length && !isLoadingSidebar" class="sidebar-empty">{{ BUSINESS_PANEL.EMPTY.loans }}</div>

          <template v-if="creditLimits.length">
            <div class="section-label">{{ BUSINESS_PANEL.SECTIONS.loans.limits }}</div>
            <article v-for="lim in creditLimits" :key="lim.limit_no" class="sidebar-card">
              <div class="card-top">
                <div class="card-title">{{ loanName(lim.product_code) || BUSINESS_PANEL.CARD_DEFAULTS.loanLimit }}</div>
                <div class="card-amount">{{ fmtAmt(lim.total_limit_amount) }}</div>
              </div>
              <div class="card-meta">产品代码：{{ lim.product_code || '-' }}</div>
              <div class="card-meta">可用额度：{{ fmtAmt(lim.available_limit_amount) }}</div>
              <div class="card-meta">已用额度：{{ fmtAmt(Number(lim.total_limit_amount || 0) - Number(lim.available_limit_amount || 0) - Number(lim.frozen_limit_amount || 0)) }}</div>
              <div class="card-meta">额度编号：{{ lim.limit_no }}</div>
              <div class="card-meta">有效期至：{{ lim.valid_to || '-' }}</div>
            </article>
          </template>

          <template v-if="loanProducts.length">
            <div class="section-label">{{ BUSINESS_PANEL.SECTIONS.loans.products }}</div>
            <article v-for="loan in loanProducts" :key="loan.product_code" class="sidebar-card">
              <div class="card-top">
                <div class="card-title">{{ loan.product_name || loanName(loan.product_code) || BUSINESS_PANEL.CARD_DEFAULTS.loanProduct }}</div>
              </div>
              <div class="card-meta">产品代码：{{ loan.product_code }}</div>
              <div class="card-meta">贷款类型：{{ categoryName(loan.loan_type) || loan.loan_type || '-' }}</div>
              <div class="card-meta">年利率：{{ (Number(loan.annual_interest_rate) * 100).toFixed(1) }}%（{{ (Number(loan.min_interest_rate) * 100).toFixed(1) }}% ~ {{ (Number(loan.max_interest_rate) * 100).toFixed(1) }}%）</div>
              <div class="card-meta">金额范围：{{ fmtAmt(loan.min_amount) }} ~ {{ fmtAmt(loan.max_amount) }}</div>
              <div class="card-meta">期限范围：{{ loan.min_term_months }} ~ {{ loan.max_term_months }} 个月</div>
              <div class="card-meta">还款方式：{{ repaymentMethodName(loan.repayment_method) }}</div>
              <div class="card-meta">风险等级：{{ riskName(loan.risk_level?.risk_level_code) || '-' }}</div>
            </article>
          </template>
        </div>

        <!-- ── Tab: 还款账单 ──────────────────────────────────────── -->
        <div v-else-if="activeTab === 'repayments'" class="sidebar-list">
          <div v-if="!repaymentBills.length && !isLoadingSidebar" class="sidebar-empty">{{ BUSINESS_PANEL.EMPTY.repayments }}</div>
          <article v-for="bill in repaymentBills" :key="bill.bill_no" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ bill.bill_no ? `账单 ${bill.bill_no}` : BUSINESS_PANEL.CARD_DEFAULTS.repaymentBill }}</div>
              <div class="card-amount" style="color: #f53f3f;">待还 {{ fmtAmt(bill.outstanding_amount) }}</div>
            </div>
            <div class="card-meta">已还金额：{{ fmtAmt(bill.paid_amount) }}</div>
            <div class="card-meta">
              <span class="status-badge" :class="(bill.bill_status === 'settled' || bill.bill_status === 'paid') ? 'status-success' : bill.bill_status === 'overdue' ? 'status-danger' : 'status-warning'">
                {{ billStatusName(bill.bill_status) }}
              </span>
            </div>
          </article>
        </div>

        <!-- ── Tab: 逾期记录 ──────────────────────────────────────── -->
        <div v-else-if="activeTab === 'overdues'" class="sidebar-list">
          <div v-if="!overdues.length && !isLoadingSidebar" class="sidebar-empty">{{ BUSINESS_PANEL.EMPTY.overdues }}</div>
          <article v-for="od in overdues" :key="od.overdue_no" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ od.overdue_no ? `逾期 ${od.overdue_no}` : BUSINESS_PANEL.CARD_DEFAULTS.overdueRecord }}</div>
              <div class="card-amount" style="color: #f53f3f;">{{ fmtAmt(od.overdue_total_amount) }}</div>
            </div>
            <div class="card-meta">逾期天数：<b>{{ od.overdue_days || 0 }}</b> 天</div>
            <div class="card-meta">逾期本金：{{ fmtAmt(od.overdue_principal_amount) }} · 罚金：{{ fmtAmt(od.penalty_amount) }}</div>
            <div class="card-meta">催收状态：{{ collectionStatusName(od.collection_status) }}</div>
            <div class="card-meta">
              <span class="status-badge" :class="od.status === 'settled' ? 'status-success' : od.status === 'collection' ? 'status-danger' : 'status-warning'">
                {{ overdueStatusName(od.status) }}
              </span>
            </div>
          </article>
        </div>

        <!-- ── Tab: 通知消息 ──────────────────────────────────────── -->
        <div v-else-if="activeTab === 'notifications'" class="sidebar-list">
          <div v-if="!notifications.length && !isLoadingSidebar" class="sidebar-empty">{{ BUSINESS_PANEL.EMPTY.notifications }}</div>
          <article v-for="msg in notifications" :key="msg.notification_no || msg.id" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ msg.message_title || notificationTypeName(msg.message_type) || BUSINESS_PANEL.CARD_DEFAULTS.notification }}</div>
              <span class="status-badge" :class="msg.send_status === 'sent' ? 'status-success' : msg.send_status === 'failed' ? 'status-danger' : 'status-info'">
                {{ sendStatusName(msg.send_status) }}
              </span>
            </div>
            <div class="card-meta" v-if="msg.message_content">{{ msg.message_content }}</div>
            <div class="card-meta">类型：{{ notificationTypeName(msg.message_type) }}（{{ msg.message_type || '-' }}）</div>
            <div class="card-meta">时间：{{ msg.created_at || msg.sent_at || '-' }}</div>
          </article>
        </div>
      </aside>

      <div
        v-if="showSessionList || showSidebar"
        class="mobile-mask"
        @click="showSessionList = false; showSidebar = false"
      ></div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300..700&family=Zen+Maru+Gothic:wght@400;500;700&display=swap');

:global(*) {
  box-sizing: border-box;
}

:global(:root) {
  /* ── Palette (Light) ── */
  --color-bg-deep: #f0f2f5;
  --color-bg-mid: #eef0f3;
  --color-bg-surface: #f7f8fa;
  --color-surface: #ffffff;
  --color-surface-hover: #f5f6f8;
  --color-surface-dim: #fafbfc;
  --color-surface-raised: #f2f3f5;
  --color-surface-field: #f2f4f7;
  --color-text-primary: #1f2329;
  --color-text-secondary: #646a73;
  --color-text-muted: #8f959e;
  --color-text-inverse: #ffffff;
  /* Accent — 京东金融蓝 */
  --color-accent: #276EFF;
  --color-accent-strong: #1E5CE6;
  --color-accent-soft: rgba(39, 110, 255, 0.12);
  --color-accent-glow: rgba(39, 110, 255, 0.16);
  --color-accent-soft-bg: rgba(39, 110, 255, 0.06);
  /* Warm — amber (products/orders) */
  --color-warm: #f59e0b;
  --color-warm-strong: #d97706;
  --color-warm-soft: rgba(245, 158, 11, 0.12);
  --color-warm-glow: transparent;
  --color-warm-soft-bg: rgba(245, 158, 11, 0.06);
  /* Semantic */
  --color-success: #00b42a;
  --color-success-soft: rgba(0, 180, 42, 0.12);
  --color-info: #276EFF;
  --color-info-soft: rgba(39, 110, 255, 0.10);
  --color-danger: #f53f3f;
  --color-danger-soft: rgba(245, 63, 63, 0.10);
  /* Borders — subtle gray lines on light surfaces */
  --color-border: #e5e6eb;
  --color-border-light: #eef0f3;
  --color-border-strong: #d0d3d9;
  /* User bubble — 京东金融蓝（默认值，样式中已硬编码覆盖） */
  --color-user-bubble-bg: #276EFF;
  --color-user-bubble-text: #ffffff;
  --color-user-bubble-border: #276EFF;
  /* Conversation canvas — gray */
  --color-chat-bg: #f0f2f5;
  /* ── Radii ── */
  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 18px;
  --radius-xl: 20px;
  --radius-full: 9999px;
  /* ── Shadows (soft, for light theme) ── */
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 6px 20px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.10);
  --shadow-glow-teal: transparent;
  --shadow-glow-amber: transparent;
  --shadow-inner-glow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
  /* ── Transitions ── */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --duration-fast: 150ms;
  --duration-base: 250ms;
  --duration-slow: 400ms;
}

:global(body) {
  margin: 0;
  font-family: "Outfit", "Zen Maru Gothic", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--color-bg-deep);
  color: var(--color-text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:global(button),
:global(input) {
  font: inherit;
}

:global(#app) {
  min-height: 100vh;
}

.app-shell {
  min-height: 100vh;
  padding: 16px;
  position: relative;
  background: #f0f2f5;
}
.app-shell::before,
.app-shell::after,
.bg-canvas,
.workspace::before {
  display: none;
}

.workspace {
  width: min(1640px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 340px;
  gap: 16px;
  position: relative;
  z-index: 1;
}

.chat-card,
.sidebar,
.conversation-list {
  min-height: calc(100vh - 32px);
  height: calc(100vh - 32px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: border-color var(--duration-base) var(--ease-in-out), box-shadow var(--duration-base) var(--ease-in-out);
}
.chat-card {
  background: var(--color-chat-bg);
}
.sidebar {
  background: var(--color-surface);
}
.chat-card {
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-md);
}
.chat-card:hover {
  border-color: var(--color-border-strong);
}
.sidebar {
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-md);
}
.sidebar:hover {
  border-color: var(--color-border-strong);
}

/* ── 会话列表面板 ── */
.conversation-list {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
}
.conversation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border-light);
}
.conversation-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
}
.new-session-button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-accent);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent-strong);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.new-session-button:hover {
  background: var(--color-accent-soft);
}
.conversation-items {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.conversation-empty {
  padding: 24px 12px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
}
.conversation-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  padding: 9px 10px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  background: transparent;
  transition: background var(--duration-fast) var(--ease-in-out), border-color var(--duration-fast) var(--ease-in-out);
}
.conversation-item:hover {
  background: var(--color-surface-hover);
}
.conversation-item.active {
  background: var(--color-accent-soft-bg);
  border-color: var(--color-accent-soft);
}
.conversation-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
}
.conversation-preview {
  font-size: 14px;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conversation-item.active .conversation-preview {
  color: var(--color-accent-strong);
}
.conversation-time {
  font-size: 12px;
  color: var(--color-text-muted);
}
.conversation-delete {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-in-out);
}
.conversation-delete:hover {
  color: var(--color-danger);
  border-color: var(--color-danger);
  background: var(--color-danger-soft);
}

/* ── 头部操作区 / 移动端图标按钮 ── */
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}
.icon-button:hover {
  background: var(--color-surface-hover);
}
.mobile-only {
  display: none;
}
.mobile-mask {
  display: none;
}

.chat-header,
.sidebar-header {
  padding: 11px 14px;
  border-bottom: 1px solid var(--color-border-light);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.chat-header h1,
.sidebar-header h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.2;
  letter-spacing: -0.01em;
  color: var(--color-text-primary);
  font-weight: 700;
}

.sidebar-header h2 {
  font-size: 16px;
  color: var(--color-text-primary);
}

.chat-header p,
.sidebar-header p {
  margin: 6px 0 0;
  color: var(--color-text-secondary);
}

/* 客服信息 */
.service-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.service-avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.service-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  padding: 2px;
  background: linear-gradient(135deg, var(--color-accent), var(--color-success));
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
@keyframes avatarSpin {
  to { transform: rotate(360deg); }
}

.status-indicator {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 14px;
  height: 14px;
  background: var(--color-success);
  border: 3px solid var(--color-surface);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.service-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.service-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.service-status {
  font-size: 12px;
  color: var(--color-success);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.service-status::before {
  content: '';
  width: 6px;
  height: 6px;
  background: var(--color-success);
  border-radius: 50%;
}

.clear-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
  white-space: nowrap;
}
.clear-button:hover {
  background: rgba(251, 113, 133, 0.10);
  border-color: var(--color-danger);
  color: var(--color-danger);
  transform: translateY(-1px);
  box-shadow: 0 4px 18px var(--color-danger-soft);
}

.controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
  padding: 9px 14px;
  border-bottom: 1px solid var(--color-border-light);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
}

.field-row {
  display: flex;
  gap: 12px;
}

.field input,
.composer input {
  width: 100%;
  min-width: 0;
  min-height: 42px;
  padding: 9px 12px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface-field);
  color: var(--color-text-primary);
  font-size: 14.5px;
  line-height: 1.4;
  transition: border-color var(--duration-fast) var(--ease-in-out), box-shadow var(--duration-fast) var(--ease-in-out);
}
.field input::placeholder,
.composer input::placeholder {
  color: var(--color-text-muted);
}
.field input:focus,
.composer input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-soft);
}

.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Turn：去掉大卡片包裹，改为轻量分组，贴近常见客服聊天流 */
.turn-card {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 2px;
  background: transparent;
  border: none;
  animation: msgEnter 0.3s var(--ease-out-back) both;
}
@keyframes msgEnter {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
.turn-card::before,
.turn-card:hover::before {
  display: none;
}
.turn-card:hover {
  background: transparent;
}

.turn-header,
.turn-badge,
.turn-label,
.section-header,
.avatar-wrapper,
.avatar,
.status-dot,
.agent-info,
.agent-label,
.role-icon,
.role-label,
.msg-time {
  display: none;
}

/* ── 京东金融风格：对话区 ────────────────────────────── */
.turn-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 0;
}

/* 发送者元信息：名称+时间（用户在右，客服在左） */
.section-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 0 2px;
}
.section-meta .meta-name {
  font-weight: 600;
  color: #606266;
}
.section-meta .meta-time {
  color: #909399;
  font-weight: 400;
}
.user-meta {
  justify-content: flex-end;
}
.bot-meta {
  justify-content: flex-start;
}
.bot-meta .meta-name {
  color: #276EFF;
}

/* 气泡基础样式 */
.turn-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  max-width: 78%;
  position: relative;
  line-height: 1.6;
}

/* 用户气泡：京东金融蓝，白字，靠右，右圆角略小 */
.user-bubble {
  align-self: flex-end;
  margin-left: auto;
  background: linear-gradient(135deg, #276EFF 0%, #1E5CE6 100%);
  color: #ffffff;
  border-radius: 12px 4px 12px 12px;
  box-shadow: 0 2px 8px rgba(39, 110, 255, 0.18);
}

/* 客服气泡：白色，浅灰边，靠左，左圆角略小 */
.bot-bubble {
  align-self: flex-start;
  margin-right: auto;
  background: #ffffff;
  color: #1f2937;
  border: 1px solid #ececec;
  border-radius: 4px 12px 12px 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.bot-messages {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.turn-bubble p {
  margin: 0;
  font-size: 14.5px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.user-bubble p {
  color: #ffffff;
}
/* 气泡中小文字颜色 */
.user-bubble .object-card-title,
.user-bubble .object-card-meta,
.user-bubble .object-card-price {
  color: #ffffff !important;
}
.user-bubble .status-badge {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
  border: none;
}

/* ── 对话区主色调整为京东金融蓝 ─────────────────────── */
.bot-actions .tts-button,
.bot-actions .copy-button,
.suggestion-chip,
.primary-button {
  background: #276EFF;
  border-color: #276EFF;
}
.primary-button:hover {
  background: #1E5CE6;
  border-color: #1E5CE6;
  box-shadow: 0 4px 12px rgba(39, 110, 255, 0.25);
}

/* 历史消息分隔线 */
.history-divider {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--color-text-muted);
  font-size: 13px;
  padding: 8px 0;
}

.history-divider::before,
.history-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--color-border-strong);
}

.history-divider span {
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  font-size: 12px;
}

.welcome {
  flex-shrink: 0;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.welcome-card {
  position: relative;
  max-width: 460px;
  width: 100%;
  padding: 32px 28px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  text-align: center;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  animation: welcomeFloat 0.6s var(--ease-out-back);
}
@keyframes welcomeFloat {
  from { opacity: 0; transform: translateY(36px) scale(0.94); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.welcome-glow {
  position: absolute;
  top: -100px; left: 50%; transform: translateX(-50%);
  width: 350px; height: 350px;
  background: radial-gradient(circle, rgba(45,212,191,0.08) 0%, rgba(45,212,191,0.02) 45%, transparent 70%);
  pointer-events: none;
}
.welcome-avatar-wrapper {
  position: relative;
  display: inline-block;
  margin-bottom: 20px;
}
.welcome-avatar {
  width: 88px; height: 88px;
  border-radius: 50%;
  padding: 4px;
  background: conic-gradient(var(--color-success), var(--color-accent), var(--color-warm), var(--color-success));
  animation: avatarSpin 4s linear infinite;
  box-shadow: 0 0 36px var(--color-accent-glow);
}
.welcome-status-pulse {
  position: absolute;
  bottom: 6px; right: 6px;
  width: 18px; height: 18px;
  background: var(--color-success);
  border: 3px solid var(--color-bg-mid);
  border-radius: 50%;
  animation: pulse 2s infinite;
  box-shadow: 0 0 16px rgba(52, 211, 153, 0.4);
}
.welcome-greeting {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
}
.welcome-subtitle {
  margin: 0 0 28px;
  color: var(--color-text-secondary);
  font-size: 15px;
}
.welcome-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-bottom: 28px;
}
.welcome-chip {
  padding: 10px 20px;
  border: 1px solid rgba(45, 212, 191, 0.16);
  border-radius: var(--radius-full);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.welcome-chip:hover:not(:disabled) {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px var(--color-accent-glow);
}
.welcome-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.welcome-features {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
}

.sidebar-empty {
  margin: auto;
  max-width: 420px;
  color: var(--color-text-muted);
  text-align: center;
  line-height: 1.7;
}

.typing-indicator {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 0 20px;
  animation: msgEnter 0.3s var(--ease-out-expo);
}
.avatar-small {
  width: 34px; height: 34px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid var(--color-success);
  box-shadow: 0 0 12px rgba(52, 211, 153, 0.25);
}
.typing-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: 20px 20px 20px 6px;
  box-shadow: var(--shadow-sm);
}
.typing-dots {
  display: flex;
  gap: 4px;
  align-items: center;
}
.typing-dots span {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: dotBounce 1.2s ease-in-out infinite;
}
.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
  30% { transform: translateY(-8px); opacity: 1; }
}
.typing-label {
  font-size: 13px;
  color: var(--color-text-muted);
}

.object-card-price {
  font-size: 15px;
  font-weight: 600;
}

/* ── 状态徽章 ────────────────────────────────────────────── */
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 12px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.status-warning {
  background: var(--color-warm-soft);
  color: var(--color-warm-strong);
  border: 1px solid rgba(245, 158, 11, 0.25);
}
.status-info {
  background: var(--color-info-soft);
  color: var(--color-info);
  border: 1px solid rgba(56, 189, 248, 0.25);
}
.status-success {
  background: var(--color-success-soft);
  color: var(--color-success);
  border: 1px solid rgba(52, 211, 153, 0.25);
}
.status-muted {
  background: rgba(113, 111, 104, 0.12);
  color: var(--color-text-muted);
  border: 1px solid rgba(113, 111, 104, 0.18);
}
.status-danger {
  background: var(--color-danger-soft);
  color: var(--color-danger);
  border: 1px solid rgba(251, 113, 133, 0.25);
}

/* ── 商品图片（侧边栏） ────────────────────────────────────── */
.card-image-wrapper {
  width: 100%;
  height: 140px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-surface-field);
  border: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--duration-base) var(--ease-out-expo);
}
.sidebar-card:hover .card-image {
  transform: scale(1.05);
}
.card-image-placeholder {
  font-size: 40px;
  opacity: 0.5;
}

/* ── 对象卡片图片（聊天区） ─────────────────────────────────── */
.object-card-image {
  width: 100%;
  height: 150px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  border: 1px solid var(--color-border-light);
  background: var(--color-surface-field);
}

/* Turn 卡片中的对象卡片样式调整 */
.turn-bubble .object-card {
  min-width: 200px;
}

.user-bubble .object-card-badge {
  background: rgba(92, 43, 34, 0.08);
  color: var(--color-user-bubble-text);
}

.composer button,
.secondary-button,
.tab-button {
  min-height: 42px;
  padding: 9px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.2;
  transition:
    transform var(--duration-fast) var(--ease-out-expo),
    box-shadow var(--duration-fast) var(--ease-out-expo),
    background var(--duration-fast) var(--ease-in-out),
    border-color var(--duration-fast) var(--ease-in-out);
}

.composer button:hover:not(:disabled),
.secondary-button:hover:not(:disabled),
.tab-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.composer button:active:not(:disabled),
.secondary-button:active:not(:disabled),
.tab-button:active:not(:disabled) {
  transform: translateY(0);
}

.composer button:disabled,
.secondary-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.error-message,
.sidebar-error {
  margin: 0;
  padding: 0 24px 14px;
  color: var(--color-danger);
  font-size: 13px;
  font-weight: 500;
}

.composer {
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  gap: 8px;
  padding: 10px 14px;
  border-top: 1px solid var(--color-border-light);
  background: #e9ebee;
}

.composer button {
  min-width: 96px;
  padding-inline: 20px;
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-strong));
  border-color: transparent;
  color: #f0fdfa;
  box-shadow: 0 14px 28px var(--color-accent-glow);
}
.composer button:hover:not(:disabled) {
  box-shadow: 0 18px 36px var(--color-accent-glow);
  transform: translateY(-2px);
}

.sidebar {
  display: flex;
  flex-direction: column;
}

.tabs {
  display: flex;
  gap: 8px;
  padding: 16px 24px 12px;
  border-bottom: 1px solid var(--color-border-light);
}
.tabs-wrap {
  flex-wrap: wrap;
  row-gap: 8px;
}

.section-label {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent-strong);
  padding: 4px 0;
  margin-top: 4px;
  letter-spacing: 0.02em;
}

.tab-button {
  min-width: 64px;
  padding-inline: 14px;
}

.tab-button.active {
  background: linear-gradient(135deg, var(--color-accent-strong), var(--color-accent));
  border-color: transparent;
  color: #f0fdfa;
  box-shadow: 0 4px 14px var(--color-accent-glow);
}

.sidebar-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sidebar-card {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.sidebar-card:hover {
  background: var(--color-surface-hover);
  border-color: rgba(245, 158, 11, 0.18);
  transform: translateY(-3px);
  box-shadow: var(--shadow-md), var(--shadow-glow-amber);
}

.card-top {
  display: flex;
  gap: 12px;
  justify-content: space-between;
  align-items: flex-start;
}

.card-title {
  font-size: 15px;
  line-height: 1.5;
  color: var(--color-text-primary);
  font-weight: 600;
}

.card-amount {
  flex-shrink: 0;
  color: var(--color-warm-strong);
  font-weight: 700;
}

.card-meta {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.bot-text-row { display: flex; align-items: flex-start; gap: 8px; }
.bot-text-row p { flex: 1; margin: 0; }
.bot-actions {
  display: flex; gap: 6px; flex-shrink: 0; align-items: center;
}
.tts-button, .copy-button {
  flex-shrink: 0; width: 32px; height: 32px; padding: 0;
  border: 1px solid var(--color-border-light); border-radius: 8px;
  background: var(--color-surface); cursor: pointer;
  font-size: 14px; display: inline-flex; align-items: center; justify-content: center;
  transition: all var(--duration-base) var(--ease-out-expo); color: var(--color-text-muted);
}
.tts-button:hover:not(:disabled), .copy-button:hover:not(:disabled) {
  background: var(--color-accent-soft); border-color: var(--color-accent); color: var(--color-accent-strong);
  transform: scale(1.1);
}
.tts-button:disabled, .copy-button:disabled { cursor: not-allowed; opacity: 0.65; }
.tts-button.tts-playing { background: var(--color-accent-soft); border-color: var(--color-accent); color: var(--color-accent-strong); }
.tts-bars {
  display: inline-flex; align-items: flex-end; gap: 3px; height: 16px;
}
.tts-bars span {
  width: 3px;
  background: var(--color-accent);
  border-radius: 2px;
  animation: barBounce 0.6s ease-in-out infinite;
}
.tts-bars span:nth-child(1) { height: 8px; animation-delay: 0s; }
.tts-bars span:nth-child(2) { height: 14px; animation-delay: 0.15s; }
.tts-bars span:nth-child(3) { height: 10px; animation-delay: 0.3s; }
@keyframes barBounce {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}
.tts-spinner {
  width: 14px; height: 14px;
  border: 2px solid var(--color-accent-soft); border-top-color: var(--color-accent);
  border-radius: 50%; animation: tts-spin 0.6s linear infinite;
}
@keyframes tts-spin { to { transform: rotate(360deg); } }
.copy-button.copy-done {
  background: var(--color-success-soft);
  border-color: var(--color-success);
  color: var(--color-success);
}

.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border-light);
}
.suggestion-chip {
  padding: 6px 14px;
  border: 1px solid rgba(45, 212, 191, 0.14);
  border-radius: var(--radius-full);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.suggestion-chip:hover:not(:disabled) {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  transform: translateY(-1px);
}
.suggestion-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.full-width {
  width: 100%;
}

.sidebar .secondary-button.full-width {
  min-height: 42px;
}

.sidebar-empty {
  margin: auto;
  max-width: 420px;
  color: var(--color-text-muted);
  text-align: center;
  line-height: 1.7;
}

/* Turn 卡片中的对象卡片样式调整 */
.turn-bubble .object-card {
  min-width: 200px;
}

.user-bubble .object-card-badge {
  background: rgba(92, 43, 34, 0.08);
  color: var(--color-user-bubble-text);
}

@media (max-width: 1180px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  /* 会话列表与右侧对象栏在移动端变为抽屉 */
  .conversation-list,
  .sidebar {
    position: fixed;
    top: 0;
    bottom: 0;
    width: 84%;
    max-width: 340px;
    height: 100vh;
    z-index: 60;
    border-radius: 0;
    box-shadow: var(--shadow-lg);
    transition: transform 0.26s var(--ease-out-expo);
  }
  .conversation-list {
    left: 0;
    transform: translateX(-100%);
  }
  .conversation-list.open {
    transform: translateX(0);
  }
  .sidebar {
    right: 0;
    transform: translateX(100%);
  }
  .sidebar.open {
    transform: translateX(0);
  }

  .mobile-only {
    display: inline-flex;
  }
  .mobile-mask {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(17, 23, 29, 0.42);
    z-index: 50;
  }
}

@media (max-width: 720px) {
  .app-shell {
    padding: 0;
  }

  .workspace {
    gap: 0;
    width: 100%;
  }

  .chat-card {
    height: 100dvh;
    min-height: 100dvh;
    border-radius: 0;
    border-left: none;
    border-right: none;
  }

  .field-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
