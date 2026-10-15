export const remaining = value => Number.isFinite(value) ? `${Math.max(0, Math.min(100, 100-value)).toFixed(0)}%` : '未知'
export const stamp = value => value ? new Date(value).toLocaleString() : '尚未采集'
export const windowLabel = minutes => minutes ? minutes >= 1440 ? `${(minutes/1440).toFixed(1)} 天窗口` : `${minutes/60} 小时窗口` : '窗口长度未知'
