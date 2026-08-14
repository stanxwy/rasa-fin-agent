/**
 * 业务领域配置
 * ======================================================
 * 所有 UI 上与业务相关的字词都集中在这里管理，便于以后替换到其他领域。
 * 如果要切换到新的行业（例如电商、教育、医疗等），只需要修改此文件，不用改 App.vue。
 * ======================================================
 */

/* ── 应用标题与客服信息 ─────────────────────────────── */
export const APP = {
  /** 顶部系统名称 */
  SYSTEM_NAME: '金融客服系统',
  /** 客服数字人配置 */
  AGENT: {
    name: '小谷',
    title: '金牌客服',
    /** 客服在线状态文本 */
    status: '在线',
  },
}

/* ── 欢迎页配置 ─────────────────────────────────────── */
export const WELCOME = {
  greeting: '你的专属金融客服，随时为你服务',
  /** 快捷提问 chips（6 个，建议不超过 10 字/条） */
  quickQuestions: [
    '查询账户余额',
    '查看交易流水',
    '理财产品推荐',
    '贷款申请进度',
    '还款计划查询',
    '催收案件详情',
  ],
  /** 功能特性标签（4 个，emoji + 文案） */
  features: [
    { icon: '💬', text: '文字对话' },
    { icon: '🔊', text: '语音播报' },
    { icon: '🏦', text: '账户查询' },
    { icon: '💰', text: '理财信贷' },
  ],
}

/* ── 业务对象 Panel（右侧 Tab） ─────────────────────── */
export const BUSINESS_PANEL = {
  /** Panel 标题 */
  title: '金融业务',
  /**
   * Tab 列表
   * key 必须与 App.vue 中 activeTab 的分支名一一对应（refeshObjects 也要用这个 key）
   * label 是展示文案，可以随便改（甚至改到电商领域：订单/商品/物流/退款）
   * refreshKey 传给 refreshObjects()，通常等于 key；也可单独配置
   */
  TABS: [
    { key: 'customer',      label: '客户',     refreshKey: 'customer' },
    { key: 'accounts',      label: '账户',     refreshKey: 'accounts' },
    { key: 'bankcards',     label: '银行卡',   refreshKey: 'bankcards' },
    { key: 'creditcards',   label: '信用卡',   refreshKey: 'creditcards' },
    { key: 'deposits',      label: '存款',     refreshKey: 'deposits' },
    { key: 'transactions',  label: '交易',     refreshKey: 'transactions' },
    { key: 'wealth',        label: '理财',     refreshKey: 'wealth' },
    { key: 'funds',         label: '基金',     refreshKey: 'funds' },
    { key: 'loans',         label: '信贷',     refreshKey: 'loans' },
    { key: 'repayments',    label: '还款',     refreshKey: 'repayments' },
    { key: 'overdues',      label: '逾期',     refreshKey: 'overdues' },
    { key: 'notifications', label: '通知',     refreshKey: 'notifications' },
  ],
  /**
   * 空状态提示（无数据时展示）
   * 键名 = tab key
   */
  EMPTY: {
    customer:      '暂无客户数据',
    accounts:      '暂无账户数据',
    bankcards:     '暂无银行卡',
    creditcards:   '暂无信用卡',
    deposits:      '暂无存款产品',
    transactions:  '暂无交易流水',
    wealth:        '暂无理财数据',
    funds:         '暂无基金产品',
    loans:         '暂无信贷数据',
    repayments:    '暂无还款账单',
    overdues:      '暂无逾期记录',
    notifications: '暂无通知消息',
  },
  /**
   * 分组标题（同一 Tab 内多分组时使用）
   */
  SECTIONS: {
    wealth: {
      positions: '我的持仓',
      products:  '在售理财',
    },
    loans: {
      limits:   '授信额度',
      products: '贷款产品',
    },
    funds: {
      products: '在售基金',
    },
    deposits: {
      products: '存款产品',
    },
  },
  /**
   * 卡片标题默认值（接口无返回数据时的兜底）
   */
  CARD_DEFAULTS: {
    customerTitle:     '客户信息',
    accountTitle:      '银行账户',
    bankCardTitle:     '银行卡',
    creditCardTitle:   '信用卡',
    depositTitle:      '存款产品',
    transactionTitle:  '交易',
    wealthPosition:    '理财产品',
    wealthProduct:     '理财产品',
    fundProduct:       '基金产品',
    loanLimit:         '授信额度',
    loanProduct:       '贷款产品',
    repaymentBill:     '还款账单',
    overdueRecord:     '逾期记录',
    notification:      '通知',
  },
}

