<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import 'element-plus/es/components/message-box/style/css'
import xiaoerAvatar from './assets/xiaoer.png'
import userProfileAvatar from './assets/userProfileAvatar.svg'

// sender_id 通过 URL 参数传入（?sender_id=xxx），未指定时默认 CUS0000001（金融客户号格式）
function resolveSenderId() {
  const param = new URLSearchParams(window.location.search).get('sender_id')
  return param && param.trim() ? param.trim() : 'CUS0000001'
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
const creditLimits = ref([])
const loanContracts = ref([])
const repaymentBills = ref([])
const collectionCases = ref([])

const isLoadingSidebar = ref(false)
const sidebarError = ref('')
const activeTab = ref('customer')

// ── 构建金融 API 请求头（X-Channel-Code + Authorization Bearer） ──────
function buildFinHeaders(extra = {}) {
  return {
    'X-Channel-Code': 'mobile_bank',
    'Authorization': `Bearer ${senderId.value.trim()}`,
    ...extra,
  }
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

// 客服数字人配置
const customerService = {
  name: '小谷',
  title: '金牌客服',
  avatar: xiaoerAvatar,
  status: '在线'
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
const finApiCustomerDetail = computed(
  () => `/api/v1/customers/${encodeURIComponent(senderId.value.trim())}`
)
const finApiCustomerAccounts = computed(
  () => `/api/v1/customers/${encodeURIComponent(senderId.value.trim())}/accounts`
)
const finApiAccountTransactions = (accountNo) =>
  `/api/v1/accounts/${encodeURIComponent(accountNo)}/transactions`
const finApiWealthProducts = '/api/v1/wealth/products'
const finApiWealthPositions = computed(
  () => `/api/v1/customers/${encodeURIComponent(senderId.value.trim())}/wealth/positions`
)
const finApiLoanProducts = '/api/v1/loan/products'
const finApiCreditLimits = computed(
  () => `/api/v1/customers/${encodeURIComponent(senderId.value.trim())}/credit-limits`
)
const finApiLoanContracts = computed(
  () => `/api/v1/customers/${encodeURIComponent(senderId.value.trim())}/loan/contracts`
)
const finApiRepaymentBills = computed(
  () => `/api/v1/repayment/bills?customer_no=${encodeURIComponent(senderId.value.trim())}`
)
const finApiCollectionCases = computed(
  () => `/api/v1/collection/customers/${encodeURIComponent(senderId.value.trim())}/cases`
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
  return message.objectType === 'order' ? '订单对象' : '商品对象'
}

function getObjectIdentifier(message) {
  const payload = message.payload ?? {}
  const id = payload.order_id ?? payload.product_id ?? payload.id
  const label = message.objectType === 'order' ? '订单号' : '商品号'
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
async function fetchFin(endpoint, headers = {}) {
  const res = await fetch(endpoint, { headers: buildFinHeaders(headers) })
  const payload = await res.json()
  if (!res.ok) throw new Error(payload?.detail || payload?.message || `请求 ${endpoint} 失败`)
  return payload?.data ?? payload ?? null
}

// 刷新右侧「业务对象」列表。
// which: 'all' | 'customer' | 'accounts' | 'transactions' | 'wealth' | 'loans' | 'repayments' | 'collections'
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
        try {
          customerInfo.value = await fetchFin(finApiCustomerDetail.value)
        } catch (e) { customerInfo.value = null }
      })())
    }

    // ── 银行账户 ──────────────────────────────────────────────
    if (need('accounts')) {
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiCustomerAccounts.value)
          accounts.value = Array.isArray(data?.accounts) ? data.accounts : Array.isArray(data) ? data : []
        } catch (e) { accounts.value = [] }
      })())
    }

    // ── 交易流水（取第一个账户的流水，若无则为空） ──────────────
    if (need('transactions')) {
      tasks.push((async () => {
        try {
          // 先确保有账户列表
          let accts = accounts.value
          if (!accts.length) {
            const data = await fetchFin(finApiCustomerAccounts.value)
            accts = Array.isArray(data?.accounts) ? data.accounts : Array.isArray(data) ? data : []
          }
          if (accts.length) {
            const accNo = accts[0].account_no || accts[0].accountNo
            const data = await fetchFin(finApiAccountTransactions(accNo))
            transactions.value = Array.isArray(data?.transactions) ? data.transactions
              : Array.isArray(data?.items) ? data.items
              : Array.isArray(data) ? data : []
          } else {
            transactions.value = []
          }
        } catch (e) { transactions.value = [] }
      })())
    }

    // ── 理财产品 + 持仓 ──────────────────────────────────────
    if (need('wealth')) {
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiWealthProducts)
          wealthProducts.value = Array.isArray(data?.products) ? data.products
            : Array.isArray(data?.items) ? data.items
            : Array.isArray(data) ? data : []
        } catch (e) { wealthProducts.value = [] }
      })())
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiWealthPositions.value)
          wealthPositions.value = Array.isArray(data?.positions) ? data.positions
            : Array.isArray(data?.items) ? data.items
            : Array.isArray(data) ? data : []
        } catch (e) { wealthPositions.value = [] }
      })())
    }

    // ── 贷款：授信额度 + 合同 ─────────────────────────────────
    if (need('loans')) {
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiCreditLimits.value)
          creditLimits.value = Array.isArray(data?.limits) ? data.limits
            : Array.isArray(data?.items) ? data.items
            : Array.isArray(data) ? data : []
        } catch (e) { creditLimits.value = [] }
      })())
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiLoanContracts.value)
          loanContracts.value = Array.isArray(data?.contracts) ? data.contracts
            : Array.isArray(data?.items) ? data.items
            : Array.isArray(data) ? data : []
        } catch (e) { loanContracts.value = [] }
      })())
    }

    // ── 还款账单 ──────────────────────────────────────────────
    if (need('repayments')) {
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiRepaymentBills.value)
          repaymentBills.value = Array.isArray(data?.bills) ? data.bills
            : Array.isArray(data?.items) ? data.items
            : Array.isArray(data) ? data : []
        } catch (e) { repaymentBills.value = [] }
      })())
    }

    // ── 催收案件 ──────────────────────────────────────────────
    if (need('collections')) {
      tasks.push((async () => {
        try {
          const data = await fetchFin(finApiCollectionCases.value)
          collectionCases.value = Array.isArray(data?.cases) ? data.cases
            : Array.isArray(data?.items) ? data.items
            : Array.isArray(data) ? data : []
        } catch (e) { collectionCases.value = [] }
      })())
    }

    await Promise.all(tasks)
  } catch (error) {
    sidebarError.value = error instanceof Error ? error.message : '加载业务对象失败。'
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
      throw new Error(data.detail || '加载历史消息失败。')
    }
    if (currentSenderId === senderId.value.trim()) {
      setHistoryMessages(Array.isArray(data?.messages) ? data.messages : [])
      await scrollToBottom()
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载历史消息失败。'
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
      throw new Error(data.detail || '加载会话列表失败。')
    }
    sessions.value = Array.isArray(data?.sessions) ? data.sessions : []
  } catch (error) {
    console.error('加载会话列表失败：', error)
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
    console.error('重置会话失败：', error)
  }
  await fetchSessions()
  activeSessionId.value = currentSessionId.value
  messages.value = []
  draftMessage.value = ''
  errorMessage.value = ''
}

