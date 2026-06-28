"""APP 全局配置常量"""

# 数据库
DB_PATH = "app_data.db"

# 时段定义
PERIODS = ["morning", "afternoon", "evening"]

# 工作日默认 (1=周一, ..., 7=周日)
DEFAULT_WORK_DAYS = "1,2,3,4,5"

# 日切时间 (小时)
DAY_CUTOFF_HOUR = 4

# 旷工判定窗口
ABSENT_MORNING_HOURS = 1.0   # 上午: 比设定上班时间晚 1 小时
ABSENT_AFTERNOON_HOURS = 1.5  # 下午: 比设定上班时间晚 1.5 小时

# 男友承诺默认门槛 (小时)
DEFAULT_BOYFRIEND_HOUR_THRESHOLD = 8.0

# 周起始日 (周一)
WEEK_START_DAY = 0  # datetime.weekday() 中周一=0

# 出勤状态常量
STATUS_PENDING = "pending"
STATUS_NORMAL = "normal"
STATUS_LATE = "late"
STATUS_EARLY_LEAVE = "early_leave"
STATUS_ABSENT_MORNING = "absent_morning"
STATUS_ABSENT_AFTERNOON = "absent_afternoon"
STATUS_LEAVE = "leave"
STATUS_SHOOTING = "shooting"

# 账本类型
LEDGER_TYPE_LATE = "late"
LEDGER_TYPE_EARLY_LEAVE = "early_leave"
LEDGER_TYPE_ABSENT = "absent"
LEDGER_TYPE_FULL_ATTENDANCE_BONUS = "full_attendance_bonus"
LEDGER_TYPE_BOYFRIEND_PROMISE = "boyfriend_promise"
LEDGER_TYPE_BET_REWARD = "bet_reward"
LEDGER_TYPE_BET_PENALTY = "bet_penalty"
LEDGER_TYPE_BET_EXTRA = "bet_extra"
LEDGER_TYPE_BET_LATE_FEE = "bet_late_fee"
LEDGER_TYPE_SHOOTING_REWARD = "shooting_reward"

# 签退方式
CHECKOUT_TYPE_MANUAL = "manual"
CHECKOUT_TYPE_AUTO = "auto"