/* ── 会话列表（左侧） ───────────────────────────────── */
export const SESSION_LIST = {
  title: '会话',
  empty: '暂无会话',
  defaultPreview: '新会话',
  newChat: '新对话',
  deleteConfirm: {
    message: '删除后不可恢复，确定删除该会话？',
    title:   '删除会话',
    confirm: '删除',
    cancel:  '取消',
  },
}

/* ── 通用 UI 按钮/提示文案 ─────────────────────────── */
export const UI = {
  sidebarErrorDefault: '加载业务对象失败。',
  sidebarChatHistoryLoadFail: '加载会话历史失败。',
  chatHistoryFailDefault: '加载历史消息失败。',
  sessionListFail: '加载会话列表失败。',
  deleteSessionFail: '删除会话失败。',
  requestFail: '请求失败。',
  senderIdRequired: '请先输入 sender_id。',
  resetSessionFail: '重置会话失败。',
  typingLabel: (agentName) => `${agentName}正在输入...`,
  sending: '发送中...',
  tts: {
    playing: '正在播放...',
    default: '语音播报',
  },
  copy: {
    done:  '已复制',
    title: '复制文字',
  },
  sendPlaceholder: '请输入您的问题...',
  send: '发送',
  /** 通用：客户状态默认值 */
  customerStatusDefault: '正常',
  /** 对象卡片徽标 */
  objectBadge: {
    order:   '订单对象',
    product: '商品对象',
  },
  /** 对象识别标签 */
  objectLabel: {
    orderId:   '订单号',
    productId: '商品号',
    genericId: '编号',
  },
}

/* ── 产品代码 → 中文名称映射字典 ─────────────────────
   （原写死在 App.vue 中的产品字典集中到这里，便于替换领域时删除或重写） */

/** 贷款产品：code → 中文名（36 个） */
export const LOAN_PRODUCT_NAMES = {
  'LOAN_CONSUMER_STD': '标准消费信用贷',
  'LOAN_CONSUMER_PLUS': '优享消费信用贷',
  'LOAN_CONSUMER_PAYROLL': '薪享消费贷',
  'LOAN_CONSUMER_GREEN': '绿色消费贷',
  'LOAN_CONSUMER_MEDICAL': '医疗消费信用贷',
  'LOAN_CONSUMER_TRAVEL': '文旅消费信用贷',
  'LOAN_CASH_FAST': '极速现金贷',
  'LOAN_CASH_SMALL': '小额周转现金贷',
  'LOAN_CASH_SALARY': '工资客户现金贷',
  'LOAN_CASH_DIGITAL': '线上现金贷',
  'LOAN_CASH_MICRO': '微额循环现金贷',
  'LOAN_CASH_APP': '移动端备用金',
  'LOAN_INSTALLMENT_EASY': '大额分期贷',
  'LOAN_INSTALLMENT_AUTO': '汽车消费分期贷',
  'LOAN_INSTALLMENT_HOME': '家装分期贷',
  'LOAN_INSTALLMENT_EDU': '教育分期贷',
  'LOAN_INSTALLMENT_DIGITAL': '数码产品分期贷',
  'LOAN_INSTALLMENT_APPLIANCE': '家电消费分期贷',
  'LOAN_BUSINESS_WORKING': '小微经营周转贷',
  'LOAN_BUSINESS_TAX': '税票经营贷',
  'LOAN_BUSINESS_MERCHANT': '商户经营贷',
  'LOAN_BUSINESS_SUPPLY': '供应链经营贷',
  'LOAN_BUSINESS_ECOM': '电商经营贷',
  'LOAN_BUSINESS_INVOICE': '发票经营贷',
  'LOAN_MORTGAGE_HOME': '房产抵押经营贷',
  'LOAN_MORTGAGE_SHOP': '商铺抵押贷',
  'LOAN_MORTGAGE_CAR': '车辆抵押贷',
  'LOAN_MORTGAGE_CERT': '存单质押贷',
  'LOAN_MORTGAGE_FACTORY': '厂房抵押经营贷',
  'LOAN_MORTGAGE_EQUIPMENT': '设备抵押经营贷',
  'LOAN_GUARANTEE_SME': '小微保证担保贷',
  'LOAN_GUARANTEE_PERSONAL': '个人保证担保贷',
  'LOAN_GUARANTEE_POLICY': '保单保证贷',
  'LOAN_GUARANTEE_GROUP': '集团保证经营贷',
  'LOAN_GUARANTEE_SUPPLIER': '供应商保证贷',
  'LOAN_GUARANTEE_FAMILY': '家庭保证消费贷',
}