async function deleteSession(id) {
  try {
    await ElMessageBox.confirm('删除后不可恢复，确定删除该会话？', '删除会话', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
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
      throw new Error(data.detail || '删除会话失败。')
    }
    if (id === activeSessionId.value) {
      activeSessionId.value = null
      messages.value = []
    }
    await fetchSessions()
  } catch (error) {
    console.error('删除会话失败：', error)
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
      throw new Error(data.detail || '请求失败。')
    }

    appendBotMessages(data.messages ?? [])
    await fetchSessions()
    syncActiveToCurrent()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '请求失败。'
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
    errorMessage.value = '请先输入 sender_id。'
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
    errorMessage.value = '请先输入 sender_id。'
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
    errorMessage.value = '请先输入 sender_id。'
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
      creditLimits.value = []
      loanContracts.value = []
      repaymentBills.value = []
      collectionCases.value = []
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
          <h2>会话</h2>
          <button type="button" class="new-session-button" @click="startNewSession">
            <span>＋</span>
            <span>新对话</span>
          </button>
        </div>
        <div class="conversation-items">
          <div v-if="!sessions.length" class="conversation-empty">暂无会话</div>
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="conversation-item"
            :class="{ active: s.session_id === activeSessionId }"
          >
            <div class="conversation-main" @click="selectSession(s.session_id)">
              <span class="conversation-preview">{{ s.preview || '新会话' }}</span>
              <span class="conversation-time">{{ formatSessionTime(s.last_activity_at) }}</span>
            </div>
            <button
              type="button"
              class="conversation-delete"
              title="删除会话"
              @click.stop="deleteSession(s.session_id)"
            >🗑</button>
          </div>
        </div>
      </aside>

      <div class="chat-card">
        <header class="chat-header">
          <div class="header-content">
            <button type="button" class="icon-button mobile-only" title="会话列表" @click="showSessionList = true">
              <span>☰</span>
            </button>
            <div class="header-info">
              <h1>金融客服系统</h1>
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
              <button type="button" class="icon-button mobile-only" title="业务对象" @click="showSidebar = true">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <circle cx="9" cy="21" r="1"></circle>
                  <circle cx="20" cy="21" r="1"></circle>
                  <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
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
                <img :src="customerService.avatar" class="welcome-avatar" alt="小谷" />
                <span class="welcome-status-pulse"></span>
              </div>
              <h2 class="welcome-greeting">Hi，我是 {{ customerService.name }}</h2>
              <p class="welcome-subtitle">你的专属金融客服，随时为你服务</p>
              <div class="welcome-chips">
                <button
                  v-for="chip in ['查询账户余额', '查看交易流水', '理财产品推荐', '贷款申请进度', '还款计划查询', '催收案件详情']"
                  :key="chip"
                  type="button"
                  class="welcome-chip"
                  :disabled="isSending"
                  @click="sendQuickText(chip)"
                >{{ chip }}</button>
              </div>
              <p class="welcome-features">
                <span>💬 文字对话</span>
                <span>🔊 语音播报</span>
                <span>🏦 账户查询</span>
                <span>💰 理财信贷</span>
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
              <!-- Turn 标识 -->
              <div class="turn-header">
                <span class="turn-badge">Turn {{ item.index }}</span>
                <span class="turn-label">对话轮次</span>
              </div>

              <!-- 用户消息区域 -->
              <div v-if="item.userMessage" class="turn-section user-section">
                <div class="section-header">
                  <div class="avatar-wrapper user-avatar">
                    <img :src="userProfile.avatar" class="avatar" />
                  </div>
                  <div class="agent-info">
                    <span class="agent-name">{{ userProfile.name }}</span>
                    <span class="agent-label">用户</span>
                  </div>
                </div>
                <div class="turn-bubble user-bubble">
                  <template v-if="item.userMessage.type === 'object'">
                    <div class="object-card" :class="`object-card-${item.userMessage.objectType}`">
                      <div class="object-card-badge">
                        {{ item.userMessage.objectType === 'order' ? '订单对象' : '商品对象' }}
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
                  <div class="msg-time">{{ formatTime(item.userMessage.timestamp) }}</div>
                </div>
              </div>

              <!-- 客服回复区域 -->
              <div v-if="item.botMessages.length > 0" class="turn-section bot-section">
                <div class="section-header">
                  <div class="avatar-wrapper service-avatar">
                    <img :src="customerService.avatar" class="avatar" />
                    <span class="status-dot"></span>
                  </div>
                  <div class="agent-info">
                    <span class="agent-name">{{ customerService.name }}</span>
                    <span class="agent-label">{{ customerService.title }}</span>
                  </div>
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
                          {{ botMsg.objectType === 'order' ? '订单对象' : '商品对象' }}
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
                            :title="ttsState[botMsg.id] === 'playing' ? '正在播放...' : '语音播报'"
                            @click.stop="playTts(botMsg)">
                            <span v-if="ttsState[botMsg.id] === 'loading'" class="tts-spinner"></span>
                            <span v-else-if="ttsState[botMsg.id] === 'playing'" class="tts-bars">
                              <span></span><span></span><span></span>
                            </span>
                            <span v-else>🔈</span>
                          </button>
                          <button type="button" class="copy-button"
                            :class="{ 'copy-done': copyState[botMsg.id] }"
                            :title="copyState[botMsg.id] ? '已复制' : '复制文字'"
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
            <img :src="customerService.avatar" class="avatar-small" alt="小谷" />
          </div>
          <div class="typing-bubble">
            <span class="typing-dots">
              <span></span><span></span><span></span>
            </span>
            <span class="typing-label">小谷正在输入...</span>
          </div>
        </div>

        <p v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </p>

        <form class="composer" @submit.prevent="sendTextMessage">
          <input
            v-model="draftMessage"
            type="text"
            placeholder="请输入咨询内容..."
            :disabled="isSending"
          />
          <button type="submit" :disabled="isSending || !draftMessage.trim()">
            {{ isSending ? '发送中...' : '发送' }}
          </button>
        </form>
      </div>

      <aside class="sidebar" :class="{ open: showSidebar }">
        <div class="sidebar-header">
          <h2>业务对象</h2>
        </div>

        <!-- 金融业务 Tabs -->
        <div class="tabs tabs-wrap">
          <button type="button" class="tab-button" :class="{ active: activeTab === 'customer' }"
            @click="activeTab = 'customer'; refreshObjects('customer')">客户</button>
          <button type="button" class="tab-button" :class="{ active: activeTab === 'accounts' }"
            @click="activeTab = 'accounts'; refreshObjects('accounts')">账户</button>
          <button type="button" class="tab-button" :class="{ active: activeTab === 'transactions' }"
            @click="activeTab = 'transactions'; refreshObjects('transactions')">交易</button>
          <button type="button" class="tab-button" :class="{ active: activeTab === 'wealth' }"
            @click="activeTab = 'wealth'; refreshObjects('wealth')">理财</button>
          <button type="button" class="tab-button" :class="{ active: activeTab === 'loans' }"
            @click="activeTab = 'loans'; refreshObjects('loans')">贷款</button>
          <button type="button" class="tab-button" :class="{ active: activeTab === 'repayments' }"
            @click="activeTab = 'repayments'; refreshObjects('repayments')">还款</button>
          <button type="button" class="tab-button" :class="{ active: activeTab === 'collections' }"
            @click="activeTab = 'collections'; refreshObjects('collections')">催收</button>
        </div>

        <p v-if="sidebarError" class="sidebar-error">{{ sidebarError }}</p>

        <!-- ── Tab: 客户信息 ────────────────────────────────────────── -->
        <div v-if="activeTab === 'customer'" class="sidebar-list">
          <div v-if="!customerInfo && !isLoadingSidebar" class="sidebar-empty">
            暂无客户数据
          </div>
          <article v-if="customerInfo" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">
                {{ customerInfo.name || customerInfo.full_name || customerInfo.customer_name || '客户信息' }}
              </div>
              <span
                class="status-badge"
                :class="(customerInfo.status === 'ACTIVE' || customerInfo.status === 'active') ? 'status-success' : 'status-muted'"
              >{{ customerInfo.status || '正常' }}</span>
            </div>
            <div class="card-meta">客户号：{{ customerInfo.customer_no || customerInfo.id || '-' }}</div>
            <div class="card-meta">客户类型：{{ customerInfo.customer_type || customerInfo.type || '个人' }}</div>
            <div class="card-meta">手机号：{{ customerInfo.phone || customerInfo.mobile || customerInfo.contact_phone || '-' }}</div>
            <div class="card-meta">证件号：{{ customerInfo.id_card_no || customerInfo.id_number || '-' }}</div>
            <div class="card-meta">注册时间：{{ customerInfo.created_at || customerInfo.register_time || '-' }}</div>
          </article>
        </div>

        <!-- ── Tab: 银行账户 ────────────────────────────────────────── -->
        <div v-else-if="activeTab === 'accounts'" class="sidebar-list">
          <div v-if="!accounts.length && !isLoadingSidebar" class="sidebar-empty">暂无账户数据</div>
          <article v-for="acc in accounts" :key="acc.account_no || acc.accountNo || acc.id" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ acc.account_name || acc.account_type || '银行账户' }}</div>
              <div class="card-amount">{{ formatAmount(acc.balance || acc.available_balance) }}</div>
            </div>
            <div class="card-meta">账号：{{ acc.account_no || acc.accountNo || '-' }}</div>
            <div class="card-meta">币种：{{ acc.currency || 'CNY' }} · 类型：{{ acc.account_type || '-' }}</div>
            <div class="card-meta">开户行：{{ acc.bank_name || acc.branch_name || '-' }}</div>
            <div class="card-meta">
              <span
                class="status-badge"
                :class="(acc.status === 'ACTIVE' || acc.status === 'active' || acc.status === '正常') ? 'status-success' : 'status-muted'"
              >{{ acc.status || '正常' }}</span>
            </div>
          </article>
        </div>

        <!-- ── Tab: 交易流水 ────────────────────────────────────────── -->
        <div v-else-if="activeTab === 'transactions'" class="sidebar-list">
          <div v-if="!transactions.length && !isLoadingSidebar" class="sidebar-empty">暂无交易流水</div>
          <article
            v-for="txn in transactions"
            :key="txn.txn_id || txn.transaction_id || txn.id"
            class="sidebar-card"
          >
            <div class="card-top">
              <div class="card-title">{{ txn.txn_type || txn.transaction_type || txn.type || '交易' }}</div>
              <div
                class="card-amount"
                :style="{ color: (txn.direction === 'IN' || txn.amount > 0) ? '#00b42a' : '#f53f3f' }"
              >
                {{ (txn.direction === 'IN' || txn.amount > 0) ? '+' : '-' }}{{ formatAmount(txn.amount) }}
              </div>
            </div>
            <div class="card-meta">流水号：{{ txn.txn_id || txn.transaction_id || '-' }}</div>
            <div class="card-meta">账户：{{ txn.account_no || '-' }}</div>
            <div class="card-meta">摘要：{{ txn.remark || txn.summary || '-' }}</div>
            <div class="card-meta">时间：{{ txn.txn_time || txn.created_at || '-' }}</div>
            <div class="card-meta">
              <span
                class="status-badge"
                :class="(txn.status === 'SUCCESS' || txn.status === 'success' || txn.status === '成功')
                  ? 'status-success'
                  : (txn.status === 'FAILED' || txn.status === 'failed') ? 'status-danger' : 'status-info'"
              >{{ txn.status || '处理中' }}</span>
            </div>
          </article>
        </div>

        <!-- ── Tab: 理财（产品 + 持仓） ─────────────────────────────── -->
        <div v-else-if="activeTab === 'wealth'" class="sidebar-list">
          <div v-if="!wealthProducts.length && !wealthPositions.length && !isLoadingSidebar" class="sidebar-empty">
            暂无理财数据
          </div>

          <!-- 持仓 -->
          <template v-if="wealthPositions.length">
            <div class="section-label">我的持仓</div>
            <article
              v-for="pos in wealthPositions"
              :key="pos.position_id || pos.product_code + '-' + (pos.id || '')"
              class="sidebar-card"
            >
              <div class="card-top">
                <div class="card-title">{{ pos.product_name || pos.product_code || '理财产品' }}</div>
                <div class="card-amount">{{ formatAmount(pos.market_value || pos.holding_amount || pos.hold_amount) }}</div>
              </div>
              <div class="card-meta">产品代码：{{ pos.product_code || '-' }}</div>
              <div class="card-meta">持有份额：{{ pos.shares || pos.holding_shares || '-' }}</div>
              <div class="card-meta">持仓成本：{{ formatAmount(pos.cost || pos.cost_value) }}</div>
              <div class="card-meta" v-if="pos.profit || pos.profit_loss">
                浮动盈亏：
                <span :style="{ color: Number(pos.profit || pos.profit_loss) >= 0 ? '#00b42a' : '#f53f3f' }">
                  {{ Number(pos.profit || pos.profit_loss) >= 0 ? '+' : '' }}{{ formatAmount(pos.profit || pos.profit_loss) }}
                </span>
              </div>
              <div class="card-meta">购买时间：{{ pos.purchase_time || pos.created_at || '-' }}</div>
            </article>
          </template>

          <!-- 理财产品列表 -->
          <template v-if="wealthProducts.length">
            <div class="section-label">在售产品</div>
            <article
              v-for="prod in wealthProducts"
              :key="prod.product_id || prod.product_code || prod.id"
              class="sidebar-card"
            >
              <div class="card-top">
                <div class="card-title">{{ prod.product_name || prod.name || '理财产品' }}</div>
                <div class="card-amount" style="color: #d97706;">
                  {{ prod.annualized_return || prod.expected_return || prod.yield_rate ? `${prod.annualized_return || prod.expected_return || prod.yield_rate}%` : '-' }}
                </div>
              </div>
              <div class="card-meta">产品代码：{{ prod.product_code || '-' }}</div>
              <div class="card-meta">风险等级：{{ prod.risk_level || 'R1' }} · 期限：{{ prod.term || prod.duration || '-' }}</div>
              <div class="card-meta">起购金额：{{ formatAmount(prod.min_amount || prod.min_purchase) }}</div>
              <div class="card-meta">产品类型：{{ prod.product_type || '固定收益' }}</div>
            </article>
          </template>
        </div>

        <!-- ── Tab: 贷款（授信 + 合同） ─────────────────────────────── -->
        <div v-else-if="activeTab === 'loans'" class="sidebar-list">
          <div v-if="!creditLimits.length && !loanContracts.length && !isLoadingSidebar" class="sidebar-empty">
            暂无贷款数据
          </div>

          <!-- 授信额度 -->
          <template v-if="creditLimits.length">
            <div class="section-label">授信额度</div>
            <article
              v-for="lim in creditLimits"
              :key="lim.credit_id || lim.id || lim.product_code"
              class="sidebar-card"
            >
              <div class="card-top">
                <div class="card-title">{{ lim.product_name || lim.product_code || '授信额度' }}</div>
                <div class="card-amount">{{ formatAmount(lim.total_amount || lim.limit_amount) }}</div>
              </div>
              <div class="card-meta">可用额度：{{ formatAmount(lim.available_amount || lim.available) }}</div>
              <div class="card-meta">已用额度：{{ formatAmount(lim.used_amount || lim.used) }}</div>
              <div class="card-meta">产品代码：{{ lim.product_code || '-' }}</div>
              <div class="card-meta">
                <span
                  class="status-badge"
                  :class="lim.status === 'ACTIVE' ? 'status-success' : 'status-muted'"
                >{{ lim.status || '有效' }}</span>
              </div>
            </article>
          </template>

          <!-- 贷款合同 -->
          <template v-if="loanContracts.length">
            <div class="section-label">贷款合同</div>
            <article
              v-for="loan in loanContracts"
              :key="loan.contract_no || loan.contract_id || loan.id"
              class="sidebar-card"
            >
              <div class="card-top">
                <div class="card-title">{{ loan.product_name || '贷款合同' }}</div>
                <div class="card-amount">{{ formatAmount(loan.principal_balance || loan.outstanding_amount || loan.principal) }}</div>
              </div>
              <div class="card-meta">合同号：{{ loan.contract_no || loan.contract_id || '-' }}</div>
              <div class="card-meta">借款金额：{{ formatAmount(loan.loan_amount || loan.principal) }}</div>
              <div class="card-meta">利率：{{ loan.interest_rate || '-' }} · 期限：{{ loan.term || loan.loan_term || '-' }}{{ loan.term_unit ? ' ' + loan.term_unit : '' }}</div>
              <div class="card-meta">放款日：{{ loan.disbursement_date || '-' }}</div>
              <div class="card-meta">到期日：{{ loan.maturity_date || loan.due_date || '-' }}</div>
              <div class="card-meta">
                <span
                  class="status-badge"
                  :class="(loan.status === 'NORMAL' || loan.status === 'normal' || loan.status === '正常') ? 'status-success'
                    : (loan.status === 'OVERDUE' || loan.status === 'overdue') ? 'status-danger' : 'status-info'"
                >{{ loan.status || '正常' }}</span>
              </div>
            </article>
          </template>
        </div>

        <!-- ── Tab: 还款账单 ──────────────────────────────────────── -->
        <div v-else-if="activeTab === 'repayments'" class="sidebar-list">
          <div v-if="!repaymentBills.length && !isLoadingSidebar" class="sidebar-empty">暂无还款账单</div>
          <article
            v-for="bill in repaymentBills"
            :key="bill.bill_no || bill.bill_id || bill.id"
            class="sidebar-card"
          >
            <div class="card-top">
              <div class="card-title">{{ bill.period || bill.term ? `第 ${bill.period || bill.term} 期` : (bill.bill_no ? '账单' : '还款账单') }}</div>
              <div class="card-amount">{{ formatAmount(bill.total_amount || bill.payable_amount) }}</div>
            </div>
            <div class="card-meta">账单号：{{ bill.bill_no || bill.bill_id || '-' }}</div>
            <div class="card-meta">本金：{{ formatAmount(bill.principal || bill.principal_amount) }} · 利息：{{ formatAmount(bill.interest || bill.interest_amount) }}</div>
            <div class="card-meta">应还日期：{{ bill.due_date || bill.repay_date || '-' }}</div>
            <div class="card-meta">合同号：{{ bill.contract_no || '-' }}</div>
            <div class="card-meta">
              <span
                class="status-badge"
                :class="(bill.status === 'PAID' || bill.status === 'paid' || bill.status === '已还')
                  ? 'status-success'
                  : (bill.status === 'OVERDUE' || bill.status === 'overdue' || bill.status === '逾期')
                    ? 'status-danger'
                    : (bill.status === 'PENDING' || bill.status === 'pending' || bill.status === '待还')
                      ? 'status-warning' : 'status-info'"
              >{{ bill.status || '待还款' }}</span>
            </div>
          </article>
        </div>

        <!-- ── Tab: 催收案件 ──────────────────────────────────────── -->
        <div v-else-if="activeTab === 'collections'" class="sidebar-list">
          <div v-if="!collectionCases.length && !isLoadingSidebar" class="sidebar-empty">暂无催收案件</div>
          <article
            v-for="c in collectionCases"
            :key="c.case_no || c.case_id || c.id"
            class="sidebar-card"
          >
            <div class="card-top">
              <div class="card-title">{{ c.case_name || '催收案件' }}</div>
              <div class="card-amount" style="color: #f53f3f;">{{ formatAmount(c.outstanding_amount || c.total_amount || c.owed_amount) }}</div>
            </div>
            <div class="card-meta">案件号：{{ c.case_no || c.case_id || '-' }}</div>
            <div class="card-meta">逾期本金：{{ formatAmount(c.overdue_principal || c.outstanding_principal) }}</div>
            <div class="card-meta">逾期天数：{{ c.overdue_days || c.dpd || '-' }} 天</div>
            <div class="card-meta">合同号：{{ c.contract_no || '-' }}</div>
            <div class="card-meta">立案时间：{{ c.create_time || c.created_at || '-' }}</div>
            <div class="card-meta">
              <span
                class="status-badge"
                :class="(c.status === 'PENDING' || c.status === '待处理') ? 'status-warning'
                  : (c.status === 'COLLECTING' || c.status === '催收中') ? 'status-info'
                  : (c.status === 'RESOLVED' || c.status === '已结清') ? 'status-success' : 'status-danger'"
              >{{ c.status || '待处理' }}</span>
            </div>
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
  /* Accent — teal (brand) */
  --color-accent: #14b8a6;
  --color-accent-strong: #0d9488;
  --color-accent-soft: rgba(20, 184, 166, 0.12);
  --color-accent-glow: rgba(20, 184, 166, 0.16);
  --color-accent-soft-bg: rgba(20, 184, 166, 0.06);
  /* Warm — amber (products/orders) */
  --color-warm: #f59e0b;
  --color-warm-strong: #d97706;
  --color-warm-soft: rgba(245, 158, 11, 0.12);
  --color-warm-glow: transparent;
  --color-warm-soft-bg: rgba(245, 158, 11, 0.06);
  /* Semantic */
  --color-success: #00b42a;
  --color-success-soft: rgba(0, 180, 42, 0.12);
  --color-info: #3b6ef5;
  --color-info-soft: rgba(59, 110, 245, 0.10);
  --color-danger: #f53f3f;
  --color-danger-soft: rgba(245, 63, 63, 0.10);
  /* Borders — subtle gray lines on light surfaces */
  --color-border: #e5e6eb;
  --color-border-light: #eef0f3;
  --color-border-strong: #d0d3d9;
  /* User bubble — light salmon (淘宝/京东风格) */
  --color-user-bubble-bg: #ffe9e3;
  --color-user-bubble-text: #5c2b22;
  --color-user-bubble-border: #ffd3c7;
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
.turn-label {
  display: none;
}

