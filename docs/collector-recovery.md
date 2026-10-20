# Collector network recovery / 采集器断网恢复

The outbound collector retries connection errors, timeouts and non-success HTTP statuses without requiring an interactive restart. Healthy polling remains `--interval 120`. Failure backoff grows exponentially but is capped by `--max-retry-delay 300` (default); up to 5 seconds of jitter and the bounded collection/request time are additional. A long outage therefore no longer stretches polling backoff to about 32 minutes. A successful upload resets the delay to the normal interval. Every attempt collects a new observation; outdated queued snapshots are not replayed.

Logs identify successful delivery or a bounded retry interval, never HTTP exception details, credentials or account IDs. `--once` exits nonzero on delivery failure. Use systemd `Restart=on-failure` for unexpected process exits; network-online.target alone is not a continuous connectivity test. Network or authentication failures are never fabricated into valid quota values.

故障测试须局限于采集进程，不能断开家庭网络或媒体服务。先建立独立自动恢复任务，再对该unit临时限制网络；恢复后等待同一个进程自动上传，而非靠人工重启冒充恢复。测试必须记录失败/恢复UTC时间、进程ID、成功上报，以及恢复后的unit配置。切勿改全局防火墙、路由或公开管理端口。完整主机断电、账号长期续期仍需另外验证。