/** 理财产品：WM_CASH_xx 精确映射；其它前缀按格式自动生成中文名称 */
export const WEALTH_PRODUCT_NAMES = {
  'WM_CASH_01': '中州现金管理01号', 'WM_CASH_02': '中州现金管理02号',
  'WM_CASH_03': '中州现金管理03号', 'WM_CASH_04': '中州现金管理04号',
  'WM_CASH_05': '中州现金管理05号', 'WM_CASH_06': '中州现金管理06号',
  'WM_CASH_07': '中州现金管理07号', 'WM_CASH_08': '中州现金管理08号',
  'WM_CASH_09': '中州现金管理09号', 'WM_CASH_10': '中州现金管理10号',
  'WM_CASH_11': '中州现金管理11号', 'WM_CASH_12': '中州现金管理12号',
  'WM_CASH_13': '中州现金管理13号', 'WM_CASH_14': '中州现金管理14号',
  'WM_CASH_15': '中州现金管理15号', 'WM_CASH_16': '中州现金管理16号',
  'WM_CASH_17': '中州现金管理17号', 'WM_CASH_18': '中州现金管理18号',
  'WM_CASH_19': '中州现金管理19号', 'WM_CASH_20': '中州现金管理20号',
}

/** 账户产品：code → 中文名（18 个） */
export const ACCOUNT_PRODUCT_NAMES = {
  'ACC_DEMAND_CNY': '人民币活期结算账户',
  'ACC_SETTLE_USD': '美元结算账户',
  'ACC_SETTLE_HKD': '港币结算账户',
  'ACC_LOAN_REPAY_CNY': '贷款还款专用账户',
  'ACC_WEALTH_CNY': '理财资金账户',
  'ACC_PAYROLL_CNY': '工资代发账户',
  'ACC_BUSINESS_CNY': '企业结算账户',
  'ACC_MERCHANT_CNY': '商户收单结算账户',
  'ACC_VIRTUAL_CNY': '线上虚拟结算账户',
  'ACC_ESCROW_CNY': '担保支付监管账户',
  'ACC_WEALTH_USD': '美元理财资金账户',
  'ACC_BUSINESS_USD': '美元企业结算账户',
  'ACC_SETTLE_EUR': '欧元结算账户',
  'ACC_SETTLE_GBP': '英镑结算账户',
  'ACC_SETTLE_JPY': '日元结算账户',
  'ACC_LOAN_REPAY_USD': '美元贷款还款账户',
  'ACC_API_SETTLE_CNY': '开放银行结算账户',
  'ACC_CROSS_BORDER_CNY': '跨境结算账户',
}

/** 产品分类代码 → 中文名 */
export const CATEGORY_NAMES = {
  'ACCOUNT_DEMAND': '活期结算账户', 'ACCOUNT_LOAN_REPAY': '贷款还款账户',
  'ACCOUNT_WEALTH': '理财资金账户',
  'LOAN_CONSUMER': '消费贷款', 'LOAN_CASH': '现金贷款',
  'LOAN_INSTALLMENT': '分期贷款', 'LOAN_BUSINESS': '经营贷款',
  'LOAN_MORTGAGE': '抵押贷款', 'LOAN_GUARANTEE': '担保贷款',
  'WEALTH_CASH': '现金管理', 'WEALTH_FIXED': '固定收益',
  'WEALTH_MIXED': '混合策略', 'WEALTH_EQUITY': '权益策略',
  'WEALTH_STRUCTURED': '结构性存款',
  'SERVICE_ACCOUNT': '账户服务', 'SERVICE_TRANSACTION': '交易服务',
  'SERVICE_WEALTH': '理财服务', 'SERVICE_LOAN': '贷款服务',
  'SERVICE_SUPPORT': '客服服务',
}