.turn-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 600;
}

/* 用户消息：头像在右侧（参考淘宝/京东客服页） */
.user-section .section-header {
  flex-direction: row-reverse;
}
.user-section .agent-info {
  align-items: flex-end;
  text-align: right;
}

/* 头像样式 */
.avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid var(--color-border);
  background: #f3f4f6;
  transition: all var(--duration-base) var(--ease-out-expo);
}

.user-avatar .avatar {
  border: 3px solid transparent;
  background: linear-gradient(#ffffff, #ffffff) padding-box,
              linear-gradient(135deg, var(--color-info), var(--color-accent)) border-box;
  box-shadow: 0 2px 14px var(--color-info-soft);
}

.service-avatar .avatar {
  border-color: var(--color-success);
  box-shadow: 0 2px 10px var(--color-success-soft);
}

.status-dot {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 12px;
  height: 12px;
  background: var(--color-success);
  border: 2px solid var(--color-surface);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.65;
    transform: scale(1.12);
  }
}

.agent-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.agent-label {
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.user-section .agent-name {
  color: var(--color-info);
}

.bot-section .agent-name {
  color: var(--color-success);
}

.role-icon {
  font-size: 16px;
}

.role-label {
  color: var(--color-text-secondary);
}

.user-section .role-label {
  color: var(--color-info);
}

.bot-section .role-label {
  color: var(--color-success);
}

.turn-bubble {
  padding: 8px 12px;
  border-radius: var(--radius-md);
  max-width: 100%;
}

.user-bubble {
  background: var(--color-user-bubble-bg);
  border: 1px solid var(--color-user-bubble-border);
  color: var(--color-user-bubble-text);
  box-shadow: var(--shadow-xs);
  margin-left: auto;
  max-width: 85%;
}

.bot-bubble {
  background: #ffffff;
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-xs);
  align-self: flex-start;
  max-width: 85%;
}

.bot-messages {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.turn-bubble p {
  margin: 0;
  font-size: 14.5px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.user-bubble p {
  color: var(--color-user-bubble-text);
}

/* 消息时间戳 */
.msg-time {
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.2;
  color: var(--color-text-muted);
  user-select: none;
}
.user-bubble .msg-time {
  text-align: right;
}
.bot-bubble .msg-time {
  text-align: left;
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