/** 币种代码 → 中文名 */
export const CURRENCY_NAMES = {
  CNY: '人民币', USD: '美元', HKD: '港币', EUR: '欧元', GBP: '英镑', JPY: '日元',
}

/** 币种代码 → 货币符号 */
export const CURRENCY_SYMBOLS = {
  CNY: '￥', USD: '$', HKD: 'HK$', EUR: '€', GBP: '£', JPY: '¥',
}

/** 风险等级代码 → 中文名 */
export const RISK_NAMES = {
  C1: '保守型', C2: '稳健型', C3: '平衡型', C4: '成长型', C5: '进取型',
  P1: '低风险', P2: '中低风险', P3: '中风险', P4: '中高风险', P5: '高风险',
  E1: '提示', E2: '关注', E3: '可疑', E4: '高危', E5: '阻断',
}

/** 客户类型 → 中文名 */
export const CUSTOMER_TYPE_NAMES = {
  personal: '个人客户', enterprise: '企业客户', individual: '个人客户',
}

/** 理财产品销售状态 → 中文名 */
export const OPEN_STATUS_NAMES = {
  selling: '在售中', closed: '已停售', pending: '募集中', redeemed: '已兑付',
}

/** 还款方式 → 中文名 */
export const REPAYMENT_METHOD_NAMES = {
  equal_principal_interest: '等额本息',
  equal_principal: '等额本金',
  interest_first: '先息后本',
  one_time: '到期一次性还本付息',
}

/** 理财产品运作方式 → 中文名 */
export const WEALTH_OPERATION_NAMES = {
  open: '开放型', closed: '封闭型', periodic_open: '定期开放型',
}

/** 理财产品类型 → 中文名 */
export const WEALTH_TYPE_NAMES = {
  cash_management: '现金管理类', fixed_income: '固定收益类',
  mixed: '混合类', equity: '权益类', structured_deposit: '结构性存款',
}

/** 通知类型 → 中文名 */
export const NOTIFICATION_TYPE_NAMES = {
  sms: '短信', app_push: 'APP推送', wechat: '微信', in_app: '站内信',
  transaction_alert: '交易提醒', marketing: '营销通知', system: '系统通知',
}

/** 通知发送状态 → 中文名 */
export const SEND_STATUS_NAMES = {
  pending: '待发送', sent: '已发送', failed: '发送失败', read: '已读',
}

/** 催收状态 → 中文名 */
export const COLLECTION_STATUS_NAMES = {
  pending: '待催收', in_collection: '催收中', resolved: '已结清', cancelled: '已撤销',
}

/** 还款账单状态 → 中文名 */
export const BILL_STATUS_NAMES = {
  pending: '待还款', paid: '已结清', overdue: '已逾期', partial: '部分还款', settled: '已结清',
}

/** 逾期状态 → 中文名 */
export const OVERDUE_STATUS_NAMES = {
  new: '新建', monitoring: '关注中', collection: '催收中', settled: '已结清',
}

/** 交易类型 → 中文名 */
export const TRANSACTION_TYPE_NAMES = {
  transfer: '转账',
  consume: '消费',
  deposit: '存款',
  withdraw: '取款',
  refund: '退款',
  adjustment: '调账',
  adjustment_credit: '调账-贷',
  wealth_purchase: '理财申购',
  wealth_redeem: '理财赎回',
  wealth_income: '理财收益',
  loan_disbursement: '贷款放款',
  loan_repayment: '贷款还款',
  income_settle: '收益结算',
  collateral_disposal: '抵押物处置',
  payment: '支付',
}

/** 业务对象类型 → 徽标中文名 */
export const OBJECT_BADGE_NAMES = {
  order: '订单对象',
  product: '商品对象',
  bank_account: '银行账户',
  bank_card: '银行卡',
  credit_card: '信用卡',
  deposit: '存款',
  loan: '贷款',
  wealth_product: '理财产品',
  fund_product: '基金产品',
  transaction: '交易流水',
  transfer: '转账记录',
}
